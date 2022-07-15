# -*- coding: utf-8 -*-
"""
Created on Thu Jan 14 18:48:12 2021

@author: Simon Kern
"""

import sys; sys.path.append('.');sys.path.append('..')
import re
import pytz
import logging
import time
from datetime import datetime, timedelta
from leihlokal import LeihLokal
from mail_client import MailClient
from collections import defaultdict
from email.utils import formataddr

logging.basicConfig(level=logging.DEBUG)
logging.getLogger().setLevel(logging.DEBUG)


def get_reminder_template(customer, rentals):
    newline = '\t\n'
    today = datetime.now(pytz.timezone('Europe/Berlin')).date()
    several = len(rentals)>1
    items = [rental.item for rental in rentals]
    items_str = ", ".join([f"{item.name} (#{item.id})" for item in items])
    s = f"""\
Liebe/r {customer.firstname} {customer.lastname},

Morgen wird die Rückgabe {'der' if several else 'des'} \
{'Gegenstände' if several else 'Gegenstands'}: "{items_str}" fällig. \
Wir bitten Sie, {'die Gegenstände' if several else 'den Gegenstand'} morgen zu \
den Öffnungszeiten zurück zu bringen.

Sollte die maximale Leihdauer von drei Wochen noch nicht erreicht sein, \
ist es ggf. möglich, die Ausleihe auf Nachfrage zu verlängern. Bitte fragen Sie
hierzu während der Öffnungszeiten telefonisch oder jederzeit per Mail nach. \
Bitte haben Sie Verständnis, dass, je nach Nachfrage des Gegenstandes, eine \
Verlängerung nicht immer möglich ist.

Sollten wir morgen nicht geöffnet haben, geben Sie \
{'die Gegenstände' if several else 'den Gegenstand'} einfach am \
nächsten Öffnungstag ab. Weitere Informationen \
finden Sie auf unserer Webseite.

Liebe Grüße, 
das leih.lokal-Team

Gerwigstr. 41, 76131 Karlsruhe
Öffnungszeiten: Mo, Do: 15-19, Sa: 10-14
Telefon: 0721/ 4700 4551

//
Das leih.lokal ist eine ehrenamtliches Projekt von der Bürgerstiftung Karlsruhe.
Wir arbeiten komplett spendenfinanziert und freuen uns daher über Ihre Spende.
Mach doch auch mit und hilf uns die Welt ein bisschen nachhaltiger zu gestalten!

Lust mitzumachen? Wir sind immer auf Menschen die Lust haben in unserem bunten \
Team mitzuwirken.
// 
Diese Email wurde automatisch generiert. Sie kann daher Fehler enthalten. \
Wir bitten dies zu entschuldigen.
//
Today: {today}
Rentals due: 
{newline.join([str(r) for r in rentals])}
"""
    return s

def valid_email(email):
  if not isinstance(email, str): return False
  return bool(re.search(r"^.+@(\[?)[a-zA-Z0-9-.]+.([a-zA-Z]{2,3}|[0-9]{1,3})(]?)$", email))


if __name__ == '__main__':

    leihlokal = LeihLokal()
    mail_client = MailClient()

    # not sure how well this plays for the github timezone?
    tomorrow = datetime.now(pytz.timezone('Europe/Berlin')).date() + timedelta(days=1)
    rentals_due_tomorrow = leihlokal.filter_rentals(lambda x: x.to_return_on==tomorrow and (not hasattr(x, 'returned_on') or not x.returned_on))

    # first concatenate all due items that belong to the same user
    reminders = defaultdict(list)
    for rental in rentals_due_tomorrow:
        customer_id = rental.customer_id
        reminders[rental.customer].append(rental)

    # now for each reminder, create and send the corresponding email
    # collect all errors, we will send them separately later in the script
    errors = []
    mail_to=''
    for customer, rentals in reminders.items():
        if customer is None:
            errors.append(f'{customer} is Null for {rentals}')
            continue
        if not valid_email(customer.email):
            errors.append(f'{customer.email} of {customer} is not a valid email adress')
            continue
        try:
            names = ', '.join([str(rental.item.name) for rental in rentals])
            email_msg = get_reminder_template(customer, rentals)
            subject = f"[leih.lokal] Rückgabe morgen fällig ({names})"
            mail_to = formataddr((f"{customer.firstname} {customer.lastname}", customer.email))
            mail_client.send(mail_to, subject, email_msg)
        except Exception as e:
            logging.info(f"Cannot send mail to {customer} for items {rentals}: {e}")
            errors.append(f"Cannot send mail to {customer} for items {rentals}: {e}")

         # wait 8 seconds before next mail to not trigger any spam protection
        time.sleep(8)
        if 'yahoo' in mail_to:
            time.sleep(30) # another 30 seconds in case of yahoo, they're picky

    # if there were error messages, we'll send them via mail
    if len(errors)>0:
        errors_str = '\n\n'.join(errors)
        subject =  "[leih.lokal] Fehler beim Ausführen der Rückgabe-Erinnerungen"
        error_msg = f"Die folgenden Fehler traten beim ausführen der Erinnerungen auf: \n\n\n{errors_str}"
        mail_client.send(mail_client.mail_from, subject, error_msg)
