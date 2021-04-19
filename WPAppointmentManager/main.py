import logging
from datetime import datetime, timedelta

from couchdb_client import CouchDbClient
from wp_client import WordpressClient

logging.basicConfig(level=logging.INFO)
couchdb_client = CouchDbClient()

def all_items_instock(item_ids):
    item_status = couchdb_client.get_status_of_items(item_ids)
    item_ids_found_in_db = list(map(lambda status: status["id"], item_status))
    item_ids_not_found_in_db = list(set(item_ids) - set(item_ids_found_in_db))
    if len(item_ids_not_found_in_db) > 0:
        logging.info(f"Could not find items in db: {item_ids_not_found_in_db}")
        return False
    for status in item_status:
        if status["status"] != "instock":
            logging.info(f"item {status['id']} is {status['status']}")
            return False
    return True

def reserve_items(items):
    # TODO
    pass

def should_auto_accept(appointment):
    if appointment["other_appointment"]:
        logging.info(f"Did not auto accept appointment {str(appointment)} because customer has other appointment")
        return False

    if appointment["return"]:
        logging.info(f"Auto accepted appointment {str(appointment)} because customer returns items")
        return True

    if len(appointment["items"]) == 0:
        logging.info(f"Did not auto accept appointment {str(appointment)} because no item ids could be found")
        return False

    if all_items_instock(appointment["items"]):
        logging.info(f"Auto accepted appointment {str(appointment)} because all items ({appointment['items']}) are instock")
        return True
    else:
        logging.info(f"Did not auto accept appointment {str(appointment)} because not all items ({appointment['items']}) are instock")
        return False

wp_client = WordpressClient()
appointments = wp_client.get_appointments(datetime.today(), datetime.today() + timedelta(days=7))

# new appointments which are not genehmigt / cancelled / attended yet
appointments = list(filter(lambda appointment: appointment["status"] == "Pending", appointments))

for appointment in appointments:
    if should_auto_accept(appointment):
        reserve_items(appointment["items"])
        wp_client.accept_appointment(appointment["appointment_id"])
        logging.info(f"Accepted items {appointment['items']} for appointment {appointment['appointment_id']}")
        # TODO: insert appointments into db, so that can be displayed in frontend
