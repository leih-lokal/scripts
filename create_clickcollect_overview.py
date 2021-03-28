# -*- coding: utf-8 -*-
"""
Created on Sun Mar 28 06:49:27 2021

This script takes the CSV from the WP Appointment Booking Hour plugin
and creates an overview for the current day in XLS format to print out

@author: Simon
"""

import os, sys
import pandas as pd
from tkinter.filedialog import askopenfilename, askdirectory
from tkinter import Tk

def choose_file(default_dir=None, title='Bitte die CSV-Datei auswählen'):
    """
    Open a file chooser dialoge with tkinter.
    
    :param default_dir: Where to open the dir, if set to None, will start at wdir
    :param exts: A string or list of strings with extensions etc: 'txt' or ['txt','csv']
    :returns: the chosen file
    """
    root = Tk()
    root.iconify()
    root.update()
    name = askopenfilename(initialdir=default_dir,
                           parent=root,
                           title = title,
                           filetypes =(("CSV", "*.csv") ,
                                       ("All Files","*.*")))
    root.update()
    root.destroy()
    if not os.path.exists(name):
        print("No file chosen")
    else:
        return name
  
def show_date_picker(title=''):
    import tkinter as tk
    from tkinter import ttk
    from tkcalendar import Calendar

    def cal_done():
        top.withdraw()
        root.quit()

    root = tk.Tk()
    root.title(title)
    root.withdraw() # keep the root window from appearing

    top = tk.Toplevel(root)

    tk.Label(top, text='Für welchen Tag soll die Übersicht erstellt werden?', font='sans 13').pack()
    cal = Calendar(top, font="Arial 12", selectmode='day', locale='de_DE')
    cal.pack(fill="both", expand=True)
    tk.Button(top, text="Diesen Tag wählen", font='sans 12 bold', command=cal_done).pack()

    root.mainloop()
    return cal.selection_get()



if __name__=='__main__':

    csv_file = choose_file(os.path.expanduser("~\\Desktop\\"))
    df = pd.read_csv(csv_file, encoding='iso-8859-1')
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

    df_selected.drop('app_date_1', axis=1, inplace=True)
    df_selected['Ihr Vor- und Zuname'] = df_selected['Ihr Vor- und Zuname'] + ' ('+ df_selected['Ihre Nutzernummer (falls zur Hand)'] + ')'
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

    xls_file = os.path.dirname(csv_file) + f'\\CC-Übersicht-{date_str}.xlsx'

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
