import logging
import pprint
from datetime import datetime, timedelta, time
import pytz

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
        return f"Could not find items in db: {item_ids_not_found_in_db}"
    if any([status["status"] != "instock" for status in item_status]):
        logging.debug(", ".join([f'{idx}: {status}' for idx, status in zip(item_ids, item_status)]))
        return ", ".join([f'{status}' for idx, status in zip(item_ids, item_status)])
    return True


def update_item_status(item_doc, status_couchdb, status_wc):
    item_doc["status"] = status_couchdb
    item_doc["last_update"] = int(datetime.now().timestamp() * 1000)
    item_doc.save()
    logging.debug(f"Set status of item {item_doc['id']} to {status_couchdb}")
    wc_client.update_item_status(item_doc["wc_id"], status_wc)
    logging.debug(f"Set status item {item_doc['id']} to {status_wc} on WooCommerce")


def reserve_items(items):
    for item_doc in couchdb_client.get_items(items):
        item_doc = couchdb_client.as_document(item_doc)
        if not item_doc["exists_more_than_once"]:
            update_item_status(item_doc, "reserved", "outofstock")
        else:
            logging.debug(f"Did not reserve item {item_doc['id']} because it exists more than once")


def appointment_to_string(appointment):
    return f"appointment at {appointment['time_start'].strftime('%d.%m %H:%M')} with id {appointment['appointment_id']}"


def should_auto_accept(appointment):
    # other appointment does not exist anymore
    # if appointment["other_appointment"]:
    #     return False, f"Did not auto accept {appointment_to_string(appointment)} because customer has other appointment"

    if appointment["return"]:
        return True, f"Auto accepted {appointment_to_string(appointment)} because customer returns items"

    if len(appointment["items"]) == 0:
        return False, f"Did not auto accept {appointment_to_string(appointment)} because no item ids could be found"

    allinstock = all_items_instock(appointment["items"])
    if allinstock==True:
        return True, f"Auto accepted {appointment_to_string(appointment)} because all items ({appointment['items']}) are instock"
    else:
        return False, f"Did not auto accept {appointment_to_string(appointment)} because not all items ({appointment['items']}) are instock: {allinstock}"


appointments = wp_client.get_appointments(datetime.today(), datetime.today() + timedelta(days=14))
# new appointments which are not genehmigt / cancelled / attended yet
pending_appointments = list(filter(lambda appointment: appointment["status"] == "Pending", appointments))

if len(pending_appointments) == 0:
    logging.info("No pending appointments")

mail_client = MailClient()

# auto accept appointments
for appointment in pending_appointments:
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

# reset status to instock for items that have been reserverd but not rented
# run this only if it is after 20:00 in the evening. The cron job
# is set to run somehwere after that, so that should clear the things of the day.
if datetime.now(pytz.timezone('Europe/Berlin')).time() > time(19, 0, tzinfo=pytz.timezone('Europe/Berlin')):
    logging.info('Clearing appointments of today')
    appointments_of_today = list(
        filter(lambda appointment: appointment["time_end"].date() == datetime.today().date(), appointments))
    appointments_after_today = list(
        filter(lambda appointment: appointment["time_end"].date() != datetime.today().date(), appointments))

    # items that should have been rented today
    item_ids_reserved_for_today = []
    for appointment in appointments_of_today:
        item_ids_reserved_for_today += appointment["items"]

    # items that are scheduled to be rented after today
    item_ids_reserved_for_after_today = []
    for appointment in appointments_after_today:
        item_ids_reserved_for_after_today += appointment["items"]

    items_reserved_for_today = couchdb_client.get_items(item_ids_reserved_for_today, ["id", "wc_id", "status"])
    items_still_reserved = list(
        filter(lambda item: item["status"] == "reserved" and item["id"] not in item_ids_reserved_for_after_today,
               items_reserved_for_today))
    items_still_reserved = list(map(lambda item: item["id"], items_still_reserved))
    reset_item_status_count = 0
    for item_doc in couchdb_client.get_items(items_still_reserved):
        logging.info(f'Reset status of {item_doc}')
        item_doc = couchdb_client.as_document(item_doc)
        update_item_status(item_doc, "instock", "instock")
        reset_item_status_count += 1

    if reset_item_status_count > 1:
        logging.info(f"Set status to 'instock' for {reset_item_status_count} reserved items")
