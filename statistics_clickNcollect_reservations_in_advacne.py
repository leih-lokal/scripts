# -*- coding: utf-8 -*-
"""
Created on Sun Mar 28 06:49:27 2021

This script takes the CSV from the WP Appointment Booking Hour plugin
and creates an overview for the current day in XLS format to print out

@author: Simon
"""
import os
import re
import datetime
import pandas as pd
from tkinter.filedialog import asksaveasfile
from tkinter import Tk
import json
import io
from mechanize import Browser #pip install mechanize
import leihlokal
import seaborn as sns
import holidays

leihlokal = leihlokal.LeihLokal()
customers = leihlokal.customers
items = leihlokal.items
rentals = leihlokal.rentals

def calculate_opening_days_since(date):
    BW_holidays = holidays.CountryHoliday('DE', prov='BW')
    today = datetime.datetime.now().date()
    opening_days = 0
    for tday in range(1, (today-date).days):
        day = today - datetime.timedelta(days=tday)
        if day.weekday() in [0,3,5] and not day in BW_holidays:
            opening_days += 1
    return opening_days

def get_days_too_late_by_id(ids_string):
    ids = [int(x) for x in re.findall('[0-9]+', ids_string)]
    if len(ids)==0: return '?€'
    today = datetime.datetime.now().date()
    active_rentals = [r for r in rentals if r.returned_on==0]
    for rental in active_rentals:
        if rental.item_id in ids:
            if rental.to_return_on < today:
                return calculate_opening_days_since(rental.to_return_on)
            else:
                return 0
    return '?'

def get_customer_id_by_name(full_name):
    found = 0
    for c in customers.values():
        if f'{c.firstname} {c.lastname}'.lower() == full_name.lower():
            cid = f'{c.id}*'
            found +=1
    if found==0:
        return '?'
    elif found>1:
        print(f'Mehrere Nutzer mit Name {full_name} gefunden.')
        return '?'
    return cid

def get_deposit_by_ids(ids_string):
    ids = [int(x) for x in re.findall('[0-9]+', ids_string)]
    if len(ids)==0: return '?€'
    deposits = [items[id].deposit if id in items else '?€' for id in ids ]
    # grouped = [list(g) for k, g in itertools.groupby(deposits)]
    # summary = [f'{len(x)}x{x[0]}' if len(x)>1 else f'{x[0]}' for x in grouped]
    try:
        total = sum(deposits)
    except:
        total = '?'
    deposit_string = '+'.join([f'{x}' for x in deposits])
    return f'{total}€ ({deposit_string})' if len(deposits)>1 else f'{total}€'


def choose_filesave(default_dir=None, default_filename='übersicht.xlsx', title='Bitte Speicherort wählen'):
    """
    Open a file chooser dialoge with tkinter.
    
    :param default_dir: Where to open the dir, if set to None, will start at wdir
    :param exts: A string or list of strings with extensions etc: 'txt' or ['txt','csv']
    :returns: the chosen file
    """
    root = Tk()
    root.iconify()
    root.update()
    name = asksaveasfile(initialdir=default_dir,
                         initialfile=default_filename,
                         parent=root,
                         title = title,
                         filetypes =(("CSV", "*.xlsx"), ))
    root.update()
    root.destroy()
    return name.name
  
def show_date_picker(title=''):
    import tkinter as tk
    from tkcalendar import Calendar

    def cal_done():
        top.withdraw()
        root.quit()

    root = Tk()
    root.iconify()
    root.update()

    root.title(title)
    root.withdraw() # keep the root window from appearing

    top = tk.Toplevel(root)

    tk.Label(top, text='Für welchen Tag soll die Übersicht erstellt werden?', font='sans 13').pack()
    cal = Calendar(top, font="Arial 12", selectmode='day', locale='de_DE')
    cal.pack(fill="both", expand=True)
    tk.Button(top, text="Diesen Tag wählen", font='sans 12 bold', command=cal_done).pack()

    root.mainloop()
    return cal.selection_get()


def download_bookings_csv():

    login_url = 'https://buergerstiftung-karlsruhe.de/wp-login.php'
    csv_url = 'https://www.buergerstiftung-karlsruhe.de/wp-admin/admin.php?page=cp_apphourbooking&cal=2&list=1&search=&dfrom=&dto=&cal=2&cp_appbooking_csv=Export+to+CSV'

    with open('settings.json', 'r') as f:
        settings = json.load(f)

    uname = settings['wp-user']
    passw = settings['wp-pass']

    br = Browser()
    br.set_handle_robots(False)
    br.addheaders = [("User-agent","Python Script using mechanize")]
    print('Connecting to WP.')
    sign_in = br.open(login_url)  #the login url
     
    br.select_form(nr = 0) #accessing form by their index. Since we have only one form in this example, nr =0.
    br["log"] = uname #the key "username" is the variable that takes the username/email value
    br["pwd"] = passw    #the key "password" is the variable that takes the password value
    print('Logging in to WP...')

    logged_in = br.submit()   #submitting the login credentials
    print('Downloading CSV from database...')

    assert logged_in.code == 200, 'Login to WP failed'  #print HTTP status code(200, 404...)
    download = br.open(csv_url)

    assert download.code == 200, 'Failed to download bookings CSV'

    return download.read().decode(encoding='iso-8859-1')


#%%
if __name__=='__main__':

    
    csv_file = download_bookings_csv()
    print('Extracting data...')
    #%%
    f = io.StringIO(csv_file)
    df = pd.read_csv(f, sep=';')

    df.fillna('', inplace=True)
    df = df.convert_dtypes('str')
    keep_columns = ['app_date_1', 'Time']

    df = df[df['Ich möchte einen Gegenstand/Gegenstände..']=='abholen']
    
    for column in df.columns:
        if  column in keep_columns: continue
        df = df.drop(column, axis=1)
    
    df['app_date_1'] = pd.to_datetime(df['app_date_1'], format='%d.%m.%Y').dt.floor('d')
    df['Time'] = pd.to_datetime(df['Time'], format='%Y-%m-%d %H:%M:%S').dt.floor('d')
    
    df = df[df['Time']<datetime.datetime.now()- datetime.timedelta(days=180)]

    diff = (df['app_date_1']-df['Time']).dt.days
    diff = diff[diff<10]
        
    
    sns.histplot(diff, bins=np.arange(9)-0.5, stat='percent')
    
