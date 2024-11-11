import config
import requests
import re


todoist_secret = config.get_value("todoist", "secret", is_secret=True)
todoist_project_id = config.get_value("todoist", "project_id")


def get_grocery_list():
    url = f"https://api.todoist.com/rest/v2/tasks?project_id={todoist_project_id}"
    headers = {"Authorization": f"Bearer {todoist_secret}"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    response_json = response.json()
    tasks = response_json

    products_to_buy = {}

    for task in tasks:
        product_name = task["content"]
        product_with_quantity = re.match("(.*?) ([0-9]+)$", product_name)
        if product_with_quantity:
            products_to_buy[product_with_quantity.group(1)] = int(
                product_with_quantity.group(2)
            )
        else:
            products_to_buy[product_name] = 1

    return products_to_buy
