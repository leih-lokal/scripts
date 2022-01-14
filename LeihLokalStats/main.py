import sys
from collections import Counter
from time import time

from tabulate import tabulate

from couchdb_client import CouchDbClient


def current_millis():
    return round(time() * 1000)


def n_days_ago_millis(n):
    one_day_millis = 1000 * 60 * 60 * 24
    return current_millis() - (n * one_day_millis)


def print_most_rented_items(since_days=sys.maxsize):
    def item_name(rental):
        return rental['item_name']

    couchdb_client = CouchDbClient()
    rentals = couchdb_client.get_rentals(fields=["item_name", "rented_on"], start=n_days_ago_millis(since_days))
    most_common = Counter(list(map(item_name, rentals))).most_common(20)
    print(tabulate(most_common, headers=['Geganstand', 'Anzahl Ausleihen'], tablefmt="grid"))

print("Letzte 30 Tage")
print_most_rented_items(30)
print()
print("Letztes Jahr")
print_most_rented_items(365)
print()
print("Seit 2018")
print_most_rented_items()