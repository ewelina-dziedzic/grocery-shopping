import requests
import json
import webbrowser
import time
import urllib.parse

# TODO think about quantity

# input
username = ''
password = ''
notion_secret = ''
todoist_secret = ''

# consts
base_url = 'https://www.frisco.pl/app/commerce'

# get products to buy from notion
products_to_buy = []
url = 'https://api.notion.com/v1/databases/6a77f92ad67a49d2be9fefdb4048bc9a/query?filter_properties=title'
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
  products_to_buy.append(ingredient_name)

# get products from todoist
url = ' https://api.todoist.com/rest/v2/tasks?project_id=2281492801'
headers = {
    'Authorization': f'Bearer {todoist_secret}'
}
response = requests.get(url, headers=headers)
response.raise_for_status()
response_json = response.json()
tasks = response_json
for task in tasks:
  product_name = task['content']
  products_to_buy.append(product_name)

print("PRODUCTS TO BUY", products_to_buy)

# get access token and user id
url = f'{base_url}/connect/token'
form_data = {
  'grant_type': 'password',
  'username': username,
  'password': password
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
url = f'{base_url}/api/v1/users/{user_id}/lists/purchased-products/query?purpose=Listing&pageIndex=1&includeFacets=true&deliveryMethod=Van&pageSize=60&language=pl&disableAutocorrect=false'
headers = {'Authorization': f'{token_type} {access_token}'}
response = requests.get(url, headers=headers)
response.raise_for_status()

purchased_products = response.json()['products']
purchased_product_ids = []

for product in purchased_products:
   product_id = product['productId']
   purchased_product_ids.append(product_id)

# search product by name
for product_to_buy in products_to_buy:
  url = f'{base_url}/api/v1/users/{user_id}/offer/products/query?purpose=Listing&pageIndex=1&search={product_to_buy}&includeFacets=true&deliveryMethod=Van&pageSize=60&language=pl&disableAutocorrect=false'
  headers = {'Authorization': f'{token_type} {access_token}'}
  response = requests.get(url, headers=headers)
  response.raise_for_status()

  found_products = response.json()['products']
  product_to_buy_id = None
  product_to_buy_name = None
  for product in found_products:
    product_id = product['productId']
    if product_id in purchased_product_ids:
      product_to_buy_id = product_id
      product_to_buy_name = product['product']['name']['pl']
      print('FOUND', product_to_buy_name, 'for', product_to_buy)
      break

  # add to cart if the search returned a product that was purchased recently
  if product_to_buy_id:
    url = f'{base_url}/api/v1/users/{user_id}/cart'
    headers = {
      'Authorization': f'{token_type} {access_token}',
      'Content-Type': 'application/json'
    }
    data = {  
      'products': [
        {
          'productId': product_to_buy_id,
          'quantity': 1
        }
      ]
    }
    response = requests.put(url, data=json.dumps(data), headers=headers)
    response.raise_for_status()
    print('ADDED TO CART', product_to_buy_name)
  # open the search page if couldn't find a product to add to cart
  else:
    webbrowser.open(f'https://www.frisco.pl/q,{urllib.parse.quote_plus(product_to_buy)}/stn,searchResults')
    time.sleep(1)
    print('NOT FOUND', product_to_buy)
