# -*- coding: utf-8 -*-
"""
Created on Wed Apr 21 20:23:41 2021

@author: Simon
"""
import os
import base64
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logging.basicConfig(level=logging.INFO)


class MailClient:

    def __init__(self):
        self._authenticate()

    def _authenticate(self):
        user = os.environ.get("MAIL_USER")
        password = os.environ.get("MAIL_PASSWORD")
        server = os.environ.get("MAIL_SERVER")
        logging.debug(f'logging in to SMTP: {server} with mail {user}')
        server = smtplib.SMTP(server, timeout=15)
        server.starttls()
        server.login(user, password)
        self.server = server
        self.leihlokal_mail = base64.b64decode(b'bGVpaGxva2FsQGJ1ZXJnZXJzdGlmdHVuZy1rYXJsc3J1aGUuZGU=').decode()

    def send(self, mail_to, subject, message):
        msg = MIMEMultipart()
        msg['From'] = self.leihlokal_mail
        msg['To'] = mail_to
        msg['Subject'] = subject

        # add in the message body
        msg.attach(MIMEText(message, 'plain'))

        # send the message via the server.
        logging.info(f"sending mail to {mail_to}: {msg['Subject']}")
        self.server.sendmail(msg['From'], mail_to, msg.as_string())
