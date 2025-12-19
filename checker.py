
import asyncio
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Dict

from playwright.async_api import async_playwright

CONFIG_FILE = Path("config.json")
STATE_FILE = Path("state.json")


def load_json_file(path: Path) -> Dict:
    try:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        print(f"Missing required file: {path}")
        sys.exit(1)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON in {path}: {exc}")
        sys.exit(1)


def load_config() -> Dict:
    data = load_json_file(CONFIG_FILE)
    required_keys = {"product_url"}
    missing = required_keys - data.keys()
    if missing:
        print(f"Missing config keys: {', '.join(sorted(missing))}")
        sys.exit(1)
    return data


def load_state() -> str:
    if not STATE_FILE.exists():
        return "unknown"
    data = load_json_file(STATE_FILE)
    return str(data.get("last_status", "unknown"))


def save_state(status: str) -> None:
    STATE_FILE.write_text(json.dumps({"last_status": status}, indent=2), encoding="utf-8")


async def select_option(page, label: str) -> bool:
    button_locator = page.get_by_role("button", name=label)
    if await button_locator.count() > 0:
        await button_locator.first.click()
        return True

    text_locator = page.get_by_text(label, exact=True)
    if await text_locator.count() > 0:
        await text_locator.first.click()
        return True

    print(f"Could not find option labeled '{label}'.")
    return False


async def determine_status(page, product_url: str) -> str:
    await page.goto(product_url, wait_until="networkidle")

    await select_option(page, "Small")
    await select_option(page, "Matte Black")

    add_to_cart = page.get_by_role("button", name=re.compile("add to cart", re.IGNORECASE))
    if await add_to_cart.count() == 0:
        print("Add to cart button not found.")
        return "unknown"

    is_disabled = await add_to_cart.first.is_disabled()
    return "out_of_stock" if is_disabled else "in_stock"


async def main() -> None:
    config = load_config()
    product_url: str = config["product_url"]

    print(f"Checking product page: {product_url}")

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        current_status = await determine_status(page, product_url)
        previous_status = load_state()

        print(f"Previous status: {previous_status}")
        print(f"Current status: {current_status}")

        if previous_status == "out_of_stock" and current_status == "in_stock":
            webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
            if webhook_url:
                payload = json.dumps({"content": f"Product is back in stock: {product_url}"}).encode(
                    "utf-8"
                )
                request = urllib.request.Request(
                    webhook_url,
                    data=payload,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                try:
                    with urllib.request.urlopen(request):
                        print("Notification sent to Discord.")
                except urllib.error.HTTPError as exc:
                    print(f"Failed to send Discord notification: {exc}")
                except urllib.error.URLError as exc:
                    print(f"Could not reach Discord webhook: {exc}")
            else:
                print("DISCORD_WEBHOOK_URL is not set. Skipping Discord notification.")

            telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
            telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")
            if telegram_token and telegram_chat_id:
                telegram_url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
                telegram_payload = json.dumps(
                    {"chat_id": telegram_chat_id, "text": f"Product is back in stock: {product_url}"}
                ).encode("utf-8")
                telegram_request = urllib.request.Request(
                    telegram_url,
                    data=telegram_payload,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                try:
                    with urllib.request.urlopen(telegram_request):
                        print("Notification sent to Telegram.")
                except urllib.error.HTTPError as exc:
                    print(f"Failed to send Telegram notification: {exc}")
                except urllib.error.URLError as exc:
                    print(f"Could not reach Telegram API: {exc}")
            else:
                print("TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID is not set. Skipping Telegram notification.")

        save_state(current_status)

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
