#! python3

# requires pyexcel, pyexcel-ods, plyer and pymsgbox packages to be installed, first argument is the ods file
"""

Ideas for statistic:
    - average items rented at any moment
    - how many people, how many items
    - items: how often
    - deposit "x people trusted us with X deposit, we returned X"
    - overdue amount


"""
import datetime
import sys
import time
from dataclasses import dataclass, field, fields
import webbrowser
import pyexcel as pe
from typing import List, Dict, Callable, Optional
import mailbox
from email.header import decode_header
import json
import traceback
import urllib.parse
from pprint import pprint
from tqdm import tqdm
from website import get_leihlokaldata


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

CUSTOMER_DELETION_NOTIFICATION_TITLE = "{} Kunde(n) sollten manuell gelöscht werden"
CUSTOMER_DELETION_NOTIFICATION_TEXT = """{} sollten manuell gelöscht und die Ausweiskopie vernichtet werden.\n\nDieses Programm löscht keine Daten."""

# in the settings.json we save user-specific variables. the file will never be uploaded to github


with open('settings.json', 'r', encoding='utf-8') as f:
    settings = json.load(f)

############ END SETTINGS ############################################

        
@dataclass
class Customer:

    id: int
    lastname: str
    firstname: str
    registration_date: datetime.date
    renewed_on: datetime.date
    remark: str
    subscribed_to_newsletter: bool
    email: str
    street: str
    house_number: str # due to 2A etc
    postal_code: int
    city: str
    telephone_number: str
    rentals: List['Rental'] = field(default_factory=list, repr=False)

    def last_contractual_interaction(self) -> datetime.date:
        try:
            registration = self.registration_date if self.registration_date else datetime.date.fromtimestamp(0)
            renewed = self.renewed_on if self.renewed_on else  registration
            rented = [rental.rented_on for rental in self.rentals]
            returned = [rental.returned_on for rental in self.rentals]
            all_dates = rented + returned + [registration, renewed]
            all_dates = [d if type(d) is datetime.date else d.date() for d in all_dates if not isinstance(d, str)]
            date =  max(all_dates)
        except Exception as e:
            traceback.print_exc()
            print(self, e)
            return registration
        return date

    def short(self) -> str:
        return f'{self.firstname} {self.lastname} ({self.id})'
    
    def __repr__(self):
        return f'{self.id}: {self.firstname} {self.lastname} ({self.email}, {self.telephone_number})'
    
    def __str__(self):
        return f'{self.id}: {self.firstname} {self.lastname} ({self.email}, {self.telephone_number})'
   
    def __post_init__(self): 
        """convert to given datatype, if possible"""
        for fieldv in fields(self):
            value = getattr(self, fieldv.name)
            if not value or value=='-': continue
            try:
                if isinstance(value, fieldv.type): continue
            except: # cant be type checked, e.g. subscripted generics
                continue
            try:
                setattr(self, fieldv.name, fieldv.type(value))
            except:
                print(f"could not convert '{value}'{type(value)} to {fieldv.type} in {repr(self)}")
    
@dataclass
class Item:
    item_id: int
    item_name: str
    brand: str
    itype: str
    category: str
    deposit: str
    parts: str
    manual: str
    package: str
    added: datetime.date
    properties: str
    n_rented:int = 0
    status:str = 'Ausleihbar'

    def __post_init__(self): 
        """convert to given datatype, if possible"""
        for fieldv in fields(self):
            value = getattr(self, fieldv.name)
            if not value or value=='-': continue
            try:
                if isinstance(value, fieldv.type): continue
            except: # cant be type checked, e.g. subscripted generics
                continue
            try:
                setattr(self, fieldv.name, fieldv.type(value))
            except:
                print(f"could not convert '{value}'{type(value)} to {fieldv.type} in {repr(self)}")
    
@dataclass
class Rental:

    item_id: int
    item_name: str

    rented_on: datetime.date
    extended_on: datetime.date
    to_return_on: datetime.date
    passing_out_employee: str
    customer_id: int
    name: str
    deposit: str
    deposit_returned: str
    returned_on: datetime.date
    receiving_employee: str
    deposit_retained: str
    deposit_retainment_reason: str
    remark: str
    customer: Optional[Customer] = field(repr=False)
    

    def __repr__(self):
        return f'customer {self.customer_id} -> item {self.item_id}: {self.rented_on} -> {self.to_return_on}'
   
    def __post_init__(self): 
        """convert to given datatype, if possible"""
        for fieldv in fields(self):
            value = getattr(self, fieldv.name)
            if not value or value=='-': continue
            try:
                if isinstance(value, fieldv.type): continue
            except: # cant be type checked, e.g. subscripted generics
                continue
            try:
                setattr(self, fieldv.name, fieldv.type(value))
            except:
                print(f"could not convert '{value}'{type(value)} to {fieldv.type} in {repr(self)}")
    
class Store:

    def __init__(self, customers: Dict[int, Customer], rentals: List[Rental],
                 items: List[Item]):
        self.customers = customers
        self.rentals = rentals
        self.items = items
        
    

    @classmethod
    def parse_file(cls, file: str) -> 'Store':
        return cls.parse(pe.get_book(file_name=file))

    @classmethod
    def parse(cls, sheet: pe.Book) -> 'Store':
        store = Store({}, [], {})
        store.customers = {int(row[0]): Customer(*row[:13]) for row in sheet.Kunden.array if str(row[0]).isdigit()
                          and len(row[2].strip()) > 0}
        store.items = {int(row[0]): Item(*row[:11]) for row in sheet.Gegenstände.array if str(row[0]).isdigit()
                          and len(row[1].strip()) > 0}
            
        for row in sheet.Leihvorgang.array:
            if str(row[6]).isdigit():
                customer = store.customers.get(int(row[6]), None)
                rental = Rental(*row[:15], customer=customer)
                if rental.item_id in store.items:
                    store.items[rental.item_id].n_rented += 1
                    status = 'Ausleihbar' if rental.returned_on else 'Verliehen'
                    store.items[rental.item_id].status = status
                if customer is not None:
                    customer.rentals.append(rental)

                store.rentals.append(rental)
        return store
    
    def send_deletion_reminder(self, customer: Customer) -> None:
        """doesnt actually send, just opens the mail program with the template"""
        customer = self.customers.get(customer.id, f'Name for {customer.id} not found')
        body = get_deletion_template(customer)
        subject = f'[leih.lokal] Löschung Ihrer Daten im leih.lokal nach 365 Tagen (Kunden-Nr. {customer.id}).'
        recipient = customer.email

        if not '@' in recipient: 
            print(f'Keine Email hinterlegt: {customer}')
            return
        webbrowser.open('mailto:?to=' + recipient + '&subject=' + subject + '&body=' + body, new=1)
        return 
    
    def send_reminder(self, rental: Rental) -> None:
        """doesnt actually send, just opens the mail program with the template"""
        customer = self.customers.get(int(rental.customer_id), f'Name for {rental.customer_id} not found')
        body = get_reminder_template(customer, rental)
        subject = f'[leih.lokal] Erinnerung an Rückgabe von {rental.item_name} (Nr. {rental.item_id})'
        recipient = customer.email

        if not '@' in recipient: 
            print(f'{customer.firstname} {customer.lastname}({customer.id}, rented {rental.item_id}:{rental.item_name}) has no email. Please call manually')
            return
        webbrowser.open('mailto:?to=' + recipient + '&subject=' + subject + '&body=' + body, new=1)
        return 

    def get_recently_sent_reminders(self, pattern='[leih.lokal] Erinnerung', cutoff_days=7) -> None:

        mboxfile = settings['thunderbird-profile']
        sent = mailbox.mbox(mboxfile)

        if len(sent)==0:

            raise FileNotFoundError(f'mailbox not found at {mboxfile}. '
                                    'Please add in file under SETTINGS')
        
        customers_reminded = []

        for message in tqdm(sent):
            to = message.get('To')
            if '<' in to:
                to = to.split('<')[-1][:-1]
            to=to.strip()
            subject = message.get('Subject')
            if not subject: continue
            subject = decode_header(subject)[0][0]
            datestr = message.get('Date')[:16].strip()
            date = datetime.datetime.strptime(datestr, '%a, %d %b %Y').date()
            diff = datetime.datetime.now().date() - date
            

            if not isinstance(subject, str) and subject: 
                try: subject = subject.decode()
                except: subject = str(subject)
            
            # do not send reminder if last one has been sent within the last 10 days
            if pattern in subject and diff.days<cutoff_days:
                filter = lambda c: c.email==to
                customers = self.filter_customers(filter)
                if len(customers)==1:
                    customer = customers[0]
                    customer.last_deletion_reminder = date
                    customers_reminded.append(customer)
                if len(customers)>1: 
                    print(f'Warning, several customers with same email were found: {to}:{[str(c)for c in customers]}')
        return customers_reminded

    def filter_items(self, predicate: Callable[[Item], bool]) -> List[Item]:
        filtered = []
        for item in self.items.values():
            try: 
                filter = predicate(item)
                if filter:
                    filtered.append(item)
            except Exception as e:
                traceback.print_exc()
                print(f'Error filtering customer {item}: {e}')
        return filtered


    def filter_customers(self, predicate: Callable[[Customer], bool]) -> List[Customer]:
        filtered = []
        for customer in self.customers.values():
            try: 
                filter = predicate(customer)
                if filter:
                    filtered.append(customer)
            except Exception as e:
                traceback.print_exc()
                print(f'Error filtering customer {customer}: {e}')
        return filtered
    
    def filter_rentals(self, predicate: Callable[[Customer], bool]) -> List[Rental]:
        filtered = []
        for rental in self.rentals:
            try: 
                filter = predicate(rental)
                if filter:
                    filtered.append(rental)
            except Exception as e:
                traceback.print_exc()
                print(f'Error filtering rental {rental}: {e}')
        return filtered
    
    def get_customers_for_deletion(self, days: int = 365) -> 'Store':
        filter = lambda c: ((datetime.datetime.now().date() - c.last_contractual_interaction()).days\
            >= 365) if c.registration_date < datetime.date(2020,5,20) else ((datetime.datetime.now().date() - c.last_contractual_interaction()).days\
            >= 365*2)
        return self.filter_customers(filter)

    def get_overdue_reminders(self) -> List[Rental]:
        filter = lambda r: ((not 'datetime.datetime' in str(type(r.to_return_on))) and \
                            r.to_return_on < datetime.datetime.now().date() and \
                            not isinstance(r.returned_on, datetime.date))
        return self.filter_rentals(filter)

    def check_website_status(self):
        """
        A small script that checks whether all items that are not available
        online are also really rented by people.
        """
        products = get_leihlokaldata()

        online_unavailable = [products[key] for key in products.keys() if products[key]['status']=='Verliehen']
        for product_online in online_unavailable:
            code = product_online['code']
            name = product_online['name']
            product_excel = self.items.get(code)
            if product_excel:
                if product_excel.status!=product_online['status']:
                    print(f'{code} ({name}) ist online auf Verliehen, aber laut Excel auf Lager')

        excel_unavailable = self.filter_items(lambda x:x.status=='Verliehen')
        for product_excel in excel_unavailable:
            code = int(product_excel.item_id)
            name = product_excel.item_name
            product_online = products.get(code)
            if product_online:
                if product_excel.status!=product_online['status']:
                    print(f'{code} ({name}) ist in Excel verliehen, aber online auf Lager')

    def extended_check_website(self):
        """run an extended check for data from the website and the excel file"""
        raise NotImplemented

    def __repr__(self) -> str:
        return f"{len(self.items)}, items {len(self.customers)}, customers {len(self.rentals)} rentals"

    def empty(self) -> bool:
        return len(self.customers) == 0

    def send_notification_for_customers_on_deletion(self, with_blocking_popup: bool = False) -> bool:
        """
        :return: really sent a notification
        """
        print('#'*25)
        print('Suche nach Mitgliedern die geloescht werden müssen')
        customers_old = self.get_customers_for_deletion()
        
        already_sent = self.get_recently_sent_reminders(pattern='[leih.lokal] Löschung', cutoff_days=9999)
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
                show_n = input(f'Für wieviele moechtest du jetzt eine Email erstellen?\n'
                               f'Zahl eintippen und mit <enter> bestaetigen.\n')
                if show_n=='': 
                    print('abgebrochen...')
                    return
                if not show_n.isdigit() or int(show_n)<1:
                    print('Muss eine Zahl sein.')
            show_n = int(show_n)
            
        for customer in customers_old[:show_n]:
            # if not rental.customer_id in customers_reminded_ids: 
            self.send_deletion_reminder(customer)
            
        if len(customers_old)>show_n: 
            printed = '\n'
            for customer in customers_old:
                customer = self.customers.get(int(customer.id), f'NOT FOUND: {customer.id}')
                printed += f'{customer} \n'
           
            print(f'\n\nDie restlichen sind:\n{printed}\n\nBitte verschicke'
                  ' die eMails und lasse das Script erneut laufen.')
        print(f'Die folgenden Kunden haben sich 7 Tage nicht gemeldet und koennen geloescht werden:\n' + 
              '\n'.join([str(c) for c in to_delete]))
        return False
    
    def send_notifications_for_customer_return_rental(self) -> bool:
        print('#'*25)
        print('Suche nach überschrittenen Ausleihfristen')
        rentals_overdue = self.get_overdue_reminders()
        customers_reminded_ids = [c.id for c in self.get_recently_sent_reminders()]
        

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
    
    def plot_statistics(self):
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

#%% main
if __name__ == '__main__':
    excel_file = settings['leihgegenstaendeliste']
    print('Lade Datenbank...')
    store = Store.parse_file(excel_file)

    # Run status check
    input('Drücke <ENTER> um den Statuscheck laufen zu lassen.\n')
    store.check_website_status()

    # Send reminder emails
    answer = input('Versäumniserinnerungen vorbereiten? (J/N)\n')
    if 'J' in answer.upper():
        try:
            store.send_notifications_for_customer_return_rental()
        except Exception as e:
            traceback.print_exc()
            print(e)

    # Send customer deletion mails
    answer = input('Kundenloeschung nach 365 Tagen vorbereiten? (J/N)\n')
    if 'J' in answer.upper():
        try:
            store.send_notification_for_customers_on_deletion()
        except Exception as e:
            traceback.print_exc()
            print(e)
    self=store # debugging made easier
    input('Fertig.')
