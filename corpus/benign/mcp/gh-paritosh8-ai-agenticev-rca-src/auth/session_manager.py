"""
Semi-automated authentication and session persistence for ElectreeFi CMS and Partner CPO Portals.
"""

import sys
import json
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

from src.config import (
    LOGIN_URL,
    BOOKINGS_URL,
    SESSION_STORAGE_PATH,
    ELECTREEFI_USERNAME,
    ELECTREEFI_PASSWORD,
    BROWSER_TIMEOUT_MS
)


def is_session_valid_sync() -> bool:
    """Checks if stored session cookies are valid via fast direct HTTP request (0 browser launch overhead)."""
    if not SESSION_STORAGE_PATH.exists():
        return False

    try:
        import urllib.request
        import urllib.parse
        from datetime import datetime

        with open(SESSION_STORAGE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        cookies = data.get("cookies", [])
        cookie_header = "; ".join([f"{c['name']}={c['value']}" for c in cookies if "ev-charge-network.com" in c.get("domain", "")])
        if not cookie_header:
            return False

        today_str = datetime.now().strftime("%Y-%m-%d")
        test_url = f"https://cms.ev-charge-network.com/ChargingStationManagement/AdminBookingDetails/CancelledBookingDataThroughAjax?StationId=&StartDate={today_str}&Enddate={today_str}&stateId=&cityId=&transactionTypeId=-1&Id=0&vin=&chargerCode=&user=&vehicleNumber="
        headers = {
            "X-Requested-With": "XMLHttpRequest",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Cookie": cookie_header
        }
        payload = urllib.parse.urlencode({"sort": "", "page": "1", "pageSize": "1", "group": "", "filter": ""}).encode("utf-8")
        req = urllib.request.Request(test_url, data=payload, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as res:
            text = res.read().decode("utf-8", errors="replace")
            return "Data" in text and "/Account/Login" not in text
    except Exception:
        return False


async def is_session_valid() -> bool:
    """Checks if the stored session cookies are valid."""
    return is_session_valid_sync()


async def interactive_login(force: bool = False) -> str:
    """
    Launches a visible Chromium window for the user to complete CAPTCHA and OTP.
    Waits for redirect away from /Account/Login and saves session state to disk.
    """
    if not force and await is_session_valid():
        return f"Existing session is valid and active. Loaded from {SESSION_STORAGE_PATH}."

    print("\n" + "=" * 60, file=sys.stderr)
    print("ELECTREEFI CMS LOGIN (SEMI-AUTOMATED)", file=sys.stderr)
    print("Launching visible browser window...", file=sys.stderr)
    print("Please solve the CAPTCHA and enter your email OTP.", file=sys.stderr)
    print("=" * 60 + "\n", file=sys.stderr)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=["--no-first-run", "--no-default-browser-check", "--disable-extensions"]
        )
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        await page.goto(LOGIN_URL, wait_until="domcontentloaded")

        if ELECTREEFI_USERNAME:
            try:
                for selector in ["#UserName", "#Email", "input[name='UserName']", "input[type='email']"]:
                    if await page.locator(selector).count() > 0:
                        await page.fill(selector, ELECTREEFI_USERNAME)
                        break
            except Exception:
                pass

        if ELECTREEFI_PASSWORD:
            try:
                for selector in ["#Password", "input[name='Password']", "input[type='password']"]:
                    if await page.locator(selector).count() > 0:
                        await page.fill(selector, ELECTREEFI_PASSWORD)
                        break
            except Exception:
                pass

        print("Waiting for login completion and redirect...", file=sys.stderr)
        try:
            await page.wait_for_url(
                lambda url: "/Account/Login" not in url,
                timeout=180000
            )
            await page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            if "/Account/Login" in page.url:
                await browser.close()
                raise TimeoutError("Login timed out. Did not detect navigation away from the login page within 3 minutes.")

        SESSION_STORAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
        await context.storage_state(path=str(SESSION_STORAGE_PATH))
        await browser.close()

    return f"Successfully logged into ElectreeFi CMS! Session saved to {SESSION_STORAGE_PATH}."


async def interactive_login_partner(party_id: str, force: bool = False) -> str:
    """
    Launches a visible browser window for the specified partner portal (e.g. IOC, VIN, MPC),
    pre-fills username and password, waits for the user to solve CAPTCHA, and saves session state to disk.
    """
    pid = party_id.strip().upper()
    portals_file = Path("data/partner_portals.json")
    portals = {}
    if portals_file.exists():
        try:
            with open(portals_file, "r", encoding="utf-8") as f:
                portals = json.load(f)
        except Exception:
            pass

    cfg = portals.get(pid, {})
    portal_url = cfg.get("portal_url", "https://cms.ev-charge-network.com")
    login_url = cfg.get("login_url") or f"{portal_url.rstrip('/')}/Account/Login"
    username = cfg.get("username", "")
    password = cfg.get("password", "")
    session_file = Path(cfg.get("session_file") or f"data/session_{pid}.json")

    print("\n" + "=" * 60, file=sys.stderr)
    print(f"PARTNER CMS LOGIN: {pid} ({cfg.get('name', pid)})", file=sys.stderr)
    print(f"URL: {login_url}", file=sys.stderr)
    print(f"Username: {username}", file=sys.stderr)
    print("Launching visible browser window. Please solve the visual CAPTCHA...", file=sys.stderr)
    print("=" * 60 + "\n", file=sys.stderr)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=["--no-first-run", "--no-default-browser-check", "--disable-extensions"]
        )

        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        async def on_response(response):
            if "UserLogin" in response.url or "Login" in response.url:
                try:
                    text = await response.text()
                    if text.startswith("{"):
                        data = json.loads(text)
                        err_code = data.get("ErrorCode")
                        err_detail = data.get("ErrorDetail") or data.get("Message")
                        if err_detail:
                            print(f"\n[CMS Feedback] {err_detail}", file=sys.stderr)
                        elif err_code == 0:
                            print(f"\n[CMS Feedback] Invalid Captcha. Please solve the new CAPTCHA.", file=sys.stderr)
                        elif err_code == -100:
                            print(f"\n[CMS Feedback] Captcha validation is required. Please check the CAPTCHA box.", file=sys.stderr)
                        elif err_code is not None and err_code < 0:
                            print(f"\n[CMS Feedback] Login rejected (ErrorCode: {err_code})", file=sys.stderr)
                        elif data.get("LoginViaOTP"):
                            print(f"\n[CMS Feedback] OTP required! Please enter the OTP received on mobile/email in the browser.", file=sys.stderr)
                        elif err_code is not None and err_code > 0:
                            print(f"\n[CMS Feedback] Login successful! Redirecting...", file=sys.stderr)
                except Exception:
                    pass

        page.on("response", on_response)
        await page.goto(login_url, wait_until="domcontentloaded")

        # Auto-fill username if available
        if username:
            for sel in ["#LoginId", "#UserName", "#Email", "input[name='LoginId']", "input[name='UserName']"]:
                try:
                    loc = page.locator(sel)
                    if await loc.count() > 0:
                        await loc.first.fill(username)
                        break
                except Exception:
                    pass

        # Auto-fill password across both visible (#password-field) and hidden (#LoginPassword) fields
        if password:
            for sel in ["#password-field", ".passwordfield", "input[type='password']", "#Password", "#LoginPassword"]:
                try:
                    loc = page.locator(sel)
                    if await loc.count() > 0:
                        await loc.first.fill(password)
                except Exception:
                    pass

            # Sync fields via JavaScript to prevent SubmitLoginForm from wiping them out
            try:
                await page.evaluate('''(pwd) => {
                    const pf = document.getElementById('password-field');
                    const lp = document.getElementById('LoginPassword');
                    const p = document.getElementById('Password');
                    if (pf) { pf.value = pwd; pf.dispatchEvent(new Event('input', { bubbles: true })); }
                    if (lp) { lp.value = pwd; lp.dispatchEvent(new Event('input', { bubbles: true })); }
                    if (p) { p.value = pwd; p.dispatchEvent(new Event('input', { bubbles: true })); }
                    const guest = document.getElementById('IsGuestUser');
                    if (guest && guest.checked) { guest.checked = false; }
                }''', password)

            except Exception:
                pass

        # Focus captcha box if present
        for sel in ["#CaptchaResponse", "input[name='CaptchaResponse']"]:
            try:
                if await page.locator(sel).count() > 0:
                    await page.focus(sel)
                    break
            except Exception:
                pass

        print("Waiting for login completion and redirect...", file=sys.stderr)
        try:
            # Wait for redirect away from /Account/Login or reaching dashboard
            await page.wait_for_url(lambda url: "/Account/Login" not in url, timeout=180000)
            await page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            # Check if session cookies are already present even if redirect is pending
            cookies = await context.cookies()
            auth_cookies = [c for c in cookies if any(k in c.get("name", "").lower() for k in ["session", "auth", "token", "evsp"])]
            if not auth_cookies and "/Account/Login" in page.url:
                await browser.close()
                raise TimeoutError("Login timed out. Did not navigate away from /Account/Login within 3 minutes.")

        session_file.parent.mkdir(parents=True, exist_ok=True)
        await context.storage_state(path=str(session_file))
        await browser.close()

    return f"Successfully logged into {pid} CMS! Session saved to {session_file}."


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="CMS Login Manager")
    parser.add_argument("--party", default=None, help="Party ID to log into (e.g. IOC, VIN, MPC)")
    parser.add_argument("--force", action="store_true", help="Force new login")
    args = parser.parse_args()

    if args.party:
        res = asyncio.run(interactive_login_partner(args.party, force=args.force))
    else:
        res = asyncio.run(interactive_login(force=args.force))
    print(res)
