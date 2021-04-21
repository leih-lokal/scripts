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
            logging.debug(f"item {status['id']} is {status['status']}")
            return False
    return True


def reserve_items(items):
    for item_doc in couchdb_client.get_items(items):
        item_doc = couchdb_client.as_document(item_doc)
        item_doc["status"] = "reserved"
        item_doc.save()
        logging.debug(f"Reserved item {item_doc['id']}")


def appointment_to_string(appointment):
    return f"appointment at {appointment['time_start'].strftime('%d.%m %H:%M')} with id {appointment['appointment_id']}"


def should_auto_accept(appointment):
    if appointment["other_appointment"]:
        return False, f"Did not auto accept {appointment_to_string(appointment)} because customer has other appointment"

    if appointment["return"]:
        return True, f"Auto accepted {appointment_to_string(appointment)} because customer returns items"

    if len(appointment["items"]) == 0:
        return False, f"Did not auto accept {appointment_to_string(appointment)} because no item ids could be found"

    if all_items_instock(appointment["items"]):
        return True, f"Auto accepted {appointment_to_string(appointment)} because all items ({appointment['items']}) are instock"
    else:
        return False, f"Did not auto accept {appointment_to_string(appointment)} because not all items ({appointment['items']}) are instock"


wp_client = WordpressClient()
appointments = wp_client.get_appointments(datetime.today(), datetime.today() + timedelta(days=7))

# new appointments which are not genehmigt / cancelled / attended yet
appointments = list(filter(lambda appointment: appointment["status"] == "Pending", appointments))

if len(appointments) == 0:
    logging.info("No pending appointments")

for appointment in appointments:
    accepting_appointment, reason = should_auto_accept(appointment)
    if accepting_appointment:
        wp_client.accept_appointment(appointment["appointment_id"])
        if len(appointment["items"]) > 0:
            reserve_items(appointment["items"])
            logging.info(f"Reserved items {appointment['items']} for {appointment_to_string(appointment)}")
        # TODO: insert appointments into db, so that can be displayed in frontend

    logging.info(reason)
