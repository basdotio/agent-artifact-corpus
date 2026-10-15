#!/usr/bin/env python3
"""Audit a sending domain's email DNS, and say what to change.

Run this BEFORE opening the registrar, so you arrive knowing exactly which records are
wrong, and again afterwards to prove the edit landed.

    dns_check.py newdomain.com
    dns_check.py newdomain.com --json
    dns_check.py newdomain.com --selector mySelector
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import subprocess
import urllib.error
import urllib.parse
import urllib.request

# Selectors worth probing blind. DKIM has no discovery mechanism, so a missing key here
# means "not found at the usual names", never "not configured" - the provider console is
# the only authority.
SELECTORS = ("google", "selector1", "selector2", "default", "k1", "k2", "s1", "s2",
             "mail", "dkim", "zoho", "fm1", "mandrill", "pm", "sendgrid", "mailjet")

MX_PROVIDERS = {
    "google": "Google Workspace", "outlook": "Microsoft 365", "protection.outlook": "Microsoft 365",
    "zoho": "Zoho", "mailgun": "Mailgun", "sendgrid": "SendGrid", "improvmx": "ImprovMX",
    "secureserver": "GoDaddy email", "messagingengine": "Fastmail", "icloud": "iCloud",
}


# Windows has no `dig`, and the audit is the first thing this skill runs - so a missing
# binary took the whole thing down before it could say anything useful. DNS-over-HTTPS needs
# nothing but urllib, works identically everywhere, and doubles as the fallback when dig is
# present but the local resolver is lying.
DOH_ENDPOINTS = ("https://cloudflare-dns.com/dns-query", "https://dns.google/resolve")
FORCE_DOH = os.environ.get("EMAILWARM_FORCE_DOH") == "1"


def _dig_binary(name: str, rtype: str) -> list[str] | None:
    """Query with the dig binary. None means dig is unavailable, [] means no records."""
    if FORCE_DOH or shutil.which("dig") is None:
        return None
    try:
        out = subprocess.run(["dig", "+short", rtype, name],
                             capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if out.returncode == 0:
        RESOLVER_OK["answered"] = True
    return [ln.strip().strip('"').replace('" "', "") for ln in out.stdout.splitlines() if ln.strip()]


RESOLVER_OK = {"answered": False}


def _doh(name: str, rtype: str) -> tuple[list[str], int | None]:
    """Query over HTTPS. Returns (answers, rcode); rcode 3 is NXDOMAIN."""
    for base in DOH_ENDPOINTS:
        url = f"{base}?name={urllib.parse.quote(name)}&type={urllib.parse.quote(rtype)}"
        req = urllib.request.Request(url, headers={"Accept": "application/dns-json",
                                                   "User-Agent": "emailwarm/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception:  # noqa: BLE001 - try the next resolver rather than dying
            continue
        RESOLVER_OK["answered"] = True
        answers = []
        for a in data.get("Answer", []) or []:
            v = str(a.get("data", "")).strip()
            if not v:
                continue
            # DoH returns TXT already quoted, and long records split into several strings.
            if v.startswith('"') and v.endswith('"'):
                v = v[1:-1].replace('" "', "")
            answers.append(v)
        return answers, data.get("Status")
    return [], None


def dig(name: str, rtype: str = "TXT") -> list[str]:
    """One DNS lookup, however this machine can manage it."""
    vals = _dig_binary(name, rtype)
    if vals is not None:
        return vals
    return _doh(name, rtype)[0]


def _real_key(values: list[str]) -> str | None:
    """A DKIM record with a usable public key, not a revoked or empty one.

    An empty p= is a revocation, so treating any "p=" as a key reports a domain that has
    switched DKIM OFF as correctly configured.
    """
    for v in values:
        low = v.lower()
        if "v=dkim1" not in low and "k=rsa" not in low:
            continue
        key = low.split("p=", 1)[1].strip().strip(';').strip() if "p=" in low else ""
        if len(key) > 40:
            return v
    return None


def serves_a_website(domain: str) -> bool:
    """Does anything answer on https://<domain>?

    Asked on every run rather than left to the operator to remember, because the answer
    changes the advice completely: a domain carrying a live site is a brand asset, and cold
    outreach should never go out from it. A blacklisted sending domain costs a registration
    to replace; a blacklisted brand domain takes the site's mail with it.
    """
    req = urllib.request.Request(
        f"https://{domain}/", method="GET",
        headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                               "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return 200 <= resp.status < 400
    except urllib.error.HTTPError as exc:
        return exc.code < 500  # a 403 or 404 still means something is serving this name
    except Exception:  # noqa: BLE001
        return False


def resolves(domain: str) -> bool:
    """Does this name exist at all? NXDOMAIN means the advice below is meaningless.

    Without this the audit happily reports "no SPF, no DMARC, no DKIM - fix these" for a
    domain nobody has registered, which sends someone hunting through a DNS panel for a zone
    that does not exist.
    """
    if not FORCE_DOH and shutil.which("dig"):
        try:
            out = subprocess.run(["dig", "+noall", "+comment", domain, "SOA"],
                                 capture_output=True, text=True, timeout=20).stdout
            return "NXDOMAIN" not in out
        except (OSError, subprocess.TimeoutExpired):
            pass
    _, status = _doh(domain, "SOA")
    # Status 3 is NXDOMAIN. A resolver we could not reach at all returns None, and an
    # unreachable resolver is not evidence the domain is missing.
    return status != 3


def audit(domain: str, extra_selector: str | None = None) -> dict:
    if not resolves(domain):
        return {"domain": domain, "exists": False, "spf": [], "dmarc": [], "dkim": {}, "mx": [],
                "nameservers": [], "dns_host": None, "serves_website": False,
                "mail_provider": None, "ready": False, "warnings": [],
                "problems": [f"{domain} does not resolve at all (NXDOMAIN). Check the spelling, "
                             "and check the domain is actually registered and its nameservers "
                             "are set, before trying to fix records on it."]}
    # Where the records actually live. A domain's registrar is often NOT its DNS host, and
    # editing at the registrar then changes nothing at all - the edit lands in a zone nobody
    # is serving. Check before sending anyone to a control panel.
    ns = dig(domain, "NS")
    dns_host = None
    for key, label in (("cloudflare", "Cloudflare"), ("godaddy", "GoDaddy"),
                       ("domaincontrol", "GoDaddy"), ("namecheap", "Namecheap"),
                       ("registrar-servers", "Namecheap"), ("google", "Google"),
                       ("awsdns", "Route 53"), ("ionos", "IONOS"), ("ui-dns", "IONOS"),
                       ("123-reg", "123-reg"), ("squarespace", "Squarespace")):
        if any(key in n.lower() for n in ns):
            dns_host = label
            break

    spf = [v for v in dig(domain) if v.lower().startswith("v=spf1")]
    dmarc = [v for v in dig(f"_dmarc.{domain}") if v.lower().startswith("v=dmarc1")]
    mx = dig(domain, "MX")

    # A wildcard TXT record answers every selector, so probe a name nobody would configure
    # first. example.com does exactly this, publishing "v=DKIM1; p=" (an empty key means
    # REVOKED under RFC 6376) at every selector, which reads as "DKIM everywhere" to a naive
    # probe and is the opposite of the truth.
    wildcard = bool(_real_key(dig(f"zzq7x-nonsense-probe._domainkey.{domain}")))

    selectors = list(SELECTORS)
    if extra_selector:
        selectors.insert(0, extra_selector)
    dkim = {}
    if not wildcard:
        for s in selectors:
            found = _real_key(dig(f"{s}._domainkey.{domain}"))
            if found:
                dkim[s] = found[:80] + ("..." if len(found) > 80 else "")

    provider = next((label for key, label in MX_PROVIDERS.items()
                     if any(key in m.lower() for m in mx)), None)

    problems, warnings = [], []

    if not spf:
        problems.append("No SPF record. Mail from this domain has nothing authorising it.")
    elif len(spf) > 1:
        problems.append(f"{len(spf)} SPF records. More than one is a permerror and fails every "
                        "check - merge them into a single record.")
    else:
        if " ~all" in spf[0]:
            warnings.append("SPF ends in ~all (soft fail). Prefer -all on a domain whose job is "
                            "to be trusted by strangers.")
        elif " -all" not in spf[0]:
            warnings.append("SPF has no all mechanism, so nothing is actually rejected.")

    if not dmarc:
        problems.append("No DMARC record. Start at p=none with a rua address so you can read "
                        "reports before enforcing.")
    else:
        d = dmarc[0].lower()
        policy = next((p for p in ("reject", "quarantine", "none") if f"p={p}" in d), "unknown")
        if policy == "none":
            warnings.append("DMARC is p=none. Correct while observing; tighten to quarantine then "
                            "reject once reports show SPF and DKIM aligning.")
        if "rua=" not in d:
            warnings.append("DMARC has no rua address, so nobody receives the reports that "
                            "justify tightening it.")

    if wildcard:
        problems.append("This domain answers EVERY name under _domainkey with a TXT record, so "
                        "selector probing cannot tell you anything. Read the selector from the "
                        "provider console and re-run with --selector.")
    elif not dkim:
        problems.append("No DKIM key found at the usual selector names. DKIM has no discovery "
                        "mechanism, so check the provider console for the real selector and "
                        "re-run with --selector.")

    if spf and provider and len(spf) == 1:
        spf_text = spf[0].lower()
        expected = {"Microsoft 365": "protection.outlook.com", "Google Workspace": "_spf.google.com",
                    "Zoho": "zoho"}.get(provider)
        if expected and expected not in spf_text:
            problems.append(
                f"SPF does not authorise {provider}, which is where the MX records point. "
                f"Mail sent through {provider} will FAIL SPF. Add its include (for Microsoft "
                "365 that is include:spf.protection.outlook.com) alongside whatever else "
                "legitimately sends.")

    if not mx:
        warnings.append("No MX records. Fine if this domain only sends, but then replies bounce.")

    return {
        "domain": domain, "spf": spf, "dmarc": dmarc, "dkim": dkim, "mx": mx,
        "nameservers": ns, "dns_host": dns_host, "serves_website": serves_a_website(domain),
        "dkim_wildcard": wildcard,
        "mail_provider": provider, "problems": problems, "warnings": warnings,
        "ready": not problems,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("domain")
    ap.add_argument("--selector", help="a DKIM selector from the provider console")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    r = audit(args.domain, args.selector)

    # A machine that cannot do DNS lookups at all used to produce a perfectly normal-looking
    # report saying every record was MISSING, which reads as a badly configured domain and is
    # the most misleading output this script could possibly give. If no resolver ever
    # answered, say THAT instead.
    if not RESOLVER_OK["answered"]:
        sys.exit(
            f"could not look up {args.domain} at all - no DNS resolver answered.\n"
            "This is a problem with this machine, not with the domain, and nothing below "
            "would have been true.\n"
            "  - `dig` is not installed (normal on Windows) and the DNS-over-HTTPS fallback "
            "could not be reached either.\n"
            "  - Check the network, a proxy, or a firewall blocking cloudflare-dns.com and "
            "dns.google."
        )

    if args.json:
        print(json.dumps(r, indent=2))
        return

    if r.get("exists") is False:
        print(f"\n{r['domain']}\n" + "-" * (len(r["domain"]) + 4))
        for prob in r["problems"]:
            print(f"  {prob}")
        return
    print(f"\n{r['domain']}" + (f"   (mail: {r['mail_provider']})" if r["mail_provider"] else "")
          + (f"   (DNS: {r['dns_host']})" if r.get("dns_host") else ""))
    print("-" * (len(r["domain"]) + 20))
    print(f"  SPF    {r['spf'][0] if r['spf'] else 'MISSING'}")
    if len(r["spf"]) > 1:
        for extra in r["spf"][1:]:
            print(f"         ALSO {extra}")
    print(f"  DMARC  {r['dmarc'][0] if r['dmarc'] else 'MISSING'}")
    print(f"  DKIM   {', '.join(r['dkim']) if r['dkim'] else ('wildcard TXT - probing tells you nothing' if r.get('dkim_wildcard') else 'none found at common selectors')}")
    print(f"  MX     {r['mx'][0] if r['mx'] else 'none'}")
    if r.get("serves_website"):
        print("\nThis domain serves a live website, so it is a brand asset.")
        print("  Ask what they intend to send from it:")
        print("   - normal business mail -> this is the right domain, fix the records below")
        print("   - cold outreach -> use a SEPARATE sending domain. A blacklisted sending")
        print("     domain costs a registration to replace; blacklisting this one takes the")
        print("     site's mail and every published contact route with it.")
    if r["problems"]:
        print("\nFix before warming:")
        for p in r["problems"]:
            print(f"  - {p}")
    if r["warnings"]:
        print("\nWorth changing:")
        for w in r["warnings"]:
            print(f"  - {w}")
    if r["ready"]:
        print("\nAuthentication is in place. Remember this buys you nothing on its own:")
        print("reputation is what wins the inbox, and that is what the warm-up builds.")


if __name__ == "__main__":
    main()
