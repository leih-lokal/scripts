# -*- coding: utf-8 -*-
"""
Created on Wed Jan 20 18:31:23 2021

@author: Simon
"""
import re
import datetime
from website import get_leihlokaldata
from email.header import decode_header
from leihlokal import LeihLokal
import urllib
import json
import mailbox
import webbrowser
from tqdm import tqdm

with open('settings.json', 'r', encoding='utf-8') as f:
    settings = json.load(f)

############ SETTINGS ################################################

def get_reminder_template(customer, rental):
    rented_on = rental.rented_on.strftime('%d.%m.%Y')
    to_return_on = rental.to_return_on.strftime('%d.%m.%Y')
    string = f'Liebe/r {customer.firstname} {customer.lastname}.\n\n' \
             f'Danke, dass Sie Ausleiher/in im leih.lokal sind.\n\n'\
             f'Wir möchten Sie daran erinnern, den am {rented_on} ausgeliehenen Gegenstand ({rental.item_name} (Nr. {rental.item_id})) wieder abzugeben. '\
             f'Der bei uns vermerkte Rückgabetermin war der {to_return_on}.\n\n'\
             f'Zum heutigen Zeitpunkt fallen 2 Euro an, die unserer Spendenkasse zugeführt werden. '\
             f'Wie Sie unseren Nutzungsbedingungen entnehmen können, kommt pro Öffnungstag eine kleine Säumnisgebühr von 2 Euro je Gegenstand dazu. '\
             f'Bei Fragen wenden Sie sich bitte via E-Mail an leih.lokal@buergerstiftung-karlsruhe.de oder telefonisch während der Öffnungszeiten unter 0721/47004551 an unsere Mitarbeiter.\n\n'\
             f'Grüße aus dem leih.lokal\n\nGerwigstr. 41, 76185 Karlsruhe\nÖffnungszeiten: Mo, Do, Fr: 15-19, Sa: 11-16'
    string = urllib.parse.quote(string)
    return string

def get_deletion_template(customer):
    lastinteraction = customer.last_contractual_interaction().strftime('%d.%m.%Y')
    string = f'Liebe/r {customer.firstname} {customer.lastname}.\n\n'\
             f'Ihre letzte Ausleihe im Leihlokal war vor mehr als einem Jahr ({lastinteraction}).\n'\
             f'Aus datenschutzrechtlichen Gründen sind wir verpflichtet Ihre Daten nach dieser Frist zu löschen.\n'\
             f'Falls Sie weiter Mitglied im Leihlokal sein wollen, antworten Sie bitte kurz auf diese Mail.\n\n'\
             f'Falls wir keine Antwort erhalten, werden wir Ihre Daten aus dem System entfernen.\n\n'\
             f'Liebe Grüße aus dem leih.lokal\n\nGerwigstr. 41, 76185 Karlsruhe\nTelefon: 0721/47004551\nÖffnungszeiten: Mo, Do, Fr: 15-19, Sa: 11-16'
    string = urllib.parse.quote(string)
    return string


############ FUNCTIONS ################################################

def send_deletion_reminder(store, customer):
    """doesnt actually send, just opens the mail program with the template"""
    customer = store.customers.get(customer.id, f'Name for {customer.id} not found')
    body = get_deletion_template(customer)
    subject = f'[leih.lokal] Löschung Ihrer Daten im leih.lokal nach Inaktivität (Kunden-Nr. {customer.id}).'
    recipient = customer.email

    if not '@' in recipient: 
        print(f'Keine Email hinterlegt: {customer}')
        return
    webbrowser.open('mailto:?to=' + recipient + '&subject=' + subject + '&body=' + body, new=1)
    return 

def send_reminder(store, rental):
    """
    send reminders for rental return

    doesnt actually send, just opens the mail program with the template
    """
    customer = store.customers.get(int(rental.customer_id), f'Name for {rental.customer_id} not found')
    body = get_reminder_template(customer, rental)
    subject = f'[leih.lokal] Erinnerung an Rückgabe von {rental.item_name} (Nr. {rental.item_id})'
    recipient = customer.email

    if not '@' in recipient: 
        print(f'{customer.firstname} {customer.lastname}({customer.id}, rented {rental.item_id}:{rental.item_name}) has no email. Please call manually')
        return
    webbrowser.open('mailto:?to=' + recipient + '&subject=' + subject + '&body=' + body, new=1)
    return 

def get_recently_sent_reminders(store, pattern='[leih.lokal] Erinnerung', cutoff_days=7) -> None:
    """Get all customers that have recently received a mail with the given pattern"""
    mboxfile = settings['thunderbird-profile']
    sent = mailbox.mbox(mboxfile)

    if len(sent)==0:
        raise FileNotFoundError(f'mailbox not found at {mboxfile}. '
                                'Please add in file under SETTINGS / thunderbird-profile')
    
    customers_reminded = []

    regex = re.compile("<(.*?)>")


    for message in tqdm(sent, desc='scanning sent emails'):
        to = message.get('To')
        if not isinstance(to, str): continue # unknown header
        if '<' in to: to = regex.search(to).group(1).strip() # format Name <name@domain.de>

        subject = message.get('Subject')
        if not subject: continue # is definitely not a reminder
        subject = decode_header(subject)[0][0]
        datestr = message.get('Date')[:16].strip()
        date = datetime.datetime.strptime(datestr, '%a, %d %b %Y').date()
        diff = datetime.datetime.now().date() - date

        # some subjects contain non-latin1 and need to be properly decoded
        if not isinstance(subject, str) and subject:
            try: subject = subject.decode()
            except: subject = str(subject)
        
        # do not send reminder if last one has been sent within the last 10 days
        if pattern in subject and diff.days<cutoff_days:
            find_customer = lambda customer: customer.email==to
            customers = store.filter_customers(find_customer)
            if len(customers)==1:
                customer = customers[0]
                customer.last_deletion_reminder = date
                customers_reminded.append(customer)
            if len(customers)>1: 
                print(f'Warning, several customers with same email were found: {to}:{[str(c)for c in customers]}')
    return customers_reminded

def send_notifications_for_customer_return_rental(store):
    """
    Send reminders to customers when their rental is overdue
    """
    print('#'*25)
    print('Suche nach überschrittenen Ausleihfristen')

    filter_overdue = lambda rental: (isinstance(rental.to_return_on, datetime.date)
                                     and rental.to_return_on < datetime.datetime.now().date()
                                     and  not isinstance(rental.returned_on, datetime.date))
    rentals_overdue = store.filter_rentals(filter_overdue)
    customers_reminded_ids = [c.id for c in get_recently_sent_reminders(store, pattern='[leih.lokal] Erinnerung', cutoff_days=7)]

    rentals = [r for r in rentals_overdue if r.customer_id not in customers_reminded_ids]
    rentals_reminded = len([r for r in rentals_overdue if r.customer_id  in customers_reminded_ids])
    print(f'{len(rentals_overdue)} überfällige Ausleihen gefunden. ({rentals_reminded} schon erinnert.)')
    show_n = 5
    if len(rentals)>show_n: 
        show_n = 'nan'
        while not show_n.isdigit():
            show_n = input(f'Für wieviele moechtest du jetzt eine Email erstellen?\n'
                           f'Zahl eintippen und mit <enter> bestaetigen.\n')
            if show_n=='': 
                print('abgebrochen...')
                return
            if not show_n.isdigit() or int(show_n)<1:
                print('Muss eine Zahl sein.')
        show_n = int(show_n)

    for rental in rentals[:show_n]:
        if not rental.customer_id in customers_reminded_ids: 
            self.send_reminder(rental)

        
    if len(rentals_overdue)>show_n: 
        printed = '\n'
        for rental in rentals_overdue[show_n:]:
            customer = self.customers.get(int(rental.customer_id))
            printed += f'customer {rental.customer_id} ({customer.firstname} {customer.lastname}): item {rental.item_id} (rental.item_name) on {rental.to_return_on}\n'
       
        print(f'\n\n{len(rentals_overdue)} Gegenstände sind insgesamt überfällig.\n'\
               f'Noch {len(rentals_overdue)-rentals_reminded} Loescherinnerungen sind zu senden.\n'\
               f'Nur die ersten {show_n} werden automatisch erstellt. \nDer Rest ist: \n' + printed + 
               f'\n\nEnde der Liste. Nachdem die Mails geschickt wurden kann das '
               f'Script erneut ausgeführt werden und die nächsten {show_n} werden erzeugt.')
    return True
def check_website_status(store):
    """
    A small script that checks whether all items that are not available
    online are also really rented by people.
    """
    wc_products = get_leihlokaldata()

    unavailable_wc = [wc_products[key] for key in wc_products.keys() if wc_products[key]['status']=='Verliehen']
    # unavailable_couchdb = self.filter_items(lambda x:x.status_on_website!='outofstock')
    curr_rentals = store.filter_rentals(lambda x:not x.returned_on)

    for product in unavailable_wc:
        code = str(product['code']).zfill(4)
        name = product['name']
        item = store.items.get(code)
        if item not in curr_rentals:
            print(f'{code} {name}: ist online auf "verliehen", aber hat keine Ausleihe')

    for product in curr_rentals:
        code = int(product.item_id)
        if not code in unavailable_wc:
            print(f'{str(code).zfill(4)} {product.item_name}: ist lokal verliehen, aber online "auf Lager"')



############ MAIN ################################################

#%% main
if __name__ == '__main__':

    store = LeihLokal()

    # Run status check
    input('Drücke <ENTER> um den Statuscheck laufen zu lassen.\n')
    store.check_website_status()

    # Send reminder emails
    print('-'*20)
    answer = input('\nVersäumniserinnerungen vorbereiten? (J/N)\n')
    if 'J' in answer.upper():
        try:
            store.send_notifications_for_customer_return_rental()
        except Exception as e:
            traceback.print_exc()
            print(e)

    # Send customer deletion mails
    print('-'*20)
    answer = input('\nKundenloeschung nach 365 Tagen vorbereiten? (J/N)\n')
    if 'J' in answer.upper():
        try:
            store.send_notification_for_customers_on_deletion()
        except Exception as e:
            traceback.print_exc()
            print(e)
    self=store # debugging made easier
    input('Fertig.')
