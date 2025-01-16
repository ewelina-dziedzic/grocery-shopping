import json
from typing import List, Optional

import requests

import grocery_shopping.config as config


class ShoppingListItem:
    def __init__(self, name: str, quantity: int, needed_for_date: Optional[str], store_link: str):
        self.name = name
        self.quantity = quantity
        self.needed_for_date = needed_for_date
        self.store_link = store_link


class MealPlan:
    def __init__(self, config_provider: config.ConfigProvider):
        self.notion_secret = config_provider.get_value("notion", "secret", is_secret=True)
        self.notion_database_id = config_provider.get_value("notion", "ingredients_database_id")

    def get_shopping_list(self) -> List[ShoppingListItem]:
        shopping_list = []
        url = f"https://api.notion.com/v1/databases/{self.notion_database_id}/query"
        headers = {
            "Authorization": f"Bearer {self.notion_secret}",
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
            shopping_list.append(
                ShoppingListItem(
                    ingredient["properties"]["Ingredient"]["title"][0]["plain_text"],
                    ingredient["properties"]["Quantity"]["number"] or 1,
                    ingredient["properties"]["Needed for date"]["formula"]["date"]["start"] if "date" in ingredient["properties"]["Needed for date"]["formula"] else None,
                    ingredient["properties"]["Frisco"]["formula"]["string"],
                )
            )
        return shopping_list
    