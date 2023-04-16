# -*- coding: utf-8 -*-
"""
Created on Tue Apr 28 18:16:18 2020

This file plots statistics for our leih.lokal

Following statistics are there
xxx

@author: skjerns
"""
import sys;sys.path.append('..')
import datetime
from leihlokal import LeihLokal
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
from joblib import Parallel, delayed
import seaborn as sns
from html2image import Html2Image
import shutil
from PIL import Image
from PIL import ImageFont
from PIL import ImageDraw
import imageio

sns.set(style='whitegrid')

#%%

def get_locations(customers):

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
                return None if found[address]=='' else found[address]

            location = self.geolocator.geocode(address)
            if location is None:
                address2 = address.replace('ae', 'ä').replace('ue', 'ü').replace('oe', 'ö')
                location = self.geolocator.geocode(address2)

            time.sleep(0.1)
            if location is None:
                found[address] = ''
                with open('locations.json', 'w') as f:
                    json.dump(found, f)
                return None
            else:
                latitude, longitude = location.latitude, location.longitude

                found[address] = (latitude, longitude)
                with open('locations.json', 'w') as f:
                    json.dump(found, f)
                return (latitude, longitude)


    locations = []
    finder = LocationFinder()
    t = 1
    for i, customer in enumerate(tqdm(customers, desc='fetching locations')):
        nr = customer.house_number
        street = customer.street
        city = customer.city
        plz = customer.postal_code
        while True:
            try:
                address = f'{street} {nr} {plz} {city}'.strip()
                if address=='': break
                location = finder.get_location(address)
                t = 1
                break
            except KeyboardInterrupt:
                raise
            except Exception as e:
                print(e)
                t*=2
                print(f'wait: {t} sec')
                time.sleep(t)
        if location is None:
            print(street, nr, f'not found ({customer.id})')
            continue
        locations.append(location)
    return locations


def make_heatmap(locations, filename='./heatmap.html', overlay=''):
    filename = os.path.abspath(filename)
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    startingLocation = [49.006239, 8.411572]
    hmap = folium.Map(location=startingLocation, zoom_start=14)

    # Creates a heatmap element
    hm_wide = HeatMap( locations,
                        min_opacity=.5,
                        radius=21, blur=25)

    # Adds the heatmap element to the map
    hmap.add_child(hm_wide)

    # Saves the map to heatmap.hmtl
    hmap.save(filename)
    hti = Html2Image(custom_flags=['--virtual-time-budget=1000'])

    png_file = hti.screenshot(url=filename, save_as=os.path.basename(filename) + '.png')[0]

    shutil.move(png_file, filename + '.png')
    img = Image.open(filename + '.png')
    draw = ImageDraw.Draw(img)
    # font = ImageFont.truetype(<font-file>, <font-size>)
    font = ImageFont.truetype("C:/Users/Simon/AppData/Local/Microsoft/Windows/Fonts/TTNorms-Bold.otf", 100)
    # draw.text((x, y),"Sample Text",(r,g,b))
    draw.text((1400, 0), overlay, (0, 0, 0), font=font, align='right')
    img = img.resize([int(x*0.5) for x in img.size])
    img.save(filename + '.png')
    return img



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



#%%
if __name__ == '__main__':
    #%% first load the database
    plt.close('all')
    store = LeihLokal()

    customers = sorted(store.customers.values(), key=lambda x: x.registration_date)
    rentals = store.rentals
    items = sorted(store.items.values(), key=lambda x: x.id)

    #%% create heatmap
    locations = get_locations(customers)

    #%% make heatmap with animation

    # make steps of 30 days to walk through the year(s)
    steps = np.where(np.diff([c.registration_date.month for c in customers]))[0]
    # steps = [np.argmax(days>i) for i in range(61, max(days), 30)]
    dates = [customers[i].registration_date.strftime('%b %Y') for i in steps]

    pngs = Parallel(n_jobs=-1)(delayed(make_heatmap)(locations[:s],
                        os.path.abspath(f'./plots/heatmap/heatmap_{i:04d}.html'),
                        overlay=f'{dates[i]}') for i, s in enumerate(tqdm(steps, desc='creating heatmap PNGs')))

    duration = ([0.3]*(len(pngs)-1)) + [5]
    print('creating GIF')
    imageio.mimsave('./plots/heatmap.gif', pngs[1:], format='GIF-FI', duration=duration, palettesize=256, quantizer='nq')
    imageio.mimsave('./plots/heatmap.mp4', pngs, format='mp4', fps=5, quality=9)

    #%% Number of customers over the years
    first = list(customers)[0].registration_date
    last = list(customers)[-1].registration_date

    days = np.cumsum([x.days for x in np.diff([c.registration_date for c in customers])])
    steps = [np.argmax(days>i) for i in range(61, max(days), 30)]
    dates = [customers[i].registration_date.strftime('%b %Y') for i in steps]

    plt.figure(figsize=[6,6], maximize=False)
    pngs = []
    for i, s in enumerate(tqdm(steps)):
        plt.clf()
        dates = [c.registration_date for c in customers[:s]]
        x = pd.DataFrame({'dates':dates})
        sns.ecdfplot(data=x, x='dates', stat='count')
        xlim, ylim = plt.xlim(), plt.ylim()
        plt.xlim(first, last)
        plt.ylim(0, len(customers))
        plt.plot([*plt.xlim()], [*plt.ylim()],'--',  c='gray', alpha=0.8)
        # plt.xlim(xlim)
        plt.xlabel('Monat', {'fontsize':16})
        plt.ylabel('Anzahl Ausleiher:innen', {'fontsize':16})
        plt.legend(['Nutzer:in', 'Linearer Anstieg'])
        plt.title('Zuwachs an Ausleiher:innen seit Eröffnung', {'fontsize':20})
        plt.xticks(rotation=25)
        plt.tight_layout()
        plt.pause(0.01)
        plt.savefig('./plots/tmp.png')
        img = imageio.imread('./plots/tmp.png')
        pngs.append(img)
    duration = ([0.3]*(len(pngs)-1)) + [5]
    imageio.mimsave('./plots/kunden.gif', pngs, format='GIF-FI', duration=duration, palettesize=256)

    # stop

    #%% Gesamte Anzahl der Ausleihen
    rental_dates = [r.rented_on for r in rentals if hasattr(r, 'rented_on') and isinstance(r.rented_on, datetime.date)]

    first = min(rental_dates)
    last =  max(rental_dates)

    x = pd.DataFrame({'dates':rental_dates})

    sns.ecdfplot(data=x, x='dates', stat='count')
    xlim, ylim = plt.xlim(), plt.ylim()
    plt.xlim(first, last)
    plt.plot([*plt.xlim()], [*plt.ylim()],'--',  c='gray', alpha=0.8)
    plt.xlim(xlim)

    plt.xlabel('Monat', {'fontsize':16})
    plt.ylabel('Gesamte Ausleihen', {'fontsize':16})

    plt.legend(['Ausleihen', 'Linearer Anstieg'])
    plt.title('Gesamte Anzahl Ausleihen seit Eröffnung', {'fontsize':20})
    plt.xticks(rotation=25)


    plt.tight_layout()
    #%% Ausleihen pro Monat
    dates = [r.rented_on for r in rentals if hasattr(r, 'rented_on') and isinstance(r.rented_on, datetime.date)]


    # dates = [d for d in dates if d.weekday() in [0, 3,4,5]]
    plt.figure(figsize=[6,4 ])
    df = pd.DataFrame(dates, columns=['date']).astype('datetime64')
    df.groupby([df["date"].dt.year, df["date"].dt.month]).count()[:-1].plot(kind="bar", ax=plt.gca())
    plt.xlabel('Monat', {'fontsize':14})
    plt.ylabel('Anzahl Ausleihen', {'fontsize':14})
    plt.title('Ausleihen pro Monat', {'fontsize':16})
    plt.axvspan(16.5, 18.5, alpha=0.2, color='r')
    plt.axvspan(26, 27.5, alpha=0.2, color='r')
    plt.text(17, 110, '1. Lockdown', color='r', rotation=90, fontsize=14)
    plt.text(26.5, 110, '2. Lockdown', color='r', rotation=90, fontsize=14)

    plt.xticks(np.arange(0,int(plt.xlim()[1]),2), rotation=25)

    plt.tight_layout()
    plt.pause(0.1)
    plt.savefig('./lockdown.png')

    #%% anzahl pro tag
    fig, ax = plt.subplots(1,1)
    # limit to after 2021
    df = df[df['date']>datetime.datetime(2022,1,1)]
    total_weeks = len(df.groupby([df["date"].dt.week, df["date"].dt.year]).count())
    df_perday = df.groupby(df["date"].dt.dayofweek).count().drop(index=[1, 2, 6])/total_weeks
    df_perday.index = ['Montag', 'Donnerstag', 'Freitag', 'Samstag']
    df_perday.plot(kind="bar", ax=ax, legend=False)
    ax.set_xticklabels(['Montag', 'Donnerstag', 'Freitag', 'Samstag'])
    ax.set_title('Ausleihen pro Tag im Durchschnitt (2022)', {'fontsize':20})
    ax.set_xlabel('Wochentag', {'fontsize':16})
    ax.set_ylabel('Ø Anzahl Ausleihen', {'fontsize':16})
    plt.xticks(rotation=25)
    plt.tight_layout()

    #%% anzahl ausleihen pro kunde

    counts = [min(len(c.rentals), 10) for c in customers if len(c.rentals)>0]
    plt.figure(figsize=[7, 5])
    sns.distplot(counts, norm_hist=False, kde=False, bins=np.arange(1, 12)-0.49, hist_kws={'alpha':0.8})
    plt.xlabel('Anzahl Ausleihen', {'fontsize':16})
    plt.ylabel('Anzahl der Nutzer:in', {'fontsize':16})
    plt.title('Anzahl der Ausleihen pro Nutzer:in im Durchschnitt', {'fontsize':16})
    plt.xticks(np.arange(1, 11), [str(x) for x in range(1, 10)] + ['>=10'])
    plt.tight_layout()
    plt.savefig('./plots/per_kunde.png')


    #%% anzahl ausleihen pro gegenstand

    counts = [min(len(i.rentals), 16) for i in items if i.wc_url!='']

    plt.figure(figsize=[7, 5])
    sns.histplot(counts, alpha=0.8, binrange=(0, 15), binwidth=3)
    plt.xlabel('Anzahl Ausleihen', {'fontsize':16})
    plt.ylabel('Anzahl der Gegenstände', {'fontsize':16})
    plt.title('Anzahl der Ausleihen pro Gegenstand im Durchschnitt', {'fontsize':16})
    plt.xticks(np.arange(0, 16)+0.5, [str(x) for x in range(0, 15)] + ['>=15'])
    plt.tight_layout()
    plt.savefig('./plots/per_gegenstand.png')
    # tops and flops
    topsflops = sorted([i for i in items if i.wc_url!=''], key=lambda x:len(x.rentals))
    x = pd.DataFrame({'Name':[x.name for x in items], 'Anzahl':[len(x.rentals) for x in items]})
    x=x.sort_values('Anzahl', ascending=False)