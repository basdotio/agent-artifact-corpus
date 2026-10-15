// Build a tailored resume + cover letter (DOCX) from a content.js module.
// Usage: node scripts/build.js <path-to-content.js> <output-dir>
// Requires: npm install docx
// Output filenames are derived from the content file's `name` field.
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, AlignmentType, BorderStyle,
  TabStopType, Tab, Table, TableRow, TableCell, WidthType,
} = require("docx");

const C = require(path.resolve(process.argv[2]));   // content.js
const OUT = path.resolve(process.argv[3] || ".");
const SLUG = C.slug || "Tailored";
const ACCENT = C.accent || "1F4E79";                // hex, no leading '#'
const NAME = C.name || "Resume";
const NAME_SLUG = NAME.replace(/[^A-Za-z0-9]+/g, "_").replace(/^_+|_+$/g, "") || "Resume";
const LETTER = { width: 12240, height: 15840 };
const CW = 9360;

const rule = (c, s = 6) => ({ bottom: { color: c, space: 2, style: BorderStyle.SINGLE, size: s } });
const nb = () => { const n = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
  return { top: n, bottom: n, left: n, right: n, insideHorizontal: n, insideVertical: n }; };
const sh = (t) => new Paragraph({ spacing: { before: 140, after: 60 }, border: rule(ACCENT),
  children: [new TextRun({ text: t, bold: true, size: 22, color: ACCENT, allCaps: true })] });
const bullet = (t, sz = 18) => new Paragraph({ spacing: { after: 12 }, indent: { left: 245, hanging: 173 },
  children: [new TextRun({ text: "•  ", size: sz, color: ACCENT }), new TextRun({ text: t, size: sz, color: "222222" })] });

function roleBlock(j) {
  const out = [];
  out.push(new Paragraph({ tabStops: [{ type: TabStopType.RIGHT, position: CW }], spacing: { before: 90, after: 6 }, children: [
    new TextRun({ text: j.role, bold: true, size: 21, color: ACCENT }),
    new TextRun({ children: [new Tab(), j.dates], size: 18, color: "595959" }),
  ] }));
  out.push(new Paragraph({ spacing: { after: 6 }, children: [
    new TextRun({ text: j.org, bold: true, size: 19, color: "333333" }),
    new TextRun({ text: `   ${j.loc}`, italics: true, size: 18, color: "808080" }),
  ] }));
  if (j.scope) out.push(new Paragraph({ spacing: { after: 12 }, children: [new TextRun({ text: j.scope, italics: true, size: 18, color: "555555" })] }));
  (j.bullets || []).forEach(b => out.push(bullet(b)));
  return out;
}
function compTable(items) {
  const rows = [];
  for (let i = 0; i < items.length; i += 2) {
    const cells = [items[i], items[i + 1] || ""].map(t => new TableCell({
      width: { size: CW / 2, type: WidthType.DXA }, borders: nb(), margins: { top: 16, bottom: 16, left: 0, right: 120 },
      children: [new Paragraph({ children: t ? [new TextRun({ text: "•  ", bold: true, color: ACCENT, size: 19 }), new TextRun({ text: t, size: 18, color: "222222" })] : [] })],
    }));
    rows.push(new TableRow({ children: cells }));
  }
  return new Table({ width: { size: CW, type: WidthType.DXA }, columnWidths: [CW / 2, CW / 2], borders: nb(), rows });
}

// ---------- RESUME ----------
const k = [];
k.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 18 }, children: [new TextRun({ text: C.name, bold: true, size: 40, color: ACCENT })] }));
k.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 50 }, children: [new TextRun({ text: C.title, size: 20, color: "333333" })] }));
k.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 54 }, children: [new TextRun({ text: C.contact, size: 18, color: "595959" })] }));
k.push(sh("Summary"));
k.push(new Paragraph({ spacing: { after: 24 }, children: [new TextRun({ text: C.summary, size: 18, color: "222222" })] }));
k.push(sh("Core Competencies"));
k.push(compTable(C.competencies));
k.push(sh("Professional Experience"));
C.experience.forEach(j => roleBlock(j).forEach(p => k.push(p)));
if (C.venture) { k.push(sh(C.ventureHeading || "Independent / Projects")); roleBlock(C.venture).forEach(p => k.push(p)); }
if (C.toolkit && C.toolkit.length) {
  k.push(sh(C.toolkitHeading || "Technical Toolkit"));
  C.toolkit.forEach(t => k.push(new Paragraph({ spacing: { after: 12 }, children: [
    new TextRun({ text: `${t.k}:  `, bold: true, size: 18, color: "333333" }),
    new TextRun({ text: t.v, size: 18, color: "222222" }) ] })));
}
k.push(sh("Education & Certifications"));
k.push(new Paragraph({ spacing: { after: 14 }, children: [new TextRun({ text: (C.education || []).join("      "), size: 18, color: "222222" })] }));
if (C.certs && C.certs.length) k.push(new Paragraph({ children: [
  new TextRun({ text: "Certifications:  ", bold: true, size: 18, color: "333333" }),
  new TextRun({ text: C.certs.join("   ·   "), size: 18, color: "222222" }) ] }));

const resume = new Document({ styles: { default: { document: { run: { font: C.font || "Calibri", size: 18 } } } },
  sections: [{ properties: { page: { size: LETTER, margin: { top: 648, bottom: 648, left: 1440, right: 1440 } } }, children: k }] });
Packer.toBuffer(resume).then(b => { const f = path.join(OUT, `${NAME_SLUG}_${SLUG}_Resume.docx`); fs.writeFileSync(f, b); console.log("wrote", f); });

// ---------- COVER ----------
if (C.coverParas && C.coverParas.length) {
  const c = [];
  c.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 10 }, children: [new TextRun({ text: C.name, bold: true, size: 36, color: ACCENT })] }));
  c.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 40 }, border: { bottom: { color: ACCENT, space: 4, style: BorderStyle.SINGLE, size: 6 } },
    children: [new TextRun({ text: C.coverTitle || C.title, size: 18, color: "333333" })] }));
  c.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 200 }, children: [new TextRun({ text: C.contact, size: 18, color: "595959" })] }));
  if (C.coverDate) c.push(new Paragraph({ spacing: { after: 200 }, children: [new TextRun({ text: C.coverDate, size: 21, color: "222222" })] }));
  C.coverParas.forEach(p => c.push(new Paragraph({ spacing: { after: 160 }, children: [new TextRun({ text: p, size: 21, color: "222222" })] })));
  c.push(new Paragraph({ spacing: { before: 60 }, children: [new TextRun({ text: C.coverSignOff || "Regards,", size: 21, color: "222222" })] }));
  c.push(new Paragraph({ spacing: { before: 20 }, children: [new TextRun({ text: C.name, bold: true, size: 21, color: "222222" })] }));
  const cover = new Document({ styles: { default: { document: { run: { font: C.font || "Calibri", size: 21 } } } },
    sections: [{ properties: { page: { size: LETTER, margin: { top: 1440, bottom: 1440, left: 1440, right: 1440 } } }, children: c }] });
  Packer.toBuffer(cover).then(b => { const f = path.join(OUT, `${NAME_SLUG}_${SLUG}_CoverLetter.docx`); fs.writeFileSync(f, b); console.log("wrote", f); });
}
