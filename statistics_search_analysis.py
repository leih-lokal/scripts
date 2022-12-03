# -*- coding: utf-8 -*-
"""
Created on Sat Mar  6 21:22:19 2021

@author: Simon
"""
import website
import pandas as pd
flatten = lambda t: [item for sublist in t for item in sublist]


csv = pd.read_csv('C:/Users/Simon/Downloads/wp-statistics-2022-11-25-16-13.csv')
searches = csv[csv['type']=='search']


queries = flatten([[row[1]['uri'][3:].title().strip() for i in range(row[1]['count'])] for row in searches.iterrows() if not row[1]['uri'][3:].isdigit()])
queries = [''.join([x for x in q if x.isalpha() or x==' ']).strip() for q in queries]


products = list(website.get_leihlokaldata_API().values())

#%%
counts = {}
found_in_shortdesc = []
for query in queries:

    ignore = ['Öffnungszeiten','Haushalt','Test', 'Fotowettbewerb', 'Freizeit', 'Vorstand', 'Leihlokal']
   

    if query in ignore:
        continue
    elif any([query in x['name'] for x in products]):
        continue
    elif any([query.lower() in x['name'].lower() for x in products]):
        continue
    elif any([query.lower() in x['short_description'].lower() for x in products]):
        continue
    elif len(query)>30:
        # print(query)
        continue

    if not query in counts:
        counts[query] = 1
    else:
        counts[query] += 1
#%%
counts = dict(zip(sorted(counts, key=counts.get, reverse=True), sorted(counts.values(), reverse=True)))

with open('suchanfragen.csv', 'w') as f:
    for key, value in counts.items():
        f.write(f'{key},{value}\n')