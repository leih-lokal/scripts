# -*- coding: utf-8 -*-
"""
Created on Thu Jan 14 18:48:12 2021

@author: Simon
"""
import traceback
import logging as log
from datetime import datetime, date
from cloudant.client import CouchDB


class Object:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            if key.startswith('_'): continue # skip hidden keys
            self.__dict__[key] = self._guess_type(key, value)

    def _guess_type(self, key, value):
        if isinstance(value, (int, float)):
            # maybe its a date in milliseconds?
            value = abs(value)
            if value>1500000000000 and value<2000000000000:
                log.info(f'{key} is millsecond-timestamp: {value}')
                return datetime.fromtimestamp(value/1000).date()

            # maybe its a date in seconds?
            elif value>1500000000 and value<2000000000:
                log.info(f'{key} is second-timestamp: {value}')
                return datetime.fromtimestamp(value).date()

        # else just leave the value in the format as it is
        return value


class Customer(Object):
    def __init__(self, **kwargs):
        super(Customer, self).__init__(**kwargs)
        self.rentals = []

    def __repr__(self):
        try:
            return f'Customer {self.id} ({self.firstname} {self.lastname}, {self.email}, {self.telephone_number})'
        except Exception as e:
            print(repr(e), str(e))

    def last_interaction(self):
        registration = self.registration_date if self.registration_date else date.fromtimestamp(0)
        try:
            renewed = self.renewed_on if self.renewed_on else registration
            rented = [rental.rented_on for rental in self.rentals]
            returned = [rental.returned_on for rental in self.rentals if rental.returned_on]
            all_dates = rented + returned + [registration, renewed]
            all_dates = [d for d in all_dates if isinstance(d, date)]
            last = max(all_dates)
        except Exception as e:
            traceback.print_exc()
            print(self, e)
            return registration
        return last


class Item(Object):
    def __init__(self, **kwargs):
        super(Item, self).__init__(**kwargs)

    def __repr__(self):
        try:
            return f'Item {self.id} ({self.item_name}, {self.deposit}€, {self.status_on_website})'
        except Exception as e:
            print(repr(e), str(e))


class Rental(Object):
    def __init__(self, **kwargs):
        super(Rental, self).__init__(**kwargs)

    def __repr__(self):
        try:
            return f'Rental (User {self.customer_id} -> Item {self.item_id}: {self.rented_on} -> {self.to_return_on})'
        except Exception as e:
            print(repr(e), str(e))

class LeihLokal(object):
    def __init__(self, user='user', password='password', url='http://localhost:5984'):
        user='user'
        password='password'
        url='http://localhost:5984'
        print(f'connecting to {url}')
        couchdb = CouchDB(user, password, url=url, connect=True, auto_renew=True)

        rentals = []
        items = {}
        customers = {}

        # get the three tables
        rentals_db = couchdb['rentals']
        items_db = couchdb['items']
        customers_db = couchdb['customers']


        # iterate over all customers and add them
        print('retrieving customers')
        for row in customers_db.all_docs(include_docs=True)['rows']:
            if row['key'].startswith('_'): continue # hidden reference
            attrs = dict(row['doc'])
            attrs['id'] = attrs['_id']
            customer = Customer(**attrs)
            customers[attrs['id'] ] = customer

        # iterate over all items and add them
        print('retrieving items')

        for row in items_db.all_docs(include_docs=True)['rows']:
            if row['key'].startswith('_'): continue # hidden reference
            attrs = dict(row['doc'])
            attrs['id'] = attrs['_id']
            item = Item(**attrs)
            item.status = 'verfügbar' # preliminarily set status to available, check later
            items[attrs['id']] = item

        # iterate over all rentals and add them
        print('retrieving rentals')
        for row in rentals_db.all_docs(include_docs=True)['rows']:
            if row['key'].startswith('_'): continue # hidden reference
            attrs = dict(row['doc'])
            attrs['id'] = attrs['_id']
            rental = Rental(**attrs)
            rental.item = items.get(rental.item_id, f"Item {rental.item_id} not found")
            customer = customers.get(rental.customer_id, None)
            rental.customer = customer
            if customer:  customer.rentals.append(rental)
            rentals.append(rental)
        rentals = sorted(rentals, key=lambda x:x.rented_on if isinstance(x.rented_on, date) else date.fromtimestamp(0))

        self.rentals = rentals
        self.items = items
        self.customers = customers

        # now set correct status according to active rentals
        curr_rentals = self.filter_rentals(lambda x:not x.returned_on )
        for rental in curr_rentals:
            rental.item.status = 'verliehen'

    def filter_items(self, predicate):
        filtered = []
        for item in self.items.values():
            try: 
                filter = predicate(item)
                if filter:
                    filtered.append(item)
            except Exception as e:
                traceback.print_exc()
                print(f'Error filtering customer {item}: {e}')
        return filtered

    def filter_customers(self, predicate):
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
    
    def filter_rentals(self, predicate):
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



if __name__=='__main__':
    store = LeihLokal()
    store.check_website_status()

