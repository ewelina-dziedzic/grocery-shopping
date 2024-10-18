import datetime
import requests
import json
import webbrowser
import time
import urllib.parse
import configparser
import re

# TODO think about quantity
# TODO unavailable product handling

def get_or_create_strategy(strategy_name, strategy_version, strategy_description):
  config = configparser.ConfigParser()
  config.read('config.ini')
  NOTION_SECRET = config['notion']['secret']
  NOTION_STRATEGY_DATABASE_ID = config['notion']['strategy_database_id']

  url = f'https://api.notion.com/v1/databases/{NOTION_STRATEGY_DATABASE_ID}/query'
  headers = {
      'Authorization': f'Bearer {NOTION_SECRET}',
      'Notion-Version': '2022-06-28',
      'Content-Type': 'application/json'
  }
  data = {
    'page_size': 1,
    'filter': {
        'and': [
            {
                'property': 'Name',
                'title': {
                    'equals': strategy_name
                }
            },
            {
                'property': 'Version',
                'number': {
                    'equals': strategy_version  
                }
            }
        ]
    }
  }
  response = requests.post(url, data=json.dumps(data), headers=headers)
  response.raise_for_status()
  response_json = response.json()
  strategies = response_json['results']
  strategies_count = len(strategies)

  if strategies_count > 0:
    return strategies[0]['id']

  url = f'https://api.notion.com/v1/pages'
  headers = {
      'Authorization': f'Bearer {NOTION_SECRET}',
      'Notion-Version': '2022-06-28',
      'Content-Type': 'application/json'
  }
  data = {
      'parent': { 'database_id': NOTION_STRATEGY_DATABASE_ID },
      'properties': {
          'Name': {
              'title': [
                  {
                      'text': {
                          'content': strategy_name
                      }
                  }
              ]
          },
          'Version': {
              'number': strategy_version
          },
          'Description': {
             'rich_text': [{ 'type': 'text', 'text': { 'content': strategy_description } }]
          }
      }
  }
  response = requests.post(url, data=json.dumps(data), headers=headers)
  response.raise_for_status()
  return response.json()['id']


def create_grocery_shopping_log(store_name, start_time, strategy_id):
  config = configparser.ConfigParser()
  config.read('config.ini')
  NOTION_SECRET = config['notion']['secret']
  NOTION_GROCERY_SHOPPING_DATABASE_ID = config['notion']['grocery_shopping_database_id']

  url = f'https://api.notion.com/v1/pages'
  headers = {
      'Authorization': f'Bearer {NOTION_SECRET}',
      'Notion-Version': '2022-06-28',
      'Content-Type': 'application/json'
  }
  data = {
      'parent': { 'database_id': NOTION_GROCERY_SHOPPING_DATABASE_ID },
      'properties': {
          'Store name': {
              'title': [
                  {
                      'text': {
                          'content': store_name
                      }
                  }
              ]
          },
          'Start time': {
              'date': {
                'start': start_time.isoformat(timespec="seconds")
              }
          },
          'Strategy': {
            'relation': [{
              'id': strategy_id
            }]
          }
      }
  }
  response = requests.post(url, data=json.dumps(data), headers=headers)
  response.raise_for_status()
  return response.json()['id']


def create_choice_log(product_name, grocery_shopping_id, store_product_id, store_product_name):
  config = configparser.ConfigParser()
  config.read('config.ini')
  NOTION_SECRET = config['notion']['secret']
  NOTION_CHOICE_DATABASE_ID = config['notion']['choice_database_id']

  url = f'https://api.notion.com/v1/pages'
  headers = {
      'Authorization': f'Bearer {NOTION_SECRET}',
      'Notion-Version': '2022-06-28',
      'Content-Type': 'application/json'
  }
  data = {
      'parent': { 'database_id': NOTION_CHOICE_DATABASE_ID },
      'properties': {
          'Product name': {
              'title': [
                  {
                      'text': {
                          'content': product_name
                      }
                  }
              ]
          },
          'Store product id': {
              'rich_text': [{ 'type': 'text', 'text': { 'content': store_product_id } }]
          },
          'Store product name': {
              'rich_text': [{ 'type': 'text', 'text': { 'content': store_product_name } }]
          },
          'Grocery shopping': {
            'relation': [{
              'id': grocery_shopping_id
            }]
          }
      }
  }
  response = requests.post(url, data=json.dumps(data), headers=headers)
  response.raise_for_status()
  return response.json()['id']


def create_empty_choice_log(product_name, grocery_shopping_id):
  config = configparser.ConfigParser()
  config.read('config.ini')
  NOTION_SECRET = config['notion']['secret']
  NOTION_CHOICE_DATABASE_ID = config['notion']['choice_database_id']

  url = f'https://api.notion.com/v1/pages'
  headers = {
      'Authorization': f'Bearer {NOTION_SECRET}',
      'Notion-Version': '2022-06-28',
      'Content-Type': 'application/json'
  }
  data = {
      'parent': { 'database_id': NOTION_CHOICE_DATABASE_ID },
      'properties': {
          'Product name': {
              'title': [
                  {
                      'text': {
                          'content': product_name
                      }
                  }
              ]
          },
          'Grocery shopping': {
            'relation': [{
              'id': grocery_shopping_id
            }]
          }
      }
  }
  response = requests.post(url, data=json.dumps(data), headers=headers)
  response.raise_for_status()
  return response.json()['id']


def pick_the_product(product_to_buy, quantity, found_products, purchased_product_ids):
  for product in found_products:
    product_id = product['productId']
    if product_id in purchased_product_ids:
      product_to_buy_name = product['product']['name']['pl']
      print('FOUND', product_to_buy_name, 'FOR', product_to_buy, '[', quantity, 'szt.]')
      return product_id, product_to_buy_name
  return None, None


strategy_id = get_or_create_strategy('Frequently bought products', 1, 'I add to a cart products that appear in the frequently bought products list')
print('strategy id', strategy_id)

grocery_shopping_id = create_grocery_shopping_log('Frisco', datetime.datetime.now(), strategy_id)
print('grocery shopping id', grocery_shopping_id)

# input
config = configparser.ConfigParser()
config.read('config.ini')

frisco_username = config['frisco']['username']
frisco_password = config['frisco']['password']

notion_secret = config['notion']['secret']
notion_database_id = config['notion']['database_id']

todoist_secret = config['todoist']['secret']
todoist_project_id = config['todoist']['project_id']

# consts
frisco_base_url = 'https://www.frisco.pl/app/commerce'

# get products to buy from notion
products_to_buy = {}
url = f'https://api.notion.com/v1/databases/{notion_database_id}/query'
headers = {
    'Authorization': f'Bearer {notion_secret}',
    'Notion-Version': '2022-06-28',
    'Content-Type': 'application/json'
}
data = {
  'filter': {
    'and': [
      {
        'property': 'Got it',
        'checkbox': {
          'equals': False  
        }
      },
      {
        'property': 'To buy',
        'checkbox': {
          'equals': True  
        }
      }
    ]
  }
}
response = requests.post(url, data=json.dumps(data), headers=headers)
response.raise_for_status()
response_json = response.json()
ingredients = response_json['results']
for ingredient in ingredients:
  ingredient_name = ingredient['properties']['Ingredient']['title'][0]['plain_text']
  ingredient_quantity = ingredient['properties']['Quantity']['number']
  products_to_buy[ingredient_name] = ingredient_quantity or 1

# get products from todoist
url = f'https://api.todoist.com/rest/v2/tasks?project_id={todoist_project_id}'
headers = {
    'Authorization': f'Bearer {todoist_secret}'
}
response = requests.get(url, headers=headers)
response.raise_for_status()
response_json = response.json()
tasks = response_json
for task in tasks:
  product_name = task['content']
  product_with_quantity =re.match('(.*?) ([0-9]+)$', product_name)
  if product_with_quantity:
    products_to_buy[product_with_quantity.group(1)] = product_with_quantity.group(2)
  else:
    products_to_buy[product_name] = 1

print("PRODUCTS TO BUY", products_to_buy)

# get access token and user id
url = f'{frisco_base_url}/connect/token'
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

# get last purchased products
url = f'{frisco_base_url}/api/v1/users/{user_id}/lists/purchased-products/query?purpose=Listing&pageIndex=1&includeFacets=true&deliveryMethod=Van&pageSize=100&language=pl&disableAutocorrect=false'
headers = {'Authorization': f'{token_type} {access_token}'}
response = requests.get(url, headers=headers)
response.raise_for_status()

purchased_products = response.json()['products']
purchased_product_ids = []

for product in purchased_products:
   product_id = product['productId']
   purchased_product_ids.append(product_id)

# search product by name
for product_to_buy, quantity in products_to_buy.items():
  url = f'{frisco_base_url}/api/v1/users/{user_id}/offer/products/query?purpose=Listing&pageIndex=1&search={product_to_buy}&includeFacets=true&deliveryMethod=Van&pageSize=60&language=pl&disableAutocorrect=false'
  headers = {'Authorization': f'{token_type} {access_token}'}
  response = requests.get(url, headers=headers)
  response.raise_for_status()

  found_products = response.json()['products']
  store_product_id, store_product_name = pick_the_product(product_to_buy, quantity, found_products, purchased_product_ids)

  # add to cart if the search returned a product that was purchased recently
  if store_product_id:
    create_choice_log(product_to_buy, grocery_shopping_id, store_product_id, store_product_name)
    url = f'{frisco_base_url}/api/v1/users/{user_id}/cart'
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
  # open the search page if couldn't find a product to add to cart
  else:
    webbrowser.open(f'https://www.frisco.pl/q,{urllib.parse.quote_plus(product_to_buy)}/stn,searchResults')
    create_empty_choice_log(product_to_buy, grocery_shopping_id)
    time.sleep(1)

webbrowser.open('https://www.frisco.pl/stn,iList') # bought often