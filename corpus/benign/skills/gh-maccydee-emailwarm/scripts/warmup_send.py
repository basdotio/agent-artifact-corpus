#!/usr/bin/env python3
"""Send one warm-up message and prove it actually sent.

The browser work lives here, deterministically, rather than in the model driving the run.
That is what lets the daily cadence run on a cheap model: it supplies the recipient and four
sentences of prose, and this handles compose, the From address, sending and confirmation.

    warmup_send.py --to someone@example.com --from-address hello@sending-domain.com \
                   --subject "quick one" --body "Two or three ordinary sentences." [--dry-run]

Exit code 0 only when the message is confirmed in Sent. Anything else is a failure the run
must log as blocked rather than counting as a send.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

PROFILE = Path(os.environ.get("EMAILWARM_PROFILE", Path.home() / ".emailwarm/browser-profile"))
SHOTS = Path(os.environ.get("EMAILWARM_SHOTS", Path.home() / ".emailwarm/shots"))

GMAIL_INBOX = "https://mail.google.com/mail/u/0/#inbox"
GMAIL_SENT = "https://mail.google.com/mail/u/0/#sent"


def _first(page, selectors, timeout=15000):
    """Return the first selector that appears. Webmail DOMs vary by rollout and change often,
    so a single selector is a time bomb; a short list degrades instead of breaking."""
    last = None
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            loc.wait_for(state="visible", timeout=timeout // len(selectors) + 1500)
            return loc
        except Exception as exc:  # noqa: PERF203, BLE001
            last = exc
    raise RuntimeError(f"none of {selectors} appeared ({last})")


def _dismiss_popups(page, rounds: int = 3) -> int:
    """Close any interstitial sitting over the page.

    AOL and Yahoo throw promotional popups whose close button is a transparent overlay
    covering the whole surface, so every click on the form underneath lands on the popup
    instead and the driver times out on an element it can plainly see. Dismissed in a loop
    because closing one can reveal another.
    """
    closed = 0
    for _ in range(rounds):
        # ONLY the interstitial's own control. A generic "anything labelled Close" sweep
        # matched the compose window's close button and shut the window this driver had
        # just opened, which looked exactly like compose failing to appear.
        for sel in ('button[aria-label="Close popup"]',):
            loc = page.locator(sel).first
            try:
                if loc.count() and loc.is_visible():
                    loc.click(timeout=4000)
                    closed += 1
                    page.wait_for_timeout(900)
                    break
            except Exception:  # noqa: BLE001 - a popup that will not close is not fatal yet
                continue
        else:
            break
    return closed


def send_gmail(ctx, args) -> dict:
    info: dict = {"to": args.to, "subject": args.subject, "dry_run": args.dry_run}
    page = ctx.new_page()
    page.goto(GMAIL_INBOX, wait_until="domcontentloaded")
    page.wait_for_timeout(9000)

    # Check the URL before looking for anything on the page. A signed-out profile lands on a
    # login form, where every mailbox selector is simply absent, and hunting for Compose
    # there produces a timeout that reads like a broken selector rather than the real cause.
    final = page.url.lower()
    if any(m in final for m in ("signin", "login", "challenge", "accounts.google.com")):
        raise RuntimeError(f"not signed in - the mailbox redirected to {page.url[:80]}. "
                           "Re-seed with: seed_login.py seed gmail")
    title = page.title()
    info["title"] = title
    if args.mailbox and args.mailbox not in title:
        # Account index URLs move, so the /u/0/ in the URL is not a promise about WHICH
        # account is open. Checking the title is what stops a warm-up going out from a
        # personal mailbox that happens to be signed in.
        raise RuntimeError(f"wrong account: title is {title!r}, expected {args.mailbox}")

    _first(page, ['div[role="button"]:has-text("Compose")', 'div:text-is("Compose")',
                  'div[role="button"][gh="cm"]']).click()
    page.wait_for_timeout(5000)
    dialog = page.locator('div[role="dialog"]').last

    # The From address decides which DOMAIN earns the reputation - not the account signed in,
    # and with a send-as alias those are deliberately different.
    if args.from_address not in dialog.inner_text():
        try:
            dialog.locator('span[role="link"], span:has-text("@")').last.click()
            page.wait_for_timeout(1500)
            page.locator(f'div[role="menuitem"][value="{args.from_address}"]').first.click()
            page.wait_for_timeout(1500)
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(
                f"could not switch From to {args.from_address}: {type(exc).__name__}. If the "
                "address is missing from the dropdown it needs adding once in the mailbox "
                "settings - that is a blocker, not a reason to send from another address"
            ) from exc

    _first(page, ['input[aria-label="To recipients"]', 'textarea[name="to"]',
                  'input[peoplekit-id]']).type(args.to, delay=25)
    page.wait_for_timeout(900)
    # Commit the address to a chip, or the autocomplete list stays open over the subject box
    # and swallows the next click, putting subject text into the wrong field.
    page.keyboard.press("Enter")
    page.wait_for_timeout(900)

    subj = _first(page, ['input[name="subjectbox"]'])
    subj.click()
    subj.type(args.subject, delay=25)
    page.wait_for_timeout(400)
    # Tab into the body rather than clicking it: a lingering overlay intercepts the click.
    subj.press("Tab")
    page.wait_for_timeout(600)
    page.keyboard.type(args.body, delay=8)
    page.wait_for_timeout(1200)

    SHOTS.mkdir(parents=True, exist_ok=True)
    dialog.screenshot(path=str(SHOTS / f"compose-{args.tag}.png"))

    # innerText never contains <input> values, and Gmail hides the From row once the header
    # collapses - so both the subject and the From address are invisible to a text scrape
    # even when the screenshot shows them correctly. Read the fields themselves.
    text = dialog.inner_text()
    actual_from = dialog.locator('input[name="from"]').first.input_value()
    actual_subject = dialog.locator('input[name="subjectbox"]').first.input_value()
    info.update({"actual_from": actual_from, "actual_subject": actual_subject})

    problems = []
    if actual_from != args.from_address:
        problems.append(f"From is {actual_from!r}, expected {args.from_address}")
    if args.to.split("@")[0] not in text:
        problems.append(f"recipient {args.to} not visible")
    if actual_subject != args.subject:
        problems.append(f"subject is {actual_subject!r}")
    if args.body.split("\n")[0][:24] not in text:
        problems.append("body not visible")
    info["problems"] = problems
    if problems:
        page.keyboard.press("Escape")  # leave a draft rather than send something wrong
        raise RuntimeError("compose verification failed: " + "; ".join(problems))

    if args.dry_run:
        page.keyboard.press("Escape")
        info["sent"] = False
        return info

    # A keyboard send shortcut is platform specific and silently leaves a draft when wrong.
    # Click the button, then prove it sent.
    _first(page, ['div[role="button"][data-tooltip^="Send"]',
                  'div[role="button"][aria-label^="Send"]',
                  'div[role="button"]:text-is("Send")']).click()
    page.wait_for_timeout(4000)
    info["toast"] = "Message sent" in page.inner_text("body")

    # Confirm on a FRESH page: navigating the compose tab to a #hash is a same-document
    # navigation, so the old view keeps rendering and the check reads Inbox rows.
    found, top = False, ""
    check = ctx.new_page()
    try:
        check.goto(GMAIL_SENT, wait_until="domcontentloaded")
        for _ in range(8):
            check.wait_for_timeout(4000)
            rows = check.locator("tr.zA")
            if rows.count():
                top = " ".join(rows.nth(i).inner_text() for i in range(min(rows.count(), 4)))
                if args.subject[:34] in top:
                    found = True
                    break
        check.screenshot(path=str(SHOTS / f"sent-{args.tag}.png"))
    finally:
        check.close()

    info["sent"] = found
    info["sent_top"] = top[:200]
    if not found:
        raise RuntimeError(f"send NOT confirmed: {args.subject!r} is not in Sent. Treat this "
                           "as blocked - a log entry claiming traffic that does not exist "
                           "corrupts the only evidence the gate is computed from")
    return info



OUTLOOK_MAIL = "https://outlook.live.com/mail/0/"
OUTLOOK_SENT = "https://outlook.live.com/mail/0/sentitems"


def send_outlook(ctx, args) -> dict:
    """Outlook.com / Hotmail. Selectors read off the live client rather than guessed:
    the compose control is "New email" (not "New mail"), To is a contenteditable div,
    Subject is a real input, and the body is a role=textbox div."""
    info: dict = {"to": args.to, "subject": args.subject, "dry_run": args.dry_run,
                  "provider": "outlook"}
    page = ctx.new_page()
    page.goto(OUTLOOK_MAIL, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(12000)

    final = page.url.lower()
    if "outlook.live.com/mail" not in final and "outlook.com/mail" not in final:
        raise RuntimeError(f"not in the mailbox - landed on {page.url[:90]}. "
                           "Re-seed with: seed_login.py seed outlook")
    info["title"] = page.title()

    _first(page, ['button[aria-label*="New email" i]', 'button:has-text("New email")']).click()
    page.wait_for_timeout(6000)

    to = _first(page, ['div[aria-label="To"][contenteditable="true"]', 'div[aria-label="To"]'])
    to.click()
    to.type(args.to, delay=25)
    page.wait_for_timeout(900)
    # Commit to a chip, same reason as Gmail: the suggestion list sits over the next field.
    page.keyboard.press("Enter")
    page.wait_for_timeout(800)

    subj = _first(page, ['input[aria-label="Subject"]', 'input[placeholder="Add a subject"]'])
    subj.click()
    subj.type(args.subject, delay=25)
    page.wait_for_timeout(400)

    body = _first(page, ['div[role="textbox"][aria-label="Message body"]',
                         'div[aria-label="Message body"]'])
    body.click()
    page.keyboard.type(args.body, delay=8)
    page.wait_for_timeout(1000)

    SHOTS.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(SHOTS / f"compose-outlook-{args.tag}.png"))

    # Read values rather than rendered text where the field is a real input; for the
    # contenteditable ones innerText IS the value, which is the opposite of Gmail.
    actual_subject = subj.input_value()
    actual_to = to.inner_text()
    actual_body = body.inner_text()

    # Personal Outlook shows a From control only when the account has aliases, so its absence
    # is normal. Match the label from the START: the toolbar carries "Sort message list by
    # From", which a contains-match happily mistakes for a From selector and then fails on.
    from_ctl = page.locator('button[aria-label^="From" i]').first
    wanted = args.from_address.lower()
    if from_ctl.count():
        if wanted not in from_ctl.inner_text().lower():
            raise RuntimeError(f"From control does not show {args.from_address} - pick the "
                               "right alias, or the message earns reputation for the wrong domain")
        info["from_verified"] = "control"
    else:
        # No alias picker: the account's own address is the only thing it can send as, so
        # confirm THAT is what was asked for. Sending warm-up mail from a different account
        # than intended is silent and wastes the whole run.
        if wanted not in page.inner_text("body").lower():
            raise RuntimeError(f"{args.from_address} does not appear in this mailbox, so this "
                               "is probably a different account. Check which address is "
                               "signed in before sending")
        info["from_verified"] = "account address on page"

    # Outlook replaces the typed address with a chip showing the RESOLVED CONTACT NAME, and
    # keeps the address nowhere in the DOM - checked, there is no title, aria-label or data
    # attribute carrying it. So compose-time verification can only prove that a chip was
    # created and nothing was left unresolved; the address itself is confirmed from the Sent
    # item afterwards, which is better evidence anyway.
    problems = []
    chip_text = actual_to.replace("\u200b", "").strip()
    if not chip_text:
        problems.append("the To field is empty - the address did not resolve to a recipient")
    elif "@" in chip_text and args.to.lower() not in chip_text.lower():
        problems.append(f"the To field still holds unresolved text {chip_text[:40]!r}")
    if actual_subject != args.subject:
        problems.append(f"subject is {actual_subject!r}")
    if args.body.split("\n")[0][:24] not in actual_body:
        problems.append("body not visible")
    info.update({"actual_subject": actual_subject,
                 "to_chip": chip_text.replace("\ue6c3", "").strip()[:60],
                 "to_verified": "chip only - address confirmed from Sent after sending",
                 "problems": problems})
    if problems:
        page.keyboard.press("Escape")
        raise RuntimeError("compose verification failed: " + "; ".join(problems))

    if args.dry_run:
        page.keyboard.press("Escape")
        info["sent"] = False
        return info

    _first(page, ['button[aria-label="Send"]', 'button:has-text("Send")']).click()
    page.wait_for_timeout(5000)

    found, top = False, ""
    check = ctx.new_page()
    try:
        check.goto(OUTLOOK_SENT, wait_until="domcontentloaded", timeout=60000)
        for _ in range(8):
            check.wait_for_timeout(4000)
            top = check.inner_text("body")[:6000]
            if args.subject[:34] in top:
                found = True
                break
        if found:
            # Open the sent item so the recipient ADDRESS is on screen, which is the check
            # the compose window could not give us.
            try:
                check.locator(f'text={args.subject[:34]}').first.click()
                check.wait_for_timeout(3500)
                detail = check.inner_text("body")
                info["to_verified"] = ("confirmed in Sent" if args.to.lower() in detail.lower()
                                       else f"SENT, BUT {args.to} not shown on the sent item")
            except Exception:  # noqa: BLE001
                info["to_verified"] = "sent, could not open the item to confirm the address"
        check.screenshot(path=str(SHOTS / f"sent-outlook-{args.tag}.png"))
    finally:
        check.close()
    info["sent"] = found
    if not found:
        raise RuntimeError(f"send NOT confirmed: {args.subject!r} is not in Sent Items")
    return info



# AOL and Yahoo run the same client, so they share this driver - but they are different
# mailboxes on different hosts, and hardcoding AOL's URL meant "--provider yahoo" signed into
# AOL and tried to send from there. The host has to follow the provider.
YAHOO_STACK_URLS = {
    "aol": ("https://mail.aol.com/", "https://mail.aol.com/d/folders/2"),
    "yahoo": ("https://mail.yahoo.com/", "https://mail.yahoo.com/d/folders/2"),
}


def send_aol(ctx, args) -> dict:
    """AOL, which runs on Yahoo's stack - so the same driver is registered for Yahoo, though
    only AOL has been tested against a live mailbox.

    Kinder than Outlook: To and Subject are real inputs, so their values can be read back
    directly rather than inferred from a chip.
    """
    mail_url, sent_url = YAHOO_STACK_URLS.get(args.provider, YAHOO_STACK_URLS["aol"])
    info: dict = {"to": args.to, "subject": args.subject, "dry_run": args.dry_run,
                  "provider": args.provider, "mailbox_url": mail_url}
    page = ctx.new_page()
    page.goto(mail_url, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(11000)

    low = page.url.lower()
    if "login" in low or "signin" in low or "challenge" in low:
        raise RuntimeError(f"not signed in - landed on {page.url[:80]}. "
                           f"Re-seed with: seed_login.py seed {args.provider}")
    # Wait for the mailbox to actually be ready before judging anything about it. Polling the
    # title on a timer raced the page load and reported a perfectly good session as the wrong
    # account; the Compose button is the signal that the client has finished rendering, so
    # wait for that instead of for a number of seconds.
    page.wait_for_selector('button:has-text("Compose")', timeout=60000)
    title, wanted = "", args.from_address.lower()
    for _ in range(10):
        title = page.title() or ""
        if title.strip():
            break
        page.wait_for_timeout(1500)
    info["title"] = title
    if wanted in title.lower():
        info["from_verified"] = "account address in page title"
    elif wanted in page.inner_text("body").lower():
        info["from_verified"] = "account address on page"
    else:
        raise RuntimeError(f"this mailbox does not appear to be {args.from_address} "
                           f"(title: {title!r}) - check which account is signed in")

    # Before compose only. Once the compose window is open, anything that closes things is
    # more likely to close that than a popup.
    info["popups_closed"] = _dismiss_popups(page)
    _first(page, ['button:has-text("Compose")', '[data-test-id="compose-button"]']).click()
    page.wait_for_timeout(5000)

    to = _first(page, ['input[aria-label="To"]'])
    to.click(); to.type(args.to, delay=25)
    page.wait_for_timeout(800)
    page.keyboard.press("Enter")
    page.wait_for_timeout(700)
    # The address suggestion list stays open on top of the subject field, so a click on the
    # subject lands on the dropdown instead. Escape closes it; filling rather than clicking
    # then keeps the rest immune to any overlay that reappears.
    page.keyboard.press("Escape")
    page.wait_for_timeout(500)

    subj = _first(page, ['input[aria-label="Subject"]'])
    subj.fill(args.subject)
    page.wait_for_timeout(400)

    body = _first(page, ['div[aria-label="Email body"]', 'div[role="textbox"]'])
    body.fill(args.body)
    page.wait_for_timeout(900)

    SHOTS.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(SHOTS / f"compose-{args.provider}-{args.tag}.png"))

    actual_subject = subj.input_value()
    # Once the address is committed the input clears and the recipient becomes a pill beside
    # it, so read the row around the field rather than the field itself. Unlike Outlook, the
    # pill keeps the real address, so this is a genuine check rather than a name match.
    actual_to = page.evaluate("""() => {
        const i = document.querySelector('input[aria-label="To"]');
        let n = i;
        for (let k = 0; k < 4 && n; k++) n = n.parentElement;
        return (n && n.innerText) || '';
    }""") or to.input_value()
    actual_body = body.inner_text()

    problems = []
    if args.to.split("@")[0].lower() not in actual_to.lower():
        problems.append(f"recipient not in the To field (shows {actual_to[:40]!r})")
    if actual_subject != args.subject:
        problems.append(f"subject is {actual_subject!r}")
    if args.body.split("\n")[0][:24] not in actual_body:
        problems.append("body not visible")
    info.update({"actual_subject": actual_subject, "actual_to": actual_to.strip()[:60],
                 "problems": problems})
    if problems:
        raise RuntimeError("compose verification failed: " + "; ".join(problems))

    if args.dry_run:
        info["sent"] = False
        return info

    _first(page, ['button:has-text("Send")']).click()
    page.wait_for_timeout(5000)

    # Sent is folder 2, reachable directly. Clicking the sidebar was tried first and does not
    # work: the nav exposes no element whose text is "Sent", so the click times out while the
    # message has in fact gone - the worst shape of failure, because it reports a send that
    # happened as a send that did not. The URL redirects (/d/folders/2 -> /f/folders/2) and
    # lands correctly; a sidebar click is kept only as a fallback.
    found, check = False, ctx.new_page()
    try:
        check.goto(sent_url, wait_until="domcontentloaded", timeout=60000)
        for _ in range(6):
            check.wait_for_timeout(3500)
            if args.subject[:34] in check.inner_text("body"):
                found = True
                break
        if not found:
            try:
                check.locator('a:has-text("Sent"), [data-test-folder-name="Sent"]').first.click(timeout=8000)
                check.wait_for_timeout(4000)
                found = args.subject[:34] in check.inner_text("body")
            except Exception:  # noqa: BLE001
                pass
        check.screenshot(path=str(SHOTS / f"sent-{args.provider}-{args.tag}.png"))
    finally:
        check.close()
    info["sent"] = found
    if not found:
        raise RuntimeError(f"send NOT confirmed: {args.subject!r} is not in Sent")
    return info


# Yahoo runs the same client as AOL, so it gets the same driver - untested against a live
# Yahoo mailbox, which is worth knowing before relying on it.
DRIVERS = {"gmail": send_gmail, "outlook": send_outlook, "aol": send_aol, "yahoo": send_aol}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--to", required=True)
    ap.add_argument("--from-address", required=True, help="the address the message must come FROM")
    ap.add_argument("--subject", required=True)
    ap.add_argument("--body", help="message text; or use --body-file")
    ap.add_argument("--body-file", type=Path)
    ap.add_argument("--provider", default="gmail", choices=sorted(DRIVERS))
    ap.add_argument("--mailbox", help="expected account, checked against the page title")
    ap.add_argument("--tag", default="run", help="label for the screenshots")
    ap.add_argument("--dry-run", action="store_true", help="compose and verify, do not send")
    ap.add_argument("--headless", action="store_true",
                    help="run without a visible window. Sensible for a scheduled job, but "
                         "webmail is more fragile headless, so prove a run works this way "
                         "before scheduling it that way.")
    args = ap.parse_args()

    if not args.body and not args.body_file:
        ap.error("one of --body or --body-file is required")
    if args.body_file:
        args.body = args.body_file.read_text(encoding="utf-8").strip()

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return int(bool(sys.stderr.write(
            "playwright is not installed for this interpreter:\n"
            f"  {sys.executable} -m pip install playwright\n"
            f"  {sys.executable} -m playwright install chromium\n"))) or 2

    result, code = {}, 0
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            str(PROFILE), headless=args.headless,
            no_viewport=True, args=["--no-first-run", "--window-size=1328,801"])
        try:
            result = DRIVERS[args.provider](ctx, args)
        except Exception as exc:  # noqa: BLE001 - the message is the product here
            result = {"sent": False, "error": f"{type(exc).__name__}: {exc}"}
            code = 1
        finally:
            ctx.close()
    print(json.dumps(result, indent=2, ensure_ascii=False)[:3000])
    return code


if __name__ == "__main__":
    raise SystemExit(main())
