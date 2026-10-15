import os
import asyncio
import requests
from playwright.async_api import async_playwright

PRODUCT_URL = "https://www.levi.com/DE/de_DE/bekleidung/damen/jeans/gerader-schnitt/501-90er-ankle-jeans/p/A91500016"
TARGET_SIZE = "31/29"          # also matches W31 / L29 variants

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
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="de-DE",
            viewport={"width": 1280, "height": 800}
        )
        page = await context.new_page()

        try:
            await page.goto(PRODUCT_URL, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(5000)

            size_buttons = await page.query_selector_all(
                'button[data-size], [data-testid*="size"], button[aria-label*="Größe"], '
                '.size-selector button, [class*="SizeButton"], button[class*="size"], '
                '[data-attr-value], [aria-label*="31"]'
            )

            for btn in size_buttons:
                text = (await btn.inner_text() or "").strip()
                aria = (await btn.get_attribute("aria-label") or "").strip()
                data_size = (await btn.get_attribute("data-size") or "").strip()
                data_value = (await btn.get_attribute("data-attr-value") or "").strip()

                combined = f"{text} {aria} {data_size} {data_value}".lower()

                if ("31/29" in combined or 
                    ("31" in combined and "29" in combined) or
                    "w31" in combined or "l29" in combined):

                    disabled = await btn.get_attribute("disabled")
                    aria_disabled = await btn.get_attribute("aria-disabled")
                    classes = (await btn.get_attribute("class") or "").lower()

                    if (disabled or 
                        aria_disabled == "true" or 
                        "disabled" in classes or 
                        "out-of-stock" in classes or 
                        "unavailable" in classes or
                        "sold-out" in classes):
                        print(f"Size found but OUT OF STOCK → {text or aria}")
                        return False

                    print(f"Size AVAILABLE → {text or aria}")
                    return True

            print("Size 31/29 not found on the page (or page was blocked)")
            return False

        except Exception as e:
            print(f"Error while checking: {e}")
            return False
        finally:
            await browser.close()

async def main():
    if await is_available():
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
