# -*- coding: utf-8 -*-
"""
Created on Fri Oct 23 20:43:15 2020

retrieve data from website

@author: Simon
"""
import os
import requests
import time
from bs4 import BeautifulSoup
from joblib import Parallel, delayed
from tqdm import tqdm


sortiment_url = 'https://www.buergerstiftung-karlsruhe.de/leihlokal/sortiment/?product-page='

def download_image(url, code):
    file = os.path.join('products', f'{code}.jpg')
    if not os.path.isdir('products'): 
        os.makedirs('products')
    c = get(url)
    with open(file, 'wb') as f:
        f.write(c.content)
    return True

def get(url, sleep=0.5):
    """retrieve an url and wait some second"""
    c = requests.get(url)
    if sleep>5: return c
    time.sleep(sleep)
    if not c.ok:
        print(f'Not OK: {c.reason}: {url}')
        return get(url, sleep*2)
    return c


def get_page_numbers():
    """retrieve the leihlokal sortiment and see how many pages there are"""
    c = get(sortiment_url)
    assert c.ok, f'Could not get url: {c.reason}'
    c = BeautifulSoup(c.content, 'html.parser')
    n_pages = (c.find_all('a', attrs={'class':'page-numbers'})[-2].text)
    return int(n_pages)

def get_leihlokaldata():
    # this is the url that we use to fetch the
    n_pages = get_page_numbers()
    request_urls = [sortiment_url + str(i) for i in range(1, n_pages+1)]
    
    # we request 8 pages at once and then 200ms delay
    res = Parallel(n_jobs=8, prefer='threads')(delayed(get)(url) for url in tqdm(request_urls, desc='downloading info'))

    # get all <li> tags that are of class 'product'
    page_html = []
    for page in res:
        soup = BeautifulSoup(page.content, 'html.parser')
        page_html += soup.find_all('li', attrs={'class':'product'})
    

    products = {}
    for p in page_html:
        code = int(p.find_all('a')[-1].attrs['data-product_sku'])
        name = p.find_all('h2')[0].text
        page_url = p.a.attrs['href']
        status = p.p.text
        products[code] = {'name': name,
                          'page_url': page_url,
                          'status': status}
    return products

