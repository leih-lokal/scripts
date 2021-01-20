# -*- coding: utf-8 -*-
"""
Created on Fri Nov  6 11:52:24 2020

This file is intended to be run to update the products with regards
to product number (SKU) inside the product description.

@author: Simon
"""

import json
import time
from tqdm import tqdm
from woocommerce import API

with open('settings.json', 'r', encoding='utf-8') as f:
    settings = json.load(f)
    assert 'wc-key' in settings, "'wc-key' from WooCommerce-API must be in settings.json"
    assert 'wc-secret' in settings, "'wc-secret' from WooCommerce-API must be in settings.json"

def get_products(wcapi):
    products = []
    print('Retrieving products', end='')

    n_pages = int(wcapi.get('products', params={'per_page':100}).headers['X-WP-TotalPages'])
    for page in tqdm(range(1, n_pages+1), total=n_pages, desc='Downloading Data'):
        response = wcapi.get('products', params={'per_page':100, 'page':page})
        page = response.json()
        products += page
        time.sleep(2)

    return products




wcapi = API(
    url="http://www.buergerstiftung-karlsruhe.de/",
    consumer_key = settings.get('wc-key'),
    consumer_secret = settings.get('wc-secret'),
    version="wc/v3",
    timeout=30
)



products = get_products(wcapi)

# products = products[:10]
#%%

updates = []
for product in tqdm(products, desc='Adding SKUs'):
    id = product['id']
    sku = product['sku']
    description = product['short_description'].strip()

    description = description.replace('<div></div>', '')

    if len(sku)!=4:
        print(f'{sku} is not yet in 4-digit-format!')
        continue
    if '<div style="display:' in description:
        description = description.split('<div style="display:')[0]
    if '<div>Art.Nr' in description:
        description = description.split('<div>Art.Nr')[0]
    if f'\n\n<div class="hidden">Art.Nr.: {sku}</div>' in description:
        print('{sku} already done')
        continue
    if '<div' in description:
        print(f'another div found {sku}')
        # SKU is already in description
        continue
    if str(int(sku)) in description:
        print(f'{sku} already contains number: {description}')
        continue

    description = description.strip()


    description += f'\n\n<div class="hidden">Art.Nr.: {sku}</div>'

    max(tqdm._instances).set_description(f'adding SKU to description for {sku}')

    updates.append({'id': id, 'short_description':description})


stop
if len(updates)>50:
    max(tqdm._instances).set_description('Submitting 50 items')
    res = wcapi.put('products/batch', data={'update':updates})
    max(tqdm._instances).set_description('Verifying')
    assert res.status_code==200, 'Status code is not {res}'
    responses = res.json()['update']
    for i1, i2 in zip(responses, updates):
        assert i1['short_description']==i2['short_description'], 'Not the same in than out'
    updates = []

