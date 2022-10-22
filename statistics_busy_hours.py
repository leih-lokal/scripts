# -*- coding: utf-8 -*-
"""
Created on Thu Jun 23 14:07:12 2022

@author: Simon
"""

import os
import re
import datetime
import pandas as pd
import pendulum
from tkinter.filedialog import asksaveasfile
from tkinter import Tk
import json
import io
from mechanize import Browser #pip install mechanize
import leihlokal
import seaborn as sns
import holidays
from leihlokal import LeihLokal
from cloudant.client import CouchDB
import numpy as np
import matplotlib.pyplot as plt

if __name__=='__main__':
    user = os.environ.get('COUCHDB_USER', 'user')
    password = os.environ.get('COUCHDB_PASSWORD', 'password')
    url = os.environ.get('COUCHDB_HOST', 'http://localhost:5984')

    print(f'connecting to {url}')

    couchdb = CouchDB(user, password, url=url, connect=True, auto_renew=True)

    db = couchdb['leihlokal']
    docs = db.all_docs(include_docs=True)['rows']

    #%% retrieve all docs that have a "last_update" field
    updates = []
    for doc in docs:
        doc = doc['doc']
        if doc.get('type')!='rental' or doc.get('last_update') is None: 
            continue
        timestamp = doc['last_update']
        date = pendulum.from_timestamp(timestamp//1000)
        updates.append(date)

    #%% subdivide into days
    
   
    binsize = 30 # 15 minute intervals
    
    per_day = {d:np.zeros(24*60//binsize) for d in range(7)}
    for date in updates:
        day = date.weekday()
        if day not in [0, 3, 4, 5]: continue
        # shiftstart = datetime.time(6, 0) if day==5 else datetime.time(11, 0)
        td = date.time() #- shiftstart
        binx = td.hour * (60//binsize) + td.minute//binsize
        binx += 60//binsize # offset by one hour
        # if binx<0 or binx>10: continue
    
        per_day[date.weekday()][binx]+=1

    daynames = ['Montag', 'Donnerstag', 'Freitag', 'Samstag']
    fig, axs = plt.subplots(4, 1); axs=axs.flatten()
    for i, d in enumerate([0, 3, 4, 5]):
        xtime = np.arange(0, 24, binsize/60)[60//binsize*7:60//binsize*21]
        axs[i].plot(xtime, per_day[d][60//binsize*7:60//binsize*21])
        axs[i].set_title(daynames[i])
        axs[i].set_ylim([0, 150])
    plt.suptitle('Leihvorgänge bearbeitet')