import configparser
import json
from openai import OpenAI

config = configparser.ConfigParser()
config.read('config.ini')

OPENAI_SECRET = config['openai']['secret']
OPENAI_ASSISTANT_ID = config['openai']['grocery_shopping_assistant_id']

def map_to_ai_product(product):
  tags_to_ignore = [
    "displayVariant",
    "isAvailable",
    "isStocked",
    "isNotAlcohol",
    "isSearchable",
    "isIndexable",
    "isPositioned",
    "isBargain"
  ]

  product = product["product"]
  return {
    "id": product["id"],
    "name": product["name"]["pl"],
    "packSize": product["packSize"],
    "unitOfMeasure": product["unitOfMeasure"],
    "grammage": product["grammage"],
    "producer": product["producer"] if "producer" in product else "",
    "brand": product["brand"],
    "price": product["price"]["price"],
    "priceAfterPromotion": product["price"]["priceAfterPromotion"] if "priceAfterPromotion" in product["price"] else product["price"]["price"],
    "tags": [tag for tag in product["tags"] if tag not in tags_to_ignore]
  }

def pick_the_product(product_to_buy, found_products):
  client = OpenAI(api_key=OPENAI_SECRET)

  products_for_ai = []

  for product in found_products:
    products_for_ai.append(map_to_ai_product(product))

  thread = client.beta.threads.create(messages=
      [
          {
              'role': 'user',
              'content': f'Chcę kupić produkt o nazwie {product_to_buy}. Który produkt z listy powinnam kupić? ```{products_for_ai}```'
          }
      ]
  )

  run = client.beta.threads.runs.create_and_poll(
      thread_id=thread.id, assistant_id=OPENAI_ASSISTANT_ID
  )
  messages = list(client.beta.threads.messages.list(thread_id=thread.id, run_id=run.id))
  message_content = messages[0].content[0].text.value
  output = json.loads(message_content)
  # print(output["id"])
  # print(output["name"])
  # print(output["reason"])
  print(message_content)
