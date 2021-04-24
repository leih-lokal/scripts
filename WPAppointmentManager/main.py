import logging
import pprint
from datetime import datetime, timedelta
from couchdb_client import CouchDbClient
from wc_client import WooCommerceClient
from wp_client import WordpressClient
from mail_client import MailClient

logging.basicConfig(level=logging.DEBUG)
logging.getLogger().setLevel(logging.DEBUG)
couchdb_client = CouchDbClient()
wc_client = WooCommerceClient()
wp_client = WordpressClient()


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
        if not item_doc["exists_more_than_once"]:
            item_doc["status"] = "reserved"
            item_doc.save()
            logging.debug(f"Reserved item {item_doc['id']}")
            wc_client.update_item_status(item_doc["wc_id"], "outofstock")
            logging.debug(f"Updated item {item_doc['id']} on WooCommerce")
        else:
            logging.debug(f"Did not reserve item {item_doc['id']} because it exists more than once")


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


appointments = wp_client.get_appointments(datetime.today(), datetime.today() + timedelta(days=14))
# new appointments which are not genehmigt / cancelled / attended yet
appointments = list(filter(lambda appointment: appointment["status"] == "Pending", appointments))

if len(appointments) == 0:
    logging.info("No pending appointments")

mail_client = MailClient()

for appointment in appointments:
    accepting_appointment, reason = should_auto_accept(appointment)
    if accepting_appointment:
        wp_client.accept_appointment(appointment["appointment_id"])
        if not appointment["return"] and len(appointment["items"]) > 0:
            reserve_items(appointment["items"])
            logging.info(f"Reserved items {appointment['items']} for {appointment_to_string(appointment)}")
    else:
        wp_client.checked_appointment(appointment["appointment_id"])
        subject = f"[!] Ansehen: {appointment['customer_name']} @ {appointment['time_start']}"
        message = "Der folgende Termin konnte nicht automatisch angenommen werden. Bitte manuell im WordPress ansehen.\n"
        message += f"Grund: {reason}\n\n\n{pprint.pformat(appointment)}"
        mail_client.send(subject, message)
    logging.info(reason)
