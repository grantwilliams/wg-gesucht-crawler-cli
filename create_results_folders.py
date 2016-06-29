import os
from os.path import expanduser
import sys
import csv


def create_folders(folder_queue):
    if sys.platform == "win32":
        if not os.path.exists("WG Ad Links"):
            os.makedirs("WG Ad Links")
        if not os.path.exists("Offline Ad Links"):
            os.makedirs("Offline Ad Links")
        file_location = "WG Ad Links"
        offline_file_location = "Offline Ad Links"
    else:
        home = expanduser('~')
        if not os.path.exists("{}/WG Finder/WG Ad Links".format(home)):
            os.makedirs("{}/WG Finder/WG Ad Links".format(home))
        if not os.path.exists("{}/WG Finder/Offline Ad Links".format(home)):
            os.makedirs("{}/WG Finder/Offline Ad Links".format(home))
        file_location = "{}/WG Finder/WG Ad Links".format(home)
        offline_file_location = "{}/WG Finder/Offline Ad Links".format(home)

    if not os.path.exists("{}/WG Ad Links.csv".format(file_location)):
        with open("{}/WG Ad Links.csv".format(file_location), "w", newline="", encoding='utf-8') as file_write:
            csv_write = csv.writer(file_write)
            csv_write.writerow(['WG Links', 'Name', 'Ad Title'])

    folder_queue.put([file_location, offline_file_location])
