#!/usr/bin/env python3
"""vibe-app-legal-audit scanner.

Static heuristic scan of a code repository for common legal-exposure
patterns (eleven checks) in quickly built (vibe coded) web apps. It reads files only. It never
executes project code and never makes network calls.

Usage:
    python scan.py <project_dir> [--json out.json] [--md out.md]

Exit code: 0 when no HIGH findings, 1 when at least one HIGH finding exists.

This is a triage aid. It is NOT legal advice. Every hit needs human review.
"""
import argparse
import json
import os
import re
import sys
from collections import defaultdict

SKIP_DIRS = {
    "node_modules", ".git", ".next", "dist", "build", ".venv", "venv", "__pycache__",
    ".cache", "coverage", ".turbo", ".vercel", ".svelte-kit", "out", "vendor", "target",
}
TEXT_EXT = {
    ".html", ".htm", ".js", ".jsx", ".ts", ".tsx", ".vue", ".svelte", ".astro", ".css",
    ".scss", ".py", ".rb", ".php", ".go", ".java", ".cs", ".json", ".yml", ".yaml",
    ".toml", ".env", ".md", ".mdx", ".txt", ".liquid", ".hbs", ".ejs", ".njk", ".mjml",
}
MAX_BYTES = 1_500_000

# ---------------------------------------------------------------- patterns
RX = lambda p: re.compile(p, re.I)

SIGNUP = RX(r"sign[\s_-]?up|register|create[\s_-]?account|createUser|signUp\(|auth\.signUp|signInWithOAuth|supabase\.auth|clerk|next-auth|NextAuth|firebase/auth|createUserWithEmail")
AGE_SIGNAL = RX(r"date[\s_-]?of[\s_-]?birth|\bdob\b|birth[\s_-]?(date|year)|\bage\b|over[\s_-]?13|13\+|16\+|18\+|under[\s_-]?13|coppa|age[\s_-]?gate|i am (at least|over)|confirm.{0,20}(13|16|18)")
KIDS_HINT = RX(r"\bkids?\b|children|child-friendly|students?|school|classroom|teen|\bgames?\b|cartoon|toddler|parents")

GFONT = RX(r"fonts\.googleapis\.com|fonts\.gstatic\.com")
NEXTFONT = RX(r"next/font/google")
OTHER_CDN = RX(r"https?://(cdnjs\.cloudflare\.com|cdn\.jsdelivr\.net|unpkg\.com|ajax\.googleapis\.com|use\.typekit\.net|use\.fontawesome\.com|maxcdn\.bootstrapcdn\.com)")

REPLAY = {
    "Hotjar": RX(r"hotjar|static\.hotjar\.com"),
    "FullStory": RX(r"fullstory|fs\.js|edge\.fullstory\.com"),
    "Microsoft Clarity": RX(r"clarity\.ms|clarity\(|microsoft[\s_-]?clarity"),
    "LogRocket": RX(r"logrocket"),
    "Mouseflow": RX(r"mouseflow"),
    "Smartlook": RX(r"smartlook"),
    "Lucky Orange": RX(r"luckyorange"),
    "Inspectlet": RX(r"inspectlet"),
    "Heap": RX(r"heap\.load|heapanalytics"),
    "PostHog session recording": RX(r"posthog.{0,200}(session_recording|capture_pageview)|session_recording|disable_session_recording"),
    "Sentry Replay": RX(r"replayIntegration|Sentry\.Replay|replaysSessionSampleRate|replaysOnErrorSampleRate"),
    "rrweb": RX(r"\brrweb\b"),
    "OpenReplay": RX(r"openreplay"),
    "PostHog": RX(r"posthog\.init|posthog-js"),
}
REPLAY_OFF = RX(r"disable_session_recording\s*:\s*true|maskAllInputs\s*:\s*true|session_recording\s*:\s*false")
CONSENT = RX(r"cookie[\s_-]?(consent|banner)|consent[\s_-]?manager|onetrust|cookiebot|osano|termly|iubenda|usercentrics|klaro|cookieyes|opt[\s_-]?in|gpc|globalprivacycontrol|navigator\.globalPrivacyControl")

EMAIL_SEND = RX(r"sendgrid|resend|nodemailer|mailgun|postmark|aws-sdk/client-ses|@aws-sdk/client-sesv2|sendMail\(|mailchimp|brevo|sendinblue|mailjet|convertkit|loops\.so|beehiiv|smtplib|SMTP|send_mail|Mail::|ActionMailer|react-email|mjml")
UNSUB = RX(r"unsubscribe|list-unsubscribe|opt[\s_-]?out|manage[\s_-]?preferences|email[\s_-]?preferences|\{\{\s*unsubscribe|\*\|UNSUB\|\*|%unsubscribe")
POSTAL = RX(r"\b\d{1,6}\s+[A-Za-z0-9.\s]{3,40}\s(street|st\.?|avenue|ave\.?|road|rd\.?|boulevard|blvd\.?|lane|ln\.?|drive|dr\.?|suite|ste\.?|way|court|ct\.?)\b|p\.?\s?o\.?\s?box|postal[\s_-]?address|mailing[\s_-]?address|physical[\s_-]?address|\{\{\s*(company_)?address|business_address|COMPANY_ADDRESS")
MARKETING_HINT = RX(r"launch|newsletter|announce|campaign|promo|waitlist|welcome|drip|broadcast|marketing")

PAYMENT = RX(r"stripe|paddle|lemon[\s_-]?squeezy|lemonsqueezy|razorpay|paypal|gumroad|chargebee|recurly|braintree|checkout\.sessions|createCheckoutSession|mode\s*:\s*['\"]subscription['\"]")
RECURRING = RX(r"subscription|recurring|per[\s_-]?month|/mo\b|/month|/yr\b|/year|monthly|annual|yearly|free[\s_-]?trial|trial_period|trial_days|interval\s*:\s*['\"](month|year)")
RENEW_DISCLOSE = RX(r"auto[\s-]?renew|automatically renew|renews? (automatically|on|at|every|each|monthly|annually|yearly)|will be charged|billed (monthly|annually|yearly|every)|until you cancel|cancel anytime|cancel any time|recurring (charge|billing|payment)")
CANCEL_FLOW = RX(r"cancel[\s_-]?(subscription|plan|membership|renewal)|billingPortal|customer[\s_-]?portal|click[\s_-]?to[\s_-]?cancel|subscriptions\.(cancel|update)")
CONSENT_CHECKBOX = RX(r"(agree|consent|accept).{0,60}(renew|recurring|subscription|charge)|(renew|recurring|subscription).{0,60}(agree|consent|accept)")

UPLOAD = RX(r"type\s*=\s*[\"']file[\"']|multer|formidable|busboy|uploadthing|react-dropzone|filepond|FileReader|FormData\(|supabase\.storage|\.storage\.from\(|cloudinary|upload(File|Image|Photo|Avatar)|S3Client|PutObjectCommand|putObject|storage\.bucket|multipart/form-data|ImageField|FileField|UploadFile|request\.files")
UGC_HINT = RX(r"avatar|gallery|post|comment|photo|image|portfolio|profile|user[\s_-]?generated|ugc|community|feed|share")
DMCA = RX(r"dmca|designated[\s_-]?agent|copyright[\s_-]?agent|copyright[\s_-]?(policy|complaint|notice)|takedown|512\(c\)|notice[\s_-]?and[\s_-]?takedown|report[\s_-]?(infringement|copyright)")

PRIVACY_POLICY = RX(r"privacy[\s_-]?(policy|notice)|/privacy\b|data[\s_-]?protection[\s_-]?(policy|notice)")
RIGHTS_PATH = RX(r"delete[\s_-]?(my[\s_-]?)?(account|data)|erase|erasure|data[\s_-]?(request|export|portability)|dsar|do[\s_-]?not[\s_-]?sell|withdraw[\s_-]?consent|revoke[\s_-]?consent|manage[\s_-]?consent")
DATA_COLLECT = RX(r"gtag\(|googletagmanager|google-analytics|analytics|posthog|mixpanel|segment\.com|amplitude|fbq\(|facebook\.net|pixel|localStorage|document\.cookie|set-cookie|supabase|firebase|mongoose|prisma|sequelize|INSERT INTO")
GRIEVANCE = RX(r"grievance[\s_-]?(officer|redressal)?|nodal[\s_-]?(contact|officer)|terms[\s_-]?(of[\s_-]?)?(service|use)|/terms\b|user[\s_-]?agreement|community[\s_-]?guidelines")
GRIEVANCE_OFFICER = RX(r"grievance[\s_-]?officer|grievance[\s_-]?redressal")
PRECHECKED = RX(r"<input[^>]*type\s*=\s*[\"']checkbox[\"'][^>]*\bchecked\b|defaultChecked|checked\s*=\s*\{?\s*true")
URGENCY = RX(r"countdown|only\s+\d+\s+(left|remaining)|hurry|offer ends in|limited[\s_-]?time|\d+\s+people (are )?(viewing|looking)|almost (gone|sold out)")
SHAMING = RX(r"no thanks,?\s*i\s*(don'?t|do not|hate|prefer|like|will)|i don'?t want to (save|be)|i'?ll (pay|stay) (full|without)|maybe later,? i")

TERMS_LINK = RX(r"terms[\s_-]?(of[\s_-]?)?(service|use)|/terms\b|user[\s_-]?agreement|terms\s*(and|&)\s*conditions|/tos\b")
TERMS_ACCEPT = RX(r"(by (signing up|creating|continuing|registering|clicking)|i (agree|accept)|you (agree|accept)).{0,120}(terms|conditions|policy)|(agree|accept).{0,40}terms|accepted_terms|terms_accepted|tos_accepted|agreed_to_terms")
SEC_ENCRYPT = RX(r"bcrypt|argon2|scrypt|pbkdf2|encrypt|aes-?\d*|createCipher|kms|crypto\.subtle|fernet|libsodium|helmet\(|strict-transport-security")
SEC_LOGS = RX(r"audit[\s_-]?log|access[\s_-]?log|winston|pino|morgan\(|logger\.|logging\.|structlog|cloudtrail|sentry")
SEC_BREACH = RX(r"breach|incident[\s_-]?response|security@|vulnerability[\s_-]?disclosure|security\.txt|data[\s_-]?protection[\s_-]?board")
SEC_RETENTION = RX(r"retention|purge|ttl\b|expires_at|expire_at|delete[\s_-]?after|cron.{0,60}delete|erasure|inactive[\s_-]?(user|account)|anonymi[sz]e")
CONSENT_LOG = RX(r"consent[\s_-]?(log|record|history|receipt)|consented_at|consent_given|consent_version|notice_version")
DPO_CONTACT = RX(r"data[\s_-]?protection[\s_-]?officer|\bdpo\b|privacy@|grievance|contact[\s_-]?(us|details).{0,80}privacy")

# ---------------------------------------------------------------- helpers

def walk(root):
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in SKIP_DIRS and not d.startswith(".git")]
        for fn in fns:
            ext = os.path.splitext(fn)[1].lower()
            if ext in TEXT_EXT or fn in {"Dockerfile", ".env.example"}:
                p = os.path.join(dp, fn)
                try:
                    if os.path.getsize(p) <= MAX_BYTES:
                        yield p
                except OSError:
                    continue


def read(p):
    try:
        with open(p, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except OSError:
        return ""


def first_line(text, rx):
    for i, line in enumerate(text.splitlines(), 1):
        if rx.search(line):
            return i, line.strip()[:160]
    return None, ""


def hit(path, root, line, snippet):
    return {"file": os.path.relpath(path, root), "line": line, "snippet": snippet}


# ---------------------------------------------------------------- scan

def scan(root):
    files = {p: read(p) for p in walk(root)}
    all_text = "\n".join(files.values())
    result = {}

    # 1 COPPA / age gate ------------------------------------------------
    signup_hits = []
    for p, t in files.items():
        if SIGNUP.search(t):
            ln, sn = first_line(t, SIGNUP)
            signup_hits.append(hit(p, root, ln, sn))
    age_found = bool(AGE_SIGNAL.search(all_text))
    kids = bool(KIDS_HINT.search(all_text))
    if signup_hits and not age_found:
        sev = "HIGH" if kids else "MEDIUM"
        status = "FAIL"
    elif signup_hits:
        sev, status = "LOW", "REVIEW"
    else:
        sev, status = "INFO", "NOT_APPLICABLE"
    result["1_coppa_age_gate"] = {
        "title": "Sign-up collects accounts with no age screen (COPPA)",
        "status": status, "severity": sev,
        "evidence": signup_hits[:8],
        "notes": ("Child-appeal keywords detected (kids, students, games and similar) so the app may be directed to children. " if kids and status == "FAIL" else "")
                 + ("Age-related terms exist somewhere in the code. Confirm they gate account creation before any personal data is stored." if age_found and signup_hits else ""),
    }

    # 2 Google Fonts / third-party CDN ---------------------------------
    gf = []
    for p, t in files.items():
        if GFONT.search(t):
            ln, sn = first_line(t, GFONT)
            gf.append(hit(p, root, ln, sn))
    nf = [hit(p, root, *first_line(t, NEXTFONT)) for p, t in files.items() if NEXTFONT.search(t)]
    cdn = []
    for p, t in files.items():
        if OTHER_CDN.search(t):
            ln, sn = first_line(t, OTHER_CDN)
            cdn.append(hit(p, root, ln, sn))
    result["2_google_fonts_ip_leak"] = {
        "title": "Fonts or assets loaded from third-party servers (visitor IP disclosed; GDPR)",
        "status": "FAIL" if gf else ("REVIEW" if cdn else "PASS"),
        "severity": "HIGH" if gf else ("LOW" if cdn else "INFO"),
        "evidence": (gf + cdn)[:10],
        "notes": ("next/font/google is detected. It self-hosts fonts at build time so it is generally safe. Verify in the built output. " if nf else ""),
    }

    # 3 Session replay --------------------------------------------------
    rp = defaultdict(list)
    for p, t in files.items():
        for name, rx in REPLAY.items():
            if name == "PostHog":
                continue
            if rx.search(t):
                ln, sn = first_line(t, rx)
                rp[name].append(hit(p, root, ln, sn))
    posthog_present = any(REPLAY["PostHog"].search(t) for t in files.values())
    off = bool(REPLAY_OFF.search(all_text))
    consent = bool(CONSENT.search(all_text))
    ev = [dict(tool=k, **v[0]) for k, v in rp.items()]
    if posthog_present and "PostHog session recording" not in rp:
        ev.append({"tool": "PostHog (session recording is ON by default in some plans; verify project settings)", "file": "-", "line": None, "snippet": ""})
    if ev:
        sev = "MEDIUM" if (consent and off) else "HIGH"
        status = "REVIEW" if (consent and off) else "FAIL"
    else:
        sev, status = "INFO", "PASS"
    result["3_session_replay_wiretap"] = {
        "title": "Session replay or keystroke capture without gated consent (CIPA wiretap theory)",
        "status": status, "severity": sev, "evidence": ev[:10],
        "notes": f"Consent-manager terms found: {consent}. Input masking or recording disabled: {off}. Consent must fire BEFORE the script loads.",
    }

    # 4 Email: unsubscribe + postal address ----------------------------
    email_files = [p for p, t in files.items() if EMAIL_SEND.search(t)]
    template_files = [p for p in email_files if os.path.splitext(p)[1].lower() in {".html", ".htm", ".mjml", ".hbs", ".ejs", ".njk", ".liquid", ".tsx", ".jsx", ".py", ".js", ".ts"}]
    email_text = "\n".join(files[p] for p in email_files)
    has_unsub = bool(UNSUB.search(email_text))
    has_addr = bool(POSTAL.search(email_text))
    marketing = bool(MARKETING_HINT.search(email_text))
    miss = []
    if email_files and not has_unsub:
        miss.append("unsubscribe link or List-Unsubscribe header")
    if email_files and not has_addr:
        miss.append("physical postal address")
    ev = []
    for p in email_files[:8]:
        ln, sn = first_line(files[p], EMAIL_SEND)
        ev.append(hit(p, root, ln, sn))
    if not email_files:
        status, sev = "NOT_APPLICABLE", "INFO"
    elif miss:
        status, sev = "FAIL", ("HIGH" if marketing else "MEDIUM")
    else:
        status, sev = "REVIEW", "LOW"
    result["4_email_can_spam"] = {
        "title": "Commercial email missing unsubscribe link or postal address (CAN-SPAM)",
        "status": status, "severity": sev, "evidence": ev,
        "notes": ("Missing: " + "; ".join(miss) + ". " if miss else "") +
                 ("Marketing language detected (launch, newsletter, campaign and similar). " if marketing else "") +
                 "Purely transactional email (receipts or password resets) has lighter duties but must not carry promotional content.",
    }

    # 5 Checkout renewal disclosure ------------------------------------
    pay_files = [p for p, t in files.items() if PAYMENT.search(t)]
    rec = [p for p in pay_files if RECURRING.search(files[p])] or [p for p, t in files.items() if PAYMENT.search(t) is None and RECURRING.search(t) and re.search(r"checkout|pricing|subscribe", t, re.I)]
    ui_text = "\n".join(t for p, t in files.items() if os.path.splitext(p)[1].lower() in {".html", ".htm", ".jsx", ".tsx", ".vue", ".svelte", ".astro", ".liquid", ".hbs", ".ejs", ".njk", ".md", ".mdx"})
    disclose = bool(RENEW_DISCLOSE.search(ui_text))
    cancel = bool(CANCEL_FLOW.search(all_text))
    ck = bool(CONSENT_CHECKBOX.search(ui_text))
    ev = []
    for p in (pay_files or rec)[:8]:
        ln, sn = first_line(files[p], PAYMENT if PAYMENT.search(files[p]) else RECURRING)
        ev.append(hit(p, root, ln, sn))
    if not pay_files and not rec:
        status, sev = "NOT_APPLICABLE", "INFO"
    else:
        gaps = []
        if not disclose:
            gaps.append("no renewal or billing-frequency wording in UI files")
        if not cancel:
            gaps.append("no self-serve online cancellation path found")
        if not ck:
            gaps.append("no explicit consent checkbox or consent copy tied to renewal terms")
        if gaps and (rec or pay_files):
            status = "FAIL" if (not disclose or not cancel) else "REVIEW"
            sev = "HIGH" if (not disclose and rec) else "MEDIUM"
        else:
            status, sev = "REVIEW", "LOW"
    result["5_auto_renewal_disclosure"] = {
        "title": "Subscription checkout lacks clear renewal terms and easy cancellation (California ARL)",
        "status": status, "severity": sev, "evidence": ev,
        "notes": f"Renewal wording found: {disclose}. Cancel flow found: {cancel}. Consent copy found: {ck}.",
    }

    # 6 DMCA agent ------------------------------------------------------
    up = []
    for p, t in files.items():
        if UPLOAD.search(t):
            ln, sn = first_line(t, UPLOAD)
            up.append(hit(p, root, ln, sn))
    dmca = bool(DMCA.search(all_text))
    ugc = bool(UGC_HINT.search(all_text))
    if up and not dmca:
        status, sev = "FAIL", ("HIGH" if ugc else "MEDIUM")
    elif up:
        status, sev = "REVIEW", "LOW"
    else:
        status, sev = "NOT_APPLICABLE", "INFO"
    result["6_dmca_safe_harbor"] = {
        "title": "User uploads with no DMCA policy or designated agent (17 U.S.C. 512)",
        "status": status, "severity": sev, "evidence": up[:8],
        "notes": ("No DMCA or takedown wording found anywhere in the repo. " if up and not dmca else "") +
                 "Code alone cannot register the agent. The owner must file at dmca.copyright.gov and publish the same contact on the site.",
    }

    # 7 Privacy notice and data-subject rights (DPDP Act / CCPA) -------
    collects = bool(DATA_COLLECT.search(all_text)) or bool(signup_hits)
    pp = [hit(p, root, *first_line(t, PRIVACY_POLICY)) for p, t in files.items() if PRIVACY_POLICY.search(t)]
    rights = bool(RIGHTS_PATH.search(all_text))
    if not collects:
        status, sev = "NOT_APPLICABLE", "INFO"
    elif not pp:
        status, sev = "FAIL", "MEDIUM"
    elif not rights:
        status, sev = "REVIEW", "MEDIUM"
    else:
        status, sev = "REVIEW", "LOW"
    result["7_privacy_notice_and_rights"] = {
        "title": "No privacy notice or data-subject rights path (India DPDP Act 2023 and Rules 2025; CCPA/CPRA)",
        "status": status, "severity": sev, "evidence": pp[:5],
        "notes": f"Privacy policy reference found: {bool(pp)}. Delete, export or withdraw-consent path found: {rights}. "
                 "DPDP notice and consent duties apply from 14 May 2027 (verify in the Gazette). CCPA applies now where thresholds are met.",
    }

    # 8 Grievance officer and terms for platforms with user content ----
    go = bool(GRIEVANCE_OFFICER.search(all_text))
    terms = bool(GRIEVANCE.search(all_text))
    if not up:
        status, sev = "NOT_APPLICABLE", "INFO"
    elif not go:
        status, sev = "FAIL", "MEDIUM"
    else:
        status, sev = "REVIEW", "LOW"
    result["8_grievance_officer_it_rules"] = {
        "title": "User-content platform with no Grievance Officer or published terms (India IT Act s.79 and IT Rules 2021)",
        "status": status, "severity": sev, "evidence": up[:5],
        "notes": f"Grievance officer wording found: {go}. Terms or user agreement wording found: {terms}. "
                 "Intermediaries serving Indian users should publish rules and a privacy policy and name a Grievance Officer. Loss of compliance can forfeit s.79 safe harbour.",
    }

    # 9 Dark patterns (CCPA India Guidelines 2023; FTC Act s.5; California ARL) --
    dp = []
    for p, t in files.items():
        for label, rx in (("pre-checked box", PRECHECKED), ("false urgency", URGENCY), ("confirm shaming", SHAMING)):
            if rx.search(t):
                ln, sn = first_line(t, rx)
                dp.append(dict(tool=label, **hit(p, root, ln, sn)))
    if dp:
        status, sev = "REVIEW", "MEDIUM"
    else:
        status, sev = "PASS", "INFO"
    result["9_dark_patterns"] = {
        "title": "Dark-pattern indicators in the UI (India Dark Patterns Guidelines 2023; FTC Act s.5; California ARL)",
        "status": status, "severity": sev, "evidence": dp[:10],
        "notes": "Pre-ticked consent boxes and fake urgency are common triggers. A pre-checked box is acceptable only for non-consent options. Consent and renewal boxes must start unticked.",
    }

    # 10 Terms of service and acceptance --------------------------------
    terms_link = [hit(p, root, *first_line(t, TERMS_LINK)) for p, t in files.items() if TERMS_LINK.search(t)]
    terms_accept = bool(TERMS_ACCEPT.search(all_text))
    if not signup_hits:
        status, sev = "NOT_APPLICABLE", "INFO"
    elif not terms_link:
        status, sev = "FAIL", "MEDIUM"
    elif not terms_accept:
        status, sev = "REVIEW", "MEDIUM"
    else:
        status, sev = "REVIEW", "LOW"
    result["10_terms_of_service"] = {
        "title": "Accounts created with no Terms of Service or no clear acceptance step (Indian Contract Act 1872; IT Act s.10A; US clickwrap case law)",
        "status": status, "severity": sev, "evidence": terms_link[:5],
        "notes": f"Terms page or link found: {bool(terms_link)}. Acceptance wording or checkbox found: {terms_accept}. "
                 "Clickwrap (an I agree action next to a link to the terms with a logged timestamp) is far more enforceable than a footer-only link (browsewrap). "
                 "Check limitation of liability, governing law, arbitration and notice of changes with a lawyer.",
    }

    # 11 DPDP engineering controls (security, breach, retention, consent log, contact) --
    signals = {
        "encryption or password hashing": bool(SEC_ENCRYPT.search(all_text)),
        "audit or access logging": bool(SEC_LOGS.search(all_text)),
        "breach or incident contact or runbook": bool(SEC_BREACH.search(all_text)),
        "retention or erasure or purge logic": bool(SEC_RETENTION.search(all_text)),
        "consent record (timestamp or notice version)": bool(CONSENT_LOG.search(all_text)),
        "DPO or privacy contact or grievance contact": bool(DPO_CONTACT.search(all_text)),
    }
    missing = [k for k, v in signals.items() if not v]
    if not collects:
        status, sev = "NOT_APPLICABLE", "INFO"
    elif len(missing) >= 4:
        status, sev = "FAIL", "MEDIUM"
    elif missing:
        status, sev = "REVIEW", "LOW"
    else:
        status, sev = "REVIEW", "INFO"
    result["11_dpdp_engineering_controls"] = {
        "title": "No visible DPDP engineering controls: security safeguards, breach path, retention, consent record, contact (DPDP Act s.8; Rules 6, 7, 8, 14)",
        "status": status, "severity": sev,
        "evidence": [{"tool": k, "file": "-", "line": None, "snippet": ""} for k in missing],
        "notes": "Missing signals listed as evidence. Present: " + (", ".join(k for k, v in signals.items() if v) or "none") + ". "
                 "Security safeguards (s.8(5)) carry the highest ceiling of Rs 250 crore. See references/dpdp-obligations.md. "
                 "A processor contract, breach drill and DPO appointment cannot be seen in code.",
    }
    return result, len(files)


def to_markdown(res, nfiles, root):
    order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2, "INFO": 3}
    lines = [f"# Legal exposure scan: `{os.path.basename(os.path.abspath(root))}`",
             f"Files scanned: {nfiles}. Heuristic scan only. Not legal advice.", "",
             "| # | Check | Status | Severity |", "|---|---|---|---|"]
    for k, v in sorted(res.items(), key=lambda kv: int(kv[0].split('_')[0])):
        lines.append(f"| {k.split('_')[0]} | {v['title']} | {v['status']} | {v['severity']} |")
    lines.append("")
    for k, v in sorted(res.items(), key=lambda kv: (order[kv[1]["severity"]], int(kv[0].split('_')[0]))):
        lines.append(f"## {k.split('_')[0]}. {v['title']}  [{v['status']} / {v['severity']}]")
        if v["notes"]:
            lines.append(v["notes"])
        for e in v["evidence"]:
            loc = f"{e.get('file','-')}:{e.get('line')}" if e.get("line") else e.get("file", "-")
            tool = f"**{e['tool']}** " if e.get("tool") else ""
            lines.append(f"- {tool}`{loc}` {('`' + e['snippet'] + '`') if e.get('snippet') else ''}")
        lines.append("")
    lines += ["## Owner-only checks (cannot be detected in code)",
              "- Trademark clearance of the app name: IP India public search (Classes 9 and 35 and 42) and USPTO search before launch. Unregistered use can also create rights.",
              "- DMCA designated agent registered at dmca.copyright.gov if users upload content.",
              "- DPDP: signed processor contracts, breach runbook and drill, DPO or contact appointed, retention schedule approved.",
              "- GDPR applies to non-EU apps that offer services to or monitor people in the EU (Art. 3(2)). Check whether an EU representative is needed (Art. 27).",
              "- CCPA applies at USD 26,625,000 revenue or 100,000 California consumers or 50 percent revenue from selling or sharing data (check the current inflation-adjusted figure).",
              "- Have a lawyer or chartered accountant review the final policy and terms.", ""]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project_dir")
    ap.add_argument("--json")
    ap.add_argument("--md")
    a = ap.parse_args()
    if not os.path.isdir(a.project_dir):
        print("Not a directory:", a.project_dir, file=sys.stderr)
        sys.exit(2)
    res, n = scan(a.project_dir)
    md = to_markdown(res, n, a.project_dir)
    if a.json:
        with open(a.json, "w") as f:
            json.dump(res, f, indent=2)
    if a.md:
        with open(a.md, "w") as f:
            f.write(md)
    print(md)
    sys.exit(1 if any(v["severity"] == "HIGH" for v in res.values()) else 0)


if __name__ == "__main__":
    main()
