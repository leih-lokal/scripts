from datetime import datetime
import re


def _appointment_to_dict(headers):
    def appointment_to_dict(appointment):
        appointment_dict = {}
        for i, entry in enumerate(appointment):
            appointment_dict[headers[i]] = entry
        return appointment_dict

    return appointment_to_dict


def _clean_data(appointment):
    items = appointment["Artikelnummer(n)"].replace(";", ",")
    items = re.split(',|\s', items)
    items = list(map(lambda item: re.sub('[^0-9]', '', item), items))
    items = list(filter(lambda item: len(item) > 0, items))
    items = list(map(lambda item: int(item), items))

    return {
        "items": items,
        "time_start": datetime.strptime(f"{appointment['app_date_1']} {appointment['app_starttime_1']}",
                                        '%d.%m.%Y %H:%M'),
        "time_end": datetime.strptime(f"{appointment['app_date_1']} {appointment['app_endtime_1']}", '%d.%m.%Y %H:%M'),
        "return": appointment['Ich mchte einen Gegenstand/Gegenstnde..'] == "zurückgeben",
        # "other_appointment": appointment[
        #                          'Haben Sie schon einen weiteren/anderen Termin fr diesen Tag gebucht?'] == "Ja",
        "status": appointment["cancelled"], # Attended / Genehmigt / Zusammengelegt / Cancelled by customer / Rejected / Cancelled / Bitte ansehen
        "customer_name": appointment['Dein Vor- und Zuname'],
        "customer_id": appointment.get('Deine Nutzernummer (falls zur Hand)'),
        "customer_mail": appointment['Deine Email'],
        "appointment_id": appointment['itemnumber']
    }


def parse_appointments(appointments):
    def apply_map_fun(map_fun):
        nonlocal appointments
        appointments = list(map(map_fun, appointments))

    headers = appointments.pop(0)
    apply_map_fun(_appointment_to_dict(headers))
    apply_map_fun(_clean_data)

    return appointments