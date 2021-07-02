# -*- coding: utf-8 -*-
"""
Created on Thu Jan 14 18:48:12 2021

@author: Simon Kern
"""

import sys; sys.path.append('.');sys.path.append('..')
import re
import logging
import time
from datetime import datetime
from leihlokal import LeihLokal
from mail_client import MailClient
from collections import defaultdict

logging.basicConfig(level=logging.DEBUG)
logging.getLogger().setLevel(logging.DEBUG)


def get_reminder_template(customer, rentals):
    several = len(rentals)>1
    items = [rental.item for rental in rentals]
    items_str = ", ".join([f"{item.name} (#{item.id})" for item in items])
    s = f"""\
Liebe/r {customer.firstname} {customer.lastname},

wir hoffen, Sie hatten viel Freude an {'den' if several else 'dem'} bei uns geliehenen \
{'Gegenständen' if several else 'Gegenstand'}!

Heute wird die Rückgabe {'der' if several else 'des'} \
{'Gegenstände' if several else 'Gegenstands'}: "{items_str}" fällig. \
Wir bitten Sie, {'die Gegenstände' if several else 'den Gegenstand'} heute zu \
den Öffnungszeiten zurück zu bringen.

Falls die maximale Leihdauer von drei Wochen noch nicht erreicht ist, \
können Sie ggf. die Ausleihe noch einmal verlängern. Sollten Sie den Gegenstand jedoch \
nicht mehr benötigen, freuen sich die nachfolgenden AusleiherInnen über eine zeitige Rückgabe.

Sollte es sich heute um keinen Öffnungstag handeln, geben Sie {'die Gegenstände' if several else 'den Gegenstand'}\
einfach am darauffolgenden Öffnungstag ab. Weitere Informationen finden Sie unter bitly.com/leihlokal

Da wir uns komplett über Spenden finanzieren, freuen wir uns über jede Art der Unterstützung!

Liebe Grüße, 
das leih.lokal-Team

Gerwigstr. 41, 76185 Karlsruhe
Öffnungszeiten: Mo, Do: 15-19, Sa: 11-16
http://www.buergerstiftung-karlsruhe.de/leihlokal/

// Diese Email wurde automatisch generiert. Sie kann daher Fehler enthalten. \
Wir bitten dies zu entschuldigen.

"""
    return s

def valid_email(email):
  if not isinstance(email, str): return False
  return bool(re.search(r"^[\w\.\+\-]+\@[\w]+\.[a-z]{2,3}$", email))


if __name__ == '__main__':

    leihlokal = LeihLokal()
    mail_client = MailClient()

    # not sure how well this plays for the github timezone?
    today = datetime.now().date()
    rentals_due_today = leihlokal.filter_rentals(lambda x: x.to_return_on==today)

    # first concatenate all due items that belong to the same user
    reminders = defaultdict(list)
    for rental in rentals_due_today:
        customer_id = rental.customer_id
        reminders[rental.customer].append(rental)

    # now for each reminder, create and send the corresponding email
    # collect all errors, we will send them separately later in the script
    errors = []
    for customer, rentals in reminders.items():
        if not valid_email(customer.email):
            errors.append(f'{customer.email} of {customer} is not a valid email adress')
            continue
        try:
            ids = ', '.join([str(rental.item_id) for rental in rentals])
            email_msg = get_reminder_template(customer, rentals)
            subject = f"[leih.lokal] Rückgabe von {ids} heute fällig"
            mail_client.send(customer.email + "x$", subject, email_msg)
        except Exception as e:
            errors.append(f"Cannot send mail to {customer} for items {rentals}: {e}")

         # wait 5 seconds before next mail to not trigger any spam protection
        time.sleep(5)

    # if there were error messages, we'll send them via mail
    if len(errors)>0:
        errors_str = '\n\n'.join(errors)
        subject =  "[leih.lokal] Fehler beim Ausführen der Rückgabe-Erinnerungen"
        error_msg = f"Die folgenden Fehler traten beim ausführen der Erinnerungen auf: \n\n\n{errors_str}"
        mail_client.send(mail_client.leihlokal_mail, subject, error_msg)