import os
import csv
from .logger import get_logger


def create_folders(dirname, logs_folder):
    if not os.path.exists(os.path.join(dirname, "WG Ad Links")):
        os.makedirs(os.path.join(dirname, "WG Ad Links"))
        ad_links_file_location = os.path.join(dirname, "WG Ad Links")

    if not os.path.exists(os.path.join(dirname, "Offline Ad Links")):
        os.makedirs(os.path.join(dirname, "Offline Ad Links"))
        offline_file_location = os.path.join(dirname, "Offline Ad Links")

    if not os.path.exists(os.path.join(ad_links_file_location, "WG Ad Links.csv")):
        with open(os.path.join(ad_links_file_location, "WG Ad Links.csv"), "w", newline="", encoding='utf-8') as write:
            csv_write = csv.writer(write)
            csv_write.writerow(['WG Links', 'Name', 'Ad Title'])

    logger = get_logger(
        __name__, folder=os.path.join(logs_folder))
    logger.warning("\n\nTwo folders have been created, %s'%s'%s contains "
                   "a 'csv' file which contains the URL's of the apartment ads the "
                   "program has messaged for you, and \n%s'%s'%s "
                   "contains a the actual ads, which can be viewed offline, in "
                   "case the submitter has removed the ad before you get chance to "
                   "look at it.\n\n",
                   '\033[92m', ad_links_file_location, '\033[0m',
                   '\033[92m', offline_file_location, '\033[0m')

    return
