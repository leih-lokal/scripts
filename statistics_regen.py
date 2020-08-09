# -*- coding: utf-8 -*-
"""
Created on Sun Aug  9 10:36:33 2020

Check whether the weather affects our customer influx

@author: Simon Kern
"""
import sys, os
import json
from leihlokal import Store
import matplotlib.pyplot as plt
import numpy as np
from tqdm import tqdm
import openweather
import pandas as pd
import requests
from datetime import timedelta, datetime

import csv
import codecs
import urllib.request
import sys


def isfloat(string):
    try:
        float(string)
        return True
    except:
        return False




with open('settings.json', 'r', encoding='latin1') as f:
        settings = json.load(f)
    
excel_file = settings['leihgegenstaendeliste']
store = Store.parse_file(excel_file)
  
customers = store.customers.values()
rentals = store.rentals
items = store.items.values()



#%% load weather data. can be downloaded from www.wetter-bw.de, for some station nearby
dateparse = lambda x: datetime.strptime(x, '%d.%m.%Y').date()
weather = pd.read_csv('wetter.csv', index_col='Tag', parse_dates=True, header=0, sep=';', decimal=',', date_parser=dateparse)
weather.index = weather.index.astype(str)
weather['customers'] = [set() for _ in range(len(weather))]
weather = weather.to_dict(orient='index')



for rental in rentals:
    customer = rental.customer_id
    date = str(rental.rented_on)

    try:
        day = weather[date]
        day['customers'].add(customer)
    except:
        print(date)

for day in weather.copy():
    if weather[day]['customers']==set():
        weather.pop(day)
    else:
        weather[day]['customers'] = len(weather[day]['customers'])


