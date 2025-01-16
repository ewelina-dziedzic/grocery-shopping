import json
import time
from typing import Any, List, Optional

from openai import OpenAI
from openai.types.beta.threads.message import Message

from grocery_shopping import config


class Product:
    def __init__(
        self,
        id: str,
        name: str,
        pack_size: int,
        unit_of_measure: str,
        grammage: float,
        price: float,
        price_after_promotion: float,
        tags: List[str],
        components: str
    ):
        self.id = id
        self.name = name
        self.pack_size = pack_size
        self.unit_of_measure = unit_of_measure
        self.grammage = grammage
        self.price = price
        self.price_after_promotion = price_after_promotion
        self.tags = tags
        self.components = components

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "packSize": self.pack_size,
            "unitOfMeasure": self.unit_of_measure,
            "grammage": self.grammage,
            "price": self.price,
            "priceAfterPromotion": self.price_after_promotion,
            "tags": self.tags,
            "components": self.components,
        }


class ChosenProduct:
    def __init__(self, id: str, name: str, price: float, price_after_promotion: float):
        self.id = id
        self.name = name
        self.price = price
        self.price_after_promotion = price_after_promotion


class Choice:
    def __init__(self, is_product_chosen: bool, reason: str, product: Optional[ChosenProduct] = None):
        self.is_product_chosen = is_product_chosen
        self.reason = reason
        self.product = product


class LLM:
    def __init__(self, config_provider: config.ConfigProvider, products_feed: dict):
        self.products_feed = products_feed
        api_key = config_provider.get_value("openai", "secret", is_secret=True)
        self.assistant_id = config_provider.get_value("openai", "grocery_shopping_assistant_id")
        self.client = OpenAI(api_key=api_key)
        self.tags_to_ignore = [
            "displayVariant",
            "isAvailable",
            "isStocked",
            "isNotAlcohol",
            "isSearchable",
            "isIndexable",
            "isPositioned",
            "isBargain",
        ]


    def map_to_product(self, store_product: dict) -> Product:
        store_product = store_product["product"]
        feed_product = self.products_feed.get(store_product["id"], {})
        return Product(
            store_product["id"],
            store_product["name"]["pl"],
            store_product["packSize"],
            store_product["unitOfMeasure"],
            store_product["grammage"],
            store_product["price"]["price"],
            store_product["price"].get("priceAfterPromotion", store_product["price"]["price"]),
            [tag for tag in store_product["tags"] if tag not in self.tags_to_ignore],
            feed_product.get("components", "")
        )


    def ask(self, product_name: str, options: list[dict[str, Any]]) -> Choice:
        products_for_llm = [self.map_to_product(product) for product in options]
        messages = self._ask(product_name, products_for_llm)
        
        if len(messages) == 0 or len(messages[0].content) == 0:
            print("Retrying a call to LLM for", product_name)
            time.sleep(10)
            messages = self._ask(product_name, products_for_llm)

        message_content = messages[0].content[0]
        assert message_content.type == "text", "Message content type should be text"
        answer = json.loads(message_content.text.value)
        
        if "id" in answer:
            store_product_id = answer["id"]
            llm_product = next(
                (product for product in products_for_llm if product.id == store_product_id)
            )
            return Choice(True, answer["reason"], ChosenProduct(
                store_product_id,
                answer["name"],
                llm_product.price,
                llm_product.price_after_promotion))
        else:
            return Choice(False, answer["reason"])
        

    def _ask(self, product_name: str, options: List[Product]) -> List[Message]:
        options_dict = [product.to_dict() for product in options]
        thread = self.client.beta.threads.create(
            messages=[
                {
                    "role": "user",
                    "content": f"Chcę kupić produkt o nazwie {product_name}. Który produkt z listy powinnam kupić? ```{options_dict}```",
                }
            ]
        )

        run = self.client.beta.threads.runs.create_and_poll(
            thread_id=thread.id, assistant_id=self.assistant_id
        )
        
        if run.status != "completed":
            raise Exception(f"Run failed with status: {run.status}, error: {run.last_error}")
       
        time.sleep(1)
        messages = list(
            self.client.beta.threads.messages.list(thread_id=thread.id)
        )
        return messages
