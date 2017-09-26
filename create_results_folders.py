import os
import csv


def create_folders(folder_queue, dirname):
    if not os.path.exists(os.path.join(dirname, "WG Ad Links")):
        os.makedirs(os.path.join(dirname, "WG Ad Links"))
        file_location = os.path.join(dirname, "WG Ad Links")

    if not os.path.exists(os.path.join(dirname, "Offline Ad Links")):
        os.makedirs(os.path.join(dirname, "Offline Ad Links"))
        offline_file_location = os.path.join(dirname, "Offline Ad Links")

    if not os.path.exists(os.path.join(file_location, "WG Ad Links.csv")):
        with open(os.path.join(file_location, "WG Ad Links.csv"), "w", newline="", encoding='utf-8') as write:
            csv_write = csv.writer(write)
            csv_write.writerow(['WG Links', 'Name', 'Ad Title'])

    folder_queue.put([file_location, offline_file_location])
