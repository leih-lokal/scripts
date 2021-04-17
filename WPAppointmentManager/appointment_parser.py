from datetime import datetime
import re

def _appointments_to_dict(appointments):
    headers = appointments.pop(0)

    def to_dict(appointment):
        appointment_dict = {}
        for i, entry in enumerate(appointment):
            appointment_dict[headers[i]] = entry
        return appointment_dict

    return list(map(to_dict, appointments))

def _clean_data(appointments):

    def clean_data(appointment):
        items = re.split(',|\s', appointment["Artikelnummer(n)"])
        items = list(map(lambda item: re.sub('[^0-9]','', item), items))
        items = list(filter(lambda item: len(item) > 0, items))

        return {
            "items": items,
            "time_start": datetime.strptime(f"{appointment['app_date_1']} {appointment['app_starttime_1']}", '%d.%m.%Y %H:%M'),
            "time_end": datetime.strptime(f"{appointment['app_date_1']} {appointment['app_endtime_1']}", '%d.%m.%Y %H:%M'),
            "return": appointment['Ich mchte einen Gegenstand/Gegenstnde..'] == "zurückgeben",
            "other_appointment": appointment['Haben Sie schon einen weiteren/anderen Termin fr diesen Tag gebucht?'] == "Ja"
        }

    return list(map(clean_data, appointments))

def parse_appointments(appointments):
    appointments = _appointments_to_dict(appointments)
    appointments_cleaned = _clean_data(appointments)

    return appointments_cleaned
