from datetime import datetime, timedelta
import json
import time
from typing import List, Dict, Any, Optional

import pytz
import requests

import grocery_shopping.config as config
import grocery_shopping.groceries as groceries
import grocery_shopping.ai as ai
import grocery_shopping.logging as logging


STORE_BASE_URL = "https://www.frisco.pl/app/commerce"


class User:
    def __init__(self, user_id: str, token_type: str, access_token: str):
        self.id = user_id
        self.headers = {
            "Authorization": f"{token_type} {access_token}",
            "Content-Type": "application/json",
        }


class ShoppingCart:
    def __init__(self, user: User):
        self.user = user

    def clear(self):
        url = f"{STORE_BASE_URL}/api/v1/users/{self.user.id}/cart/products"
        response = requests.delete(url, headers=self.user.headers)
        response.raise_for_status()
    
    def add(self, store_product_id: str, quantity: int):
        url = f"{STORE_BASE_URL}/api/v1/users/{self.user.id}/cart"
        data = {"products": [{"productId": store_product_id, "quantity": quantity}]}
        response = requests.put(url, data=json.dumps(data), headers=self.user.headers)
        response.raise_for_status()


class Delivery:
    def __init__(self, user: User, date: datetime):
        self.user = user
        self.date = date

    def get_shipping_address(self) -> Dict[str, Any]:
        url = f"{STORE_BASE_URL}/api/v1/users/{self.user.id}/addresses/shipping-addresses"
        response = requests.get(url, headers=self.user.headers)
        response.raise_for_status()
        response_json = response.json()
        return response_json[0]["shippingAddress"]

    def get_delivery_windows(self, shipping_address: Dict[str, Any]) -> List[Dict[str, Any]]:
        url = f"{STORE_BASE_URL}/api/v2/users/{self.user.id}/calendar/Van/{self.date.year}/{self.date.month}/{self.date.day}"
        data = shipping_address
        response = requests.post(url, data=json.dumps(data), headers=self.user.headers)
        response.raise_for_status()
        return response.json()

    def find_best_delivery_window(self, preferred_start_time: List[str], delivery_windows: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        for start_time in preferred_start_time:
            hour, minute = start_time.split(":")
            start_date = self.date.replace(
                hour=int(hour), minute=int(minute), second=0, microsecond=0
            )
            for delivery_window in delivery_windows:
                if delivery_window["canReserve"] and delivery_window["deliveryWindow"][
                    "startsAt"
                ] == start_date.isoformat(timespec="seconds"):
                    return delivery_window["deliveryWindow"]
        return None    

    def reserve_delivery(self, shipping_address: Dict[str, Any], delivery_window: Dict[str, Any]) -> None:
        url = f"{STORE_BASE_URL}/api/v2/users/{self.user.id}/cart/reservation"
        data = {
            "deliveryWindow": delivery_window,
            "shippingAddress": shipping_address,
        }
        response = requests.post(url, data=json.dumps(data), headers=self.user.headers)
        response.raise_for_status()


class ProductsFeed:
    @staticmethod
    def download() -> Dict[str, Dict[str, str]]:
        url = "https://commerce.frisco.pl/api/v1/integration/feeds/public?language=pl"
        response = requests.get(url)
        response.raise_for_status()
        products = response.json()["products"]
        result = {}

        for product in products:
            result[product["productId"]] = {
                "components": product.get("contentData", "").get("components", "")
            }
        return result


class ProductsSearch:
    def __init__(self, user: User):
        self.user = user

    def search(self, product_name: str) -> List[Dict[str, Any]]:
        url = f"{STORE_BASE_URL}/api/v1/users/{self.user.id}/offer/products/query?purpose=Listing&pageIndex=1&search={product_name}&includeFacets=true&deliveryMethod=Van&pageSize=50&language=pl&disableAutocorrect=false"
        response = requests.get(url, headers=self.user.headers)
        response.raise_for_status()
        return response.json()["products"]
    

class Store:
    def __init__(self, config_provider: config.ConfigProvider):
        self.config_provider = config_provider

    def log_in(self) -> User:
        frisco_username = self.config_provider.get_value("frisco", "username")
        frisco_password = self.config_provider.get_value("frisco", "password", is_secret=True)
        url = f"{STORE_BASE_URL}/connect/token"
        form_data = {
            "grant_type": "password",
            "username": frisco_username,
            "password": frisco_password,
        }
        headers = {
            "referer": "https://www.frisco.pl/",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        response = requests.post(url, data=form_data, headers=headers)
        response.raise_for_status()
        response_json = response.json()
        return User(response_json["user_id"], response_json["token_type"], response_json["access_token"])

    def schedule(self, user: User, preferred_start_time: List[str]) -> Optional[Dict[str, Any]]:
        warsaw_tz = pytz.timezone("Europe/Warsaw")
        tomorrow = warsaw_tz.localize(datetime.now() + timedelta(days=1))
        delivery = Delivery(user, tomorrow)
        shipping_address = delivery.get_shipping_address()
        delivery_windows = delivery.get_delivery_windows(shipping_address)
        delivery_window = delivery.find_best_delivery_window(preferred_start_time, delivery_windows)
        if delivery_window is None:
            return None
        delivery.reserve_delivery(shipping_address, delivery_window)
        return delivery_window
    
    def shop(self, user: User, grocery_list: List[groceries.GroceryItem]) -> List[groceries.GroceryItem]:
        shopping_cart = ShoppingCart(user)
        products_search = ProductsSearch(user)
        model = ai.LLM(self.config_provider, ProductsFeed.download())
        logger = logging.Logger(self.config_provider)

        shopping_cart.clear()
        log_shopping_id = logger.log_shopping_start("Frisco", datetime.now())
        bought_grocery_items = []

        for grocery_item in grocery_list:
            found_products = products_search.search(grocery_item.name)
            available_products = [product for product in found_products if product["product"].get("isAvailable")]
            choice = model.ask(grocery_item.name, available_products)        
            if choice.is_product_chosen:
                assert choice.product is not None, "Product should not be None when is_product_chosen is True"
                shopping_cart.add(choice.product.id, grocery_item.quantity)
                bought_grocery_items.append(grocery_item)
            logger.log_choice(log_shopping_id, grocery_item, choice)
            time.sleep(5)

        logger.log_shopping_end(log_shopping_id, datetime.now())
        return bought_grocery_items
    