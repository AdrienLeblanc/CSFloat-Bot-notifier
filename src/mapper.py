from tiers import Tiers

class EmbedMapper:
    @staticmethod
    def map_to_new_offer(item, listing, usd_to_eur):
        listing_id = str(listing["id"])
        price_usd = listing["price"] / 100
        price_eur = price_usd * usd_to_eur
        flt = listing["item"]["float_value"]
        note = listing.get("description")
        tier = Tiers.determine(item['def_index'], item['paint_index'])
        link = f"https://csfloat.com/item/{listing_id}"

        fields = [
            {
                "name": "💰 Price",
                "value": f"**{price_eur:.2f}€** (**${price_usd:.2f}**)",
                "inline": True
            },
            {
                "name": "💎 Float",
                "value": f"{flt}",
                "inline": True
            },
        ]
        if tier is not None:
            fields.append({
                "name": "🏅 Tier",
                "value": f"{tier}",
                "inline": True
            })
        if note is not None:
            fields.append({
                "name": "📝 Note",
                "value": f"{note}",
                "inline": True
            })
        return {
            "title": "🆕 New offer detected!",
            "description": f"**{item['name']}**",
            "color": 0x2ecc71,
            "fields": fields,
            "url": link,
            "footer": {"text": "CSFloat Bot"},
        }

    @staticmethod
    def map_to_edited_offer(item, prev, listing, usd_to_eur):
        prev_price_eur = prev["price"] * usd_to_eur
        listing_id = str(listing["id"])
        price_usd = listing["price"] / 100
        price_eur = price_usd * usd_to_eur
        delta = price_eur - prev_price_eur
        percent = (abs(delta) / prev_price_eur) * 100 if prev_price_eur else 0
        flt = listing["item"]["float_value"]
        tier = Tiers.determine(item['def_index'], item['paint_index'])
        note = listing.get("description")
        link = f"https://csfloat.com/item/{listing_id}"

        if price_usd < prev["price"]:
            change_msg = f"Decrease of **{abs(delta):.2f}€** (-{percent:.2f}%)"
            color = 0x27ae60  # Green
        else:
            change_msg = f"Increase of **{abs(delta):.2f}€** (+{percent:.2f}%)"
            color = 0xe67e22  # Orange
        fields = [
            {
                "name": "Previous price",
                "value": f"**{prev_price_eur:.2f}€** (**${prev['price']:.2f}**)",
                "inline": True
            },
            {
                "name": "New price",
                "value": f"**{price_eur:.2f}€** (**${price_usd:.2f}**)",
                "inline": True
            },
            {
                "name": "Change",
                "value": change_msg,
                "inline": False
            },
            {
                "name": "💎 Float",
                "value": f"{flt}",
                "inline": True
            },
        ]
        if tier is not None:
            fields.append({
                "name": "🏅 Tier",
                "value": f"{tier}",
                "inline": True
            })
        if note is not None:
            fields.append({
                "name": "📝 Note",
                "value": f"{note}",
                "inline": True
            })
        return {
            "title": "🔄 Price change detected!",
            "description": f"**{item['name']}**",
            "color": color,
            "fields": fields,
            "url": link,
            "footer": {"text": "CSFloat Bot"},
        }
