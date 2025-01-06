import config
import requests
import re


todoist_secret = config.get_value("todoist", "secret", is_secret=True)
todoist_project_id = config.get_value("todoist", "project_id")

class GroceryItem:
    def __init__(self, name, quantity, task_id):
        self.name = name
        self.quantity = quantity
        self.task_id = task_id

    def __str__(self):
        return f"{self.quantity}x {self.name}"


def get_grocery_list():
    url = f"https://api.todoist.com/rest/v2/tasks?project_id={todoist_project_id}"
    headers = {"Authorization": f"Bearer {todoist_secret}"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    response_json = response.json()
    tasks = response_json

    products_to_buy = []

    for task in tasks:
        product_name = task["content"]

        if product_name.startswith("local"):
            continue

        product_with_quantity = re.match("^([0-9]+)x (.*?)$", product_name)
        if product_with_quantity:
            products_to_buy.append(
                GroceryItem(
                    product_with_quantity.group(2),
                    int(product_with_quantity.group(1)),
                    task["id"],
                )
            )
        else:
            products_to_buy.append(
                GroceryItem(
                    product_name,
                    1,
                    task["id"],
                )
            )

    return products_to_buy


def add_grocery_item(ingredient_name, quantity):
    url = f"https://api.todoist.com/rest/v2/tasks?project_id={todoist_project_id}"
    headers = {"Authorization": f"Bearer {todoist_secret}"}
    data = {"content": f"{quantity}x {ingredient_name}"}
    if quantity == 1:
        data = {"content": ingredient_name}
    response = requests.post(url, data=data, headers=headers)
    response.raise_for_status()


def complete_tasks(tasks_to_complete):
    for task_id in tasks_to_complete:
        url = f"https://api.todoist.com/rest/v2/tasks/{task_id}/close"
        headers = {"Authorization": f"Bearer {todoist_secret}"}
        response = requests.post(url, headers=headers)
        response.raise_for_status()