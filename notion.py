import config
import json
import requests
from datetime import datetime, timedelta

import todoist


notion_secret = config.get_value("notion", "secret", is_secret=True)
notion_database_id = config.get_value("notion", "ingredients_database_id")

class ShoppingListItem:
    def __init__(self, name, quantity, needed_for_date):
        self.name = name
        self.quantity = quantity
        self.needed_for_date = needed_for_date


def get_grocery_list():
    products_to_buy = []
    url = f"https://api.notion.com/v1/databases/{notion_database_id}/query"
    headers = {
        "Authorization": f"Bearer {notion_secret}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }
    data = {
        "filter": {
            "and": [
                {"property": "Got it", "checkbox": {"equals": False}},
                {"property": "To buy", "checkbox": {"equals": True}},
            ]
        }
    }
    response = requests.post(url, data=json.dumps(data), headers=headers)
    response.raise_for_status()
    response_json = response.json()
    ingredients = response_json["results"]
    for ingredient in ingredients:
        ingredient_name = ingredient["properties"]["Ingredient"]["title"][0][
            "plain_text"
        ]
        ingredient_quantity = ingredient["properties"]["Quantity"]["number"]
        products_to_buy.append(
            ShoppingListItem(
                ingredient_name,
                ingredient_quantity or 1,
                ingredient["properties"]["Needed for date"]["formula"]["date"]["start"],
            )
        )
        

    return products_to_buy


def listify(event, context):
    grocery_list = get_grocery_list()
    for item in grocery_list:
        needed_for_date = datetime.strptime(item.needed_for_date, "%Y-%m-%d")
        due_date = needed_for_date - timedelta(days=1)
        todoist.add_grocery_item(item.name, item.quantity, due_date.strftime("%Y-%m-%d"))


if __name__ == "__main__":
    listify(None, None)
