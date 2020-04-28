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






    #%%
if __name__=='__main__':
    with open('settings.json', 'r', encoding='latin1') as f:
        settings = json.load(f)
    
    file = settings['leihgegenstaendeliste']
    sheet = pe.get_book(file_name=file)
    
    locations = get_locations(sheet)
    make_heatmap(locations)
