# -*- coding: utf-8 -*-
"""
Created on Thu Jan 14 18:48:12 2021

send mail to all users that have registered that day before.

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

def get_reminder_template(customer):
    today = datetime.now(pytz.timezone('Europe/Berlin'))
    s = f"""\
Liebe/r {customer.firstname} {customer.lastname},

herzlich willkommen im leih.lokal!

Deine Mitgliedsnummer ist: {customer.id}.

Hier ein paar wichtige Infos:

Zur Ausleihe:
- du erhältst einen Tag vor Rückgabe eine Erinnerungsmail.
- du kannst die Ausleihe ggf. per Mail oder telefonisch verlängern.
- solltest du deine Nutzernummer nicht parat haben, können wir dich auch über deinen Namen identifizieren.
- wenn etwas mit dem geliehenen Gegenstand nicht funktioniert oder er kaputt geht, melde dich umgehend bei uns per Mail oder Telefon.
- wenn du zwei Jahre nichts leihst, werden deine Daten bei uns automatisch gelöscht.

Über das leih.lokal:
- bei uns kannst du kostenlos Gegenstände leihen.
- wir sind ein ehrenamtliches Projekt und freuen uns über deine Mithilfe.
- wir suchen immer nach helfenden Händen; melde dich gerne bei uns (z.B. für Ladenschichten, Reparaturen von Gegenständen, Design von Flyern und Website, etc.).
- auch mit einer (kleinen) Spende hilfst du uns, denn wir arbeiten komplett spendenfinanziert.

Ansonsten wünschen wir dir jetzt viel Erfolg/Freude mit unseren Gegenständen!

Liebe Grüße
das leih.lokal-Team

www.leihlokal-ka.de

Gerwigstr. 41, 76131 Karlsruhe
Öffnungszeiten: Mo, Do, Fr: 15-19, Sa: 10-14
Telefon: 0721/ 4700 4551
Email: info@leihlokal-ka.de

//
Diese Email wurde automatisch generiert. Sie kann daher Fehler enthalten. \
Wir bitten dies zu entschuldigen.
//
Today: {today}
"""
    return s

def valid_email(email):
  if not isinstance(email, str): return False
  return bool(re.search(r"^.+@(\[?)[a-zA-Z0-9-.]+.([a-zA-Z]{2,3}|[0-9]{1,3})(]?)$", email))


if __name__ == '__main__':

    leihlokal = LeihLokal()
    mail_client = MailClient()

    # not sure how well this plays for the github timezone?
    today = datetime.now(pytz.timezone('Europe/Berlin')).date()

    new_customers = leihlokal.filter_customers(lambda x: x.registration_date==today)
    logging.error(f"{len(new_customers)} new customers: {new_customers}")

    # now for new customer, create and send the corresponding email
    # collect all errors, we will send them separately later in the script
    errors = []
    mail_to=''
    for customer  in new_customers:
        if not valid_email(customer.email):
            errors.append(f'{customer.email} of {customer} is not a valid email adress')
            continue
        try:
            email_msg = get_reminder_template(customer)
            subject = "[leih.lokal] Willkommen beim leih.lokal!"
            mail_to = formataddr((f"{customer.firstname} {customer.lastname}",
                                  customer.email))
            mail_client.send(mail_to, subject, email_msg)
        except Exception as e:
            logging.error(f"Cannot send mail to {customer}: {e}")
            errors.append(f"Cannot send mail to {customer}: {e}")

         # wait 8 seconds before next mail to not trigger any spam protection
        time.sleep(8)
        if 'yahoo' in mail_to:
            time.sleep(30) # another 30 seconds in case of yahoo, they're picky

    # if there were error messages, we'll send them via mail to ourselves
    if len(errors)>0:
        errors_str = '\n\n'.join(errors)
        subject =  "[leih.lokal] Fehler beim Ausführen der Rückgabe-Erinnerungen"
        error_msg = f"Die folgenden Fehler traten beim ausführen der Erinnerungen auf: \n\n\n{errors_str}"
        mail_client.send(mail_client.mail_from, subject, error_msg)
