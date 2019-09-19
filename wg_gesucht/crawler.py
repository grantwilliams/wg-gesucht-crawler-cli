import os
import re
import csv
import sys
import json
import time
import errno
import random
import urllib
import logging
import datetime
import requests
from bs4 import BeautifulSoup


class InfoFilter(logging.Filter):
    def filter(self, record):
        return record.levelno in [20, 30]


class WgGesuchtCrawler:
    def __init__(self, login_info, ad_links_folder, offline_ad_folder, logs_folder, template, filter_names):
        self.login_info = login_info
        self.ad_links_folder = ad_links_folder
        self.offline_ad_folder = offline_ad_folder
        self.logs_folder = logs_folder
        self.template_name = template
        self.filter_names = filter_names
        self.submit_message_url = 'https://www.wg-gesucht.de/ajax/api/Smp/api.php?action=conversations'
        self.session = requests.Session()
        self.logger = self.get_logger()
        self.counter = 1
        self.continue_next_page = True

    def get_logger(self):
        formatter = logging.Formatter(
            '%(asctime)s::%(name)s::%(levelname)s::%(message)s', datefmt='%Y-%m-%d %H:%M:%S')

        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)

        info_file_handler = logging.FileHandler(
            os.path.join(self.logs_folder, 'info.log'))
        info_file_handler.setFormatter(formatter)
        info_file_handler.addFilter(InfoFilter())
        info_file_handler.setLevel(logging.INFO)

        error_file_handler = logging.FileHandler(
            os.path.join(self.logs_folder, 'error.log'))
        error_file_handler.setFormatter(formatter)
        error_file_handler.setLevel(logging.ERROR)

        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.WARNING)

        logger.addHandler(info_file_handler)
        logger.addHandler(error_file_handler)
        logger.addHandler(stream_handler)

        return logger

    def sign_in(self):
        self.logger.info('Signing into WG-Gesucht...')

        payload = {
            'login_email_username': self.login_info['email'],
            'login_password': self.login_info['password'],
            'login_form_auto_login': '1',
            'display_language': 'de'
        }

        try:
            login = self.session.post(
                'https://www.wg-gesucht.de/ajax/api/Smp/api.php?action=login', json=payload)
        except requests.exceptions.Timeout:
            self.logger.exception('Timed out trying to log in')
            sys.exit(1)
        except requests.exceptions.ConnectionError:
            self.logger.exception('Could not connect to internet')
            sys.exit(1)

        if login.json() is True:
            self.logger.info('Logged in successfully')
        else:
            self.logger.warning(
                'Could not log into wg-gesucht.de with the given email and password')
            sys.exit(1)

    def get_page(self, url):
        # randomise time between requests to avoid reCAPTCHA
        time.sleep(random.randint(5, 8))
        try:
            page = self.session.get(url)
        except requests.exceptions.Timeout:
            self.logger.exception('Timed out trying to log in')
            sys.exit(1)
        except requests.exceptions.ConnectionError:
            self.logger.exception('Could not connect to internet')
            sys.exit(1)

        if self.no_captcha(page):
            self.logger.info('%s: requested successfully', url)
            return page
        return None

    def no_captcha(self, page):
        soup = BeautifulSoup(page.content, 'html.parser')
        recaptcha = soup.find_all('div', {'class': 'g-recaptcha'})

        if recaptcha:
            self.logger.warning("""
                Sorry! A 'reCAPTCHA' has been detected, please sign into you WG-Gesucht
                account through a browser and solve the 'reCAPTCHA', you may also have to
                wait 15-20 mins before restarting
                """)
            sys.exit(1)
        else:
            return True

    def retrieve_email_template(self):
        self.logger.info('Retrieving email template...')

        template_page = self.get_page(
            'https://www.wg-gesucht.de/mein-wg-gesucht-message-templates.html')

        def no_template_error():
            self.logger.warning("""
                You have not yet saved an email template in your WG-Gesucht account, please log
                into your account and save one at https://www.wg-gesucht.de/mein-wg-gesucht-message-templates.html
                """)
            sys.exit(1)

        soup = BeautifulSoup(template_page.content, 'html.parser')
        template_texts = [text.find_all('div', {'class': 'truncate_title'})
                          for text in soup.find_all('div', {'class': 'panel-body'})]
        try:
            if not self.template_name:
                chosen_text = template_texts[0][1].text
            else:
                chosen_text = list(filter(lambda text: text[0].text.strip(
                ).lower() == self.template_name, template_texts))[0][1].text
        except IndexError:
            no_template_error()

        if not chosen_text:
            no_template_error()
        else:
            return chosen_text.lstrip().rstrip()

    def fetch_filters(self):
        filters_page = self.get_page(
            'https://www.wg-gesucht.de/mein-wg-gesucht-filter.html')

        soup = BeautifulSoup(filters_page.content, 'html.parser')

        filter_results = soup.find_all(id=re.compile('^filter_name_'))
        filters_to_check = []
        if self.filter_names:
            filters_to_check = [filter.get('href') for filter in filter_results
            if filter.text.strip().lower() in self.filter_names]
        else:
            filters_to_check = [filter.get('href') for filter in filter_results]

        if self.filter_names and len(filters_to_check) != len(self.filter_names):
            self.logger.warning('Not all filters you wanted were found, maybe you mispelled one?')

        if not filters_to_check:
            self.logger.warning(
                'No filters found! Please create at least 1 filter on your WG-Gesucht account')
            sys.exit(1)
        else:
            self.logger.info('Filters found: %s', len(filters_to_check))
        return filters_to_check

    def already_sent(self, href):
        with open(os.path.join(self.ad_links_folder, 'WG Ad Links.csv'), 'rt', encoding='utf-8') as file:
            wg_links_file_csv = csv.reader(file)
            for wg_links_row in wg_links_file_csv:
                if wg_links_row[0] == href:
                    return True
        return False

    def change_to_list_details_view(self, soup, list_view_href=None):
        view_type_links = soup.find_all('a', href=True, title=True)
        if view_type_links[0]['title'] == 'Listenansicht':
            list_view_href = view_type_links[0]['href']

        #  change gallery view to list details view
        if list_view_href:
            details_results_page = self.get_page(
                'https://www.wg-gesucht.de/{}'.format(list_view_href))
            soup = BeautifulSoup(details_results_page.content, 'html.parser')
        return soup

    def process_filter_results(self, filter_results):
        url_list = list()
        for result in filter_results:
            post_date_link = result.find(
                'td', {'class': 'ang_spalte_datum'}).find('a')
            #  ignores ads older than 2 days
            try:
                post_date = datetime.datetime.strptime(
                    post_date_link.text.strip(), '%d.%m.%Y').date()
                if post_date >= datetime.date.today() - datetime.timedelta(days=2):
                    complete_href = 'https://www.wg-gesucht.de/{}'.format(
                        post_date_link.get('href'))
                    if not self.already_sent(complete_href):
                        url_list.append(complete_href)
                    else:
                        continue
                else:
                    self.continue_next_page = False
            except ValueError:  # caught if ad is inactive or has no date
                self.continue_next_page = False
        return url_list

    def fetch_ads(self, filters):
        self.logger.info('Searching filters for new ads, may take a while, depending on how many filters you '
                         'have set up.')
        url_list = list()
        for wg_filter in filters:
            # resets for each fitler, otherwise will immediately skip other filters
            self.continue_next_page = True
            while self.continue_next_page:
                search_results_page = self.get_page(wg_filter)

                soup = self.change_to_list_details_view(
                    BeautifulSoup(search_results_page.content, 'html.parser'))

                link_table = soup.find('table', {'id': 'table-compact-list'})

                pagination = soup.find('ul', {'class': 'pagination'})
                if not pagination:
                    self.continue_next_page = False
                else:
                    next_button_href = pagination.find_all('a')[-1].get('href')

                #  gets each row from the search results table
                search_results = link_table.find_all(
                    'tr', {'class': ['listenansicht0', 'listenansicht1']})

                url_list.extend(self.process_filter_results(search_results))

                if self.continue_next_page:
                    wg_filter = 'https://www.wg-gesucht.de/{}'.format(
                        next_button_href)

        self.logger.info('Number of apartments to email: %s',
                         len(set(url_list)))
        return set(url_list)

    def get_info_from_ad(self, url):
        # cleans up file name to allow saving (removes illegal file name characters)
        def text_replace(text):
            text = re.sub(
                r'\bhttps://www.wg-gesucht.de/\b|[:/*?|<>&^%@#!]', '', text)
            text = text.replace(':', '').replace('/', '').replace('\\', '').replace('*', '').replace('?', '').replace(
                '|', '').replace('<', '').replace('>', '').replace('https://www.wg-gesucht.de/', '')
            return text.rstrip().lstrip()

        ad_page = self.get_page(url)

        ad_page_soup = BeautifulSoup(ad_page.content, 'html.parser')

        ad_submitter = ad_page_soup.find('div', {'class': 'rhs_contact_information'}).find(
            'div', {'class': 'panel-body'})
        online_status = ad_submitter.find('div', {'class': 'col-md-6','class':'text-right'})
        online_status.extract() if online_status else None

        ad_title = text_replace(ad_page_soup.find('title').text)
        ad_submitter = text_replace(ad_submitter.text)
        ad_url = text_replace(url)

        return {
            'ad_page_soup': ad_page_soup,
            'ad_title': ad_title,
            'ad_submitter': ad_submitter,
            'ad_url': ad_url
        }

    def update_files(self, url, ad_info):
        MAX_FILENAME_LENGTH = 245

        ad_page_soup, ad_title, ad_submitter, ad_url = ad_info['ad_page_soup'], ad_info[
            'ad_title'], ad_info['ad_submitter'], ad_info['ad_url']
        # save url to file, so as not to send a message to them again
        with open(os.path.join(self.ad_links_folder, 'WG Ad Links.csv'), 'a', newline='',
                  encoding='utf-8') as file_write:
            csv_file_write = csv.writer(file_write)
            csv_file_write.writerow([url, ad_submitter, ad_title])

        # save a copy of the ad for offline viewing, in case the ad is deleted before the user can view it online
        max_ad_title_length = MAX_FILENAME_LENGTH - len(ad_submitter) - len(ad_url)
        if len(ad_title) > max_ad_title_length:
            ad_title = ad_title[:max_ad_title_length - 1] + '...'
        
        file_name = '{}-{}-{}'.format(ad_submitter, ad_title, ad_url)
        try:
            with open(os.path.join(self.offline_ad_folder, file_name),
                    'w', encoding='utf-8') as outfile:
                outfile.write(str(ad_page_soup))
        except OSError as err:
            if err.errno == errno.ENAMETOOLONG:
                self.logger.exception('File name of {} is too long, could not save this ad offline'.format(file_name))

    def get_payload(self, submit_form, template_text):
        return {
            'user_id': submit_form.find(attrs={'name': 'user_id'})['value'],
            'ad_type': submit_form.find(attrs={'name': 'ad_type'})['value'],
            'ad_id': submit_form.find(attrs={'name': 'ad_id'})['value'],
            'csrf_token': submit_form.find(attrs={'name': 'csrf_token'})['value'],
            'messages': [{'content': template_text, 'message_type': 'text'}]
        }

    def email_apartment(self, url, template_text):
        ad_info = self.get_info_from_ad(url)

        try:
            send_message_url = ad_info['ad_page_soup'].find(
                'a', {'class': 'btn btn-block btn-md wgg_orange'}).get('href')
        except AttributeError:
            self.logger.exception(
                'Could not find submit form, you have possibly already sent a message to this user')
            self.update_files(url, ad_info)
            return

        submit_form_page = self.get_page(send_message_url)
        submit_form_page_soup = BeautifulSoup(
            submit_form_page.content, 'html.parser')
        submit_form = submit_form_page_soup.find(
            'form', {'id': 'messenger_form'})

        headers = {
            'Content-Type': 'application/json',
            'Cache-Control': 'no-cache',
            'Referer': send_message_url,
            'Accept': 'application/json, text/javascript, */*',
            'Origin': 'https://www.wg-gesucht.de',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'
        }

        try:
            payload = self.get_payload(submit_form, template_text)
        except AttributeError:
            self.logger.exception(
                'Could not find submit form, you have possibly already sent a message to this user')
            self.update_files(url, ad_info)
            return

        json_data = json.dumps(payload)

        try:
            sent_message = self.session.post(
                self.submit_message_url, data=json_data, headers=headers).json()
        except requests.exceptions.Timeout:
            self.logger.exception(
                'Timed out sending a message to %s, will try again next time', ad_info['ad_submitter'])
            return

        if not sent_message.get('conversation_id', None):
            self.logger.warning(
                'Failed to send message to %s, will try again next time', ad_info['ad_submitter'])
            return

        self.update_files(url, ad_info)
        time_now = datetime.datetime.now().strftime('%H:%M:%S')
        self.logger.info('Message Sent to %s at %s!',
                         ad_info['ad_submitter'], time_now)

    def search(self):
        if self.counter < 2:
            self.logger.debug('Starting...')
        else:
            self.logger.info('Resuming...')

        template_text = self.retrieve_email_template()

        filters_to_check = self.fetch_filters()

        ad_list = self.fetch_ads(filters_to_check)

        for ad_url in ad_list:
            self.email_apartment(ad_url, template_text)

        time_now = datetime.datetime.now().strftime('%H:%M:%S')
        self.logger.info(
            'Program paused at %s... Will resume in 4-5 minutes', time_now)
        self.logger.info('WG-Gesucht checked %s %s since running',
                         self.counter, 'time' if self.counter <= 1 else 'times')
        # pauses for 4-5 mins before searching again
        time.sleep(random.randint(240, 300))
        self.counter += 1
        self.search()
