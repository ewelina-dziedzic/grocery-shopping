import datetime
import requests
import json
import webbrowser
import time
import urllib.parse
import configparser

import ai
import notion_logging
import notion
import todoist

# TODO unavailable product handling

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

def get_last_purchased_products(user_id, token_type, access_token):
  url = f'{FRISCO_BASE_URL}/api/v1/users/{user_id}/lists/purchased-products/query?purpose=Listing&pageIndex=1&includeFacets=true&deliveryMethod=Van&pageSize=100&language=pl&disableAutocorrect=false'
  headers = {'Authorization': f'{token_type} {access_token}'}
  response = requests.get(url, headers=headers)
  response.raise_for_status()

  purchased_products = response.json()['products']
  purchased_product_ids = []

  for product in purchased_products:
    product_id = product['productId']
    purchased_product_ids.append(product_id)
  return purchased_product_ids

def search_product(user_id, token_type, access_token, product_to_buy):
  url = f'{FRISCO_BASE_URL}/api/v1/users/{user_id}/offer/products/query?purpose=Listing&pageIndex=1&search={product_to_buy}&includeFacets=true&deliveryMethod=Van&pageSize=60&language=pl&disableAutocorrect=false'
  headers = {'Authorization': f'{token_type} {access_token}'}
  response = requests.get(url, headers=headers)
  response.raise_for_status()
  found_products = response.json()['products']
  return found_products

def pick_the_product(found_products, purchased_product_ids):
  for product in found_products:
    product_id = product['productId']
    if product_id in purchased_product_ids:
      product_to_buy_name = product['product']['name']['pl']
      return product_id, product_to_buy_name
  return None, None


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

if __name__ == "__main__":
  strategy_id = notion_logging.get_or_create_strategy('Frequently bought products', 1, 'I add to a cart products that appear in the frequently bought products list')
  grocery_shopping_id = notion_logging.create_grocery_shopping_log('Frisco', datetime.datetime.now(), strategy_id)

  # get products to buy from notion
  products_to_buy = notion.get_grocery_list()

  # get products from todoist
  grocery_list = todoist.get_grocery_list()
  for product_name, quantity in grocery_list.items():
    products_to_buy[product_name] = quantity

  print("PRODUCTS TO BUY", products_to_buy)

  token_type, access_token, user_id = log_in()
  purchased_product_ids = get_last_purchased_products(user_id, token_type, access_token)

  for product_to_buy, quantity in products_to_buy.items():
    found_products = search_product(user_id, token_type, access_token, product_to_buy)
    store_product_id, store_product_name = pick_the_product(found_products, purchased_product_ids)
    
    # testing for a time being
    ai.pick_the_product(product_to_buy, found_products)

    if store_product_id:
      add_to_cart(user_id, token_type, access_token, store_product_id, quantity)
      notion_logging.create_choice_log(product_to_buy, grocery_shopping_id, store_product_id, store_product_name)
    else:
      webbrowser.open(f'https://www.frisco.pl/q,{urllib.parse.quote_plus(product_to_buy)}/stn,searchResults')
      notion_logging.create_empty_choice_log(product_to_buy, grocery_shopping_id)
      time.sleep(1)

  webbrowser.open('https://www.frisco.pl/stn,iList') # bought often