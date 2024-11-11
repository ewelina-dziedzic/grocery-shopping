import datetime
import requests
import json
import time
import pytz

import ai
import config
import notion_logging
import notion
import todoist


# consts
FRISCO_BASE_URL = "https://www.frisco.pl/app/commerce"


def log_in():
    frisco_username = config.get_value("frisco", "username")
    frisco_password = config.get_value("frisco", "password", is_secret=True)

    url = f"{FRISCO_BASE_URL}/connect/token"
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

    token_type = response_json["token_type"]
    access_token = response_json["access_token"]
    user_id = response_json["user_id"]
    return token_type, access_token, user_id


def clear_shopping_cart(token_type, access_token, user_id):
    url = f"{FRISCO_BASE_URL}/api/v1/users/{user_id}/cart/products"
    headers = {
        "Authorization": f"{token_type} {access_token}",
        "Content-Type": "application/json",
    }
    response = requests.delete(url, headers=headers)
    response.raise_for_status()


def find_best_delivery_window(date, preferred_start_time, delivery_windows):
    for start_time in preferred_start_time:
        hour, minute = start_time.split(":")
        start_date = date.replace(
            hour=int(hour), minute=int(minute), second=0, microsecond=0
        )
        for delivery_window in delivery_windows:
            if delivery_window["canReserve"] and delivery_window["deliveryWindow"][
                "startsAt"
            ] == start_date.isoformat(timespec="seconds"):
                return delivery_window["deliveryWindow"]
    return None


def reserve_delivery(token_type, access_token, user_id, preferred_start_time):
    url = f"{FRISCO_BASE_URL}/api/v1/users/{user_id}/addresses/shipping-addresses"
    headers = {
        "Authorization": f"{token_type} {access_token}",
        "Content-Type": "application/json",
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    response_json = response.json()
    shipping_address = response_json[0]["shippingAddress"]

    warsaw_tz = pytz.timezone("Europe/Warsaw")
    tomorrow = warsaw_tz.localize(datetime.datetime.now() + datetime.timedelta(days=1))

    # to get available slots
    url = f"{FRISCO_BASE_URL}/api/v2/users/{user_id}/calendar/Van/{tomorrow.year}/{tomorrow.month}/{tomorrow.day}"
    headers = {
        "Authorization": f"{token_type} {access_token}",
        "Content-Type": "application/json",
    }
    data = shipping_address
    response = requests.post(url, data=json.dumps(data), headers=headers)
    response.raise_for_status()
    delivery_windows = response.json()

    delivery_window = find_best_delivery_window(
        tomorrow, preferred_start_time, delivery_windows
    )
    if delivery_window is None:
        return None

    url = f"{FRISCO_BASE_URL}/api/v2/users/{user_id}/cart/reservation"
    headers = {
        "Authorization": f"{token_type} {access_token}",
        "Content-Type": "application/json",
    }
    data = {
        # 'extendedRange': null,
        "deliveryWindow": delivery_window,
        "shippingAddress": shipping_address,
    }
    response = requests.post(url, data=json.dumps(data), headers=headers)
    response.raise_for_status()
    return delivery_window


# def get_last_purchased_products(user_id, token_type, access_token):
#   url = f'{FRISCO_BASE_URL}/api/v1/users/{user_id}/lists/purchased-products/query?purpose=Listing&pageIndex=1&includeFacets=true&deliveryMethod=Van&pageSize=100&language=pl&disableAutocorrect=false'
#   headers = {'Authorization': f'{token_type} {access_token}'}
#   response = requests.get(url, headers=headers)
#   response.raise_for_status()

#   purchased_products = response.json()['products']
#   purchased_product_ids = []

#   for product in purchased_products:
#     product_id = product['productId']
#     purchased_product_ids.append(product_id)
#   return purchased_product_ids


def search_product(user_id, token_type, access_token, product_to_buy):
    url = f"{FRISCO_BASE_URL}/api/v1/users/{user_id}/offer/products/query?purpose=Listing&pageIndex=1&search={product_to_buy}&includeFacets=true&deliveryMethod=Van&pageSize=60&language=pl&disableAutocorrect=false"
    headers = {"Authorization": f"{token_type} {access_token}"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    found_products = response.json()["products"]
    return found_products


# def pick_the_product(found_products, purchased_product_ids):
#   for product in found_products:
#     product_id = product['productId']
#     if product_id in purchased_product_ids:
#       product_to_buy_name = product['product']['name']['pl']
#       return product_id, product_to_buy_name
#   return None, None


def add_to_cart(user_id, token_type, access_token, store_product_id, quantity):
    url = f"{FRISCO_BASE_URL}/api/v1/users/{user_id}/cart"
    headers = {
        "Authorization": f"{token_type} {access_token}",
        "Content-Type": "application/json",
    }
    data = {"products": [{"productId": store_product_id, "quantity": quantity}]}
    response = requests.put(url, data=json.dumps(data), headers=headers)
    response.raise_for_status()


def send_status_update(message):
    url = config.get_value("make", "status_update_webhook", is_secret=True)

    headers = {"Content-Type": "text/plain; charset=utf-8"}
    response = requests.post(url, data=message.encode("utf-8"), headers=headers)
    response.raise_for_status()


def schedule(event, context):
    try:
        token_type, access_token, user_id = log_in()
        preferred_start_time = ["8:00", "8:30", "7:30", "9:00", "7:00", "9:30"]
        delivery_window = reserve_delivery(
            token_type, access_token, user_id, preferred_start_time
        )
        if delivery_window is None:
            send_status_update("❌ no delivery window found")
            return {"statusCode": 200, "body": json.dumps("No delivery window found!")}

        start_date = datetime.datetime.fromisoformat(delivery_window["startsAt"])
        end_date = datetime.datetime.fromisoformat(delivery_window["endsAt"])
        send_status_update(
            f"✅ delivery is scheduled at {start_date.strftime('%A %d.%m.%Y %H:%M')}-{end_date.strftime('%H:%M')}"
        )
        return {
            "statusCode": 200,
            "body": json.dumps("Scheduling completed successfully!"),
        }
    except Exception as exception:
        send_status_update(f"💥 error: {str(exception)}")
        raise


def shop(event, context):
    try:
        # get products to buy from notion
        products_to_buy = notion.get_grocery_list()

        # get products from todoist
        grocery_list = todoist.get_grocery_list()
        for product_name, quantity in grocery_list.items():
            products_to_buy[product_name] = quantity

        print("GROCERY LIST", products_to_buy)

        token_type, access_token, user_id = log_in()

        # delivery reserved so start shopping
        strategy_id = notion_logging.get_or_create_strategy(
            "AI Assistent",
            1,
            "Use Chat GPT to choose product to buy within a given list",
        )
        grocery_shopping_id = notion_logging.create_grocery_shopping_log(
            "Frisco", datetime.datetime.now(), strategy_id
        )

        # purchased_product_ids = get_last_purchased_products(user_id, token_type, access_token)

        clear_shopping_cart(token_type, access_token, user_id)
        for product_to_buy, quantity in products_to_buy.items():
            found_products = search_product(
                user_id, token_type, access_token, product_to_buy
            )
            available_products = [
                product
                for product in found_products
                if product["product"].get("isAvailable")
                and product["product"].get("isStocked")
            ]
            store_product_id, store_product_name, reason, price, priceAfterPromotion = (
                ai.pick_the_product(product_to_buy, available_products)
            )
            time.sleep(10)

            if store_product_id:
                add_to_cart(
                    user_id, token_type, access_token, store_product_id, quantity
                )
                notion_logging.create_choice_log(
                    product_to_buy,
                    grocery_shopping_id,
                    store_product_id,
                    store_product_name,
                    quantity,
                    reason,
                    price,
                    priceAfterPromotion,
                )
            else:
                notion_logging.create_empty_choice_log(
                    product_to_buy, grocery_shopping_id, quantity, reason
                )

        notion_logging.update_grocery_shopping_log(
            grocery_shopping_id, datetime.datetime.now()
        )
        send_status_update("✅ items successfully added to your cart")
        return {
            "statusCode": 200,
            "body": json.dumps("Grocery shopping completed successfully!"),
        }
    except Exception as exception:
        send_status_update(f"💥 error: {str(exception)}")
        raise


if __name__ == "__main__":
    schedule(None, None)
    shop(None, None)
