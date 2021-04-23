import os

import requests


class WooCommerceClient:

    def _item_url(self, wc_item_id):
        return f"{os.getenv('WC_URL')}/products/{wc_item_id}?consumer_key={os.getenv('WC_KEY')}&consumer_secret={os.getenv('WC_SECRET')}"

    def _get_item(self, wc_item_id):
        response = requests.get(self._item_url(wc_item_id))
        if response.status_code != 200:
            raise RuntimeError(f"Failed to fetch item {wc_item_id} from WooCommerce")
        return response.json()

    def update_item_status(self, wc_item_id, status):
        response = requests.put(self._item_url(wc_item_id), json={"stock_status": status})
        if response.status_code != 200:
            raise RuntimeError(f"Failed to update item {wc_item_id} on WooCommerce")
