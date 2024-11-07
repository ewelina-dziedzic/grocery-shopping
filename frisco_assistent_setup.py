import config
import requests

import ai


frisco_username = config.get_value('frisco', 'username')
frisco_password = config.get_value('frisco', 'password', is_secret=True)

# consts
frisco_base_url = 'https://www.frisco.pl/app/commerce'

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
url = f'{frisco_base_url}/api/v1/users/{user_id}/lists/purchased-products/query?purpose=Listing&pageIndex=1&includeFacets=true&deliveryMethod=Van&pageSize=20&language=pl&disableAutocorrect=false'
headers = {'Authorization': f'{token_type} {access_token}'}
response = requests.get(url, headers=headers)
response.raise_for_status()

purchased_products = response.json()['products']

result = []


for product in purchased_products:
    result.append(ai.map_to_ai_product(product))

# print(result)

# search for Jogurt
product_to_buy = "Jogurt"
url = f'{frisco_base_url}/api/v1/users/{user_id}/offer/products/query?purpose=Listing&pageIndex=1&search={product_to_buy}&includeFacets=true&deliveryMethod=Van&pageSize=10&language=pl&disableAutocorrect=false'
headers = {'Authorization': f'{token_type} {access_token}'}
response = requests.get(url, headers=headers)
response.raise_for_status()

result = []

found_products = response.json()['products']
for product in found_products:
    result.append(ai.map_to_ai_product(product))

print(result)
