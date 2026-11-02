#!/usr/bin/env python3
import asyncio, json, sqlite3, hashlib, os, argparse
from datetime import datetime
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

SESSION_FILE = os.path.expanduser("~/.openclaw/skills/cre-scraper/session.json")
DB_PATH = os.path.expanduser("~/.openclaw/workspace/data/deals.db")
CREXI_TYPE_MAP = {"rv park": "rv-parks", "self storage": "self-storage", "marina": "marinas"}

def save_lead(source, url, address, city, state, asset_type, asking_price, raw_data):
    conn = sqlite3.connect(DB_PATH)
    h = hashlib.md5(f"{url}{address}".encode()).hexdigest()
    try:
        conn.execute("INSERT INTO leads (hash,source,url,address,city,state,asset_type,asking_price,raw_data) VALUES (?,?,?,?,?,?,?,?,?)",
            (h, source, url, address, city, state, asset_type, asking_price, json.dumps(raw_data)))
        conn.execute("INSERT INTO pipeline (lead_id,stage) VALUES ((SELECT id FROM leads WHERE hash=?),'new')", (h,))
        conn.commit()
        print(f"  ✓ Saved: {address}, {city} {state} - ${asking_price:,.0f}")
        return True
    except sqlite3.IntegrityError:
        print(f"  ~ Skip: {address}")
        return False
    finally:
        conn.close()

async def scrape(asset_types, states, min_price, max_price, min_cap):
    results = []
    if not os.path.exists(SESSION_FILE):
        print("ERROR: Run bootstrap_session.py first.")
        return results

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
        context = await browser.new_context(storage_state=SESSION_FILE,
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1440, "height": 900}, locale="en-US", timezone_id="America/New_York")
        page = await context.new_page()
        await Stealth().apply_stealth_async(page)

        for asset_type in asset_types:
            slug = CREXI_TYPE_MAP.get(asset_type.lower())
            if not slug: continue
            for state in states:
                api_data = []
                async def handle_response(response):
                    if "api.crexi.com/assets/search" in response.url:
                        try:
                            body = await response.json()
                            api_data.append(body)
                            print(f"  ✓ API intercepted: {len(body.get('results', []))} results")
                        except: pass
                page.on("response", handle_response)
                url = f"https://www.crexi.com/properties?types={slug}&states={state}&minPrice={int(min_price)}&maxPrice={int(max_price)}"
                print(f"\n[Crexi] {asset_type} in {state}...")
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    await page.wait_for_timeout(10000)
                    for i in range(3):
                        await page.evaluate(f"window.scrollTo(0, {i*400})")
                        await page.wait_for_timeout(1500)
                    await page.wait_for_timeout(3000)
                    for data in api_data:
                        for listing in data.get("results", []):
                            try:
                                asking_price = listing.get("askingPrice", 0) or 0
                                cap_rate = listing.get("capRate", 0) or 0
                                if asking_price < min_price or asking_price > max_price: continue
                                if cap_rate > 0 and cap_rate < min_cap: continue
                                address = listing.get("address", "")
                                city = listing.get("city", "")
                                lst_state = listing.get("state", state)
                                lid = listing.get("id", "")
                                name = listing.get("name", address)
                                lurl = f"https://www.crexi.com/properties/{lid}"
                                saved = save_lead("crexi", lurl, name, city, lst_state, asset_type, asking_price,
                                    {"id": lid, "name": name, "askingPrice": asking_price, "capRate": cap_rate,
                                     "noi": listing.get("noi", 0), "address": address, "city": city,
                                     "state": lst_state, "sqft": listing.get("sqft", 0)})
                                if saved: results.append(lurl)
                            except Exception as e:
                                print(f"  ! Error: {e}")
                except Exception as e:
                    print(f"  ! Error: {e}")
                page.remove_listener("response", handle_response)
                await page.wait_for_timeout(2000)
        await browser.close()
    return results

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--asset-types", nargs="+", default=["rv park","self storage","marina"])
    parser.add_argument("--states", nargs="+", default=["FL","GA","SC","NC","TN","AL","MS"])
    parser.add_argument("--min-price", type=float, default=1000000)
    parser.add_argument("--max-price", type=float, default=10000000)
    parser.add_argument("--min-cap", type=float, default=8.0)
    args = parser.parse_args()
    print(f"CRE Scraper starting: {datetime.now().isoformat()}")
    results = await scrape(args.asset_types, args.states, args.min_price, args.max_price, args.min_cap)
    print(f"\n✓ Done. {len(results)} new leads saved.")

if __name__ == "__main__":
    asyncio.run(main())
