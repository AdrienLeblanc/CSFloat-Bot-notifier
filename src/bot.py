import requests
import time
import json
import os
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv
import sys
import threading

DEFAULT_USD_TO_EUR = 0.866

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)

class CSFloatBot:
    def __init__(self):
        if getattr(sys, 'frozen', False):
            self.BASE_DIR = os.path.dirname(sys.executable)
        else:
            self.BASE_DIR = os.path.dirname(os.path.abspath(__file__))

        load_dotenv(os.path.join(self.BASE_DIR, '../.env'))
        load_dotenv(os.path.join(self.BASE_DIR, '../.env.secrets'), override=True)

        self.DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")
        self.DISCORD_USER_ID = os.getenv("DISCORD_USER_ID")
        self.CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", 60))
        self.CSFLOAT_TOKEN = os.getenv("CSFLOAT_TOKEN")
        self.OPEN_EXCHANGE_RATES_TOKEN = os.getenv("OPEN_EXCHANGE_RATES_TOKEN")
        self.HISTORY_FILE = os.path.join(self.BASE_DIR, "../history.json")
        self.USD_TO_EUR = DEFAULT_USD_TO_EUR

        self.ITEMS = [
            {
                "name": "★ M9 Bayonet | Crimson Web",
                "def_index": 508,
                "paint_index": 12,
                "max_price": 1716,
                "min_float": 0,
                "max_float": 0.15
            },
            {
                "name": "★ Karambit | Crimson Web",
                "def_index": 507,
                "paint_index": 12,
                "max_price": 1716,
                "min_float": 0,
                "max_float": 0.15
            },
        ]

        self.history = self.load_history()
        self.fetch_currency_exchange_rate()
        self.lock = threading.Lock()

    def load_history(self):
        if os.path.exists(self.HISTORY_FILE):
            with open(self.HISTORY_FILE, "r") as f:
                return json.load(f)
        return {}

    def save_history(self):
        with open(self.HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(self.history, f, indent=2, ensure_ascii=False)

    def fetch_currency_exchange_rate(self):
        if not self.OPEN_EXCHANGE_RATES_TOKEN:
            logging.warning("OPEN_EXCHANGE_RATES_TOKEN not set, using default rate.")
            self.USD_TO_EUR = DEFAULT_USD_TO_EUR
            return
        try:
            url = f"https://openexchangerates.org/api/latest.json?app_id={self.OPEN_EXCHANGE_RATES_TOKEN}"
            r = requests.get(url)
            data = r.json()
            self.USD_TO_EUR = data["rates"]["EUR"]
        except Exception as e:
            logging.error(f"Error fetching exchange rate: {e}")

    def send_discord_message(self, message: str):
        if self.DISCORD_WEBHOOK:
            try:
                mention = f"<@{self.DISCORD_USER_ID}>\n" if self.DISCORD_USER_ID else ""
                requests.post(self.DISCORD_WEBHOOK, json={"content": f"{mention}{message}"})
                logging.info(message)
            except Exception as e:
                logging.error(f"Error sending to Discord: {e}")
        else:
            logging.warning("DISCORD_WEBHOOK not set, message not sent.")

    def fetch_csfloat_data(self, item):
        url = (
            "https://csfloat.com/api/v1/listings?"
            f"sort_by=lowest_price&min_float={item['min_float']}&max_float={item['max_float']}&def_index={item['def_index']}&paint_index={item['paint_index']}"
        )
        headers = {}
        if self.CSFLOAT_TOKEN:
            headers["Authorization"] = self.CSFLOAT_TOKEN
        else:
            raise Exception("CSFLOAT_TOKEN not set")
        r = requests.get(url, headers=headers)
        data = r.json()
        if data.get("code") == 1:
            raise Exception(data.get("message"))
        return data

    def process_listing(self, item, item_key: str, listing):
        listing_id = str(listing["id"])
        price_usd = listing["price"] / 100
        price_eur = price_usd * self.USD_TO_EUR
        flt = listing["item"]["float_value"]
        now = datetime.now().isoformat()
        link = f"https://csfloat.com/item/{listing_id}"

        with self.lock:
            if item_key not in self.history:
                self.history[item_key] = {}
            if listing_id not in self.history[item_key]:
                self.history[item_key][listing_id] = {
                    "price": price_usd,
                    "float": flt,
                    "timestamp": now,
                    "changes": [
                        {"price": price_usd, "float": flt, "timestamp": now}
                    ]
                }
                if price_usd <= item["max_price"] and flt <= item["max_float"]:
                    msg = (
                        f"🆕 **New offer detected!**\n"
                        f"🎯 **{item['name']}** \n"
                        f"💰 Price: **{price_eur:.2f}€** (**${price_usd:.2f}**)\n"
                        f"💎 Float: {flt}\n"
                        f"🔗 {link}"
                    )
                    self.send_discord_message(msg)
                    self.save_history()
            else:
                prev = self.history[item_key][listing_id]
                if prev["price"] != price_usd:
                    prev_price_eur = prev["price"] * self.USD_TO_EUR
                    delta = price_eur - prev_price_eur
                    percent = (abs(delta) / prev_price_eur) * 100 if prev_price_eur else 0
                    if price_usd < prev["price"]:
                        change_msg = f"Price drop of **{abs(delta):.2f}€**! (-{percent:.2f}%)\n"
                    else:
                        change_msg = f"Price increase of **{abs(delta):.2f}€**. (+{percent:.2f}%)\n"
                    msg = (
                        f"🔄 **Price change detected!**\n"
                        f"🎯 **{item['name']}** \n"
                        f"💰 Old price: **{prev_price_eur:.2f}€** (**${prev['price']:.2f}**) → New price: **{price_eur:.2f}€** (**${price_usd:.2f}**)\n"
                        f"🏷️ {change_msg}"
                        f"💎 Float: {flt}\n"
                        f"🔗 {link}"
                    )
                    self.send_discord_message(msg)
                    prev["changes"].append({"price": price_usd, "float": flt, "timestamp": now})
                    prev["price"] = price_usd
                    prev["float"] = flt
                    prev["timestamp"] = now
                    self.save_history()

    def check_item(self, item):
        try:
            data = self.fetch_csfloat_data(item)
            item_key = f"{item['name']}"
            for listing in data.get("data", []):
                self.process_listing(item, item_key, listing)
        except Exception as e:
            logging.error(f"Error: {e}")

    def stats_message(self, period_hours=24):
        now = datetime.now()
        since = now - timedelta(hours=period_hours)
        new_offers = 0
        price_changes = 0
        min_prices = {}

        with self.lock:
            for item in self.ITEMS:
                item_key = item["name"]
                min_price = None
                min_float = None
                for listing_id, info in self.history.get(item_key, {}).items():
                    try:
                        ts = datetime.fromisoformat(info["timestamp"])
                    except Exception:
                        continue
                    if ts >= since:
                        new_offers += 1
                        price_eur = info["price"] * self.USD_TO_EUR
                        if min_price is None or price_eur < min_price:
                            min_price = price_eur
                            min_float = info["float"]
                    for change in info.get("changes", []):
                        try:
                            cts = datetime.fromisoformat(change["timestamp"])
                        except Exception:
                            continue
                        if cts >= since:
                            price_changes += 1
                if min_price is not None:
                    min_prices[item_key] = (min_price, min_float)

        msg = f"📊 **Stats for the last {period_hours}h**\n"
        msg += f"- New offers detected: {new_offers}\n"
        msg += f"- Price changes: {price_changes}\n"
        for item in self.ITEMS:
            item_key = item["name"]
            if item_key in min_prices:
                price, flt = min_prices[item_key]
                msg += f"- Lowest offer for {item_key}: {price:.2f}€ (float {flt})\n"
        return msg

    def stats_listener(self):
        import msvcrt  # Windows only
        while True:
            if msvcrt.kbhit():
                key = msvcrt.getch()
                if key in (b's', b'S'):
                    print("\n" + self.stats_message())
            time.sleep(0.1)

    def run(self):
        logging.info("Bot started...\n")
        threading.Thread(target=self.stats_listener, daemon=True).start()
        while True:
            logging.info("⏰ Checking at: %s", datetime.now().strftime("%H:%M"))
            for item in self.ITEMS:
                self.check_item(item)
            time.sleep(self.CHECK_INTERVAL)

if __name__ == "__main__":
    bot = CSFloatBot()
    bot.run()
