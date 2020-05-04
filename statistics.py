# -*- coding: utf-8 -*-
"""
Created on Tue Apr 28 18:16:18 2020

This file plots statistics for our leih.lokal

Following statistics are there
xxx

@author: skjerns
"""
import datetime
from leihlokal import Store
import os, sys
import numpy as np
import time
import json
import urllib.parse
from tqdm import tqdm
import matplotlib.pyplot as plt
from geopy.geocoders import Nominatim
import string
import random
import pandas as pd
import folium
import matplotlib.dates as mdates
from folium.plugins import HeatMap
import seaborn as sns
sns.set(style='whitegrid')

#%%

def get_locations(sheet):

    class LocationFinder():
        def __init__(self):
            
            
            if not os.path.isfile('locations.json'):
                with open('locations.json', 'w') as f:
                    json.dump({}, f)
            
            def randomString(stringLength=10):
                """Generate a random string of fixed length """
                letters = string.ascii_lowercase
                return ''.join(random.choice(letters) for i in range(stringLength))
            
            # use random string as useragent to prevent blocking
            self.geolocator = Nominatim(user_agent=randomString())
    
        def get_location(self, address):
            spcial_char_map = {ord('ä'):'ae', ord('ü'):'ue', ord('ö'):'oe', ord('ß'):'ss'}
            address = address.lower()
            address = address.translate(spcial_char_map)
            with open('locations.json', 'r') as f:
                found = json.load(f)
            
            if address in found: 
                return found[address]
            
            location = self.geolocator.geocode(address)
            if location is None: 
                return None
            latitude, longitude = location.latitude, location.longitude
    
            found[address] = (latitude, longitude)
            
            with open('locations.json', 'w') as f:
                json.dump(found, f)
            time.sleep(0.1)
            return (latitude, longitude)
    
    
    
    kunden = sheet.Kunden
    addressen = list(zip(kunden.column[7], kunden.column[8], kunden.column[9], kunden.column[10]))
    
    locations = []
    finder = LocationFinder()
    t = 1
    for i, (street, nr, plz, city) in enumerate(tqdm(addressen[1:])):
        while True:
            try:
                location = finder.get_location(f'{street} {nr} {plz} {city}')
                t = 1
                break
            except:
                t*=2
                print(f'wait: {t} sec')
                time.sleep(t)
                
        if location is None:
            print(street, nr, 'not found')
            continue
        locations.append(location)
    return locations
def make_heatmap(locations):
    startingLocation = [49.006239, 8.411572]
    hmap = folium.Map(location=startingLocation, zoom_start=12)
    
    # Creates a heatmap element
    hm_wide = HeatMap( locations,
                        min_opacity=0.1,
                        radius=10, blur=20,
                        max_zoom=0)
    
    # Adds the heatmap element to the map
    hmap.add_child(hm_wide)
    
    # Saves the map to heatmap.hmtl
    hmap.save(os.path.join('.', 'heatmap.html'))
    
    

def plot_(store):
    import matplotlib.pyplot as plt
    rentals = store.rentals
    months = [str(r.rented_on.month)+'/'+str(r.rented_on.year-2000) for r in rentals]
    plt.hist(months)
    plt.title('Ausleihen pro Monat')
    
    rented = [r.rented_on.strftime('%A') for r in rentals]
    rented = [d for d in rented if not d in ['Sunday', 'Tuesday']]
    plt.figure()
    plt.hist(rented, 7)
    plt.title('Ausleihen pro Tag')

    returned = [r.returned_on.strftime('%A') for r in rentals if isinstance(r.returned_on, datetime.date)]
    returned = [d for d in returned if not d in ['Sunday', 'Tuesday']]
    plt.figure()
    plt.hist(returned)
    plt.title('Rückgabe pro Tag')





if __name__ == '__main__':
    #%% first load the database
    plt.close('all')
    with open('settings.json', 'r', encoding='latin1') as f:
        settings = json.load(f)
    
    excel_file = settings['leihgegenstaendeliste']
    store = Store.parse_file(excel_file)
  
    customers = store.customers.values()
    rentals = store.rentals
    items = store.items.values() 
  
    #%% Number of customers over the years
    plt.figure()
    first = list(customers)[0].registration_date
    last = list(customers)[-1].registration_date
    n_days = (last-first).days
    n_customers = {day:0 for day in np.arange(n_days+1)}
    for customer in customers:
        if not isinstance(customer.registration_date, datetime.date): continue
        i_day = (customer.registration_date - first).days
        n_customers[i_day] += 1
    for i in list(n_customers)[1:]:
        n_customers[i] = n_customers[i-1]+n_customers[i]
        
    
    plt.plot(list(n_customers), list(n_customers.values()))
    plt.xlabel('Monate nach Eröffnung')
    plt.ylabel('Anzahl Kunden')
    plt.plot([0,n_days], [0, n_days],'--',  c='gray', alpha=0.5)
    plt.legend(['Kunden', 'Linearer Anstieg'])
    plt.xticks(np.arange(0,n_days, 30), np.arange(0,n_days))    
    
    
    #%% Ausleihen pro Monat  
    dates = [r.rented_on for r in store.rentals]
    # remove dates that are not opening dates
    dates = [d for d in dates if d.weekday() in [0, 3,4,5]]

    df = pd.DataFrame(dates, columns=['date']).astype('datetime64')
    df.groupby([df["date"].dt.year, df["date"].dt.month]).count().plot(kind="bar")
    plt.title('Ausleihen über die Zeit verteilt')
    plt.xlabel('Monat')
    plt.ylabel('Anzahl Ausleihen in diesem Monat')
    
    #%%
    fig, axs = plt.subplots(2,1)
    ax = axs.flatten()[0]
    df.groupby(df["date"].dt.dayofweek).count().plot(kind="bar", ax=ax)
    ax.set_xticklabels(['Monatg', 'Donnerstag', 'Freitag', 'Samstag'])
    ax.set_title('Ausleihen pro Tag')
    ax.set_xlabel('Tag')
    ax.set_ylabel('Anzahl Ausleihen in diesem Tag')