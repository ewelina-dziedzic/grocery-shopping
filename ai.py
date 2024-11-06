import boto3
import json
import time
from openai import OpenAI


ssm = boto3.client('ssm')
parameter_response = ssm.get_parameter(Name='/openai/secret', WithDecryption=True)
OPENAI_SECRET = parameter_response['Parameter']['Value']

parameter_response = ssm.get_parameter(Name='/openai/grocery_shopping_assistant_id')
OPENAI_ASSISTANT_ID = parameter_response['Parameter']['Value']


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

  def call_openai(product_to_buy, products_for_ai):
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
    return messages

  messages = call_openai(product_to_buy, products_for_ai)
  if(len(messages) == 0 or len(messages[0].content) == 0):
    print("Retrying a call to LLM for", product_to_buy)
    time.sleep(10)
    messages = call_openai(product_to_buy, products_for_ai)

  message_content = messages[0].content[0].text.value
  output = json.loads(message_content)
  if "id" in output:
    store_product_id = output["id"]
    store_product_name = output["name"]
    reason = output["reason"]
    found_product = next(filter(lambda product: product["id"] == store_product_id, products_for_ai), None)
    return store_product_id, store_product_name, reason, found_product["price"], found_product["priceAfterPromotion"]
  else:
    reason = output["reason"]
    return None, None, reason, None, None