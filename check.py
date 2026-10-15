import os
import asyncio
import requests
from playwright.async_api import async_playwright

PRODUCT_URL = "https://www.levi.com/DE/de_DE/bekleidung/damen/jeans/gerader-schnitt/501-90er-ankle-jeans/p/A91500016"
TARGET_SIZE = "31/29"

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

def send_telegram(message: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(url, json={
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }, timeout=15)

async def is_available() -> bool:
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
            locale="de-DE",
            viewport={"width": 1366, "height": 768},
            extra_http_headers={
                "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
            }
        )
        page = await context.new_page()

        try:
            print("Opening page...")
            response = await page.goto(PRODUCT_URL, wait_until="domcontentloaded", timeout=60000)
            print(f"HTTP status: {response.status if response else 'None'}")

            await page.wait_for_timeout(6000)

            title = await page.title()
            print(f"Page title: {title}")

            # Detect if we got blocked
            content = await page.content()
            if "Access Denied" in content or "access denied" in content.lower() or "errors.edgesuite" in content:
                print(">>> BLOCKED by Levi’s / Akamai")
                return False

            # Try to find size buttons
            size_buttons = await page.query_selector_all(
                'button, [role="button"], [data-size], [data-testid*="size"], '
                '[aria-label*="Größe"], [aria-label*="Size"], [class*="size"]'
            )
            print(f"Found {len(size_buttons)} possible buttons")

            found_texts = []
            for btn in size_buttons:
                text = (await btn.inner_text() or "").strip()
                aria = (await btn.get_attribute("aria-label") or "").strip()
                data_size = (await btn.get_attribute("data-size") or "").strip()
                data_value = (await btn.get_attribute("data-attr-value") or "").strip()

                combined = f"{text} | {aria} | {data_size} | {data_value}".strip(" |")
                if combined and len(combined) < 40:
                    found_texts.append(combined)

                lower = combined.lower()
                if ("31/29" in lower or 
                    ("31" in lower and "29" in lower) or
                    "w31" in lower or "l29" in lower):

                    disabled = await btn.get_attribute("disabled")
                    aria_disabled = await btn.get_attribute("aria-disabled")
                    classes = (await btn.get_attribute("class") or "").lower()

                    if (disabled or aria_disabled == "true" or 
                        "disabled" in classes or "out-of-stock" in classes or 
                        "unavailable" in classes or "sold-out" in classes):
                        print(f"Size found but OUT OF STOCK → {combined}")
                        return False

                    print(f"Size AVAILABLE → {combined}")
                    return True

            print("Size texts I could see:")
            for t in found_texts[:15]:
                print(f"  - {t}")
            print("Size 31/29 not found")
            return False

        except Exception as e:
            print(f"Error: {e}")
            return False
        finally:
            await browser.close()

async def main():
    available = await is_available()
    if available:
        msg = (
            f"✅ <b>Levi’s 501 90s Ankle – Größe 31/29 ist verfügbar!</b>\n\n"
            f"<a href='{PRODUCT_URL}'>Jetzt öffnen & kaufen</a>"
        )
        send_telegram(msg)
        print("Telegram notification sent!")
    else:
        print("Still unavailable")

if __name__ == "__main__":
    asyncio.run(main())
