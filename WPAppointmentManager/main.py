import os
from appointment_parser import parse_appointments
from wp_client import WordpressClient
from datetime import datetime, timedelta

wp_client = WordpressClient()
wp_client.authenticate(os.environ.get("WP_USER"), os.environ.get("WP_PASSWORD"))
appointments = wp_client.get_appointments(datetime.today(), datetime.today() + timedelta(days=7))
appointments = parse_appointments(appointments)
print(appointments)