import config
import json
import time
from openai import OpenAI


OPENAI_SECRET = config.get_value("openai", "secret", is_secret=True)
OPENAI_ASSISTANT_ID = config.get_value("openai", "grocery_shopping_assistant_id")


def map_to_ai_product(product, products_feed):
    tags_to_ignore = [
        "displayVariant",
        "isAvailable",
        "isStocked",
        "isNotAlcohol",
        "isSearchable",
        "isIndexable",
        "isPositioned",
        "isBargain",
    ]

    product = product["product"]
    feed_product = products_feed.get(product["id"], {})
    return {
        "id": product["id"],
        "name": product["name"]["pl"],
        "packSize": product["packSize"],
        "unitOfMeasure": product["unitOfMeasure"],
        "grammage": product["grammage"],
        "price": product["price"]["price"],
        "priceAfterPromotion":
            product["price"]["priceAfterPromotion"]
            if "priceAfterPromotion" in product["price"]
            else product["price"]["price"],
        "tags": [tag for tag in product["tags"] if tag not in tags_to_ignore],
        "components": feed_product.get("components", "")
        }


def pick_the_product(product_to_buy, found_products, products_feed):
    client = OpenAI(api_key=OPENAI_SECRET)

    products_for_ai = []

    for product in found_products:
        products_for_ai.append(map_to_ai_product(product, products_feed))

    def call_openai(product_to_buy, products_for_ai):
        thread = client.beta.threads.create(
            messages=[
                {
                    "role": "user",
                    "content": f"Chcę kupić produkt o nazwie {product_to_buy}. Który produkt z listy powinnam kupić? ```{products_for_ai}```",
                }
            ]
        )

        run = client.beta.threads.runs.create_and_poll(
            thread_id=thread.id, assistant_id=OPENAI_ASSISTANT_ID
        )
        
        if run.status != "completed":
            raise Exception(f"Run failed with status: {run.status}, error: {run.last_error}")
       
        time.sleep(1)
        messages = list(
            client.beta.threads.messages.list(thread_id=thread.id)
        )
        return messages

    messages = call_openai(product_to_buy, products_for_ai)
    if len(messages) == 0 or len(messages[0].content) == 0:
        print("Retrying a call to LLM for", product_to_buy)
        time.sleep(10)
        messages = call_openai(product_to_buy, products_for_ai)

    message_content = messages[0].content[0].text.value
    output = json.loads(message_content)
    if "id" in output:
        store_product_id = output["id"]
        store_product_name = output["name"]
        reason = output["reason"]
        found_product = next(
            filter(lambda product: product["id"] == store_product_id, products_for_ai),
            None,
        )
        return (
            store_product_id,
            store_product_name,
            reason,
            found_product["price"],
            found_product["priceAfterPromotion"],
        )
    else:
        reason = output["reason"]
        return None, None, reason, None, None
