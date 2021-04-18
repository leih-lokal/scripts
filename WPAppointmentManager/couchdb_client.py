import os
from cloudant.client import CouchDB


class CouchDbClient:

    def __init__(self):
        client = CouchDB(os.environ['COUCHDB_USER'], os.environ['COUCHDB_PASSWORD'],
                         url=os.environ['COUCHDB_HOST'],
                         connect=True, auto_renew=True)
        self.db = client["leihlokal"]

    def get_status_of_items(self, item_ids):
        result = self.db.get_query_result({"$and": [{'type': {'$eq': "item"}}, {'id': {'$in': item_ids}}]},
                                        fields=["id", "status"], raw_result=True)
        return result["docs"]
