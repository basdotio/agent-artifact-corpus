#!/usr/bin/env python3
"""
CRE Scraper - Crexi + LoopNet
Scrapes commercial real estate listings and stores in deals.db
"""

import asyncio
import sqlite3
import hashlib
import json
import os
import sys
import argparse
from datetime import datetime
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

DB_PATH = os.path.expanduser("~/.openclaw/workspace/data/deals.db")

# Default filters (overridable via args)
DEFAULT_ASSET_TYPES = ["rv park", "self storage", "marina"]
DEFAULT_STATES = ["FL", "GA", "SC", "NC", "TN", "AL", "MS"]
DEFAULT_MIN_PRICE = 1_000_000
DEFAULT_MAX_PRICE = 10_000_000
DEFAULT_MIN_CAP = 8.0

CREXI_ASSET_MAP = {
    "rv park": "rv-parks",
    "self storage": "self-storage",
    "marina": "marinas"
}

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def make_hash(url, address):
    return hashlib.md5(f"{url}{address}".encode()).hexdigest()

def save_lead(source, url, address, city, state, asset_type, asking_price, raw_data):
    conn = get_db()
    h = make_hash(url, address)
    try:
        conn.execute("""
            INSERT INTO leads (hash, source, url, address, city, state, asset_type, asking_price, raw_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (h, source, url, address, city, state, asset_type, asking_price, json.dumps(raw_data)))
        conn.execute("""
            INSERT INTO pipeline (lead_id, stage) VALUES (
                (SELECT id FROM leads WHERE hash = ?), 'new'
            )
        """, (h,))
        conn.commit()
        print(f"  ✓ Saved: {address}, {city} {state} - ${asking_price:,.0f}")
        return True
    except sqlite3.IntegrityError:
        print(f"  ~ Skip (exists): {address}")
        return False
    finally:
        conn.close()

async def scrape_crexi(asset_types, states, min_price, max_price, min_cap):
    results = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = await context.new_page()
        await Stealth().apply_stealth_async(page)

        for asset_type in asset_types:
            slug = CREXI_ASSET_MAP.get(asset_type.lower())
            if not slug:
                continue

            for state in states:
                url = (
                    f"https://www.crexi.com/properties?types={slug}"
                    f"&states={state}"
                    f"&minPrice={min_price}"
                    f"&maxPrice={max_price}"
                )
                print(f"\n[Crexi] {asset_type} in {state}...")
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    await page.wait_for_timeout(3000)

                    listings = await page.query_selector_all("[data-testid='property-card']")
                    print(f"  Found {len(listings)} listings")

                    for listing in listings:
                        try:
                            title = await listing.query_selector("[data-testid='property-name']")
                            price = await listing.query_selector("[data-testid='property-price']")
                            location = await listing.query_selector("[data-testid='property-location']")
                            cap = await listing.query_selector("[data-testid='cap-rate']")
                            link = await listing.query_selector("a")

                            title_text = await title.inner_text() if title else ""
                            price_text = await price.inner_text() if price else "0"
                            location_text = await location.inner_text() if location else ""
                            cap_text = await cap.inner_text() if cap else "0"
                            href = await link.get_attribute("href") if link else ""

                            # Parse price
                            price_clean = float(
                                price_text.replace("$", "").replace(",", "").replace("M", "000000")
                                .replace("K", "000").split()[0]
                            ) if price_text else 0

                            # Parse cap rate
                            cap_clean = float(cap_text.replace("%", "").strip()) if cap_text else 0

                            # Apply cap rate filter
                            if cap_clean > 0 and cap_clean < min_cap:
                                continue

                            # Parse location
                            parts = location_text.split(",")
                            city = parts[0].strip() if parts else ""
                            st = parts[1].strip() if len(parts) > 1 else state

                            full_url = f"https://www.crexi.com{href}" if href.startswith("/") else href

                            saved = save_lead(
                                source="crexi",
                                url=full_url,
                                address=title_text,
                                city=city,
                                state=st,
                                asset_type=asset_type,
                                asking_price=price_clean,
                                raw_data={
                                    "title": title_text,
                                    "price": price_text,
                                    "cap_rate": cap_text,
                                    "location": location_text
                                }
                            )
                            if saved:
                                results.append(full_url)

                        except Exception as e:
                            print(f"  ! Error parsing listing: {e}")
                            continue

                except Exception as e:
                    print(f"  ! Error scraping {state}: {e}")
                    continue

                await page.wait_for_timeout(2000)  # rate limit

        await browser.close()
    return results

async def scrape_loopnet(asset_types, states, min_price, max_price, min_cap):
    results = []
    email = os.environ.get("LOOPNET_EMAIL")
    [REDACTED_SECRET]"LOOPNET_PASS")

    if not email or not [REDACTED_SECRET]"[LoopNet] Skipping — LOOPNET_EMAIL / LOOPNET_PASS not set")
        return results

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
        page = await context.new_page()
        await Stealth().apply_stealth_async(page)

        # Login
        print("\n[LoopNet] Logging in...")
        try:
            await page.goto("https://www.loopnet.com/user/login/", wait_until="domcontentloaded", timeout=30000)
            await page.fill("input[name='username']", email)
            await page.fill("input[name='password']", password)
            await page.click("button[type='submit']")
            await page.wait_for_timeout(3000)
            print("  ✓ Logged in")
        except Exception as e:
            print(f"  ! Login failed: {e}")
            await browser.close()
            return results

        LOOPNET_ASSET_MAP = {
            "rv park": "rv-parks",
            "self storage": "self-storage-facilities",
            "marina": "marinas-boat-storage"
        }

        for asset_type in asset_types:
            slug = LOOPNET_ASSET_MAP.get(asset_type.lower())
            if not slug:
                continue

            for state in states:
                url = (
                    f"https://www.loopnet.com/{slug}-for-sale/{state}/"
                    f"?price={min_price}-{max_price}"
                )
                print(f"\n[LoopNet] {asset_type} in {state}...")
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    await page.wait_for_timeout(3000)

                    listings = await page.query_selector_all(".placard-tile")
                    print(f"  Found {len(listings)} listings")

                    for listing in listings:
                        try:
                            title = await listing.query_selector(".placard-title")
                            price = await listing.query_selector(".price")
                            location = await listing.query_selector(".placard-location")
                            cap = await listing.query_selector(".cap-rate")
                            link = await listing.query_selector("a")

                            title_text = await title.inner_text() if title else ""
                            price_text = await price.inner_text() if price else "0"
                            location_text = await location.inner_text() if location else ""
                            cap_text = await cap.inner_text() if cap else "0"
                            href = await link.get_attribute("href") if link else ""

                            price_clean = float(
                                price_text.replace("$", "").replace(",", "").split()[0]
                            ) if price_text else 0

                            cap_clean = float(cap_text.replace("%", "").strip()) if cap_text else 0

                            if cap_clean > 0 and cap_clean < min_cap:
                                continue

                            parts = location_text.split(",")
                            city = parts[0].strip() if parts else ""
                            st = parts[1].strip() if len(parts) > 1 else state

                            full_url = f"https://www.loopnet.com{href}" if href.startswith("/") else href

                            saved = save_lead(
                                source="loopnet",
                                url=full_url,
                                address=title_text,
                                city=city,
                                state=st,
                                asset_type=asset_type,
                                asking_price=price_clean,
                                raw_data={
                                    "title": title_text,
                                    "price": price_text,
                                    "cap_rate": cap_text,
                                    "location": location_text
                                }
                            )
                            if saved:
                                results.append(full_url)

                        except Exception as e:
                            print(f"  ! Error parsing listing: {e}")
                            continue

                except Exception as e:
                    print(f"  ! Error scraping {state}: {e}")
                    continue

                await page.wait_for_timeout(2500)

        await browser.close()
    return results

async def main():
    parser = argparse.ArgumentParser(description="CRE Scraper - Crexi + LoopNet")
    parser.add_argument("--asset-types", nargs="+", default=DEFAULT_ASSET_TYPES)
    parser.add_argument("--states", nargs="+", default=DEFAULT_STATES)
    parser.add_argument("--min-price", type=float, default=DEFAULT_MIN_PRICE)
    parser.add_argument("--max-price", type=float, default=DEFAULT_MAX_PRICE)
    parser.add_argument("--min-cap", type=float, default=DEFAULT_MIN_CAP)
    parser.add_argument("--source", choices=["crexi", "loopnet", "both"], default="both")
    args = parser.parse_args()

    print(f"CRE Scraper starting: {datetime.now().isoformat()}")
    print(f"Asset types: {args.asset_types}")
    print(f"States: {args.states}")
    print(f"Price: ${args.min_price:,.0f} - ${args.max_price:,.0f}")
    print(f"Min cap rate: {args.min_cap}%")

    total = []

    if args.source in ("crexi", "both"):
        crexi_results = await scrape_crexi(
            args.asset_types, args.states,
            args.min_price, args.max_price, args.min_cap
        )
        total.extend(crexi_results)

    if args.source in ("loopnet", "both"):
        loopnet_results = await scrape_loopnet(
            args.asset_types, args.states,
            args.min_price, args.max_price, args.min_cap
        )
        total.extend(loopnet_results)

    print(f"\n✓ Done. {len(total)} new leads saved to deals.db")

if __name__ == "__main__":
    asyncio.run(main())
