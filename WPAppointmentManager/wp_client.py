import os
import requests
import csv

from appointment_parser import parse_appointments


class WordpressClient:

    def __init__(self):
        self.session = requests.Session()
        self._authenticate()

    def _authenticate(self):
        user = os.environ.get("WP_USER")
        password = os.environ.get("WP_PASSWORD")
        LOGIN_URL = "https://www.buergerstiftung-karlsruhe.de/wp-login.php"
        self.session.get(LOGIN_URL)
        headers = {
            "referer": LOGIN_URL
        }
        data = {
            "log": user,
            "pwd": password,
            "wp-submit": "Anmelden",
            "redirect_to": "https://www.buergerstiftung-karlsruhe.de/wp-admin/"
        }
        response = self.session.post(LOGIN_URL, headers=headers, data=data)
        if response.status_code != 200:
            raise RuntimeError("Failed to authenticate: " + response.text)

    def get_appointments(self, from_date, to_date):
        response = self.session.get(
            f"https://www.buergerstiftung-karlsruhe.de/wp-admin/admin.php?page=cp_apphourbooking&cal=2&schedule=1&dfrom={from_date.strftime('%d.%m.%Y')}&dto={to_date.strftime('%d.%m.%Y')}&paid=&status=-1&cal=2&cp_appbooking_csv2=Exportieren+nach+CSV")

        appointments = list(csv.reader(response.content.decode('utf8', "ignore").splitlines(), delimiter=';'))
        return parse_appointments(appointments)
