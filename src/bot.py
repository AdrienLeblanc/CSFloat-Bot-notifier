import requests
import time
import json
import os
import subprocess
from datetime import datetime
from dotenv import load_dotenv

# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')

if getattr(sys, 'frozen', False):
    # Exécution depuis un .exe PyInstaller
    BASE_DIR = os.path.dirname(sys.executable)
else:
    # Exécution normale (script Python)
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Charge d'abord .env, puis .env.secrets (qui écrase les valeurs si besoin)
load_dotenv(os.path.join(BASE_DIR, '../.env'))
load_dotenv(os.path.join(BASE_DIR, '../.env.secrets'), override=True)

DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")
DISCORD_USER_ID = os.getenv("DISCORD_USER_ID")
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", 60))
CSFLOAT_TOKEN = os.getenv("CSFLOAT_TOKEN")
OPEN_EXCHANGE_RATES_TOKEN = os.getenv("OPEN_EXCHANGE_RATES_TOKEN")
HISTORY_FILE = os.path.join(BASE_DIR, "../history.json")

# Liste des items à surveiller
ITEMS = [
    {
        "name": "★ M9 Bayonet | Crimson Web",
        "def_index": 508,   # M9 Bayonet
        "paint_index": 12,  # Crimson Web
        "max_price": 1716,  # USD
        "min_float": 0,
        "max_float": 0.15   # Minimal Wear
    },
    {
        "name": "★ Karambit | Crimson Web",
        "def_index": 507,   # Karambit
        "paint_index": 12,  # Crimson Web
        "max_price": 1716,
        "min_float": 0,
        "max_float": 0.15   # Minimal Wear
    },
]

def ensure_dependencies():
    try:
        import requests
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
    try:
        import dotenv
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "python-dotenv"])

# === Gestion de l'historique ===
def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_history(history):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)

history = load_history()

def send_discord_message(message: str):
    if DISCORD_WEBHOOK and DISCORD_USER_ID:
        try:
            mention = f"<@{DISCORD_USER_ID}>"
            requests.post(DISCORD_WEBHOOK, json={"content": f"{mention}\n{message}"})
            print(message)
        except Exception as e:
            print(f"❌ Erreur envoi Discord : {e}")

def fetch_currency_exchange_rate():
    global USD_TO_EUR
    try:
        url = f"https://openexchangerates.org/api/latest.json?app_id={OPEN_EXCHANGE_RATES_TOKEN}"
        r = requests.get(url)
        data = r.json()
        USD_TO_EUR = data["rates"]["EUR"]
    except Exception as e:
        print(f"❌ Erreur récupération taux de change : {e}")

def check_item(item):
    global history
    try:
        url = (
            "https://csfloat.com/api/v1/listings?"
            f"sort_by=lowest_price&min_float={item['min_float']}&max_float={item['max_float']}&def_index={item['def_index']}&paint_index={item['paint_index']}"
        )

        headers = {}
        if CSFLOAT_TOKEN:
            headers["Authorization"] = CSFLOAT_TOKEN

        r = requests.get(url, headers=headers)
        data = r.json()

        item_key = f"{item['def_index']}_{item['paint_index']}"
        if item_key not in history:
            history[item_key] = {}

        new_items_found = 0
        if (data.get("code") == 1):
            raise Exception(data.get("message"))

        for listing in data.get("data", []):
            listing_id = str(listing["id"])
            price_usd = listing["price"] / 100
            price_eur = price_usd * USD_TO_EUR

            previous_price = history[item_key].get(listing_id)
            flt = listing["item"]["float_value"]
            link = f"https://csfloat.com/item/{listing_id}"

            # Nouveau listing
            if previous_price is None:
                if price_usd <= item["max_price"] and flt <= item["max_float"]:
                    msg = (
                        f"🆕 **Nouvelle offre détectée !**\n"
                        f"🎯 **{item['name']}** \n"
                        f"💰 Prix: **{price_eur:.2f}€** (**${price_usd:.2f}**)\n"
                        f"💎 Float: {flt}\n"
                        f"🔗 {link}"
                    )
                    send_discord_message(msg)
                    new_items_found += 1
            # Listing déjà vu, mais prix changé
            elif previous_price != price_usd:
                previous_price_eur = previous_price * USD_TO_EUR
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
                send_discord_message(msg)
                new_items_found += 1

            # Mettre à jour l'historique avec le prix actuel
            history[item_key][listing_id] = price_usd

        if new_items_found:
            save_history(history)

    except Exception as e:
        print(f"❌ Erreur : {e}")

def main():
    ensure_dependencies()
    fetch_currency_exchange_rate()
    print(os.path.join(BASE_DIR, '../.env.secrets'))
    print("🚀 Lancement du bot...\n")
    while True:
        print("⏰ Vérification :", datetime.now().strftime("%H:%M"))
        for item in ITEMS:
            check_item(item)
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
