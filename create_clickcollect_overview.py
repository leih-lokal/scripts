# -*- coding: utf-8 -*-
"""
Created on Sun Mar 28 06:49:27 2021

This script takes the CSV from the WP Appointment Booking Hour plugin
and creates an overview for the current day in XLS format to print out

@author: Simon
"""
import os
import pandas as pd
from tkinter.filedialog import asksaveasfile
from tkinter import Tk
import json
import io
from mechanize import Browser #pip install mechanize


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

    df_selected = df_selected.convert_dtypes('str')
    df_selected.drop('app_date_1', axis=1, inplace=True)
    df_selected['Ihr Vor- und Zuname'] = df_selected['Ihr Vor- und Zuname'] + ' ('+ df_selected['Ihre Nutzernummer (falls zur Hand)'].astype(str) + ')'
    df_selected.drop('Ihre Nutzernummer (falls zur Hand)', axis=1, inplace=True)

    # rename columns
    df_selected.rename({'Ihr Vor- und Zuname':'NutzerIn',
                        'Ich möchte einen Gegenstand/Gegenstände..':'Vorgang',
                        'app_starttime_1':'Zeit',
                        'Haben Sie noch Kommentare oder Anmerkungen zu Ihrem Termin?':'Kommentar',
                        'app_status_1': 'Status',
                        'Ich bin': 'Neu?'},
                        inplace=True, axis=1)

    df_selected['Kommentar'] = df_selected['Kommentar'].map(lambda x: x.replace('\r', '').replace('\n', ' ' ).replace('\t', ''))
    df_selected['Kommentar'] = df_selected['Kommentar'].map(lambda x: x[:30] + ('[...]' * (len(x)>20)))
    df_selected['Neu?'] = df_selected['Neu?'].map(lambda x: 'Ja' if 'Neu' in x else '')
    df_selected['Vorgang'] = df_selected['Vorgang'].map(lambda x: x.replace('geben', ''))

    opening_hours = range(11, 16) if date.weekday()==5 else range(15, 19)
    missing_slots = [f'{h}:{m}0' for h in opening_hours for m in range(6) if not f'{h}:{m}0' in df_selected['Zeit'].values][:-1]

    df_selected = df_selected.append([{'Zeit': s} for s in missing_slots], ignore_index=True)
    df_selected.fillna('', inplace=True)

    df_selected = df_selected.sort_values('Zeit', ignore_index=True)
    df_selected.set_index('Zeit', inplace=True)

    xls_file = choose_filesave(default_dir=os.path.expanduser('~\\Desktop\\'), default_filename=f'CC-Übersicht-{date_str}.xlsx')


    with pd.ExcelWriter(xls_file, engine='xlsxwriter') as writer:
        book = writer.book
        df_selected.to_excel(writer, sheet_name=date_str)
        sheet = writer.sheets[date_str]
        sheet.set_landscape()
        sheet.center_vertically()
        sheet.center_horizontally()
        sheet.hide_gridlines(False)
        sheet.fit_to_pages(1,1)
        sheet.set_margins(0, 0, 0, 0)
        sheet.set_print_scale(120)

        def get_col_widths(dataframe):
            # First we find the maximum length of the index column
            idx_max = max([len(str(s)) for s in dataframe.index.values] + [len(str(dataframe.index.name))])
            # Then, we concatenate this to the max of the lengths of column name and its values for each column, left to right
            return [idx_max] + [max([len(str(s)) for s in dataframe[col].values] + [len(col)]) for col in dataframe.columns]
        
        for i, width in enumerate(get_col_widths(df_selected)):
            sheet.set_column(i, i, min(width+1, 20))


        format = book.add_format()
        format.set_align('center')
        format.set_align('vcenter')
        sheet.set_column('D:E',5, format)


    os.system(f'start excel.exe "{xls_file}"')
    if 'clickandcollect_' in csv_file:
        os.remove(csv_file)