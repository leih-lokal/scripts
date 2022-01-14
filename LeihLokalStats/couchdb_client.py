import os
import sys

from cloudant.client import CouchDB


class CouchDbClient:

    def __init__(self):
        client = CouchDB(os.environ['COUCHDB_USER'], os.environ['COUCHDB_PASSWORD'],
                         url=os.environ['COUCHDB_HOST'],
                         connect=True, auto_renew=True)
        self.db = client["leihlokal"]

    def get_rentals(self, start=0, end=sys.maxsize, fields=None):
        return self.db.get_query_result(
            {"$and": [{'type': {'$eq': "rental"}}, {"rented_on": {"$gte": start}}, {"rented_on": {"$lt": end}}]},
            raw_result=True, fields=fields, limit=sys.maxsize)["docs"]
