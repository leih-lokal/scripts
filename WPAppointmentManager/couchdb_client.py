import os
from cloudant.client import CouchDB
from cloudant.document import Document


class CouchDbClient:

    def __init__(self):
        client = CouchDB(os.environ['COUCHDB_USER'], os.environ['COUCHDB_PASSWORD'],
                         url=os.environ['COUCHDB_HOST'],
                         connect=True, auto_renew=True)
        self.db = client["leihlokal"]

    def get_items(self, item_ids, fields=None):
        return \
        self.db.get_query_result({"$and": [{'type': {'$eq': "item"}}, {'id': {'$in': item_ids}}]}, raw_result=True,
                                 fields=fields)["docs"]

    def get_status_of_items(self, item_ids):
        return self.get_items(item_ids, ["id", "status"])

    def as_document(self, item_dict):
        document = Document(self.db, item_dict["_id"])
        document.update(item_dict)
        return document
