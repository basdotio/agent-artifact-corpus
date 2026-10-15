#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
 reachdirect — FastMCP Tool Server
=============================================================================
 A production-ready MCP server exposing three outreach tools:
   1. send_email           — Brevo v3 transactional email via HTTPS API
   2. send_whatsapp        — WhatsApp Web automation via Playwright async API
   3. save_outreach_contact — Log contacted leads to an Excel (.xlsx) tracker

 Features:
   • Brevo HTTPS email delivery: sends via the Brevo v3 Transactional API
     over HTTPS (port 443) — never blocked by ISPs, no SMTP needed.
     Authenticated via BREVO_API_KEY env var.  300 emails/day free.
   • Declaration-based sender: the user states their name and email in
     the chat prompt.  Zero configuration for end users — no passwords.
   • Persistent WhatsApp session: Playwright async API launches a headed
     Chromium browser with a persistent user data directory so the QR-code
     login is only required once.  Includes explicit QR-code detection with
     a graceful instructional message instead of silent hangs.
   • Contact tracker: saves every outreach action (Name, Email, Phone, Date)
     to an Excel .xlsx file on the user's Desktop for easy follow-up.
   • Auto-update from git remote on startup (graceful offline fallback)
   • Global usage counter with Patreon support message on every 5th call
   • FastMCP Context injection for secure, protocol-safe client logging

=============================================================================
 DEPENDENCIES — Install inside WSL (Ubuntu) with pip:
=============================================================================
 pip install --break-system-packages "mcp<2"             # MCP SDK (< v2)
 pip install --break-system-packages "fastmcp[client]"   # FastMCP framework
 pip install --break-system-packages httpx                # HTTPS client
 pip install --break-system-packages playwright           # Browser automation
 pip install --break-system-packages openpyxl             # Excel .xlsx I/O
 playwright install chromium                              # Chromium binary
=============================================================================
"""

# ---------------------------------------------------------------------------
#  Standard-library imports
# ---------------------------------------------------------------------------
import os
import sys
import subprocess
from datetime import datetime

# ---------------------------------------------------------------------------
#  Third-party imports
# ---------------------------------------------------------------------------
import httpx
import openpyxl
from fastmcp import FastMCP, Context

# ---------------------------------------------------------------------------
#  Playwright is imported lazily inside send_whatsapp to avoid a hard
#  import-time failure when only the email / contact tools are needed.
# ---------------------------------------------------------------------------

# ===========================================================================
#  Brevo v3 Transactional Email API configuration
# ===========================================================================
#  The API key is set ONCE by the server operator — typically in the MCP
#  client's server config (e.g. oterm config.json "env" block) or as a
#  system environment variable.  End users never see or touch it.
#
#  Required env var:
#    BREVO_API_KEY — Brevo API key (starts with "xkeysib-...")
#                    Get one at https://app.brevo.com/settings/keys/api
# ===========================================================================

_BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"

# ===========================================================================
#  Contact tracker — Excel file on the user's Desktop
# ===========================================================================
#  Each outreach action is appended as a row:  Name | Email | Phone | Date
#  The file is created automatically on first use.
# ===========================================================================

_DESKTOP_DIR = os.path.join(os.path.expanduser("~"), "Desktop")
_CONTACTS_FILE = os.path.join(_DESKTOP_DIR, "outreach_contacts.xlsx")

# ===========================================================================
#  Server initialisation
# ===========================================================================
mcp = FastMCP("reachdirect")

# ===========================================================================
#  Global usage counter & Patreon support message
# ===========================================================================
_usage_counter: int = 0

_PATREON_MESSAGE: str = (
    "\n\nI hope you enjoy using this tool. Please show your support for my "
    "further research and development project via patreon: "
    "[https://www.patreon.com/c/netizen4_bit]"
    "(https://www.patreon.com/c/netizen4_bit)"
)


def _increment_and_maybe_append(result: str) -> str:
    """Increment the global usage counter.

    If the counter is now a multiple of 5, append the Patreon support
    message to *result* and return it; otherwise return *result* unchanged.
    """
    global _usage_counter
    _usage_counter += 1

    if _usage_counter % 5 == 0:
        return result + _PATREON_MESSAGE
    return result


# ===========================================================================
#  Tool 1 — send_email  (Brevo v3 HTTPS API)
# ===========================================================================
#  Mailchimp-style workflow:
#    • The USER declares: name, email, subject, message in the chat prompt.
#    • The Brevo API authenticates in the background using BREVO_API_KEY.
#    • The USER never types a password, configures SMTP, or touches a file.
#    • Delivery goes over HTTPS (port 443) — never blocked by any ISP.
# ===========================================================================
@mcp.tool()
async def send_email(
    recipient_email: str,
    sender_name: str,
    sender_email: str,
    subject: str,
    message: str,
    ctx: Context = None,
) -> str:
    """Send an email via the Brevo v3 transactional HTTPS API.

    The user declares their name, email, subject, and message body.
    No passwords, no SMTP — the Brevo API key is loaded from the
    BREVO_API_KEY environment variable.  300 emails/day free.

    Args:
        recipient_email: Recipient's email address (required).
        sender_name:     Your full name for the From line
                         (e.g. "Riyad Gasimov").
        sender_email:    Your email address for the From line
                         (e.g. "sales@doradoland.com").
        subject:         Email subject line (required).
        message:         Email body text / message content (required).
        ctx:             FastMCP Context — injected automatically.

    Returns:
        A human-readable status string.
    """

    # ── Conversational fallback ──────────────────────────────────────────
    missing = []
    if not sender_name:
        missing.append("your full name (e.g. Riyad Gasimov)")
    if not sender_email:
        missing.append("your email address (e.g. sales@doradoland.com)")
    if not subject:
        missing.append("a subject line for the email")
    if not message:
        missing.append("the message body / content")

    if missing:
        needed = " and ".join(missing) if len(missing) <= 2 else (
            ", ".join(missing[:-1]) + f", and {missing[-1]}"
        )
        result = (
            f"I'd be happy to send that email for you!  I just need {needed}.  "
            f"No passwords or configuration needed."
        )
        return _increment_and_maybe_append(result)

    # ── Load Brevo API key from environment ──────────────────────────────
    api_key = os.environ.get("BREVO_API_KEY", "")

    if not api_key:
        result = (
            "⚠️ The Brevo API key is not configured.  The server operator "
            "needs to set the BREVO_API_KEY environment variable "
            "(get one at https://app.brevo.com/settings/keys/api)."
        )
        return _increment_and_maybe_append(result)

    if ctx:
        await ctx.info(
            f"Sending via Brevo API.  "
            f"From: {sender_name} <{sender_email}> → To: {recipient_email}."
        )

    # ── Build the Brevo v3 payload ───────────────────────────────────────
    payload = {
        "sender": {"name": sender_name, "email": sender_email},
        "to": [{"email": recipient_email}],
        "subject": subject,
        "textContent": message,
    }

    headers = {
        "api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    # ── Send via HTTPS POST ──────────────────────────────────────────────
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                _BREVO_API_URL, json=payload, headers=headers
            )

        if response.status_code in (200, 201):
            try:
                msg_id = response.json().get("messageId", "unknown")
            except Exception:
                msg_id = "unknown"

            if ctx:
                await ctx.info(f"Email sent successfully (ID: {msg_id}).")
            result = (
                f"✅ Email sent from {sender_name} <{sender_email}> "
                f"to {recipient_email}.  (ID: {msg_id})\n"
                f"⚠️ Note: If the email does not arrive, please check the Brevo "
                f"'Transactional > Logs' dashboard, and verify that your sender "
                f"domain's SPF/DKIM records are fully authenticated in Brevo."
            )

        elif response.status_code == 401:
            if ctx:
                await ctx.error("Brevo API authentication failed (401).")
            result = (
                "❌ Brevo rejected the API key (401 Unauthorized).  "
                "Please verify the BREVO_API_KEY environment variable."
            )

        elif response.status_code == 403:
            if ctx:
                await ctx.error(f"Brevo forbidden (403): {response.text}")
            domain = sender_email.rsplit("@", 1)[-1]
            result = (
                f"❌ Brevo returned 403 Forbidden.  The sender domain "
                f"'{domain}' may not be verified in your Brevo account.  "
                f"Details: {response.text}"
            )

        elif response.status_code == 422:
            if ctx:
                await ctx.error(f"Brevo validation error (422): {response.text}")
            result = (
                f"❌ Brevo rejected the request (422 Validation Error).  "
                f"Details: {response.text}"
            )

        else:
            if ctx:
                await ctx.error(
                    f"Brevo returned HTTP {response.status_code}: {response.text}"
                )
            result = (
                f"❌ Unexpected Brevo response (HTTP {response.status_code}).  "
                f"Details: {response.text}"
            )

    except httpx.ConnectError as exc:
        if ctx:
            await ctx.error(f"Network connection failed: {exc}")
        result = (
            f"❌ Could not connect to Brevo API.  "
            f"Please check your network connection.  Error: {exc}"
        )

    except httpx.TimeoutException as exc:
        if ctx:
            await ctx.error(f"Brevo API request timed out: {exc}")
        result = f"❌ The Brevo API request timed out.  Error: {exc}"

    except Exception as exc:  # noqa: BLE001
        if ctx:
            await ctx.error(f"Unexpected error: {exc}")
        result = f"❌ Unexpected error while sending email: {exc}"

    return _increment_and_maybe_append(result)


# ===========================================================================
#  Tool 2 — send_whatsapp  (Playwright async API, persistent session)
# ===========================================================================
#  Flow:
#    1. Launch persistent Chromium context (session saved to disk).
#    2. Navigate to WhatsApp Web with the pre-filled message URL.
#    3. Race-detect: QR code canvas  vs  message input box.
#       • QR detected → instruct user to scan, then wait up to 120s.
#       • Input detected → user is logged in, press Enter to send.
#    4. Close browser context.
# ===========================================================================
@mcp.tool()
async def send_whatsapp(
    phone_number: str,
    message: str,
    ctx: Context = None,
) -> str:
    """Send a WhatsApp message via WhatsApp Web automation (Playwright async).

    Uses a persistent Chromium profile at ~/.whatsapp_context so the
    QR-code login only needs to happen once.  If the QR code is detected,
    the tool pauses and instructs the user to scan it before proceeding.

    Args:
        phone_number: Full international phone number WITHOUT the leading
                      '+' sign (e.g. "14155552671" for US).
        message:      The text message to send.
        ctx:          FastMCP Context — injected automatically.

    Returns:
        A human-readable status string (success or error details).
    """

    # ── Lazy import of Playwright async API ──────────────────────────────
    try:
        from playwright.async_api import async_playwright
        from playwright.async_api import TimeoutError as PwTimeout
    except ImportError:
        result = (
            "❌ Playwright is not installed.  Run:\n"
            "  pip install playwright && playwright install chromium"
        )
        return _increment_and_maybe_append(result)

    # ── Persistent browser profile directory ──────────────────────────────
    user_data_dir = os.path.join(os.path.expanduser("~"), ".whatsapp_context")
    os.makedirs(user_data_dir, exist_ok=True)

    # ── Sanitise phone number ────────────────────────────────────────────
    clean_number = (
        phone_number.strip().lstrip("+").replace(" ", "").replace("-", "")
    )

    wa_url = (
        f"https://web.whatsapp.com/send"
        f"?phone={clean_number}&text={message}"
    )

    if ctx:
        await ctx.info(
            f"Launching Chromium (profile: {user_data_dir}).  "
            f"Target: +{clean_number}."
        )

    # ── Automate the browser (async API) ─────────────────────────────────
    try:
        async with async_playwright() as pw:
            browser_context = await pw.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                headless=False,
                channel="msedge",
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                ],
                viewport={"width": 1280, "height": 900},
            )

            page = (
                browser_context.pages[0]
                if browser_context.pages
                else await browser_context.new_page()
            )

            await page.goto(
                wa_url, wait_until="domcontentloaded", timeout=60_000
            )

            if ctx:
                await ctx.info("WhatsApp Web loaded.  Checking login state…")

            # ── QR-code detection ────────────────────────────────────────
            # QR-code detection
            qr_selector = 'canvas'
            input_selector = 'div[contenteditable="true"][data-tab="10"]'

            # Wait for whichever appears first (max 45s).
            await page.wait_for_selector(
                f"{qr_selector}, {input_selector}",
                state="visible",
                timeout=45_000,
            )

            # Check if we need to log in (QR code is present).
            qr_element = await page.query_selector(qr_selector)
            if qr_element and await qr_element.is_visible():
                if ctx:
                    await ctx.warning(
                        "WhatsApp QR Code detected! I am generating a live-refreshing QR code viewer on your Desktop."
                    )

                qr_img_path = os.path.join(_DESKTOP_DIR, "whatsapp_qr.png")
                qr_html_path = os.path.join(_DESKTOP_DIR, "WhatsApp_Login.html")

                # Create an HTML file that auto-refreshes the image every 2 seconds
                with open(qr_html_path, "w", encoding="utf-8") as html_f:
                    html_f.write(
                        '<html><head><meta http-equiv="refresh" content="2"></head>'
                        '<body style="text-align:center; font-family:sans-serif; background:#f0f2f5; padding-top:50px;">'
                        '<h2>Scan this QR code with your WhatsApp app</h2>'
                        '<p>This image auto-refreshes every 2 seconds so it never expires!</p>'
                        '<img src="whatsapp_qr.png" style="border: 10px solid white; border-radius: 10px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); max-width: 400px;">'
                        '</body></html>'
                    )

                if ctx:
                    await ctx.info(f"Please open this file on your Desktop to scan: {qr_html_path}")

                logged_in = False
                # Loop for up to 180 seconds (60 iterations * 3s), updating screenshot
                for _ in range(60):
                    qr_still_there = await page.query_selector(qr_selector)
                    if not qr_still_there or not await qr_still_there.is_visible():
                        logged_in = True
                        break
                    
                    await qr_still_there.screenshot(path=qr_img_path)
                    await page.wait_for_timeout(3000)

                if not logged_in:
                    await browser_context.close()
                    result = (
                        "❌ QR code was not scanned in time.  "
                        f"Please run the tool again and open WhatsApp_Login.html on your Desktop immediately."
                    )
                    return _increment_and_maybe_append(result)

                if ctx:
                    await ctx.info("QR code scanned successfully! Session saved.")

                # Re-navigate to the target chat now that we're logged in.
                await page.goto(wa_url, wait_until="domcontentloaded", timeout=60_000)

            # ── Logged in — wait for the message input box ───────────────
            if ctx:
                await ctx.info("Waiting for the message input box…")

            await page.wait_for_selector(
                input_selector, state="visible", timeout=30_000
            )

            if ctx:
                await ctx.info("Message input box detected.  Sending…")

            # The message text is pre-filled via the URL query param.
            # Just press Enter to dispatch it.
            await page.keyboard.press("Enter")

            # Brief pause to let WhatsApp process the send.
            await page.wait_for_timeout(3000)

            if ctx:
                await ctx.info("Message sent.  Closing browser.")
            await browser_context.close()

        result = f"✅ WhatsApp message sent to +{clean_number}."

    except PwTimeout:
        if ctx:
            await ctx.error("Timed out waiting for WhatsApp Web.")
        result = (
            "❌ Timed out waiting for WhatsApp Web to load.  "
            "Please ensure you have scanned the QR code at least once, "
            f"then try again.  Profile: {user_data_dir}"
        )

    except Exception as exc:  # noqa: BLE001
        if ctx:
            await ctx.error(f"WhatsApp automation error: {exc}")
        result = f"❌ WhatsApp automation failed: {exc}"

    return _increment_and_maybe_append(result)


# ===========================================================================
#  Tool 3 — save_outreach_contact  (Excel .xlsx tracker)
# ===========================================================================
#  Appends a row to ~/Desktop/outreach_contacts.xlsx every time a lead is
#  contacted.  Creates the file with headers on first use.
# ===========================================================================
@mcp.tool()
async def save_outreach_contact(
    name: str,
    email: str = "",
    phone: str = "",
    notes: str = "",
    ctx: Context = None,
) -> str:
    """Save a contacted lead to the Excel outreach tracker on the Desktop.

    Each call appends one row:  Name | Email | Phone | Date | Notes.
    The file (outreach_contacts.xlsx) is created automatically on the
    user's Desktop if it does not already exist.

    Args:
        name:   Contact's full name (required).
        email:  Contact's email address (optional).
        phone:  Contact's phone number (optional).
        notes:  Free-text notes about the outreach (optional).
        ctx:    FastMCP Context — injected automatically.

    Returns:
        A confirmation string with the saved details.
    """

    if not name:
        result = (
            "I need at least the contact's name to save the record.  "
            "Could you provide it?"
        )
        return _increment_and_maybe_append(result)

    # ── Ensure the Desktop directory exists ───────────────────────────────
    os.makedirs(_DESKTOP_DIR, exist_ok=True)

    # ── Current timestamp ────────────────────────────────────────────────
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ── Open or create the Excel workbook ────────────────────────────────
    try:
        if os.path.exists(_CONTACTS_FILE):
            wb = openpyxl.load_workbook(_CONTACTS_FILE)
            ws = wb.active
        else:
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Outreach Contacts"
            # Write header row.
            headers = ["Name", "Email", "Phone", "Date", "Notes"]
            for col_idx, header in enumerate(headers, start=1):
                cell = ws.cell(row=1, column=col_idx, value=header)
                cell.font = openpyxl.styles.Font(bold=True)
            # Set reasonable column widths.
            ws.column_dimensions["A"].width = 25   # Name
            ws.column_dimensions["B"].width = 30   # Email
            ws.column_dimensions["C"].width = 20   # Phone
            ws.column_dimensions["D"].width = 22   # Date
            ws.column_dimensions["E"].width = 40   # Notes

        # ── Append the new contact row ───────────────────────────────────
        next_row = ws.max_row + 1
        ws.cell(row=next_row, column=1, value=name)
        ws.cell(row=next_row, column=2, value=email)
        ws.cell(row=next_row, column=3, value=phone)
        ws.cell(row=next_row, column=4, value=date_str)
        ws.cell(row=next_row, column=5, value=notes)

        wb.save(_CONTACTS_FILE)
        wb.close()

        total_rows = next_row - 1  # Exclude header.

        if ctx:
            await ctx.info(
                f"Contact saved to {_CONTACTS_FILE} (row {next_row}, "
                f"total contacts: {total_rows})."
            )
        result = (
            f"✅ Contact saved to outreach tracker:\n"
            f"   Name:  {name}\n"
            f"   Email: {email or '—'}\n"
            f"   Phone: {phone or '—'}\n"
            f"   Date:  {date_str}\n"
            f"   Notes: {notes or '—'}\n"
            f"   File:  {_CONTACTS_FILE}  ({total_rows} contacts total)"
        )

    except Exception as exc:  # noqa: BLE001
        if ctx:
            await ctx.error(f"Failed to save contact: {exc}")
        result = f"❌ Could not save contact to Excel file: {exc}"

    return _increment_and_maybe_append(result)


# ===========================================================================
#  Entry point — auto-update then start the MCP server
# ===========================================================================
if __name__ == "__main__":
    # ------------------------------------------------------------------
    #  Auto-update: pull the latest code from the git remote.
    # ------------------------------------------------------------------
    try:
        update_result = subprocess.run(
            ["git", "pull"],
            cwd=os.path.dirname(os.path.abspath(__file__)),
            capture_output=True,
            text=True,
            timeout=15,
        )
        if update_result.returncode == 0:
            print(
                f"[reachdirect] git pull: {update_result.stdout.strip()}",
                file=sys.stderr,
            )
        else:
            print(
                f"[reachdirect] git pull warning: {update_result.stderr.strip()}",
                file=sys.stderr,
            )
    except FileNotFoundError:
        pass
    except subprocess.TimeoutExpired:
        pass
    except Exception:
        pass

    # ------------------------------------------------------------------
    #  Start the FastMCP server (stdio transport).
    # ------------------------------------------------------------------
    mcp.run()
