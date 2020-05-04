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
from dataclasses import dataclass, field
import webbrowser
import pyexcel as pe
from typing import List, Dict, Callable, Optional
import mailbox
from email.header import decode_header
import json
import traceback
import urllib.parse
from tqdm import tqdm


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


with open('settings.json', 'r', encoding='latin1') as f:
    settings = json.load(f)

############ END SETTINGS ############################################

        
@dataclass
class Customer:

    id: int
    lastname: str
    firstname: str
    registration_date: datetime.date
<<<<<<< HEAD
    renewed_on: datetime.date
=======
    renewed_on: str
>>>>>>> ac418c961ed094d240c3bc5d7dcda52fcd539988
    remark: str
    subscribed_to_newsletter: bool
    email: str
    street: str
    house_number: int
    postal_code: int
    city: str
    telephone_number: str
    rentals: List['Rental'] = field(default_factory=list, repr=False)

    def last_contractual_interaction(self) -> datetime.date:
        try:
            registration = self.registration_date if self.registration_date else datetime.date.fromtimestamp(0)
            renewed = self.renewed_on if self.renewed_on else  registration
            rental = [rental.rented_on for rental in self.rentals]
            date =  max(rental + [registration, renewed])
        except Exception as e:
            traceback.print_exc()
            print(e)
            return registration
        return date

    def short(self) -> str:
        return f'{self.firstname} {self.lastname} ({self.id})'
    
    def __repr__(self):
        return f'{self.id}: {self.firstname} {self.lastname} ({self.email}, {self.telephone_number})'
    def __str__(self):
        return f'{self.id}: {self.firstname} {self.lastname} ({self.email}, {self.telephone_number})'
    
@dataclass
class Item:
    item_id: int
    item_name: str
    brand: str
    itype: str
    category: str
    deposit: int
    parts: int
    manual: bool
    package: str
    added: datetime.date
    properties: str
    def __repr__(self):
        return f'{self.item_id}: {self.item_name} ({self.deposit}€)'
    
@dataclass
class Rental:

    item_id: int
    item_name: str

    rented_on: datetime.datetime
    extended_on: datetime.datetime
    to_return_on: datetime.datetime
    passing_out_employee: str
    customer_id: int
    name: str
    deposit: int
    deposit_returned: int
    returned_on: datetime.date
    receiving_employee: datetime.date
    deposit_retained: int
    deposit_retainment_reason: str
    remark: str
    customer: Optional[Customer] = field(repr=False)

    def __repr__(self):
        return f'customer {self.customer_id} -> item {self.item_id}: {self.rented_on} -> {self.to_return_on}'
    
    
    
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
        store.customers = {row[0]: Customer(*row[:13]) for row in sheet.Kunden.array if isinstance(row[0], int)
                          and len(row[2].strip()) > 0}
        store.items = {row[0]: Item(*row[:11]) for row in sheet.Gegenstände.array if isinstance(row[0], int)
                          and len(row[1].strip()) > 0}
        for row in sheet.Leihvorgang.array:
            if isinstance(row[0], int):
                customer = store.customers.get(row[6], None)
                rental = Rental(*row[:15], customer=customer)
                if customer is not None:
                    customer.rentals.append(rental)
                store.rentals.append(rental)
        return store
    
    def send_deletion_reminder(self, customer: Customer) -> None:
        """doesnt actually send, just opens the mail program with the template"""
        customer = self.customers.get(customer.id, f'Name for {customer.id} not found')
        body = get_deletion_template(customer)
        subject = f'[leih.lokal] Löschung Ihrer Daten im leih.lokal nach 365 Tagen.'
        recipient = customer.email

        if not '@' in recipient: 
            print(f'Keine Email hinterlegt: {customer}')
            return
        webbrowser.open('mailto:?to=' + recipient + '&subject=' + subject + '&body=' + body, new=1)
        return 
    
    def send_reminder(self, rental: Rental) -> None:
        """doesnt actually send, just opens the mail program with the template"""
        customer = self.customers.get(rental.customer_id, f'Name for {rental.customer_id} not found')
        body = get_reminder_template(customer, rental)
        subject = f'[leih.lokal] Erinnerung an Rückgabe von {rental.item_name} (Nr. {rental.item_id})'
        recipient = customer.email

        if not '@' in recipient: 
            print(f'{customer.firstname} {customer.lastname}({customer.id}, rented {rental.item_id}:{rental.item_name}) has no email. Please call manually')
            return
        webbrowser.open('mailto:?to=' + recipient + '&subject=' + subject + '&body=' + body, new=1)
        return 

    def get_recently_sent_reminders(self, pattern='[leih.lokal] Erinnerung', cutoff_days=10) -> None:

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
            date = datetime.datetime.strptime(datestr, '%a, %d %b %Y')
            diff = datetime.datetime.now() - date
            

            if not isinstance(subject, str) and subject: 
                try: subject = subject.decode()
                except: subject = str(subject)
            
            # do not send reminder if last one has been sent within the last 10 days
            if pattern in subject and diff.days<cutoff_days:
                filter = lambda c: c.email==to
                customers = self.filter_customers(filter)
                customer = customers[0]
                customer.last_deletion_reminder = date
                customers_reminded.append(customer)
                if len(customers)>1: 
                    print(f'Warning, several customers with same email were found: {to}:{[str(c)for c in customers]}')
        return customers_reminded
    
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
    
    def get_customers_for_deletion(self, min_full_started_days_since_last_contractual_interaction: int = 365) -> 'Store':
        filter = lambda c: (datetime.datetime.now().date() - c.last_contractual_interaction()).days\
            >= min_full_started_days_since_last_contractual_interaction
        return self.filter_customers(filter)

    def get_overdue_reminders(self) -> List[Rental]:
        filter = lambda r: ((not 'datetime.datetime' in str(type(r.to_return_on))) and \
                            r.to_return_on < datetime.datetime.now().date() and \
                            not isinstance(r.returned_on, datetime.date))
        return self.filter_rentals(filter)

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
        customers = self.get_customers_for_deletion()
        print(f'{len(customers)} Kunden gefunden die seit 365 Tagen nichts geliehen haben.')
        
<<<<<<< HEAD
        already_sent = self.get_recently_sent_reminders(pattern='[leih.lokal] Löschung', cutoff_days=9999)
        customers = [c for c in customers if c not in already_sent]
        # this list has all kunden which did not respons within 10 days.
        to_delete = [c for c in already_sent if (datetime.datetime.now() - c.last_deletion_reminder).days>-1]
        
        print(f'{len(already_sent)-len(to_delete)} Wurden schon erinnert \n{len(to_delete)} haben sich nach 10 Tagen nicht gemeldet und koennen geloescht werden.')
        
        show_n = 5
        if len(customers)>show_n: 
=======
        #customers_reminded_id = self.get_recently_sent_reminders(pattern='[leih.lokal] Löschung')
        #customers_reminded_ids = [c.id for c in customers_reminded_id]
        show_n = 10
        if len(customers)>10: 
>>>>>>> ac418c961ed094d240c3bc5d7dcda52fcd539988
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
            
        for customer in customers[:show_n]:
            # if not rental.customer_id in customers_reminded_ids: 
            self.send_deletion_reminder(customer)
            
        if len(customers)>show_n: 
            printed = '\n'
            for customer in customers:
                customer = self.customers.get(int(customer.id), f'NOT FOUND: {customer.id}')
                printed += f'{customer} \n'
           
            print(f'\n\nDie restlichen sind:\n{printed}\n\nBitte verschicke'
                  ' die eMails und lasse das Script erneut laufen.')
        print(f'Die folgenden Kunden haben sich 10 Tage nicht gemeldet und koennen geloescht werden:\n' + 
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


if __name__ == '__main__':
    excel_file = settings['leihgegenstaendeliste']
    print('Lade Datenbank...')
    store = Store.parse_file(excel_file)
    # store.plot_statistics()
<<<<<<< HEAD
    answer = input('Versäumniserinnerungen vorbereiten? (J/N) ')
    if 'J' in answer.upper():
        try:
            store.send_notifications_for_customer_return_rental()
        except Exception as e:
            traceback.print_exc()
            print(e)
            
    answer = input('Kundenloeschung nach 365 Tagen vorbereiten? (J/N) ')
    if 'J' in answer.upper():
        try:
            store.send_notification_for_customers_on_deletion()
        except Exception as e:
            traceback.print_exc()
            print(e)
    self=store # debugging made easier
    input('Fertig.')
=======
    answer = input('Erinnerungen für Versäumnis vorbereiten? (J/N) ')
    if 'J' in answer.upper():
        try: store.send_notifications_for_customer_return_rental()
        except Exception as e: print(e)
    answer = input('Kunden zur Löschung  anzeigen? (J/N) ')
    if 'J' in answer.upper():
        try: store.send_notification_for_customers_on_deletion()
        except Exception as e: print(e)

    self=store # debugging made easier
    input('Fertig!')
>>>>>>> ac418c961ed094d240c3bc5d7dcda52fcd539988
