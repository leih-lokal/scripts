# -*- coding: utf-8 -*-
"""
Created on Tue Mar  3 08:35:30 2020

this script will use the customer data base and create a heatmap
of where people that visit the leih.lokal come from.

steps:
    1. load addresses as strings
    2. convert addresses to gps coordinates using Nominatim
    3. create heatmap

@author: skjerns
"""
import time
import pyexcel as pe
import json
import urllib.parse
from tqdm import tqdm
from geopy.geocoders import Nominatim
import os
import urllib
import simplejson
import string
import random
import pandas as pd
import folium
import os
import sys
from folium.plugins import HeatMap


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
    #%%
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

    #%%
if __name__=='__main__':
    with open('settings.json', 'r', encoding='latin1') as f:
        settings = json.load(f)
    
    file = settings['leihgegenstaendeliste']
    sheet = pe.get_book(file_name=file)
    
    locations = get_locations(sheet)
    make_heatmap(locations)
