# -*- coding: utf-8 -*-
"""
Created on Wed Apr 21 20:23:41 2021

@author: Simon
"""
import os
import time
import base64
import logging
import smtplib
import imaplib
from email.utils import formatdate
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr

logging.basicConfig(level=logging.DEBUG)


class MailClient:

    def __init__(self):
        self._authenticate()

    def _authenticate(self):
        user = os.environ.get("MAIL_USER")
        password = os.environ.get("MAIL_PASSWORD")
        server = os.environ.get("MAIL_SERVER")
        logging.debug(f'logging in to SMTP: {server} with mail {user}')
        
        smpt = smtplib.SMTP(server, timeout=15)
        smpt.starttls()
        smpt.login(user, password)

        imap = imaplib.IMAP4_SSL(server, timeout=15)
        imap.login(user, password)
        
        leihlokal_mail = base64.b64decode(b'bGVpaGxva2FsQGJ1ZXJnZXJzdGlmdHVuZy1rYXJsc3J1aGUuZGU=').decode()
        self.imap = imap
        self.smpt = smpt
        self.mail_from = formataddr(('leih.lokal Karlsruhe', leihlokal_mail))

    def send(self, mail_to, subject, message):
        msg = MIMEMultipart()
        msg['From'] = self.mail_from
        msg['To'] = mail_to.strip()
        msg['Subject'] = subject
        msg["Date"] = formatdate(localtime=True)
        print('current date', formatdate(localtime=True))

        # add in the message body
        msg.attach(MIMEText(message, 'plain'))
        
        # add fake unsubscribe link
        if any([x in mail_to.lower() for x in ['yahoo', 'web.de', 'posteo']]):
            msg.add_header('List-Unsubscribe',
                           '<https://buergerstiftung-karlsruhe.de/leihlokal/>')

        # send the message via the server.
        logging.info(f"sending mail to {mail_to}: {msg['Subject']}")
        self.smpt.sendmail(msg['From'], mail_to, msg.as_string())

        self.imap.append('INBOX.Archives', '\\Seen', 
                         imaplib.Time2Internaldate(time.time()), 
                         msg.as_string().encode('utf8'))
