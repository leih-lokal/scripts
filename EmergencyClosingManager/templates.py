#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Jun 16 07:32:37 2023

templates for uploads and emails

@author: simon
"""
from datetime import datetime
import pytz


def get_email_template(customer):
    today = datetime.now(pytz.timezone('Europe/Berlin'))
    s = f"""\
Liebe/r {customer.firstname} {customer.lastname}.

Heute wäre deine Rückgabe eines unserer Gegenstände fällig. \
Leider muss das leih.lokal heute aus unvorhergesehenen Gründen geschlossen bleiben.

Deine Ausleihe kannst du daher einfach am darauffolgenden Öffnungstag zurück bringen, kein Problem! Bitte stelle keine ausgeliehenen Gegenstände bei uns vor der Tür ab, die Rückgabe läuft bei uns nur persönlich.

Wir bitten um Entschuldigung für die Unannehmlichkeit. Bei Fragen wende dich gerne per Mail an uns.

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
