import requests

import grocery_shopping.config as config


class Notifier:
    def __init__(self, config_provider: config.ConfigProvider):
        self.url = config_provider.get_value("make", "status_update_webhook", is_secret=True)
        self.headers = {"Content-Type": "text/plain; charset=utf-8"}

    def update_status(self, message: str):
        response = requests.post(self.url, data=message.encode("utf-8"), headers=self.headers)
        response.raise_for_status()
