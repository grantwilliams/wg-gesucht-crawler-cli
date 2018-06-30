import os
import re
import csv
import sys
import time
import random
import urllib
import datetime
import requests
from bs4 import BeautifulSoup
from .logger import get_logger


def sign_in(login_info, logger):
    logger.info('Signing into WG-Gesucht...')

    payload = {
        'login_email_username': login_info['email'],
        'login_password': login_info['password'],
        'login_form_auto_login': '1',
        'display_language': 'de'
    }

    session = requests.Session()

    try:
        login = session.post('https://www.wg-gesucht.de/ajax/api/Smp/api.php?action=login', json=payload)
    except requests.exceptions.Timeout:
        logger.exception('Timed out tring to log in')
    except requests.exceptions.ConnectionError:
        logger.exception('Could not connect to internet')

    if login.json() is True:
        logger.info('Logged in successfully')
        return session
    else:
        logger.warning('Could not log into wg-gesucht.de with the given email and password')
        sys.exit(1)


def get_page(session, url, logger):
    """
    Fetches the URL and returns a requests Response object
    :param session: Requests Session instance
    :param url: URL to request
    :return: requests Response object
    """

    # randomise time between requests to avoid reCAPTCHA
    time.sleep(random.randint(5, 8))
    try:
        page = session.get(url)
    except requests.exceptions.Timeout:
        logger.exception('Timed out trying to log in')
    except requests.exceptions.ConnectionError:
        logger.exception('Could not connect to internet')
    else:
        if no_captcha(page, logger):
            logger.info('%s: requested successfully', page)
            return page


def no_captcha(page, logger):
    """
    Checks to see whether the current page is asking to solve a CAPTCHA
    :param page: the current page being accessed.
    :return: returns True if their is no CAPTCHA, otherwise quits with a message informing the user.
    """

    soup = BeautifulSoup(page.content, 'html.parser')
    table = soup.find_all('div', {'class': 'g-recaptcha'})

    if table:
        logger.warning("""
            Sorry! A 'reCAPTCHA' has been detected, please sign into you WG-Gesucht
            account through a browser and solve the 'reCAPTCHA', you may also have to
            wait 15-20 mins before restarting
            """)
        sys.exit(1)
    else:
        return True


def retrieve_email_template(session, logger):
    """
    Retrieves the users email template from their WG-Gesucht account
    :param session: Requests Session instance.
    :return: the email template as a string.
    """
    logger.info('Retrieving email template...')

    template_page = get_page(session, 'https://www.wg-gesucht.de/mein-wg-gesucht-email-template.html', logger)

    soup = BeautifulSoup(template_page.content, 'html.parser')
    template_text = soup.find('textarea', {'id': 'user_email_template'}).text

    if not template_text:
        logger.warning("""
            You have not yet saved an email template in your WG-Gesucht account, please log
            into your account and save one at https://www.wg-gesucht.de/mein-wg-gesucht-email-template.html
            """)
        sys.exit(1)
    else:
        return template_text


def fetch_filters(session, logger):
    """
    Create a list of filters to search.
    :param session: Requests Session instance.
    :return: a list of hrefs for search filters
    """

    filters_page = get_page(session, 'https://www.wg-gesucht.de/mein-wg-gesucht-filter.html', logger)

    soup = BeautifulSoup(filters_page.content, 'html.parser')

    filters_to_check = [link.get('href') for link in soup.find_all(id=re.compile('^filter_name_'))]

    if len(filters_to_check) < 1:
        logger.warning('No filters found! Please create at least 1 filter on your WG-Gesucht account')
        sys.exit(1)
    else:
        logger.info('Filters found: %s', len(filters_to_check))
    return filters_to_check


def already_sent(href, wg_ad_links_dir):
    """
    Check if an ad has already been applied for.
    :param href: URL for an ad
    :return: True or False, depending on whether the ad has already been applied for or not.
    """

    with open(os.path.join(wg_ad_links_dir, 'WG Ad Links.csv'), 'rt', encoding='utf-8') as file:
        wg_links_file_csv = csv.reader(file)
        for wg_links_row in wg_links_file_csv:
            if wg_links_row[0] == href:
                return True
    return False


def fetch_ads(session, filters, wg_ad_links_dir, logger):
    """
    Create a list of URLs of apartments to message/email.
    :param session: Requests Session instance.
    :param filters: a list of URLs for search filters (returned from func 'fetch_filters')
    :return: list a list of URLs of apartments to message/email.
    """

    logger.info('Searching filters for new ads, may take a while, depending on how many filters you have set up.')
    url_list = list()
    details_list_showing = False
    for wg_filter in filters:
        continue_next_page = True
        while continue_next_page:
            search_results_page = get_page(session, wg_filter, logger)

            soup = BeautifulSoup(search_results_page.content, 'html.parser')

            view_type_links = soup.find_all('a', href=True, title=True)
            if view_type_links[0]['title'] == 'Listenansicht':
                list_view_href = view_type_links[0]['href']
            else:
                details_list_showing = True

            #  change gallery view to list details view
            if not details_list_showing:
                details_results_page = get_page(session, 'https://www.wg-gesucht.de/{}'.format(list_view_href), logger)
                soup = BeautifulSoup(details_results_page.content, 'html.parser')
                details_list_showing = True

            link_table = soup.find('table', {'id': 'table-compact-list'})

            pagination = soup.find('ul', {'class': 'pagination'})
            if not pagination:
                continue_next_page = False
            else:
                next_button_href = pagination.find_all('a')[-1].get('href')

            #  gets each row from the search results table
            search_results = link_table.find_all('tr', {'class': ['listenansicht0', 'listenansicht1']})

            #  iterates through table row to extract individual ad hrefs
            for item in search_results:
                post_datelink = item.find('td', {'class': 'ang_spalte_datum'}).find('a')
                #  ignores ads older than 2 days
                try:
                    post_date = datetime.datetime.strptime(post_datelink.text.strip(), '%d.%m.%Y').date()
                    if post_date >= datetime.date.today() - datetime.timedelta(days=2):
                        complete_href = 'https://www.wg-gesucht.de/{}'.format(post_datelink.get('href'))
                        if complete_href not in url_list:
                            already_exists = already_sent(complete_href, wg_ad_links_dir)
                            if not already_exists:
                                url_list.append(complete_href)
                        else:
                            pass
                    else:
                        continue_next_page = False
                except ValueError:  # caught if ad is inactive and has no date
                    continue_next_page = False

            if continue_next_page:
                wg_filter = 'https://www.wg-gesucht.de/{}'.format(next_button_href)

    logger.info('Number of apartments to email: {}'.format(len(url_list)))
    return url_list


def email_apartment(session, url, login_info, template_text, wg_ad_links_dir, offline_ad_links_dir, logger):
    """
    Sends the user's template message to each new apartment listing found.
    :param session: Requests Session instance.
    :param url: URL of an ad for an apartment.
    :param login_info: User's WG-Gesucht account login details.
    :param template_text: User's saved template text fetched from account
    :return:
    """

    # cleans up file name to allow saving (removes illegal file name characters)
    def text_replace(text):
        text = re.sub(r'\bhttps://www.wg-gesucht.de/\b|[:/*?|<>&^%@#!]', '', text)
        text = text.replace(':', '').replace('/', '').replace('\\', '').replace('*', '').replace('?', '').replace(
            '|', '').replace('<', '').replace('>', '').replace('https://www.wg-gesucht.de/', '')
        return text

    ad_page = get_page(session, url, logger)

    ad_page_soup = BeautifulSoup(ad_page.content, 'html.parser')

    ad_submitter = ad_page_soup.find('div', {'class': 'rhs_contact_information'}).find(
        'div', {'class': 'text-capitalise'}).text.strip()

    ad_title = text_replace(ad_page_soup.find('title').text.strip())
    ad_submitter = text_replace(ad_submitter)
    ad_url = text_replace(url)

    send_message_url = ad_page_soup.find('a', {'class': 'btn btn-block btn-md btn-orange'}).get('href')

    submit_form_page = get_page(session, send_message_url, logger)
    submit_form_page_soup = BeautifulSoup(submit_form_page.content, 'html.parser')

    headers = {
        'content-type': 'application/x-www-form-urlencoded',
        'cache-control': 'no-cache',
    }

    payload = {
        'nachricht': template_text,
        'u_anrede': list(filter(lambda x: x['value'] != '',
                                submit_form_page_soup.find_all('option', selected=True)))[0]['value'],  # Title
        'vorname': submit_form_page_soup.find(attrs={'name': 'vorname'})['value'],  # First name
        'nachname': submit_form_page_soup.find(attrs={'name': 'nachname'})['value'],  # Last name
        'email': login_info['email'],
        'agb': 'on',  # accept terms of service
        'kopieanmich': 'on',  # send copy to self
        'telefon': login_info['phone'],
    }

    query_string = urllib.parse.urlencode(payload)

    try:
        sent_message = session.post(send_message_url, data=query_string, headers=headers)
    except requests.exceptions.Timeout:
        logger.exception('Timed out sending a message to %s, will try again next time', ad_submitter)
        return

    if 'erfolgreich kontaktiert' not in sent_message.text:
        logger.warning('Failed to send message to %s, will try again next time', ad_submitter)
        return

    # save url to file, so as not to send a message to them again
    with open(os.path.join(wg_ad_links_dir, 'WG Ad Links.csv'), 'a', newline='', encoding='utf-8') as file_write:
        csv_file_write = csv.writer(file_write)
        csv_file_write.writerow([url, ad_submitter, ad_title])

    # save a copy of the ad for offline viewing, in case the ad is deleted before the user can view it online
    if len(ad_title) > 150:
        ad_title = ad_title[:150]
    with open(os.path.join(offline_ad_links_dir, '{}-{}-{}'.format(ad_submitter, ad_title, ad_url)),
              'w', encoding='utf-8') as outfile:
        outfile.write(str(ad_page_soup))

    time_now = datetime.datetime.now().strftime('%H:%M:%S')
    logger.info('Message Sent to %s at %s!', ad_submitter, time_now)


def start_searching(login_info, wg_ad_links_dir, offline_ad_links_dir, logs_folder, counter=1):
    """

    :param login_info: login details for WG-Gesucht
    :param log_output_queue: message queue for log window
    :param counter: to keep track of how many times WG-Gesucht has been checked
    :return:
    """

    logger = get_logger(__name__, logs_folder)

    if counter < 2:
        logger.debug('Starting...')
    else:
        logger.info('Resuming...')

    session = sign_in(login_info, logger)

    template_text = retrieve_email_template(session, logger)

    filters_to_check = fetch_filters(session, logger)

    ad_list = fetch_ads(session, filters_to_check, wg_ad_links_dir, logger)

    for url in ad_list:
        email_apartment(session, url, login_info, template_text, wg_ad_links_dir, offline_ad_links_dir, logger)

    time_now = datetime.datetime.now().strftime('%H:%M:%S')
    logger.info('Program paused at %s... Will resume in 4-5 minutes', time_now)
    logger.info('WG-Gesucht checked %s %s since running', counter, 'time' if counter <= 1 else 'times')
    # pauses for 4-5 mins before searching again
    time.sleep(random.randint(240, 300))
    start_searching(login_info, wg_ad_links_dir, offline_ad_links_dir, logger, counter + 1)
