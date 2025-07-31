#!/bin/env/python

# setup: pip install lxml httpx
#
# usage: xoyondo_updater.py [-h] [--purge] [-p [PARTICIPANTS ...]] [-d FUTURE_DAYS] admin_url
#
# leih.lokal Xoyondo Updater
#
# positional arguments:
#   admin_url             The Xoyondo admin URL
#
# options:
#   -h, --help                              Show this help message and exit
#   --purge                                 Delete all entries
#   -p, --participants [PARTICIPANTS ...]   List of default participants
#   -d, --future-days FUTURE_DAYS           Number of future days to add

import httpx
from lxml import html
from datetime import date, timedelta
import sys
import logging
import calendar
from urllib.parse import urlparse
import json
import argparse

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger('main')
logger.setLevel(level=logging.INFO)

# Config: leih.lokal opening hours / shifts
SCHEDULE = {
    calendar.MONDAY:    [('15:00', '17:00'), ('17:00', '19:00')],
    calendar.THURSDAY:  [('15:00', '17:00'), ('17:00', '19:00')],
    calendar.FRIDAY:    [('15:00', '17:00'), ('17:00', '19:00')],
    calendar.SATURDAY:  [('10:00', '12:00'), ('12:00', '14:00')],
}

class XoyondoPoll:
    def __init__(self, admin_url: str):
        parsed_url = urlparse(admin_url)
        path_parts = [part for part in parsed_url.path.split('/') if part]
        
        if len(path_parts) < 3:
            raise ValueError('Invalid admin URL. It must contain the poll ID and admin password.')

        self.base_url = f'{parsed_url.scheme}://{parsed_url.netloc}'
        self.poll_id = path_parts[1]
        self.admin_pass = path_parts[2]
        self.admin_url = admin_url
        self.post_url = f'{self.base_url}/pc/poll-change-poll'
        
        self.client = httpx.Client(
            timeout=10.0,
            follow_redirects=True,
            headers={
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:140.0) Gecko/20100101 Firefox/140.0',
                'Connection': 'keep-alive'
            },
            cookies={'lang': 'en-us'},
        )
        
    @property
    def user_pass(self) -> str:
        return self.client.cookies.get('ident' + self.poll_id)

    def fetch_dates(self) -> list[dict]:
        response = self.client.get(self.admin_url)
        response.raise_for_status()
        
        tree = html.fromstring(response.text)
        
        date_elements = tree.xpath("//div[@id='signup-table-container']//div[contains(@class, 'd-flex') and contains(@class, 'flex-row')]")
        
        extracted_dates = []
        for element in date_elements:
            date_text_list = element.xpath("./div[2]/text()")
            delete_icon_id_list = element.xpath(".//a[@class='dropdown-item js-slot-delete']/@data-key")

            if date_text_list and delete_icon_id_list:
                date_id = delete_icon_id_list[0].split('-')[-1]
                date_str = date_text_list[0].split(' ')[0]
                
                participant_elements = element.xpath("../..//span[@class='js-view-compact']/div[contains(@class, 'participant-box')]")
                participants = [p.text.strip() for p in participant_elements if p.text]
                
                su_checkbox_key = element.xpath("../..//input[@name = 'su_checkbox']/@data-key")[0]

                try:
                    month, day, year = map(int, date_str.split('/'))
                    date_obj = date(year, month, day)
                    extracted_dates.append({'date_id': date_id, 'date': date_obj, 'participants': participants, 'key': su_checkbox_key})
                except (ValueError, IndexError):
                    continue
        
        return extracted_dates

    def add_date(self, new_date: date, times: list[tuple[str]], after: str = '-1') -> bool:
        date_str = new_date.strftime('%Y/%m/%d')
        
        time_objects = []
        for t_from, t_to in times:
            time_objects.append({'timeStart': t_from, 'timeEnd': t_to})

        payload = {
            'ID': self.poll_id,
            'product': 's',
            'operation': 'signup-slots-add',
            'outerinner': 'outer',
            'type': 'date',
            'dates': date_str,
            'times': json.dumps(time_objects),
            'insertAfter': after,
            'pass': self.admin_pass,
        }
        
        try:
            response = self.client.post(self.post_url, data=payload)
            response.raise_for_status()
            return True
        except httpx.RequestError as e:
            logger.error(f'An error occurred while adding date: {e}')
            return False

    def delete_date(self, date_id: str) -> bool:
        payload = {
            'ID': self.poll_id,
            'product': 's',
            'slotID': date_id,
            'outerinner': 'outer',
            'operation': 'signup-slot-delete',
            'pass': self.admin_pass
        }

        try:
            response = self.client.post(self.post_url, data=payload)
            response.raise_for_status()
            return True
        except httpx.RequestError as e:
            logger.error(f'An error occurred while deleting date: {e}')
            return False

    def add_participant(self, name: str, keys: list[str], all_keys: list[str]) -> bool:
        payload = {
            'ID': self.poll_id,
            'pass': self.admin_pass,
            'name': name,
            'user_edit': '',
            'registeredUserId': '-1',
            'window_position': '0',
            'additional_info': '',
            'arePremiumFeaturesActive': '',
            'showAds': '1',
            'yourmailh': '',
            'last_name': '',
            'su_checkbox': ['on'] * len(keys),
            'pass': self.admin_pass,
            'upass': self.user_pass,
        }

        for key in all_keys:
            payload[f'votes[{key}]'] = '1' if key in keys else '0'

        try:
            response = self.client.post(f'{self.base_url}/pc/signup-vote-redirect', data=payload)
            response.raise_for_status()
            return True
        except httpx.RequestError as e:
            logger.error(f'An error occurred while adding participant: {e}')
            return False

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='leih.lokal Xoyondo Updater')
    parser.add_argument('admin_url', type=str, help='The Xoyondo admin URL')
    parser.add_argument('--purge', action='store_true', help='Delete all entries')
    parser.add_argument('-p', '--participants', type=str, nargs='*', default=[], help='List of default participants')
    parser.add_argument('-d', '--future-days', type=int, default=30, help='Number of future days to add')

    args = parser.parse_args()

    admin_url: str = args.admin_url
    delete_all: bool = args.purge
    default_participants: list[str] = args.participants
    future_days: int = args.future_days

    print('leih.lokal Xoyondo Updater')
    print('='*40)

    try:
        poll = XoyondoPoll(admin_url)
        
        # Purge mode
        # ---

        if delete_all:
            logger.info('Deleting all entries...')
            existing_date_ids = poll.fetch_dates()
            
            if not existing_date_ids:
                logger.info('No entries to delete.')
            else:
                for item in existing_date_ids:
                    if poll.delete_date(item['date_id']):
                        logger.info(f"Deleted {item['date']}.")
                    else:
                        logger.error(f"Failed to delete {item['date']}.")
                        
            logger.info('All entries have been deleted.')
            sys.exit(0)
        
        # Normal mode
        # ---
        
        today = date.today()

        # Delete past dates
        logger.info('Deleting past dates ...')
        existing_date_ids = poll.fetch_dates()
        for item in existing_date_ids:
            if item['date'] < today:
                if poll.delete_date(item['date_id']):
                    logger.info(f"Deleted {item['date']}.")
                else:
                    logger.error(f"Failed to delete {item['date']}.")

        # Add new dates
        logger.info(f'Adding new dates within next {future_days} days ...')
        existing_dates = poll.fetch_dates()
        existing_date_ids = {d['date'] for d in existing_dates}
        last_date_id = sorted(existing_dates, key=lambda d: d['date'])[-1]['date_id'] if len(existing_dates) else '-1'

        for i in reversed(range(future_days)):
            target_date = today + timedelta(days=i)
            weekday = target_date.weekday()

            if weekday in SCHEDULE and target_date not in existing_date_ids:
                times = SCHEDULE[weekday]
                if poll.add_date(target_date, times, after=last_date_id):
                    logger.info(f"Added {target_date}.")
                else:
                    logger.error(f"Failed to add {target_date}.")
                    
        # Add default participants
        if len(default_participants):
            logger.info(f'Adding default participants ({default_participants}) to all dates ...')
            existing_date_ids = poll.fetch_dates()
            for name in default_participants:
                all_date_keys = [d['key'] for d in existing_date_ids]
                filtered_date_keys = [d['key'] for d in existing_date_ids if name not in d['participants']]
                poll.add_participant(name, filtered_date_keys, all_date_keys)
                
    except (ValueError, httpx.RequestError) as e:
        logger.critical(f'A critical error occurred: {e}')