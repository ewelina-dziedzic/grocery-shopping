import json
from datetime import datetime
from typing import Any, Dict

import grocery_shopping.config as config
import grocery_shopping.groceries as groceries
import grocery_shopping.meal_planing as meal_planing
from grocery_shopping.notifications import Notifier
import grocery_shopping.shopping as shopping


def listify(event: Any, context: Any):
    config_provider = config.ConfigProvider()
    notifier = Notifier(config_provider)

    try:
        meal_plan = meal_planing.MealPlan(config_provider)
        grocery_list = groceries.GroceryList(config_provider)
        shopping_list = meal_plan.get_shopping_list()
        grocery_list.load(shopping_list)
    except Exception as exception:
        notifier.update_status(f"💥 error: {str(exception)}")
        raise

def schedule(event: Dict[str, Any], context: Any):
    config_provider = config.ConfigProvider()
    notifier = Notifier(config_provider)

    try:
        preferred_start_time = event["preferred_start_time"]
        store = shopping.Store(config_provider)
        user = store.log_in()
        delivery_window = store.schedule(user, preferred_start_time)
        if delivery_window is None:
            notifier.update_status("❌ no delivery window found")
            return {"statusCode": 200, "body": json.dumps("No delivery window found!")}

        start_date = datetime.fromisoformat(delivery_window["startsAt"])
        end_date = datetime.fromisoformat(delivery_window["endsAt"])
        notifier.update_status(
            f"✅ delivery is scheduled at {start_date.strftime("%A %d.%m.%Y %H:%M")}-{end_date.strftime("%H:%M")}"
        )
        return {
            "statusCode": 200,
            "body": json.dumps("Scheduling completed successfully!"),
        }
    except Exception as exception:
        notifier.update_status(f"💥 error: {str(exception)}")
        raise

def shop(event: Any, context: Any):
    config_provider = config.ConfigProvider()
    notifier = Notifier(config_provider)

    try:
        grocery_list = groceries.GroceryList(config_provider)
        store = shopping.Store(config_provider)
        user = store.log_in()
        bought_grocery_items = store.shop(user, grocery_list.get())
        grocery_list.complete(bought_grocery_items)
        notifier.update_status("✅ items successfully added to your cart")
        return {
            "statusCode": 200,
            "body": json.dumps("Grocery shopping completed successfully!"),
        }
    except Exception as exception:
        notifier.update_status(f"💥 error: {str(exception)}")
        raise

if __name__ == "__main__":
    listify(None, None)
    schedule({"preferred_start_time": ["8:00", "8:30", "7:30", "9:00", "7:00", "9:30"]}, None)
    shop(None, None)
