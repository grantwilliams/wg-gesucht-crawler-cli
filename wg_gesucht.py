import re
import os
import csv
import sys
import time
import datetime
import random
import requests
import urllib
from bs4 import BeautifulSoup


def check_wg_credentials(login_info, cred_queue, call_origin):
    cred_queue.put("Signing into WG-Gesucht...")

    payload = {
        "login_email_username": login_info['email'],
        "login_password": login_info['password'],
        "login_form_auto_login": "1",
        "display_language": "de"
    }

    session = requests.Session()

    try:
        login = session.post("https://www.wg-gesucht.de/ajax/api/Smp/api.php?action=login", json=payload)
    except requests.exceptions.Timeout:
        cred_queue.put(f"timed out {call_origin}")
        return
    except requests.exceptions.ConnectionError:
        cred_queue.put(f"no connection {call_origin}")
        return

    if call_origin == "running":
        return session

    if login.json() == True:
        cred_queue.put(f"login ok {call_origin}")
        return
    else:
        cred_queue.put(f"login not ok {call_origin}")
        return

def get_page(session, url, log_output_queue):
    """
    Fetches the URL and returns a requests Response object
    :param session: Requests Session instance
    :param url: URL to request
    :param log_output_queue: message queue for log window
    :return: requests Response object
    """

    time.sleep(random.randint(5, 8))  # randomise time between requests to avoid reCAPTCHA
    try:
        page = session.get(url)
    except requests.exceptions.Timeout:
        log_output_queue.put("timed out running")
    except requests.exceptions.ConnectionError:
        log_output_queue.put("no connection running")
    else:
        if no_captcha(log_output_queue, page):
            return page

def no_captcha(log_output_queue, page):
    """
    Checks to see whether the current page is asking to solve a CAPTCHA
    :param log_output_queue: message queue for log window
    :param page: the current page being accessed.
    :return: returns True if their is no CAPTCHA, otherwise quits with a message informing the user.
    """

    soup = BeautifulSoup(page.content, 'html.parser')
    table = soup.find_all("div", {"class": "g-recaptcha"})

    if len(table) > 0:
        log_output_queue.put(["exit", "Sorry! A 'reCAPTCHA' has been detected, please wait 10-15 mins and restart"])
        sys.exit()
    else:
        return True


def retrieve_email_template(session, log_output_queue):
    """
    Retrieves the users email template from their WG-Gesucht account
    :param session: Requests Session instance.
    :param log_output_queue: message queue for log window
    :return: the email template as a string.
    """
    log_output_queue.put("Retrieving email template...")

    template_page = get_page(session, "https://www.wg-gesucht.de/mein-wg-gesucht-email-template.html", log_output_queue)

    soup = BeautifulSoup(template_page.content, 'html.parser')
    template_text = soup.find("textarea", {"id": "user_email_template"}).text

    if template_text == "":
        log_output_queue.put(
            ["exit", "You have not yet saved an email template in your WG-Gesucht account, please log into your "
                     "account and save one at 'https://www.wg-gesucht.de/mein-wg-gesucht-email-template.html'"])
        sys.exit()
    else:
        return template_text


def fetch_filters(session, log_output_queue):
    """
    Create a list of filters to search.
    :param session: Requests Session instance.
    :param log_output_queue: message queue for log window
    :return: a list of hrefs for search filters
    """

    filters_page = get_page(session, "https://www.wg-gesucht.de/mein-wg-gesucht-filter.html", log_output_queue)

    soup = BeautifulSoup(filters_page.content, 'html.parser')

    filters_to_check = [link.get('href') for link in soup.find_all(id=re.compile("^filter_name_"))]

    if len(filters_to_check) < 1:
        log_output_queue.put(
            ["exit", "No filters found! Please create at least 1 filter on your WG-Gesucht account"])
        return
    else:
        log_output_queue.put(f"Filters found: {len(filters_to_check)}")
    return filters_to_check


def already_sent(href, wg_ad_links_dir):
    """
    Check if an ad has already been applied for.
    :param href: URL for an ad
    :return: True or False, depending on whether the ad has already been applied for or not.
    """

    with open(os.path.join(wg_ad_links_dir, "WG Ad Links.csv"), 'rt', encoding='utf-8') as file:
        wg_links_file_csv = csv.reader(file)
        link_exists = False
        for wg_links_row in wg_links_file_csv:
            if wg_links_row[0] == href:
                link_exists = True
                break
    return link_exists


def fetch_ads(session, log_output_queue, filters, wg_ad_links_dir):
    """
    Create a list of URLs of apartments to message/email.
    :param session: Requests Session instance.
    :param log_output_queue: message queue for log window
    :param filters: a list of URLs for search filters (returned from func 'fetch_filters')
    :return: list a list of URLs of apartments to message/email.
    """

    log_output_queue.put("Searching filters for new ads, may take a while, depending on how many filters you have"
                         " set up.")
    url_list = list()
    details_list_showing = False
    for wg_filter in filters:
        continue_next_page = True
        while continue_next_page:
            search_results_page = get_page(session, wg_filter, log_output_queue)

            soup = BeautifulSoup(search_results_page.content, 'html.parser')

            view_type_links = soup.find_all('a', href=True, title=True)
            if view_type_links[0]['title'] == 'Listenansicht':
                list_view_href = view_type_links[0]['href']
            else:
                details_list_showing = True

            #  change gallery view to list details view
            if not details_list_showing:
                details_results_page = get_page(session, f"https://www.wg-gesucht.de/{list_view_href}", log_output_queue)
                soup = BeautifulSoup(details_results_page.content, 'html.parser')
                details_list_showing = True

            link_table = soup.find('table', {'id': 'table-compact-list'})

            pagination = soup.find('ul', {"class": "pagination"})
            if not pagination:
                continue_next_page = False
            else:
                next_button_href = pagination.find_all('a')[-1].get('href')

            #  gets each row from the search results table
            search_results = link_table.find_all('tr', {'class': ['listenansicht0', 'listenansicht1']})

            #  iterates through table row to extract individual ad hrefs
            for item in search_results:
                post_datelink = item.find('td', {"class": "ang_spalte_datum"}).find('a')
                #  ignores ads older than 2 days
                try:
                    post_date = datetime.datetime.strptime(post_datelink.text.strip(), "%d.%m.%Y").date()
                    if post_date >= datetime.date.today() - datetime.timedelta(days=2):
                        complete_href = f"https://www.wg-gesucht.de/{post_datelink.get('href')}"
                        if complete_href not in url_list:
                            already_exists = already_sent(complete_href, wg_ad_links_dir)
                            if not already_exists:
                                url_list.append(complete_href)
                        else:
                            pass
                    else:
                        continue_next_page = False
                except ValueError:  #  caught if ad is inactive and has no date
                    continue_next_page = False

            if continue_next_page:
                wg_filter = f"https://www.wg-gesucht.de/{next_button_href}"

    log_output_queue.put(f"Number of apartments to email: {len(url_list)}")
    return url_list


def email_apartment(session, log_output_queue, url, login_info, template_text, wg_ad_links_dir, offline_ad_links_dir):
    """
    Sends the user's template message to each new apartment listing found.
    :param session: Requests Session instance.
    :param log_output_queue: message queue for log window
    :param url: URL of an ad for an apartment.
    :param login_info: User's WG-Gesucht account login details.
    :param template_text: User's saved template text fetched from account
    :return:
    """

    # cleans up file name to allow saving (removes illegal file name characters)
    def text_replace(text):
        text = re.sub(r'\bhttps://www.wg-gesucht.de/\b|[:/*?|<>&^%@#!]', '', text)
        text = text.replace(':', '').replace('/', '').replace('\\', '').replace('*', '').replace('?', '').replace(
            '|', '').replace('<', '').replace('>', '').replace("https://www.wg-gesucht.de/", "")
        return text

    ad_page = get_page(session, url, log_output_queue)

    ad_page_soup = BeautifulSoup(ad_page.content, 'html.parser')

    ad_submitter = ad_page_soup.find("div", {"class": "rhs_contact_information"}).find("div", {"class": "text-capitalise"}).text.strip()

    ad_title = text_replace(ad_page_soup.find("title").text.strip())
    ad_submitter = text_replace(ad_submitter)
    ad_url = text_replace(url)

    send_message_url = ad_page_soup.find("a", {"class": "btn btn-block btn-md btn-orange"}).get('href')

    submit_form_page = get_page(session, send_message_url, log_output_queue)
    submit_form_page_soup = BeautifulSoup(submit_form_page.content, "html.parser")

    headers = {
        'content-type': "application/x-www-form-urlencoded",
        'cache-control': "no-cache",
    }

    payload = {
        "nachricht": template_text,
        "u_anrede": list(filter(lambda x: x['value'] != '', submit_form_page_soup.find_all("option", selected=True)))[0]['value'],  # Title (Herr/Frau)
        "vorname": submit_form_page_soup.find(attrs={"name": "vorname"})["value"],  # First name
        "nachname": submit_form_page_soup.find(attrs={"name": "nachname"})["value"],  # Last name
        "email": login_info['email'],
        "agb": "on",  # accept terms of service
        "kopieanmich": "on",  # send copy to self
        "telefon": login_info['phone_number'],
    }

    query_string = urllib.parse.urlencode(payload)

    try:
        sent_message = session.post(send_message_url, data=query_string, headers=headers)
    except requests.exceptions.Timeout:
        log_output_queue.put(f"Failed to send message to {ad_submitter}, will try again next time")
        return

    if "erfolgreich kontaktiert" not in sent_message.text:
        log_output_queue.put(f"Failed to send message to {ad_submitter}, will try again next time")
        return

    # save url to file, so as not to send a message to them again
    with open(os.path.join(wg_ad_links_dir, "WG Ad Links.csv"), 'a', newline="", encoding='utf-8') as file_write:
        csv_file_write = csv.writer(file_write)
        csv_file_write.writerow([url, ad_submitter, ad_title])

    # save a copy of the ad for offline viewing, in case the ad is deleted before the user can view it online
    if len(ad_title) > 150:
        ad_title = ad_title[:150]
    with open(os.path.join(offline_ad_links_dir, f"{ad_submitter}-{ad_title}-{ad_url}"),
    'w', encoding='utf-8') as outfile:
        outfile.write(str(ad_page_soup))

    time_now = datetime.datetime.now().strftime("%H:%M:%S")
    log_output_queue.put(f"Message Sent to {ad_submitter} at {time_now}!")


def start_searching(login_info, log_output_queue, wg_ad_links_dir, offline_ad_links_dir, counter=1):
    """

    :param login_info: login details for WG-Gesucht
    :param log_output_queue: message queue for log window
    :param counter: to keep track of how many times WG-Gesucht has been checked
    :return:
    """

    if counter < 2:
        log_output_queue.put("Starting...")
    else:
        log_output_queue.put("Resuming...")

    session = check_wg_credentials(login_info, log_output_queue, "running")

    template_text = retrieve_email_template(session, log_output_queue)

    filters_to_check = fetch_filters(session, log_output_queue)

    ad_list = fetch_ads(session, log_output_queue, filters_to_check, wg_ad_links_dir)

    for url in ad_list:
        email_apartment(session, log_output_queue, url, login_info, template_text, wg_ad_links_dir, offline_ad_links_dir)

    time_now = datetime.datetime.now().strftime("%H:%M:%S")
    log_output_queue.put(f"\nProgram paused at {time_now}... Will resume in 4-5 minutes")
    log_output_queue.put(f"WG-Gesucht checked {counter} {'time' if counter <= 1 else 'times'} since running\n")
    time.sleep(random.randint(240, 300))  # pauses for 4-5 mins before searching again
    start_searching(login_info, log_output_queue, wg_ad_links_dir, offline_ad_links_dir, counter + 1)
