import json
from datetime import datetime

import requests

import grocery_shopping.config as config
from grocery_shopping.groceries import GroceryItem
from grocery_shopping.ai import Choice


PAGES_BASE_URL = "https://api.notion.com/v1/pages"


class Logger:
    def __init__(self, config_provider: config.ConfigProvider):
        notion_secret = config_provider.get_value("notion", "secret", is_secret=True)
        self.grocery_shopping_database_id = config_provider.get_value("notion", "grocery_shopping_database_id")
        self.choice_database_id = config_provider.get_value("notion", "choice_database_id")
        self.headers = {
            "Authorization": f"Bearer {notion_secret}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        }

    def log_shopping_start(self, store_name: str, start_time: datetime) -> str:
        data = {
            "parent": {"database_id": self.grocery_shopping_database_id},
            "properties": {
                "Store name": {"title": [{"text": {"content": store_name}}]},
                "Start time": {"date": {"start": start_time.isoformat(timespec="seconds")}}
            },
        }
        response = requests.post(PAGES_BASE_URL, data=json.dumps(data), headers=self.headers)
        response.raise_for_status()
        return response.json()["id"]

    def log_shopping_end(self, grocery_shopping_id: str, end_time: datetime) -> str:
        url = f"{PAGES_BASE_URL}/{grocery_shopping_id}"
        data = {
            "properties": {
                "End time": {"date": {"start": end_time.isoformat(timespec="seconds")}}
            }
        }
        response = requests.patch(url, data=json.dumps(data), headers=self.headers)
        response.raise_for_status()
        return response.json()["id"]

    def log_choice(self, grocery_shopping_id: str, grocery_item: GroceryItem, choice: Choice) -> str:
        if choice.is_product_chosen:
            assert choice.product is not None, "Product should not be None when is_product_chosen is True"
            data = {
                "parent": {"database_id": self.choice_database_id},
                "properties": {
                    "Product name": {"title": [{"text": {"content": grocery_item.name}}]},
                    "Store product id": {
                        "rich_text": [{"type": "text", "text": {"content": choice.product.id}}]
                    },
                    "Store product name": {
                        "rich_text": [{"type": "text", "text": {"content": choice.product.name}}]
                    },
                    "Grocery shopping": {"relation": [{"id": grocery_shopping_id}]},
                    "Quantity": {"number": grocery_item.quantity},
                    "Reason": {"rich_text": [{"type": "text", "text": {"content": choice.reason}}]},
                    "Price": {"number": choice.product.price},
                    "Price after promotion": {"number": choice.product.price_after_promotion},
                },
            }
        else:
            data = {
                "parent": {"database_id": self.choice_database_id},
                "properties": {
                    "Product name": {"title": [{"text": {"content": grocery_item.name}}]},
                    "Grocery shopping": {"relation": [{"id": grocery_shopping_id}]},
                    "Quantity": {"number": grocery_item.quantity},
                    "Reason": {"rich_text": [{"type": "text", "text": {"content": choice.reason}}]},
                },
            }
        response = requests.post(PAGES_BASE_URL, data=json.dumps(data), headers=self.headers)
        response.raise_for_status()
        return response.json()["id"]
    