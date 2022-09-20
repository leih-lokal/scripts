# -*- coding: utf-8 -*-
"""
Created on Wed Jan 20 18:31:23 2021

@author: Simon
"""
import re
import traceback
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
    string = f"""Liebe:r {customer.firstname} {customer.lastname}

danke, dass Sie Ausleiher:in im leih.lokal sind. 
Wir freuen uns, dass immer mehr Menschen Gegenstände leihen.
   
Bei der Ausleihe am {rented_on} hatten wir als Rückgabefrist den {to_return_on} vereinbart.
Damit auch andere Nutzer von unserem Angebot profitieren können, bitten wir Sie, den Gegenstand {rental.item_name} (Nr. {rental.item_id}) zurückzubringen.
Mit jedem Öffnungstag fällt eine kleine Säumnisgebühr von 2 Euro an, die dem Erhalt des leih.lokals zugute kommt, d.h. zum jetzigen Zeitpunkt 2 Euro.

Bei Fragen oder wegen möglicher Verlängerung wenden Sie sich bitte via E-Mail an leihlokal@buergerstiftung-karlsruhe.de oder telefonisch während der Öffnungszeiten unter 0721/47004551 an einen unserer ehrenamtlichen MitarbeiterInnen.
Viele Grüße aus dem leih.lokal.

Gerwigstr. 41, 76131 Karlsruhe
Öffnungszeiten: Mo, Do: 15-19, Sa: 11-16
http://www.buergerstiftung-karlsruhe.de/leihlokal/

Diese Email wurde automatisch erstellt."""
    string = urllib.parse.quote(string)
    return string

def get_deletion_template(customer):
    lastinteraction = customer.last_interaction().strftime('%d.%m.%Y')
    string = f'Liebe:r {customer.firstname} {customer.lastname},\n\n'\
             f'um die persönlichen Daten unserer Kund:innen zu schützen löschen wir diese ' \
             f'nachdem mehr als zwei Jahre seit dem letzten Kontakt vergangen ist. ' \
             f'In deinem Fall ist dies am {lastinteraction} gewesen.\n' \
             f'Wir freuen uns, wenn du weiter Mitglied im leih.lokal sein möchtest.\n'\
             f'In diesem Fall antworte bitte kurz auf diese Mail.\n\n'\
             f'Liebe Grüße und vielleicht bis bald aus dem leih.lokal\n\nGerwigstr. 41, 76131 Karlsruhe\nTelefon: 0721/47004551\nÖffnungszeiten: Mo, Do: 15-19, Sa: 11-16'
    string = urllib.parse.quote(string)
    return string


############ FUNCTIONS ################################################

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

def send_notifications_for_overdue_rental(store):
    """
    Send reminders to customers when their rental is overdue
    """
    print('#'*25)
    print('Suche nach überschrittenen Ausleihfristen')

    filter_overdue = lambda rental: (isinstance(rental.to_return_on, datetime.date)
                                     and rental.to_return_on < datetime.datetime.now().date()
                                     and not isinstance(rental.returned_on, datetime.date))
    rentals_overdue = store.filter_rentals(filter_overdue)
    customers_reminded_ids = [c.id for c in get_recently_sent_reminders(store, pattern='[leih.lokal] Erinnerung', cutoff_days=7)]

    rentals = [r for r in rentals_overdue if r.customer_id not in customers_reminded_ids]
    rentals_reminded = len([r for r in rentals_overdue if r.customer_id  in customers_reminded_ids])
    print(f'{len(rentals_overdue)} überfällige Ausleihen gefunden. ({rentals_reminded} schon erinnert.)')
    show_n = 5
    if len(rentals)>show_n: 
        show_n = 'nan'
        while not show_n.isdigit():
            show_n = input('Für wieviele moechtest du jetzt eine Email erstellen?\n'
                           'Zahl eintippen und mit <enter> bestaetigen.\n')
            if show_n=='': 
                print('abgebrochen...')
                return
            if not show_n.isdigit() or int(show_n)<1:
                print('Muss eine Zahl sein.')
        show_n = int(show_n)

    for rental in rentals[:show_n]:
        if not rental.customer_id in customers_reminded_ids: 
            send_return_reminder(rental)

        
    if len(rentals_overdue)>show_n: 
        printed = '\n'
        for rental in rentals_overdue[show_n:]:
            customer = store.customers.get(int(rental.customer_id))
            printed += f'customer {rental.customer_id} ({customer.firstname} {customer.lastname}): item {rental.item_id} (rental.item_name) on {rental.to_return_on}\n'
       
        print(f'\n\n{len(rentals_overdue)} Gegenstände sind insgesamt überfällig.\n'\
               f'Noch {len(rentals_overdue)-rentals_reminded} Loescherinnerungen sind zu senden.\n'\
               f'Nur die ersten {show_n} werden automatisch erstellt. \nDer Rest ist: \n' + printed + 
               f'\n\nEnde der Liste. Nachdem die Mails geschickt wurden kann das '
               f'Script erneut ausgeführt werden und die nächsten {show_n} werden erzeugt.')
    return True


def send_notification_for_customers_on_deletion(store):
        """
        find all customers that havnt had an interaction with leihlokal
        for 1 or two years, and send them a question if their data should be
        deleted.
        """
        print('#'*25)
        print('Suche nach Mitgliedern die geloescht werden müssen')

        today = datetime.datetime.now().date()
        delta2y = datetime.timedelta(days=365*2)

        # get all rentals of the last 2 years
        rentals_2years = store.filter_rentals(lambda r: r.rented_on > today-delta2y)
        # get all customers that rented something in the last two years
        customers_ids_2years = set([r.customer_id for r in rentals_2years])
        
        # lambda to get all that had 'last_interaction' before two years ago
        func = lambda c: (today - c.last_interaction()).days >= 365*2
        customers_old = store.filter_customers(func)
        # sanity check, really no rentals on their id?
        customers_old = [c for c in customers_old if not c.id in customers_ids_2years]

        already_sent = get_recently_sent_reminders(store, pattern='[leih.lokal] Löschung', cutoff_days=9999)
        already_sent = [c for c in already_sent if c in customers_old]
        customers_old = [c for c in customers_old if c not in already_sent]
        customers_old = [c for c in customers_old if not (c.lastname=='' and c.firstname=='')]
        
        # this list has all kunden which did not respons within 10 days.
        to_delete = [c for c in already_sent if (datetime.datetime.now().date() - c.last_deletion_reminder).days>7]
        print(f'{len(customers_old)} Kunden gefunden die seit 365 Tagen nichts geliehen haben.')

        print(f'{len(already_sent)-len(to_delete)} Wurden schon erinnert und müssen sich melden \n{len(to_delete)} haben sich nach 7 Tagen nicht gemeldet und koennen geloescht werden.')
        
        show_n = 5
        if len(customers_old)>show_n: 
            show_n = 'nan'
            while not show_n.isdigit():
                show_n = input('Für wieviele moechtest du jetzt eine Email erstellen?\n'
                               'Zahl eintippen und mit <enter> bestaetigen.\n')
                if show_n=='': 
                    print('abgebrochen...')
                    return
                if not show_n.isdigit() or int(show_n)<1:
                    print('Muss eine Zahl sein.')
            show_n = int(show_n)
            
        for customer in customers_old[:show_n]:
            # if not rental.customer_id in customers_reminded_ids: 
            send_deletion_reminder(customer)
            
        if len(customers_old)>show_n: 
            printed = '\n'
            for customer in customers_old:
                customer = store.customers.get(customer.id, f'NOT FOUND: {customer.id}')
                printed += f'{customer} \n'
           
            print(f'\n\nDie restlichen sind:\n{printed}\n\nBitte verschicke'
                  ' die eMails und lasse das Script erneut laufen.')
        print('Die folgenden Kunden haben sich 7 Tage nicht gemeldet und koennen geloescht werden:\n' +
              '\n'.join([str(c) for c in to_delete]))
        return False


def send_deletion_reminder(customer):
    """doesnt actually send, just opens the mail program with the template"""
    body = get_deletion_template(customer)
    subject = f'[leih.lokal] Löschung Ihrer Daten im leih.lokal nach Inaktivität (Kunden-Nr. {customer.id}).'
    recipient = customer.email

    if not '@' in recipient: 
        print(f'Keine Email: {customer}, direkt löschen.')
        return
    webbrowser.open('mailto:?to=' + recipient + '&subject=' + subject + '&body=' + body, new=1)
    return 

def send_return_reminder(rental):
    """
    send reminders for rental return

    doesnt actually send, just opens the mail program with the template
    """
    customer = rental.customer
    body = get_reminder_template(customer, rental)
    subject = f'[leih.lokal] Erinnerung an Rückgabe von {rental.item_name} (Nr. {rental.item_id})'
    recipient = customer.email

    if not '@' in recipient: 
        print(f'{customer.firstname} {customer.lastname}({customer.id}, rented {rental.item_id}:{rental.item_name}) has no email. Please call manually')
        return
    webbrowser.open('mailto:?to=' + recipient + '&subject=' + subject + '&body=' + body, new=1)
    return 



def check_website_status(store):
    """
    A small script that checks whether all items that are not available
    online are also really rented by people and vice versa.
    """
    wc_products = get_leihlokaldata()

    unavailable_wc = {str(key).zfill(4):wc_products[key] for key in wc_products.keys() if wc_products[key]['status']=='Verliehen'}
    available_wc = {str(key).zfill(4):wc_products[key] for key in wc_products.keys() if wc_products[key]['status']=='Ausleihbar'}

    # unavailable_couchdb = self.filter_items(lambda x:x.status_on_website!='outofstock')
    curr_rental_items = list(set([rental.item for rental in store.filter_rentals(lambda x:not x.returned_on)]))
    curr_reserved_items = store.filter_items(lambda x: x.status=='reserved')
    curr_inrepair_items = store.filter_items(lambda x: x.status=='onbackorder')

    print('\n------- Online verliehen, aber keine Ausleihe ---------')
    for code in sorted(unavailable_wc):
        name = unavailable_wc[code]['name']
        item = store.items.get(int(code))
        if item is None: 
            print(f'{item} nicht gefunden')
            continue
        if item not in curr_rental_items \
            and not item.id in curr_reserved_items\
            and not item.id in curr_inrepair_items:
            print(f'{code} {name}: ist online auf "verliehen", aber hat keine Ausleihe')
        if item.exists_more_than_once:
            print(f"{code} {name}: Existiert mehr als einmal, ist aber online auf 'Verliehen'")

    print('\n------- Online verfügbar, aber aktive Ausleihe -------')
    for item in sorted(curr_rental_items, key=lambda x:x.id if hasattr(x, 'id') else 0):
        try:
            code = f'{item.id}'.zfill(4)
            if not code in unavailable_wc and not item.exists_more_than_once:
                print(f'{code} {item.name}: aktive Ausleihe, aber ist online "auf Lager"')

        except Exception as e:
            print(f'Fehler beim filtern von {item}: {e}')

    print('\n------- Online reserviert, schau bitte ob Reservierung noch aktuell-------')
    curr_reserved_items = sorted(curr_reserved_items, key=lambda x:x.last_update,
                                 reverse = True)
    for item in curr_reserved_items:
        print(f'Am {item.last_update} reserviert: {item}')

    print('\n------- [INFO] Als "in Reparatur" markiert -------')
    for item in curr_inrepair_items:
        if item.id in available_wc:
            print(f'WARNUNG: {item.id} {item.name} ist online als verfügbar')
        print(f'{item} online nicht verfügbar seit {item.last_update if hasattr(item, "last_update") else ""}')


    print('\n' + '-'*55)



############ MAIN ################################################

#%% main
if __name__ == '__main__':

    store = LeihLokal()

    # Run status check
    input('Drücke <ENTER> um den Statuscheck laufen zu lassen.\n')
    try:
        check_website_status(store)
    except Exception as e:
        traceback.print_exc()
        print(e)

    # Send reminder emails
    #answer = input('\nVersäumniserinnerungen vorbereiten? (J/N)\n')
    #if 'J' in answer.upper():
    #    try:
    #        send_notifications_for_overdue_rental(store)
    #    except FileNotFoundError as e:
    #        print('ERROR: Thunderbird mailbox file nicht gefunden?')
    #        print('Muss in settings.json angegeben werden.')
    #        print(e)
    #    except Exception as e:
    #        traceback.print_exc()
    #        print(e)

    # Send customer deletion mails
    print('-'*20)
    answer = input('\nKundenloeschung nach 365 Tagen vorbereiten? (J/N)\n')
    if 'J' in answer.upper():
        try:
            send_notification_for_customers_on_deletion(store)
        except FileNotFoundError as e:
            print('ERROR: Thunderbird mailbox file nicht gefunden?')
            print('Muss in settings.json angegeben werden.')
            print(e)
        except Exception as e:
            traceback.print_exc()
            print(e)
    input('Fertig.')
