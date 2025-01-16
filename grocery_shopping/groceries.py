import re
from datetime import datetime, timedelta
from typing import List

import requests

import grocery_shopping.config as config
import grocery_shopping.meal_planing as meal_planing


TASKS_BASE_URL = "https://api.todoist.com/rest/v2/tasks"


class GroceryItem:
    def __init__(self, name: str, quantity: int, task_id: str):
        self.name = name
        self.quantity = quantity
        self.task_id = task_id

    def __str__(self) -> str:
        return f"{self.quantity}x {self.name}"


class GroceryList:
    def __init__(self, config_provider: config.ConfigProvider):
        todoist_secret = config_provider.get_value("todoist", "secret", is_secret=True)
        self.todoist_project_id = config_provider.get_value("todoist", "project_id")
        self.headers = {"Authorization": f"Bearer {todoist_secret}"}

    def get(self) -> List[GroceryItem]:
        url = f"{TASKS_BASE_URL}?project_id={self.todoist_project_id}"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        tasks = response.json()
        grocery_list = []

        for task in tasks:
            product_name = task["content"]

            if product_name.startswith("local"):
                continue

            product_with_quantity = re.match(r"^([0-9]+)x (.*?)$", product_name)
            if product_with_quantity:
                grocery_list.append(
                    GroceryItem(
                        product_with_quantity.group(2),
                        int(product_with_quantity.group(1)),
                        task["id"],
                    )
                )
            else:
                grocery_list.append(GroceryItem(product_name, 1, task["id"]))
        return grocery_list

    def load(self, shopping_list: List[meal_planing.ShoppingListItem]):
        for item in shopping_list:
            if item.needed_for_date:
                needed_for_date = datetime.fromisoformat(item.needed_for_date)
                due_date = needed_for_date - timedelta(days=1)
                self._add_grocery_item(item.name, item.quantity, due_date.strftime("%Y-%m-%d"), item.store_link)
            else:
                self._add_grocery_item(item.name, item.quantity, "", item.store_link)

    def _add_grocery_item(self, ingredient_name: str, quantity: int, due_date: str, description: str):
        url = f"{TASKS_BASE_URL}?project_id={self.todoist_project_id}"
        data = {"content": f"{quantity}x {ingredient_name}", "due_string": due_date}
        if quantity == 1:
            data = {"content": ingredient_name, "due_string": due_date, "description": description}
        response = requests.post(url, data=data, headers=self.headers)
        response.raise_for_status()

    def complete(self, grocery_items: List[GroceryItem]):
        for grocery_item in grocery_items:
            url = f"{TASKS_BASE_URL}/{grocery_item.task_id}/close"
            response = requests.post(url, headers=self.headers)
            response.raise_for_status()
