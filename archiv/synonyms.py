# -*- coding: utf-8 -*-
"""
Created on Sat Feb 29 23:33:55 2020

This script parses a WP-Woocommerce exported CSV file of products
and adds synonyms of the product to the description.
it also copies the Kurzbeschreibung to the Beschreibung.



@author: skjerns
"""
import os
import pandas as pd
from unisens.utils import read_csv
import json, requests
from tqdm import tqdm
import time
import logging
logger = requests.logging.getLogger().setLevel(logging.WARNING)

class SynonymFinder():
    
    def __init__(self):
        if not os.path.isfile('synonyms.json'):
            with open('synonyms.json', 'w') as f:
                json.dump({}, f)
    
    def get_synonyms(self, term):
        
        with open('synonyms.json', 'r') as f:
            found = json.load(f)
            
        if term in found: 
            return found[term]
        
        req = requests.get("http://www.openthesaurus.de/synonyme/search", params={"q": term, "format": "application/json"}).text
        try:
            d = json.loads(req)
        except:
            print(f'cant load {term}:', req)  
        try: 
            synonyms = [o["term"] for o in d["synsets"][0]["terms"]]
            i=synonyms.index(term)
            del synonyms[i]
            if len(synonyms)==0: synonyms=False
            print(f"{term}: {synonyms}")
        except IndexError: 
            print(f"{term} has no synonyms")
            synonyms = False
        except Exception as e:
            print(term, e)
            return False
        
        found[term] = synonyms
        with open('synonyms.json', 'w') as f:
            json.dump(found, f)
        time.sleep(1)
        return synonyms



finder = SynonymFinder()

try:
    products_csv = "wc-product-export-1-3-2020-1583061900018.csv"
except:
    raise Exception('Bitte lade das CSV-file aus dem WordPress mit den spalten ID, Name, ShortDescrpition')
liste = read_csv(products_csv, sep=',', convert_nums=False, keep_empty=True)
a=0
b=0
altered = []
for i,product in enumerate(tqdm(liste[1:])):
    name = product[1]
    desc = product[2]
    synonyms = finder.get_synonyms(name)
    if synonyms!=False:
        product[2] += f'<br><small>(Synonyme: {"/".join(synonyms)})</small>'
        altered.append(",".join(product))

header = [','.join(liste[0])]
csv = '\n'.join(header+altered)
with open('new_products.csv', 'w') as f:
    f.write(csv)