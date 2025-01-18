import unittest
from datetime import datetime
from grocery_shopping.shopping import Store
from grocery_shopping.groceries import GroceryItem
from grocery_shopping.config import ConfigProvider


class TestStoreIntegration(unittest.TestCase):
    def setUp(self):
        self.config_provider = ConfigProvider()
        self.store = Store(self.config_provider)
        self.user = self.store.log_in()

    def test_shop_integration(self):
        # arrange
        grocery_list = [
            GroceryItem(name="Jogurt", quantity=2, task_id="1"),
            GroceryItem(name="Jajka", quantity=1, task_id="2"),
            GroceryItem(name="Mleko", quantity=3, task_id="3"),
            GroceryItem(name="Marchewka", quantity=1, task_id="5"),
            GroceryItem(name="Pietruszka", quantity=1, task_id="6")
        ]

        # act
        bought_grocery_items = self.store.shop(self.user, grocery_list)

        # assert
        self.assertGreater(len(bought_grocery_items), 0)

if __name__ == "__main__":
    unittest.main()