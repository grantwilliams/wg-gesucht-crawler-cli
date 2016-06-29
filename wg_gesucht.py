import re
from os.path import expanduser
import sys
import csv
import time
from datetime import datetime, timedelta
import random
import requests.exceptions
import mechanicalsoup


def check_wg_credentials(login_info, cred_queue, call_origin):
    browser = mechanicalsoup.Browser(soup_config={'features': 'html.parser'})

    try:
        login_page = browser.get('https://www.wg-gesucht.de/mein-wg-gesucht.html', timeout=15)
    except requests.exceptions.HTTPError:
        cred_queue.put("no connection {}".format(call_origin))
        return
    except requests.exceptions.ConnectionError:
        cred_queue.put("no connection {}".format(call_origin))
        return
    except requests.exceptions.Timeout:
        cred_queue.put("timed out {}".format(call_origin))
        return

    login_form = login_page.soup.select('.panel-body')[0].select('form')[0]
    login_form.find("input", {"id": "email_user"})['value'] = login_info['email']
    login_form.find("input", {"id": "passwort-static"})['value'] = login_info['password']

    cred_queue.put("Signing into WG-Gesucht...")
    home_page = browser.submit(login_form, login_page.url)

    #  checks if the logout menu exists, if not then the login was not successful
    if len(home_page.soup.find_all("div", {"class": "dropdown toggle-logout-menu"})) > 0:
        cred_queue.put("login ok {}".format(call_origin))
        return
    else:
        cred_queue.put("login not ok {}".format(call_origin))
        return


def no_captcha(log_output_queue, page):
    """
    Checks to see whether the current page is asking to solve a CAPTCHA
    :param log_output_queue: message queue for log window
    :param page: the current page being accessed.
    :return: returns True if their is no CAPTCHA, otherwise quits with a message informing the user.
    """
    table = page.soup.find_all("table", {"id": "captcha"})

    if len(table) > 0:
        log_output_queue.put(["exit", "Sorry! A 'CAPTCHA' has been detected, please wait 10-15 mins and restart"])
        return
    else:
        return True


def retrieve_email_template(browser, log_output_queue):
    """
    Retrieves the users email template from their WG-Gesucht account
    :param browser: Mechanicalsoup Browser instance.
    :param log_output_queue: message queue for log window
    :return: the email template as a string.
    """
    log_output_queue.put("Retrieving email template...")
    try:
        template_page = browser.get("https://www.wg-gesucht.de/mein-wg-gesucht-email-template.html", timeout=15)
    except requests.exceptions.HTTPError:
        log_output_queue.put("no connection")
        return
    except requests.exceptions.ConnectionError:
        log_output_queue.put("no connection")
        return
    except requests.exceptions.Timeout:
        log_output_queue.put("timed out")
        return
    template_text = ""
    if no_captcha(log_output_queue, template_page):
        template_text = template_page.soup.find("textarea", {"id": "user_email_template"}).text

    if template_text == "":
        log_output_queue.put(
            ["exit", "You have not yet saved an email template in your WG-Gesucht account, please log into your "
                     "account and save one at 'https://www.wg-gesucht.de/mein-wg-gesucht-email-template.html'"])
        return
    else:
        return template_text


def fetch_filters(browser, log_output_queue):
    """
    Create a list of filters to search.
    :param browser: Mechanicalsoup Browser instance.
    :param log_output_queue: message queue for log window
    :return: a list of hrefs for search filters
    """
    try:
        filters_page = browser.get("https://www.wg-gesucht.de/mein-wg-gesucht-filter.html", timeout=15)
    except requests.exceptions.HTTPError:
        log_output_queue.put("no connection")
        return
    except requests.exceptions.ConnectionError:
        log_output_queue.put("no connection")
        return
    except requests.exceptions.Timeout:
        log_output_queue.put("timed out")
        return

    filter_links = []
    if no_captcha(log_output_queue, filters_page):
        filter_links = filters_page.soup.find_all('a')

    filters_to_check = []
    for link in filter_links:
        href = link.get('href')
        if href is not None:
            if 'wohnraumangebote.html?filter=' in href:
                filters_to_check.append(href)

    if len(filters_to_check) < 1:
        log_output_queue.put(
            ["exit", "No filters found! Please create at least 1 filter on your WG-Gesucht account"])
        return
    else:
        log_output_queue.put("Filters found: {0}".format(len(filters_to_check)))
    return filters_to_check


def already_sent(href):
    """
    Check if an ad has already been applied for.
    :param href: URL for an ad
    :return: True or False, depending on whether the ad has already been applied for or not.
    """
    home = expanduser('~')
    if sys.platform == 'win32':
        file_location = "WG Ad Links"
    else:
        file_location = "{}/WG Finder/WG Ad Links".format(home)
    with open("{}/WG Ad Links.csv".format(file_location), 'rt'.format(file_location), encoding='utf-8') as file:
        wg_links_file_csv = csv.reader(file)
        link_exists = False
        for wg_links_row in wg_links_file_csv:
            if wg_links_row[0] == href:
                link_exists = True
                break
            else:
                link_exists = False
    return link_exists


def fetch_ads(browser, log_output_queue, filters):
    """
    Create a list of URLs of apartments to message/email.
    :param browser: Mechanicalsoup Browser instance.
    :param log_output_queue: message queue for log window
    :param filters: a list of URLs for search filters (returned from func 'fetch_filters')
    :return: list a list of URLs of apartments to message/email.
    """
    url_list = list()
    for wg_filter in filters:
        time.sleep(random.randint(4, 7))
        wg_filter = wg_filter
        while True:
            try:
                search_results_page = browser.get(wg_filter, timeout=15)
            except requests.exceptions.HTTPError:
                log_output_queue.put("no connection")
                return
            except requests.exceptions.ConnectionError:
                log_output_queue.put("no connection")
                return
            except requests.exceptions.Timeout:
                log_output_queue.put("timed out")
                return
            if no_captcha(log_output_queue, search_results_page):
                #  get all elements in table of search results
                link_table = search_results_page.soup.find_all('table', {'id': 'table-compact-list'})

                next_button_href = ""
                all_links = search_results_page.soup.find_all('a')
                for link in all_links:
                    if link is not None:
                        if link.text.strip() == "»":
                            next_button_href = link.get('href')

                #  gets soup data from the search results table
                search_results = []
                for tag in link_table:
                    results = tag.find_all('tr', {'class': ['listenansicht0', 'listenansicht1']})
                    for item in results:
                        search_results.append(item)

                continue_next_page = True
                #  iterates through raw soup data to extract individual ad hrefs
                for item in search_results:
                    links = item.find_all('a')
                    #  only get ads less than 1 day old
                    if datetime.strptime(links[2].text.strip(), "%d.%m.%y") >= datetime.now() - timedelta(days=1):
                        complete_href = "https://www.wg-gesucht.de/{}".format(links[2].get('href'))
                        if complete_href not in url_list:
                            already_exists = already_sent(complete_href)
                            if not already_exists:
                                url_list.append(complete_href)
                        else:
                            pass
                    else:
                        continue_next_page = False
                        break

                if continue_next_page:
                    time.sleep(random.randint(4, 7))
                    wg_filter = "https://www.wg-gesucht.de/{}".format(next_button_href)
                else:
                    break
    log_output_queue.put("Number of apartments to email: {}".format(len(url_list)))
    return url_list


def email_apartment(browser, log_output_queue, url, login_info, template_text):
    """
    Sends the user's template message to each new apartment listing found.
    :param browser: Mechanicalsoup Browser instance.
    :param log_output_queue: message queue for log window
    :param url: URL of an ad for an apartment.
    :return:
    """
    def text_replace(text):
        text = re.sub(r'\bhttps://www.wg-gesucht.de/\b|[:/\*?|<>&^%@#!]', '', text)
        text = text.replace(':', '').replace('/', '').replace('\\', '').replace('*', '').replace('?', '').replace(
            '|', '').replace('<', '').replace('>', '').replace("https://www.wg-gesucht.de/", "")
        return text
    try:
        ad_page = browser.get(url, timeout=15)
    except requests.exceptions.HTTPError:
        log_output_queue.put("no connection")
        return
    except requests.exceptions.ConnectionError:
        log_output_queue.put("no connection")
        return
    except requests.exceptions.Timeout:
        log_output_queue.put("timed out")
        return
    if no_captcha(log_output_queue, ad_page):
        ad_title = text_replace(ad_page.soup.find(
            "h1", {"class": "headline headline-detailed-view-title"}).text.strip())
        ad_submitter = text_replace(ad_page.soup.find("div", {"class": "col-sm-9"}).text.strip())
        send_message_url = ad_page.soup.find("a", {"class": "btn btn-block btn-md btn-orange"})
        try:
            send_message_page = browser.get(send_message_url.get("href"), timeout=15)
        except requests.exceptions.HTTPError:
            log_output_queue.put("no connection")
            return
        except requests.exceptions.ConnectionError:
            log_output_queue.put("no connection")
            return
        except requests.exceptions.Timeout:
            log_output_queue.put("timed out")
            return

        send_message_form = send_message_page.soup.select(".panel-body")[0].select("form")[0]
        time.sleep(2)
        send_message_form.find(attrs={"name": "telefon"})["value"] = login_info['phone_number']
        time.sleep(2)
        send_message_form.find(attrs={"id": "nachricht-text"}).insert(0, template_text)

        try:
            assert send_message_page.soup.find("input", {"name": "telefon"})["value"] == login_info['phone_number']
        except AssertionError:
            log_output_queue.put(["exit", "Error: Could not enter phone number, please close and restart"])
            return
        try:
            assert send_message_page.soup.find("textarea", {"id": "nachricht-text"}).text == template_text
        except AssertionError:
            log_output_queue.put(["exit", "Error: Could not enter email template, please close and restart"])
            return

        message_sent_page = browser.submit(send_message_form, send_message_page.url)

        if len(message_sent_page.soup.find_all("div", {"class": "alert alert-success"})) > 0:
            home = expanduser('~')
            if sys.platform == 'win32':
                ad_csv_location = "WG Ad Links"
                offline_ad_location = "Offline Ad Links"

            else:
                ad_csv_location = "{}/WG Finder/WG Ad Links".format(home)
                offline_ad_location = "{}/WG Finder/Offline Ad Links".format(home)
            # save url to file, so as not to send a message to them again
            with open("{}/WG Ad Links.csv".format(ad_csv_location), 'a', newline="", encoding='utf-8') as file_write:
                csv_file_write = csv.writer(file_write)
                csv_file_write.writerow([url, ad_submitter, ad_title])

            # save a copy of the ad for offline viewing, in case the ad is deleted before the user can view it online
            with open("{}/{}-{}-{}".format(offline_ad_location, ad_submitter, ad_title, text_replace(str(url))),
                      'w', encoding='utf-8') as outfile:
                outfile.write(str(ad_page.soup))

            log_output_queue.put(
                "Message Sent to {} at {}!".format(ad_submitter, datetime.now().strftime("%H:%M:%S")))
        else:
            log_output_queue.put("Failed to send message to {}, will try again next time".format(ad_submitter))


def start_searching(login_info, log_output_queue, counter=1):
    """

    :param login_info: login details for WG-Gesucht
    :param log_output_queue: message queue for log window
    :param counter: to keep track of how many times WG-Gesucht has been checked
    :return:
    """
    browser = mechanicalsoup.Browser(soup_config={'features': 'html.parser'})

    if counter < 2:
        log_output_queue.put("Starting...")
    else:
        log_output_queue.put("Resuming...")

    try:
        login_page = browser.get('https://www.wg-gesucht.de/mein-wg-gesucht.html', timeout=15)
    except requests.exceptions.HTTPError:
        log_output_queue.put("no connection")
        return
    except requests.exceptions.ConnectionError:
        log_output_queue.put("no connection")
        return
    except requests.exceptions.Timeout:
        log_output_queue.put("timed out")
        return

    login_form = login_page.soup.select('.panel-body')[0].select('form')[0]
    login_form.find("input", {"id": "email_user"})['value'] = login_info['email']
    login_form.find("input", {"id": "passwort-static"})['value'] = login_info['password']

    log_output_queue.put("Signing into WG-Gesucht...")
    home_page = browser.submit(login_form, login_page.url)

    #  checks if the logout menu exists, if not then the login was not successful
    if len(home_page.soup.find_all("div", {"class": "dropdown toggle-logout-menu"})) > 0:
        log_output_queue.put("Login successful!")
    else:
        log_output_queue.put("login not ok")
        return

    time.sleep(random.randint(4, 7))  # to try appear human to avoid CAPTCHA
    template_text = retrieve_email_template(browser, log_output_queue)

    time.sleep(random.randint(4, 7))
    filters_to_check = fetch_filters(browser, log_output_queue)

    time.sleep(random.randint(4, 7))
    ad_list = fetch_ads(browser, log_output_queue, filters_to_check)

    for url in ad_list:
        time.sleep(random.randint(4, 7))
        email_apartment(browser, log_output_queue, url, login_info, template_text)

    log_output_queue.put("\nProgram paused at {}... Will resume in 4-5 minutes".format(
        datetime.now().strftime("%H:%M:%S")))
    log_output_queue.put("WG-Gesucht checked {} {} since running\n".format(
        counter, "time" if counter <= 1 else "times"))
    time.sleep(random.randint(240, 300))  # pauses for 4-5 mins before searching again
    start_searching(login_info, log_output_queue, counter + 1)
