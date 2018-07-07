import os
import sys
import json
import atexit
import click
from .create_results_folders import create_folders
from .logger import get_logger
from . import user_details as user
from .crawler import WgGesuchtCrawler


@click.command()
@click.option('--change-email', is_flag=True, help='Change your saved email address')
@click.option('--change-password', is_flag=True, help='Change your saved password')
@click.option('--change-phone', is_flag=True, help='Change your saved phone number')
@click.option('--change-all', is_flag=True, help='Change all you saved user details')
@click.option('--no-save', is_flag=True, help="The script won't save your wg-gesucht login details for future use")
def cli(change_email, change_password, change_phone, change_all, no_save):
    """
    -------------------------Wg-Gesucht crawler-------------------------\n
    Searches wg-gesucht.de for new room listings based off your saved filters.
    Gets your template text from your account and applys to any new ads that match.\n
    Run on a RPi or EC2 instance 24/7 to always be one of the first people to apply
    for a free room.\n
    Logs files in '/home/YOUR_NAME/Documents/WG Finder'
    """
    home_path = 'HOMEPATH' if sys.platform == 'win32' else 'HOME'
    dirname = os.path.join(os.environ[home_path], 'Documents', 'WG Finder')
    wg_ad_links = os.path.join(dirname, "WG Ad Links")
    offline_ad_links = os.path.join(dirname, "Offline Ad Links")
    logs_folder = os.path.join(dirname, 'logs')
    user_folder = os.path.join(dirname, '.user')
    login_info_file = os.path.join(user_folder, '.login_info.json')

    if not os.path.exists(logs_folder):
        os.makedirs(os.path.join(dirname, 'logs'))
    if not os.path.exists(user_folder):
        os.makedirs(os.path.join(dirname, '.user'))

    if not os.path.exists(wg_ad_links) or not os.path.exists(offline_ad_links):
        create_folders(dirname, logs_folder)

    logger = get_logger(__name__, folder=logs_folder)
    @atexit.register
    def exiting():
        logger.warning('Stopped running!')
    login_info = dict()
    if os.path.isfile(login_info_file):
        with open(login_info_file) as file:
            login_info = json.load(file)

    login_info_changed = False
    if change_all or not login_info.get('email', '') or not login_info.get('password', ''):
        login_info = user.change_all()
        login_info_changed = True

    if change_email:
        login_info['email'] = user.change_email()
        login_info_changed = True

    if change_password:
        login_info['password'] = user.change_password()
        login_info_changed = True

    if change_phone:
        login_info['phone'] = user.change_phone()
        login_info_changed = True

    if login_info_changed and not no_save:
        user.save_details(login_info_file, login_info)
        logger.info('User login details saved to file')

    wg_gesucht = WgGesuchtCrawler(login_info, wg_ad_links, offline_ad_links, logs_folder)
    wg_gesucht.sign_in()
    logger.warning('Running until canceled, check info.log for details...')
    wg_gesucht.search()
