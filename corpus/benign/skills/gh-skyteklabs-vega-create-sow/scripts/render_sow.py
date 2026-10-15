# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "docxtpl>=0.18",
#   "jsonschema>=4.21",
#   "python-docx>=1.1",
#   "docx2pdf>=0.1.8; sys_platform == 'darwin' or sys_platform == 'win32'",
# ]
# ///
"""Render a SOW: validate the data, fill the Word template, convert to PDF.

    uv run render_sow.py --data SOW.json [--template T.docx] [--out-dir DIR] [--no-pdf]
    uv run render_sow.py --check-template [--template T.docx]
    uv run render_sow.py --convert SOW.docx

Prints one JSON object: {"docx", "pdf", "data", "pdf_error"}.
Exit codes: 0 docx and pdf written; 2 invalid data or template;
3 docx written but no PDF converter was found or it failed.
"""

import argparse
import copy
import datetime as dt
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from docx.image.image import Image as DocxImage
from docx.shared import Inches
from docxtpl import DocxTemplate, InlineImage, Listing
from jinja2 import Environment, StrictUndefined
from jsonschema import Draft202012Validator

SKILL_DIR = Path(__file__).resolve().parent.parent
DEFAULT_TEMPLATE = SKILL_DIR / "assets" / "sow-template.docx"
SCHEMA_PATH = SKILL_DIR / "assets" / "sow.schema.json"

# Template variables computed here rather than supplied in the data.
COMPUTED = {"subtotal", "total_fees", "total_mandays", "client_logo"}
# Schema properties that never reach the template.
HIDDEN = {"_sources"}

PRICING_LABELS = {
    "fixed_price": "Fixed price",
    "time_and_materials": "Time and materials",
    "retainer": "Retainer",
}
ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SOFFICE_PATHS = [
    "/Applications/LibreOffice.app/Contents/MacOS/soffice",
    "C:/Program Files/LibreOffice/program/soffice.exe",
]
WORD_PATHS = ["/Applications/Microsoft Word.app"]


class SowError(Exception):
    pass


def load_schema():
    return json.loads(SCHEMA_PATH.read_text())


def template_fields(schema):
    return (set(schema["properties"]) - HIDDEN) | COMPUTED


def validate(data, schema):
    errors = sorted(Draft202012Validator(schema).iter_errors(data), key=lambda e: list(e.path))
    if errors:
        lines = [f"{'.'.join(map(str, e.path)) or '(root)'}: {e.message}" for e in errors]
        raise SowError("invalid SOW data:\n  " + "\n  ".join(lines))
    total = pricing(data)["total"]
    if total < 0:
        raise SowError("invalid SOW data:\n  fees: the total is negative")
    scheduled = sum(p["amount"] for p in data["payment_schedule"])
    if round(scheduled - total, 2) != 0:
        raise SowError(
            "invalid SOW data:\n  payment_schedule: amounts sum to "
            f"{scheduled:,.2f}, total cost is {total:,.2f}"
        )
    if data.get("client_logo_path"):
        path = Path(data["client_logo_path"])
        if not path.is_file():
            raise SowError(f"invalid SOW data:\n  client_logo_path: no such file: {path}")
        try:
            DocxImage.from_file(str(path))
        except Exception as e:
            raise SowError(f"invalid SOW data:\n  client_logo_path: not a readable image ({e})") from e


def pricing(data):
    """Line amounts for the package items or effort, then subtotal, total and total mandays."""
    if data["project_type"] == "package":
        lines = [i["quantity"] * i["unit_price"] for i in data["package_items"]]
        mandays = 0
    else:
        lines = [e["mandays"] * e["day_rate"] for e in data["effort"]]
        mandays = sum(e["mandays"] for e in data["effort"])
    subtotal = sum(lines)
    total = subtotal + sum(f["amount"] for f in data.get("fees", []))
    return {"lines": lines, "subtotal": subtotal, "total": total, "mandays": mandays}


def check_template(template, schema):
    """The template's variables must be exactly the schema's fields plus COMPUTED."""
    env = Environment(undefined=StrictUndefined)
    used = DocxTemplate(str(template)).get_undeclared_template_variables(env)
    expected = template_fields(schema)
    missing, unknown = expected - used, used - expected
    problems = []
    if unknown:
        problems.append(f"template uses fields the schema lacks: {sorted(unknown)}")
    if missing:
        problems.append(f"schema fields the template never shows: {sorted(missing)}")
    if problems:
        raise SowError("; ".join(problems))


def fmt_date(value):
    if isinstance(value, str) and ISO_DATE.match(value):
        try:
            d = dt.date.fromisoformat(value)
        except ValueError as e:
            raise SowError(f"invalid SOW data:\n  {value}: not a real calendar date") from e
        return f"{d.day} {d.strftime('%B %Y')}"
    return value


def fmt_number(value):
    """10 -> '10', 2.5 -> '2.5', 1200 -> '1,200'."""
    return f"{value:,.0f}" if value == int(value) else f"{value:,}"


def fmt_money(amount, currency):
    if amount < 0:
        return f"({currency} {-amount:,.2f})"
    return f"{currency} {amount:,.2f}"


def display(value):
    """ISO dates become '9 October 2026'; text with line breaks keeps them."""
    if isinstance(value, dict):
        return {k: display(v) for k, v in value.items()}
    if isinstance(value, list):
        return [display(v) for v in value]
    if isinstance(value, str):
        value = fmt_date(value)
        return Listing(value) if "\n" in value else value
    return value


def build_context(data, schema, tpl):
    ctx = copy.deepcopy(data)
    for name, prop in schema["properties"].items():
        if name not in ctx:
            ctx[name] = copy.deepcopy(prop.get("default", [] if prop.get("type") == "array" else ""))
    for name in HIDDEN:
        ctx.pop(name, None)
    if ctx.get("client_logo_path"):
        ctx["client_logo"] = InlineImage(tpl, ctx["client_logo_path"], width=Inches(2.2))
    for d in ctx["deliverables"]:
        d.setdefault("format", "Document")
    for p in ctx["payment_schedule"]:
        p.setdefault("deliverables", "")
    currency = ctx["currency"]
    totals = pricing(data)
    lines = ctx["package_items"] if ctx["project_type"] == "package" else ctx["effort"]
    for row, amount in zip(lines, totals["lines"]):
        row["amount"] = amount
    for row in ctx["package_items"]:
        row.setdefault("description", "")
        row["quantity"] = fmt_number(row["quantity"])
        row["unit_price"] = fmt_money(row["unit_price"], currency)
    for row in ctx["effort"]:
        row["mandays"] = fmt_number(row["mandays"])
        row["day_rate"] = fmt_money(row["day_rate"], currency)
    for row in lines + ctx["fees"] + ctx["payment_schedule"]:
        row["amount"] = fmt_money(row["amount"], currency)
    ctx["pricing_model"] = PRICING_LABELS[ctx["pricing_model"]]
    ctx = display(ctx)
    ctx["subtotal"] = fmt_money(totals["subtotal"], currency)
    ctx["total_fees"] = fmt_money(totals["total"], currency)
    ctx["total_mandays"] = fmt_number(totals["mandays"])
    return ctx


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40] or "untitled"


def next_base(out_dir, data):
    stem = f"SOW_{slug(data['client_name'])}_{slug(data['project_title'])}_{data['sow_date']}"
    taken = [
        int(m.group(1))
        for p in out_dir.glob(f"{stem}_v*")
        if (m := re.match(re.escape(stem) + r"_v(\d+)\.", p.name))
    ]
    return out_dir / f"{stem}_v{max(taken, default=0) + 1}"


def find_soffice():
    for name in ("soffice", "libreoffice"):
        if found := shutil.which(name):
            return found
    return next((p for p in SOFFICE_PATHS if Path(p).exists()), None)


def to_pdf(docx_path):
    """Convert with LibreOffice, else MS Word via docx2pdf. Returns (pdf path, error)."""
    pdf_path = docx_path.with_suffix(".pdf")
    soffice = find_soffice()
    if soffice:
        # A throwaway profile, so a LibreOffice window the user has open can't block us.
        with tempfile.TemporaryDirectory() as profile:
            try:
                subprocess.run(
                    [
                        soffice,
                        f"-env:UserInstallation={Path(profile).as_uri()}",
                        "--headless",
                        "--convert-to",
                        "pdf",
                        "--outdir",
                        str(docx_path.parent),
                        str(docx_path),
                    ],
                    check=True,
                    capture_output=True,
                    timeout=180,
                )
            except (subprocess.SubprocessError, OSError) as e:
                return None, f"LibreOffice conversion failed: {e}"
        if pdf_path.exists():
            return pdf_path, None
        return None, "LibreOffice ran but wrote no PDF"
    if any(Path(p).exists() for p in WORD_PATHS) or sys.platform == "win32":
        try:
            from docx2pdf import convert

            convert(str(docx_path), str(pdf_path))
        except Exception as e:  # docx2pdf surfaces Word automation errors as anything
            return None, f"Word conversion failed: {e}"
        if pdf_path.exists():
            return pdf_path, None
        return None, "Word ran but wrote no PDF"
    return None, (
        "no PDF converter found: install LibreOffice "
        "(macOS: brew install --cask libreoffice) or Microsoft Word, "
        "or export the .docx to PDF by hand"
    )


def render(data_path, template, out_dir, want_pdf=True):
    schema = load_schema()
    data = json.loads(Path(data_path).read_text())
    validate(data, schema)
    check_template(template, schema)

    out_dir.mkdir(parents=True, exist_ok=True)
    base = next_base(out_dir, data)
    docx_path = base.with_suffix(".docx")
    data_copy = base.with_suffix(".sow.json")

    tpl = DocxTemplate(str(template))
    tpl.render(
        build_context(data, schema, tpl),
        jinja_env=Environment(undefined=StrictUndefined),
        autoescape=True,
    )
    tpl.save(str(docx_path))
    data_copy.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")

    pdf_path, pdf_error = to_pdf(docx_path) if want_pdf else (None, "skipped (--no-pdf)")
    return {
        "docx": str(docx_path),
        "pdf": str(pdf_path) if pdf_path else None,
        "data": str(data_copy),
        "pdf_error": pdf_error,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--data", type=Path)
    parser.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE)
    parser.add_argument("--out-dir", type=Path, default=Path("sow"))
    parser.add_argument("--no-pdf", action="store_true")
    parser.add_argument("--check-template", action="store_true")
    parser.add_argument("--convert", type=Path, metavar="DOCX", help="only convert this .docx to PDF")
    args = parser.parse_args()

    try:
        if args.check_template:
            check_template(args.template, load_schema())
            print(json.dumps({"template": str(args.template), "ok": True}))
            return 0
        if args.convert:
            if not args.convert.exists():
                raise FileNotFoundError(args.convert)
            pdf_path, pdf_error = to_pdf(args.convert.resolve())
            print(json.dumps({"pdf": str(pdf_path) if pdf_path else None, "pdf_error": pdf_error}))
            return 0 if pdf_path else 3
        if not args.data:
            parser.error("--data is required")
        result = render(args.data, args.template, args.out_dir, want_pdf=not args.no_pdf)
    except (SowError, json.JSONDecodeError, FileNotFoundError) as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        return 2
    except Exception as e:  # anything else is a bad data file or template, not a crash to hand the user
        print(json.dumps({"error": f"{type(e).__name__}: {e}"}), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    return 0 if result["pdf"] or args.no_pdf else 3


if __name__ == "__main__":
    sys.exit(main())
