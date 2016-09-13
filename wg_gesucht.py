import re
from os.path import expanduser
import sys
import csv
import time
from datetime import datetime, timedelta
import random
from selenium import webdriver
from selenium.common import exceptions
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup


def check_wg_credentials(login_info, cred_queue, call_origin):
    driver = webdriver.PhantomJS(executable_path='.phantomjs/bin/phantomjs')
    # driver = webdriver.Firefox()
    driver.set_window_size(1920, 1080)
    driver.set_page_load_timeout(15)

    try:
        driver.get('https://www.wg-gesucht.de/')
    except exceptions.TimeoutException:
        cred_queue.put("timed out {}".format(call_origin))
        return

    login_button = driver.find_element_by_xpath(".//*[@id='login_register']/a[2]")
    login_button.click()

    # wait until login modal appears
    try:
        WebDriverWait(driver, 10).until(EC.visibility_of_element_located((
            By.ID, 'login_email_username')))
    except exceptions.TimeoutException:
        cred_queue.put("timed out {}".format(call_origin))
        driver.quit()
        return

    email = driver.find_element_by_id('login_email_username')
    email.send_keys(login_info['email'])
    password = driver.find_element_by_id('login_password')
    password.send_keys(login_info['password'])
    password.submit()

    cred_queue.put("Signing into WG-Gesucht...")

    try:
        WebDriverWait(driver, 40).until(EC.visibility_of_element_located((
            By.XPATH, ".//*[@id='service-navigation']/div[1]/div/a")))  # Xpath of logout button
    except exceptions.TimeoutException:
        cred_queue.put("timed out {}".format(call_origin))
        driver.quit()
        return

    soup = BeautifulSoup(driver.page_source, 'html.parser')

    #  checks if the logout menu exists, if not then the login was not successful
    if len(soup.find_all("div", {"class": "dropdown toggle-logout-menu"})) > 0:
        cred_queue.put("login ok {}".format(call_origin))
        driver.quit()
        return
    else:
        cred_queue.put("login not ok {}".format(call_origin))
        driver.quit()
        return


def no_captcha(log_output_queue, page):
    """
    Checks to see whether the current page is asking to solve a CAPTCHA
    :param log_output_queue: message queue for log window
    :param page: the current page being accessed.
    :return: returns True if their is no CAPTCHA, otherwise quits with a message informing the user.
    """

    soup = BeautifulSoup(page, 'html.parser')
    table = soup.find_all("table", {"id": "captcha"})

    if len(table) > 0:
        log_output_queue.put(["exit", "Sorry! A 'CAPTCHA' has been detected, please wait 10-15 mins and restart"])
        return
    else:
        return True


def retrieve_email_template(driver, log_output_queue):
    """
    Retrieves the users email template from their WG-Gesucht account
    :param driver: Selenium PhantomJS driver instance.
    :param log_output_queue: message queue for log window
    :return: the email template as a string.
    """
    log_output_queue.put("Retrieving email template...")
    try:
        driver.get("https://www.wg-gesucht.de/mein-wg-gesucht-email-template.html")
    except exceptions.TimeoutException:
        log_output_queue.put("timed out")
        driver.quit()
        return

    template_page = driver.page_source
    soup = BeautifulSoup(template_page, 'html.parser')
    template_text = ""
    if no_captcha(log_output_queue, template_page):
        template_text = soup.find("textarea", {"id": "user_email_template"}).text

    if template_text == "":
        log_output_queue.put(
            ["exit", "You have not yet saved an email template in your WG-Gesucht account, please log into your "
                     "account and save one at 'https://www.wg-gesucht.de/mein-wg-gesucht-email-template.html'"])
        return
    else:
        return template_text


def fetch_filters(driver, log_output_queue):
    """
    Create a list of filters to search.
    :param driver: Selenium PhantomJS driver instance.
    :param log_output_queue: message queue for log window
    :return: a list of hrefs for search filters
    """
    try:
        driver.get("https://www.wg-gesucht.de/mein-wg-gesucht-filter.html")
    except exceptions.TimeoutException:
        log_output_queue.put("timed out")
        driver.quit()
        return

    filters_page = driver.page_source
    soup = BeautifulSoup(filters_page, 'html.parser')
    filter_links = []
    if no_captcha(log_output_queue, filters_page):
        filter_links = soup.find_all('a')

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


def fetch_ads(driver, log_output_queue, filters):
    """
    Create a list of URLs of apartments to message/email.
    :param driver: Selenium PhantomJS driver instance.
    :param log_output_queue: message queue for log window
    :param filters: a list of URLs for search filters (returned from func 'fetch_filters')
    :return: list a list of URLs of apartments to message/email.
    """

    log_output_queue.put("Searching filters for new ads, may take a while, depending on how many filters you have"
                         " set up.")
    url_list = list()
    for wg_filter in filters:
        wg_filter = wg_filter
        while True:
            try:
                driver.get(wg_filter)
            except exceptions.TimeoutException:
                log_output_queue.put("timed out")
                driver.quit()
                return

            search_results_page = driver.page_source
            soup = BeautifulSoup(search_results_page, 'html.parser')
            if no_captcha(log_output_queue, search_results_page):
                #  get all elements in table of search results
                link_table = soup.find_all('table', {'id': 'table-compact-list'})

                next_button_href = ""
                all_links = soup.find_all('a')
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
                    #  only get ads less than 2 days old
                    if datetime.strptime(links[2].text.strip(), "%d.%m.%y") >= datetime.now() - timedelta(days=2):
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
                    wg_filter = "https://www.wg-gesucht.de/{}".format(next_button_href)
                else:
                    break
    log_output_queue.put("Number of apartments to email: {}".format(len(url_list)))
    return url_list


def email_apartment(driver, log_output_queue, url, login_info, template_text):
    """
    Sends the user's template message to each new apartment listing found.
    :param driver: Selenium PhantomJS driver instance.
    :param log_output_queue: message queue for log window
    :param url: URL of an ad for an apartment.
    :param login_info: User's WG-Gesucht account login details.
    :param template_text: User's saved template text fetched from account
    :return:
    """

    # cleans up file name to allow saving (removes illegal file name characters)
    def text_replace(text):
        text = re.sub(r'\bhttps://www.wg-gesucht.de/\b|[:/\*?|<>&^%@#!]', '', text)
        text = text.replace(':', '').replace('/', '').replace('\\', '').replace('*', '').replace('?', '').replace(
            '|', '').replace('<', '').replace('>', '').replace("https://www.wg-gesucht.de/", "")
        return text
    try:
        driver.get(url)
    except exceptions.TimeoutException:
        log_output_queue.put("timed out")
        driver.quit()
        return

    ad_page = driver.page_source
    ad_page_soup = BeautifulSoup(ad_page, 'html.parser')

    contact_panel = ad_page_soup.find_all("div", {"class": "rhs_contact_information"})
    ad_submitter = ''
    for tag in contact_panel:
        panel_body = tag.find_all("div", {"class": "panel-body"})
        for panel in panel_body:
            divs = panel.find_all("div")
            for div in divs:
                if div is not None and div.text.strip() == 'Name:':
                    ad_submitter = divs[divs.index(div) + 1].text.strip()

    if no_captcha(log_output_queue, ad_page):
        ad_title = text_replace(ad_page_soup.find("title").text.strip())
        ad_submitter = text_replace(ad_submitter)
        send_message_url = ad_page_soup.find("a", {"class": "btn btn-block btn-md btn-orange"})

        try:
            driver.get(send_message_url.get("href"))
        except exceptions.TimeoutException:
            log_output_queue.put("timed out")
            driver.quit()
            return

        # clicks security alert, should occur just once per session
        try:
            driver.find_element_by_id("sicherheit_bestaetigung").click()
        except exceptions.ElementNotVisibleException:
            pass
        except exceptions.NoSuchElementException:
            pass

        telephone_field = driver.find_element_by_name('telefon')
        telephone_field.send_keys(login_info['phone_number'])
        message_field = driver.find_element_by_id('nachricht-text')
        message_field.send_keys(template_text)

        try:
            driver.find_element_by_name('telefon').get_attribute('value') == login_info['phone_number']
        except AssertionError:
            log_output_queue.put(["exit", "Error: Could not enter phone number, please close and restart"])
            driver.quit()
            return
        try:
            driver.find_element_by_id('nachricht-text').get_attribute('value') == template_text
        except AssertionError:
            log_output_queue.put(["exit", "Error: Could not enter email template, please close and restart"])
            driver.quit()
            return

        message_field.submit()

        try:
            WebDriverWait(driver, 10).until(EC.visibility_of_element_located((
                By.CLASS_NAME, 'alert-success')))
        except exceptions.TimeoutException:
            log_output_queue.put("Failed to send message to {}, will try again next time".format(ad_submitter))
            return

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
            outfile.write(str(ad_page_soup))

        log_output_queue.put(
            "Message Sent to {} at {}!".format(ad_submitter, datetime.now().strftime("%H:%M:%S")))


def start_searching(login_info, log_output_queue, counter=1):
    """

    :param login_info: login details for WG-Gesucht
    :param log_output_queue: message queue for log window
    :param counter: to keep track of how many times WG-Gesucht has been checked
    :return:
    """
    driver = webdriver.PhantomJS(executable_path='.phantomjs/bin/phantomjs')
    # driver = webdriver.Firefox()
    driver.set_window_size(1920, 1080)
    driver.set_page_load_timeout(60)

    if counter < 2:
        log_output_queue.put("Starting...")
    else:
        log_output_queue.put("Resuming...")

    try:
        driver.get('https://www.wg-gesucht.de/')
    except exceptions.TimeoutException:
        log_output_queue.put("timed out")
        driver.quit()
        return

    login_button = driver.find_element_by_xpath(".//*[@id='login_register']/a[2]")
    login_button.click()

    # wait until login modal appears
    try:
        WebDriverWait(driver, 10).until(EC.visibility_of_element_located((
            By.ID, 'login_email_username')))
    except exceptions.TimeoutException:
        log_output_queue.put("timed out")
        driver.quit()
        return

    email = driver.find_element_by_id('login_email_username')
    email.send_keys(login_info['email'])
    password = driver.find_element_by_id('login_password')
    password.send_keys(login_info['password'])
    password.submit()

    log_output_queue.put("Signing into WG-Gesucht...")

    try:
        WebDriverWait(driver, 40).until(EC.visibility_of_element_located((
            By.XPATH, ".//*[@id='service-navigation']/div[1]/div/a")))  # Xpath of logout button
    except exceptions.TimeoutException:
        log_output_queue.put("timed out")
        driver.quit()
        return

    soup = BeautifulSoup(driver.page_source, 'html.parser')

    #  checks if the logout menu exists, if not then the login was not successful
    if len(soup.find_all("div", {"class": "dropdown toggle-logout-menu"})) > 0:
        log_output_queue.put("Login successful!")
    else:
        log_output_queue.put("login not ok")
        return

    template_text = retrieve_email_template(driver, log_output_queue)

    filters_to_check = fetch_filters(driver, log_output_queue)

    ad_list = fetch_ads(driver, log_output_queue, filters_to_check)

    for url in ad_list:
        email_apartment(driver, log_output_queue, url, login_info, template_text)

    log_output_queue.put("\nProgram paused at {}... Will resume in 4-5 minutes".format(
        datetime.now().strftime("%H:%M:%S")))
    log_output_queue.put("WG-Gesucht checked {} {} since running\n".format(
        counter, "time" if counter <= 1 else "times"))
    time.sleep(random.randint(240, 300))  # pauses for 4-5 mins before searching again
    start_searching(login_info, log_output_queue, counter + 1)
