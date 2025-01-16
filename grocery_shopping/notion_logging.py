import json
import requests

import config

NOTION_SECRET = config.get_value("notion", "secret", is_secret=True)
NOTION_STRATEGY_DATABASE_ID = config.get_value("notion", "strategy_database_id")
NOTION_GROCERY_SHOPPING_DATABASE_ID = config.get_value(
    "notion", "grocery_shopping_database_id"
)
NOTION_CHOICE_DATABASE_ID = config.get_value("notion", "choice_database_id")


def create_grocery_shopping_log(store_name, start_time):
    url = f"https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_SECRET}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }
    data = {
        "parent": {"database_id": NOTION_GROCERY_SHOPPING_DATABASE_ID},
        "properties": {
            "Store name": {"title": [{"text": {"content": store_name}}]},
            "Start time": {"date": {"start": start_time.isoformat(timespec="seconds")}}
        },
    }
    response = requests.post(url, data=json.dumps(data), headers=headers)
    response.raise_for_status()
    return response.json()["id"]


def update_grocery_shopping_log(grocery_shopping_id, end_time):
    url = f"https://api.notion.com/v1/pages/{grocery_shopping_id}"
    headers = {
        "Authorization": f"Bearer {NOTION_SECRET}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }
    data = {
        "properties": {
            "End time": {"date": {"start": end_time.isoformat(timespec="seconds")}}
        }
    }
    response = requests.patch(url, data=json.dumps(data), headers=headers)
    response.raise_for_status()
    return response.json()["id"]


def create_choice_log(
    product_name,
    grocery_shopping_id,
    store_product_id,
    store_product_name,
    quantity,
    reason,
    price,
    priceAfterPromotion,
):
    url = f"https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_SECRET}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }
    data = {
        "parent": {"database_id": NOTION_CHOICE_DATABASE_ID},
        "properties": {
            "Product name": {"title": [{"text": {"content": product_name}}]},
            "Store product id": {
                "rich_text": [{"type": "text", "text": {"content": store_product_id}}]
            },
            "Store product name": {
                "rich_text": [{"type": "text", "text": {"content": store_product_name}}]
            },
            "Grocery shopping": {"relation": [{"id": grocery_shopping_id}]},
            "Quantity": {"number": quantity},
            "Reason": {"rich_text": [{"type": "text", "text": {"content": reason}}]},
            "Price": {"number": price},
            "Price after promotion": {"number": priceAfterPromotion},
        },
    }
    response = requests.post(url, data=json.dumps(data), headers=headers)
    response.raise_for_status()
    return response.json()["id"]


def create_empty_choice_log(product_name, grocery_shopping_id, quantity, reason):
    url = f"https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_SECRET}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }
    data = {
        "parent": {"database_id": NOTION_CHOICE_DATABASE_ID},
        "properties": {
            "Product name": {"title": [{"text": {"content": product_name}}]},
            "Grocery shopping": {"relation": [{"id": grocery_shopping_id}]},
            "Quantity": {"number": quantity},
            "Reason": {"rich_text": [{"type": "text", "text": {"content": reason}}]},
        },
    }
    response = requests.post(url, data=json.dumps(data), headers=headers)
    response.raise_for_status()
    return response.json()["id"]
