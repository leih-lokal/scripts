#! python3

# requires pyexcel, pyexcel-ods, plyer and pymsgbox packages to be installed, first argument is the ods file

import datetime
import sys
import os
import time
from dataclasses import dataclass, field
from pprint import pprint
import webbrowser
import pyexcel as pe
from typing import List, Dict, Callable, Optional
import mailbox
from email.header import decode_header


############ SETTINGS ################################################ 
def get_reminder_template(customer, rental):
    
    string = 'Liebe/r {customer.firstname} {customer.lastname}.\n\n' \
             'Danke, dass Sie Ausleiher/in im leih.lokal sind.\n\n'\
              'Wir möchten Sie daran erinnern, den am {rental.rented_on} ausgeliehenen Gegenstand ({rental.item_name} ({rental.item_id})) wieder abzugeben. '\
              'Der bei uns vermerkte Rückgabetermin war der {rental.to_return_on}.\n\n'\
              'Zum heutigen Zeitpunkt fallen 2 Euro an, die unserer Spendenkasse zugeführt werden. '\
              'Wie Sie unseren Nutzungsbedingungen entnehmen können, kommt pro Öffnungstag eine kleine Säumnisgebühr von 2 Euro je Gegenstand dazu. '\
              'Bei Fragen wenden Sie sich bitte via E-Mail an leih.lokal@buergerstiftung-karlsruhe.de oder telefonisch während der Öffnungszeiten unter 0721/47004551 an unsere Mitarbeiter.\n\n'\
              'Grüße aus dem leih.lokal\n\nÖffnungszeiten: Mo, Do, Fr: 15-19, Sa: 11-16'

    return string

CUSTOMER_DELETION_NOTIFICATION_TITLE = "{} Kunde(n) sollten manuell gelöscht werden"
CUSTOMER_DELETION_NOTIFICATION_TEXT = """{} sollten manuell gelöscht und die Ausweiskopie vernichtet werden.\n\nDieses Programm löscht keine Daten."""

# set the sent folder of thunderbird in this file so it doesnt upload to github
with open('thunderbird-profile-path.txt', 'r') as f:
    mboxfile = f.read().strip()

############ END SETTINGS ############################################
#%%
        
@dataclass
class Customer:

    id: int
    lastname: str
    firstname: str
    registration_date: datetime.date
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
        return max([self.registration_date if self.registration_date else datetime.date.fromtimestamp(0)] + [rental.rented_on for rental in self.rentals])

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
    rented_on: datetime.date
    extended_on: datetime.date
    to_return_on: datetime.date
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
        store.customers = {row[0]: Customer(*row[:12]) for row in sheet.Kunden.array if isinstance(row[0], int)
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
    
    def send_reminder(self, rental):
        """doesnt actually send, just opens the mail program with the template"""
        customer = self.customers.get(rental.customer_id, f'Name for {rental.customer_id} not found')
        body = get_reminder_template(customer, rental)
        subject = f'[leih.lokal] Erinnerung an Rückgabe von {rental.item_name}'
        recipient = customer.email
        if not recipient: 
            print(f'{customer.firstname} {customer.lastname}({customer.id}, rented {rental.item_id}:{rental.item_name}) has no email. Please call manually')
            return
        webbrowser.open('mailto:?to=' + recipient + '&subject=' + subject + '&body=' + body, new=1)
        return 

    def get_recently_sent_reminders(self):
        sent = mailbox.mbox(mboxfile)
        
        if len(sent)==0:
            raise FileNotFoundError('mailbox not found at {mboxfile}. Please add in file under SETTINGS')
        
        customers_reminded = []
        for message in sent:
            to = message.get('To')
            if '<' in to:
                to = to.split('<')[-1][:-1]
            to=to.strip()
            subject = message.get('Subject')
            subject = decode_header(subject)[0][0]
            
            if not isinstance(subject, str): subject = subject.decode()
            
            if '[leih.lokal] Erinnerung' in subject:
                filter = lambda c: c.email==to
                customer = self.filter_customers(filter)
                customers_reminded.append(customer[0])
                if len(customer)>1: 
                    print(f'Warning, several customers with same email were found: {to}:{[str(c)for c in customer]}')
        return customers_reminded

    def filter_customers(self, predicate: Callable[[Customer], bool]) -> 'Store':
        customers = [customer for customer in self.customers.values() if predicate(customer)]
        return customers
    
    def filter_rentals(self, predicate: Callable[[Customer], bool]) -> 'Store':
        rentals = [rental for rental in self.rentals if predicate(rental)]
        return rentals
    
    def get_customers_for_deletion(self, min_full_started_days_since_last_contractual_interaction: int = 360) -> 'Store':
        filter = lambda c: (datetime.datetime.now().date() - c.last_contractual_interaction()).days\
            >= min_full_started_days_since_last_contractual_interaction
        return self.filter_rentals(filter)

    def get_overdue_reminders(self):
        filter = lambda r: (r.to_return_on < datetime.datetime.now().date()) and not\
                            isinstance(r.returned_on, datetime.date)
        return self.filter_rentals(filter)

    def __repr__(self) -> str:
        return f"Customers: \n{repr(self.customers)} \n\n\n Rentals: \n {repr(self.rentals)}"

    def empty(self) -> bool:
        return len(self.customers) == 0

    def send_notification_for_customers_on_deletion(self, with_blocking_popup: bool = False) -> bool:
        """
        :return: really sent a notification
        """
        customers = self.get_customers_for_deletion().customers.values()
        if len(customers) > 0:
            notify(CUSTOMER_DELETION_NOTIFICATION_TITLE.format(len(customers)),
                   CUSTOMER_DELETION_NOTIFICATION_TEXT.format(", ".join(customer.short() for customer in customers)),
                   with_blocking_popup=with_blocking_popup)
            return True
        return False
    
    def send_notifications_for_customer_return_rental(self) -> bool:
        rentals_overdue = self.get_overdue_reminders()
        for rental in rentals_overdue[:5]:
            self.send_reminder(rental)
            
        if len(rentals_overdue)>5: 
            printed = '\n'.join([str(rental) for rental in rentals_overdue])
            print(f'There are {len(rentals_overdue)} reminders to be sent. '\
                   'only showing first 5. Rest: \n' + printed)
        return True


def notify(title: str, text: str, timeout: int = 120, with_blocking_popup: bool = False):
    import plyer
    plyer.notification.notify(title=title, message=text, timeout=timeout, app_name='leihladen.py')
    if with_blocking_popup:
        import pymsgbox
        pymsgbox.alert(text, title, button='Zur Kenntnis genommen')


if __name__ == '__main__':
    excel_file = os.path.join(os.path.abspath(os.path.dirname(os.path.dirname(__file__))), "Leihgegenständeliste.ods")
    while True:
        store = Store.parse_file(excel_file)
        try:
            store.send_notifications_for_customer_return_rental()
            store.send_notification_for_customers_on_deletion()
        except Exception as ex:
            print(ex, file=sys.stderr)
        time.sleep(1)
        break
