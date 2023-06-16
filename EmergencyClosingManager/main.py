# -*- coding: utf-8 -*-
"""
Created on Thu Jan 14 18:48:12 2021

enacts our Notfallplan if leih.lokal needs to stay closed today.

Only start this script on the day itself.

Does the following things:

    1. Send info mail to all rentals that would be due today

@author: Simon Kern
"""

import sys; sys.path.append('.');sys.path.append('..')
import os
import re
import pytz
import logging
import time
from datetime import datetime, timedelta
from leihlokal import LeihLokal
from mail_client import MailClient
from collections import defaultdict
from email.utils import formataddr
import templates

logging.basicConfig(level=logging.DEBUG)
logging.getLogger().setLevel(logging.DEBUG)


def valid_email(email):
  if not isinstance(email, str): return False
  return bool(re.search(r"^.+@(\[?)[a-zA-Z0-9-.]+.([a-zA-Z]{2,3}|[0-9]{1,3})(]?)$", email))


def send_mails():
    leihlokal = LeihLokal()
    mail_client = MailClient()

    # not sure how well this plays for the github timezone?
    today = datetime.now(pytz.timezone('Europe/Berlin')).date()

    def filterx(r):
        """filters rentals that are either due to today or overdue"""
        if isinstance(r.to_return_on, int):
            return False
        if not isinstance(r.returned_on, int):
            return False
        return r.to_return_on<=today

    due_today = leihlokal.filter_rentals(filterx)
    logging.info(f"{len(due_today)} due rentals: {due_today}")

    customers_to_notify = set([r.customer for r in due_today])

    # now for new customer, create and send the corresponding email
    # collect all errors, we will send them separately later in the script
    errors = []
    mail_to=''
    for customer in customers_to_notify:
        if not valid_email(customer.email):
            errors.append(f'{customer.email} of {customer} is not a valid email adress')
            continue
        try:
            email_msg = templates.get_email_template(customer)
            subject = "[leih.lokal] Heute außerplanmäßig geschlossen!"
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
        subject =  "[leih.lokal] Fehler beim Ausführen des Notfallplans"
        error_msg = f"Die folgenden Fehler traten auf beim Ausführen der Emails an alle Ausleihen die heute fällig wären: \n\n\n{errors_str}"
        mail_client.send(mail_client.mail_from, subject, error_msg)


if __name__ == '__main__':
    send_mails()