import datetime
import requests
import json
import time
import configparser
import pytz

import ai
import notion_logging
import notion
import todoist


# TODO unavailable product handling
# TODO reservations - handle more cases and add validation
# TODO reservation start and end time as the event data
# TODO add status to grocery shopping entry in notion and end date


# consts
FRISCO_BASE_URL = 'https://www.frisco.pl/app/commerce'

def log_in():
  config = configparser.ConfigParser()
  config.read('config.ini')

  frisco_username = config['frisco']['username']
  frisco_password = config['frisco']['password']

  url = f'{FRISCO_BASE_URL}/connect/token'
  form_data = {
    'grant_type': 'password',
    'username': frisco_username,
    'password': frisco_password
    }
  headers = {
      'referer': 'https://www.frisco.pl/',
      'Content-Type': 'application/x-www-form-urlencoded'
  }
  response = requests.post(url, data=form_data, headers=headers)
  response.raise_for_status()
  response_json = response.json()

  token_type = response_json['token_type']
  access_token = response_json['access_token']
  user_id = response_json['user_id']
  return token_type, access_token, user_id

def clear_shopping_cart(token_type, access_token, user_id):
  url = f'{FRISCO_BASE_URL}/api/v1/users/{user_id}/cart/products'
  headers = {
    'Authorization': f'{token_type} {access_token}',
    'Content-Type': 'application/json'
  }
  response = requests.delete(url, headers=headers)
  response.raise_for_status()

def reserve_delivery(token_type, access_token, user_id, start_hour, end_hour):
  url = f'{FRISCO_BASE_URL}/api/v1/users/{user_id}/addresses/shipping-addresses'
  headers = {
    'Authorization': f'{token_type} {access_token}',
    'Content-Type': 'application/json'
  }
  response = requests.get(url, headers=headers)
  response.raise_for_status()
  response_json = response.json()
  shipping_address = response_json[0]["shippingAddress"]
  delivery_method = response_json[0]["deliveryMethod"]
  
  warsaw_tz = pytz.timezone('Europe/Warsaw')
  today = warsaw_tz.localize(datetime.datetime.now())
  tomorrow = warsaw_tz.localize(datetime.datetime.now() + datetime.timedelta(days=1))
  
  # to get available slots - ignore until neccessary
  # url = f'{FRISCO_BASE_URL}/api/v2/users/{user_id}/calendar/Van/{tomorrow.year}/{tomorrow.month}/{tomorrow.day}'
  # headers = {
  #   'Authorization': f'{token_type} {access_token}',
  #   'Content-Type': 'application/json'
  # }
  # data = shipping_address
  # response = requests.post(url, data=json.dumps(data), headers=headers)
  # response.raise_for_status()
  # response_json = response.json()
  # print(response_json)

  start_time = tomorrow.replace(hour=start_hour, minute=0, second=0, microsecond=0)
  end_time = tomorrow.replace(hour=end_hour, minute=0, second=0, microsecond=0)
  closes_at = today.replace(hour=13, minute=0, second=0, microsecond=0)
  final_at = closes_at
  prev_ends_at = start_time + datetime.timedelta(minutes=30)
  next_starts_at = prev_ends_at
  
  url = f'{FRISCO_BASE_URL}/api/v2/users/{user_id}/cart/reservation'
  headers = {
    'Authorization': f'{token_type} {access_token}',
    'Content-Type': 'application/json'
  }
  data = {
    # "extendedRange": null,
    "deliveryWindow":{  
      "warehouse": "WRO",
      "deliveryMethod": delivery_method,
      "startsAt": start_time.isoformat(timespec='seconds'),
      "endsAt": end_time.isoformat(timespec='seconds'), 
      "closesAt": closes_at.isoformat(timespec='seconds'),
      "finalAt": final_at.isoformat(timespec='seconds'),
      "prev-ends-at": prev_ends_at.isoformat(timespec='seconds'),
      "next-starts-at": next_starts_at.isoformat(timespec='seconds'),
      "isMondayAfterNonTradeSunday": false,
    },
    "shippingAddress" : shipping_address
  }
  response = requests.post(url, data=json.dumps(data), headers=headers)
  response.raise_for_status()


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
  url = f'{FRISCO_BASE_URL}/api/v1/users/{user_id}/offer/products/query?purpose=Listing&pageIndex=1&search={product_to_buy}&includeFacets=true&deliveryMethod=Van&pageSize=60&language=pl&disableAutocorrect=false'
  headers = {'Authorization': f'{token_type} {access_token}'}
  response = requests.get(url, headers=headers)
  response.raise_for_status()
  found_products = response.json()['products']
  return found_products

# def pick_the_product(found_products, purchased_product_ids):
#   for product in found_products:
#     product_id = product['productId']
#     if product_id in purchased_product_ids:
#       product_to_buy_name = product['product']['name']['pl']
#       return product_id, product_to_buy_name
#   return None, None


def add_to_cart(user_id, token_type, access_token, store_product_id, quantity):
  url = f'{FRISCO_BASE_URL}/api/v1/users/{user_id}/cart'
  headers = {
    'Authorization': f'{token_type} {access_token}',
    'Content-Type': 'application/json'
  }
  data = {  
    'products': [
      {
        'productId': store_product_id,
        'quantity': quantity
      }
    ]
  }
  response = requests.put(url, data=json.dumps(data), headers=headers)
  response.raise_for_status()

def lambda_handler(event, context):
  # get products to buy from notion
  products_to_buy = notion.get_grocery_list()

  # get products from todoist
  grocery_list = todoist.get_grocery_list()
  for product_name, quantity in grocery_list.items():
    products_to_buy[product_name] = quantity

  print("GROCERY LIST", products_to_buy)

  token_type, access_token, user_id = log_in()
  # reserve_delivery(token_type, access_token, user_id, start_hour=8, end_hour=9)

  # delivery reserved so start shopping
  strategy_id = notion_logging.get_or_create_strategy('AI Assistent', 1, 'Use Chat GPT to choose product to buy within a given list')
  grocery_shopping_id = notion_logging.create_grocery_shopping_log('Frisco', datetime.datetime.now(), strategy_id)

  # purchased_product_ids = get_last_purchased_products(user_id, token_type, access_token)

  clear_shopping_cart(token_type, access_token, user_id)
  for product_to_buy, quantity in products_to_buy.items():
    found_products = search_product(user_id, token_type, access_token, product_to_buy)
    store_product_id, store_product_name, reason, price, priceAfterPromotion = ai.pick_the_product(product_to_buy, found_products)
    time.sleep(5)

    if store_product_id:
      add_to_cart(user_id, token_type, access_token, store_product_id, quantity)
      notion_logging.create_choice_log(product_to_buy, grocery_shopping_id, store_product_id, store_product_name, quantity, reason, price, priceAfterPromotion)
    else:
      notion_logging.create_empty_choice_log(product_to_buy, grocery_shopping_id, quantity, reason)

  return {
      'statusCode': 200,
      'body': json.dumps('Grocery shopping completed successfully!')
  }

if __name__ == "__main__":
  lambda_handler(None, None)