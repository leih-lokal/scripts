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
import datetime
from tkinter.filedialog import asksaveasfile
from tkinter import Tk
import json
import io
from mechanize import Browser #pip install mechanize
import leihlokal
import itertools
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

    df.fillna('',inplace=True)
    df = df.convert_dtypes('str')
    keep_columns = ['app_starttime_1', 'Ich möchte einen Gegenstand/Gegenstände..',
                    'Ihr Vor- und Zuname', 'Ich bin', 'Artikelnummer(n)','app_status_1',
                    'Haben Sie noch Kommentare oder Anmerkungen zu Ihrem Termin?',
                    'Ihre Nutzernummer (falls zur Hand)', 'app_date_1',
                    ]

    date = show_date_picker('Bitte Tag wählen')
    date_str = date.strftime("%d.%m.%Y")

    for column in df.columns:
        if  column in keep_columns: continue
        df = df.drop(column, axis=1)

    df = df.reindex(keep_columns, axis=1)
    df_selected = df.loc[df['app_date_1'] == date_str]
    df_selected = df_selected.loc[df['app_status_1'] != 'Cancelled by customer']
    df_selected = df_selected.loc[df['app_status_1'] != 'Cancelled']
    df_selected = df_selected.loc[df['app_status_1'] != 'Rejected']
    df_selected = df_selected.loc[df['app_status_1'] != 'Zusammengelegt']

    df_selected = df_selected.convert_dtypes('str')

    ids_infered = []
    for name, neu, customer_id in zip(df_selected['Ihr Vor- und Zuname'], df_selected['Ich bin'], df_selected['Ihre Nutzernummer (falls zur Hand)']):
        try:
            customer_id = int(customer_id)
        except:
            pass
        if neu=='NeukundIn':
            customer_id = 'neu'
        elif customer_id=='':
            customer_id = get_customer_id_by_name(name)
        ids_infered.append(customer_id)
    df_selected['Ihre Nutzernummer (falls zur Hand)'] = ids_infered

    deposit_infered = []
    for ids_string, mode in zip(df_selected['Artikelnummer(n)'], df_selected['Ich möchte einen Gegenstand/Gegenstände..']):
        # if mode=='zurückgeben':
        #     deposit = ''
        # else:
        try:
            deposit = get_deposit_by_ids(ids_string)
        except:
            deposit = '?€'
        deposit_infered.append(deposit)
    df_selected.insert(5, 'Pfand', deposit_infered)

    opening_days_missed = []
    for ids_string, mode in zip(df_selected['Artikelnummer(n)'], df_selected['Ich möchte einen Gegenstand/Gegenstände..']):
        if mode=='abholen':
            opening_days_since = ''
        else:
            try:
                opening_days_since = get_days_too_late_by_id(ids_string)
            except:
                opening_days_since = '?'
        opening_days_missed.append(opening_days_since)
    df_selected.insert(9, 'Tage zu spät', opening_days_missed)


    df_selected.drop('app_date_1', axis=1, inplace=True)
    df_selected['Ihr Vor- und Zuname'] = df_selected['Ihr Vor- und Zuname'] + ' ('+ df_selected['Ihre Nutzernummer (falls zur Hand)'].astype(str) + ')'
    df_selected.drop('Ihre Nutzernummer (falls zur Hand)', axis=1, inplace=True)
    df_selected.drop('Ich bin', axis=1, inplace=True)

    # rename columns
    df_selected.rename({'Ihr Vor- und Zuname':'NutzerIn',
                        'Ich möchte einen Gegenstand/Gegenstände..':'a/z',
                        'app_starttime_1':'Zeit',
                        'Haben Sie noch Kommentare oder Anmerkungen zu Ihrem Termin?':'Kommentar',
                        'app_status_1': 'Status'},
                        inplace=True, axis=1)



    df_selected['Kommentar'] = df_selected['Kommentar'].map(lambda x: x.replace('\r', '').replace('\n', ' ' ).replace('\t', ''))
    df_selected['Kommentar'] = df_selected['Kommentar'].map(lambda x: x[:20] + ('[...]' * (len(x)>15)))
    df_selected['a/z'] = df_selected['a/z'].map(lambda x: x.replace('abholen', 'ab'))
    df_selected['a/z'] = df_selected['a/z'].map(lambda x: x.replace('zurückgeben', 'z'))

    opening_hours = range(10, 14) if date.weekday()==5 else range(15, 19)
    missing_slots = [f'{h}:{m}0' for h in opening_hours for m in range(6) if not f'{h}:{m}0' in df_selected['Zeit'].values][:-1]

    df_selected = df_selected.append([{'Zeit': s} for s in missing_slots], ignore_index=True)
    df_selected.fillna('', inplace=True)

    df_selected = df_selected.sort_values('Zeit', ignore_index=True)
    df_selected.set_index('Zeit', inplace=True)
    df_selected['Eingetragen?'] = ['[   ]']*len(df_selected)

    row = ['', '* Nutzernummer und Pfandbeträge automatisch inferiert. Kann fehlerhaft sein!', *(len(df_selected.columns)-2)*['']]
    row2 = ['', 'Es werden sämtliche Zahlen im Textfeld als Gegenstandsnummern interpretiert und das Pfand in Klammern geschrieben.', *(len(df_selected.columns)-2)*['']]

    df_selected.loc[len(df_selected)] = row
    df_selected.loc[len(df_selected)] = row2

    df_selected.index = df_selected.index.to_list()[:-2]+ ['', '']

    xls_file = choose_filesave(default_dir=os.path.expanduser('~\\Desktop\\'), default_filename=f'CC-Übersicht-{date_str}.xlsx')

    print('Writing excel...')
#%%
    with pd.ExcelWriter(xls_file, engine='xlsxwriter') as writer:
        book = writer.book
        df_selected.to_excel(writer, sheet_name=date_str)
        sheet = writer.sheets[date_str]
        sheet.set_paper(9)
        sheet.set_landscape()
        sheet.center_vertically()
        sheet.center_horizontally()
        sheet.hide_gridlines(False)
        sheet.fit_to_pages(1,1)
        sheet.set_margins(0, 0, 0, 0)
        sheet.set_print_scale(110)

        format = book.add_format()
        format.set_shrink()
        sheet.set_column('D:H', 5,  format)

        def get_col_widths(dataframe):
            # First we find the maximum length of the index column
            idx_max = max([len(str(s)) for s in dataframe.index.values] + [len(str(dataframe.index.name))])
            # Then, we concatenate this to the max of the lengths of column name and its values for each column, left to right
            return [idx_max] + [max([len(str(s)) for s in dataframe[col].values[:-1]] + [len(col)]) for col in dataframe.columns]
        
        for i, width in enumerate(get_col_widths(df_selected)):
            sheet.set_column(i, i, min(width+1, 27))


        format = book.add_format()
        format.set_align('center')
        format.set_align('vcenter')
        # sheet.set_column('D:E', None, format)
        sheet.set_column('B:B', 3, format)
        sheet.set_column('E:E', 4, format)

        format = book.add_format()
        format.set_font_size(9)
        sheet.set_column('E:E', 12, format)
        sheet.set_column('F:F', 7, format)
        sheet.set_column('G:G', 5, format)
        sheet.set_column('G:G', 15)

        format = book.add_format()
        format.set_font_color('#808080')
        format.set_align('center')
        sheet.set_column('H1:H32', 12, format)

    os.system(f'start excel.exe "{xls_file}"')
    #%%
    if 'clickandcollect_' in csv_file:
        os.remove(csv_file)
