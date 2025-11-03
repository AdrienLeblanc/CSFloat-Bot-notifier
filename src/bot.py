import requests
import time
import json
import os
import subprocess
from datetime import datetime
from dotenv import load_dotenv
import sys

sys.stdout.reconfigure(encoding='utf-8')

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
        self.USD_TO_EUR = 0.866

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
        self.ensure_dependencies()
        self.fetch_currency_exchange_rate()

    def ensure_dependencies(self):
        try:
            import requests
        except ImportError:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
        try:
            import dotenv
        except ImportError:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "python-dotenv"])

    def load_history(self):
        if os.path.exists(self.HISTORY_FILE):
            with open(self.HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def save_history(self):
        with open(self.HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(self.history, f, indent=2, ensure_ascii=False)

    def fetch_currency_exchange_rate(self):
        if not self.OPEN_EXCHANGE_RATES_TOKEN:
            print("⚠️ OPEN_EXCHANGE_RATES_TOKEN non défini, utilisation taux fixe 0.866")
            self.USD_TO_EUR = 0.866
            return
        try:
            url = f"https://openexchangerates.org/api/latest.json?app_id={self.OPEN_EXCHANGE_RATES_TOKEN}"
            r = requests.get(url)
            data = r.json()
            self.USD_TO_EUR = data["rates"]["EUR"]
        except Exception as e:
            print(f"❌ Erreur récupération taux de change : {e}")

    def send_discord_message(self, message: str):
        if self.DISCORD_WEBHOOK:
            try:
                mention = f"<@{self.DISCORD_USER_ID}>\n" if self.DISCORD_USER_ID else ""
                requests.post(self.DISCORD_WEBHOOK, json={"content": f"{mention}{message}"})
                print(message)
            except Exception as e:
                print(f"❌ Erreur envoi Discord : {e}")
        else:
            print("⚠️ DISCORD_WEBHOOK non défini, message non envoyé.")

    def fetch_csfloat_data(self, item):
        url = (
            "https://csfloat.com/api/v1/listings?"
            f"sort_by=lowest_price&min_float={item['min_float']}&max_float={item['max_float']}&def_index={item['def_index']}&paint_index={item['paint_index']}"
        )
        headers = {}
        if self.CSFLOAT_TOKEN:
            headers["Authorization"] = self.CSFLOAT_TOKEN
        else:
            raise Exception("CSFLOAT_TOKEN non défini")
        r = requests.get(url, headers=headers)
        data = r.json()
        if data.get("code") == 1:
            raise Exception(data.get("message"))
        return data

    def process_listing(self, item, item_key: str, listing, new_items_found):
        listing_id = str(listing["id"])
        price_usd = listing["price"] / 100
        price_eur = price_usd * self.USD_TO_EUR

        previous_price = self.history[item_key].get(listing_id)
        flt = listing["item"]["float_value"]
        link = f"https://csfloat.com/item/{listing_id}"

        if previous_price is None:
            if price_usd <= item["max_price"] and flt <= item["max_float"]:
                msg = (
                    f"🆕 **Nouvelle offre détectée !**\n"
                    f"🎯 **{item['name']}** \n"
                    f"💰 Prix: **{price_eur:.2f}€** (**${price_usd:.2f}**)\n"
                    f"💎 Float: {flt}\n"
                    f"🔗 {link}"
                )
                self.send_discord_message(msg)
                new_items_found += 1
        elif previous_price != price_usd:
            previous_price_eur = previous_price * self.USD_TO_EUR
            msg = (
                f"🔄 **Changement de prix détecté !**\n"
                f"🎯 **{item['name']}** \n"
                f"💰 Ancien prix: **{previous_price_eur:.2f}€** (**${previous_price:.2f}**) → Nouveau prix: **{price_eur:.2f}€** (**${price_usd:.2f}**)\n"
                f"🏷️ {f"Réduction de **{previous_price_eur - price_eur:.2f}€** ! (-{((previous_price_eur - price_eur) / previous_price_eur) * 100:.2f}%)\n"
                if price_usd < previous_price
                else f"Augmentation de **{price_eur - previous_price_eur:.2f}€**. (+{((price_eur - previous_price_eur) / previous_price_eur) * 100:.2f}%)\n"}"
                f"💎 Float: {flt}\n"
                f"🔗 {link}"
            )
            self.send_discord_message(msg)
            new_items_found += 1

        self.history[item_key][listing_id] = price_usd
        return new_items_found

    def check_item(self, item):
        try:
            data = self.fetch_csfloat_data(item)
            item_key = f"{item['name']}"
            if item_key not in self.history:
                self.history[item_key] = {}
            new_items_found = 0
            for listing in data.get("data", []):
                new_items_found = self.process_listing(item, item_key, listing, new_items_found)
            if new_items_found:
                self.save_history()
        except Exception as e:
            print(f"❌ Erreur : {e}")

    def run(self):
        print(os.path.join(self.BASE_DIR, '../.env.secrets'))
        print("🚀 Lancement du bot...\n")
        while True:
            print("⏰ Vérification :", datetime.now().strftime("%H:%M"))
            for item in self.ITEMS:
                self.check_item(item)
            time.sleep(self.CHECK_INTERVAL)

if __name__ == "__main__":
    bot = CSFloatBot()
    bot.run()
