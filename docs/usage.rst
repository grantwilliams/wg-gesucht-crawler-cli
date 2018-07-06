========
Usage
========

To use WG Gesucht Crawler in a project::

    from wg_gesucht.crawler import WgGesuchtCrawler

    crawler = WgGesuchtCrawler(login_info, ad_links_folder, offline_ad_folder, logs_folder)
    crawler.sign_in()
    crawler.search()


Paramaters
----------

*login_info*
""""""""""""
dict: containing wg-gesucht login details

keys: 'email', 'password', 'phone'*(optional)*

*ad_links_folder*
"""""""""""""""""
path to folder where a 'csv' file will be kept with previously applied for ads

*offline_ad_folder*
"""""""""""""""""""
path to folder where offline ads will be saved

*logs_folder*
"""""""""""""
path to folder where the log files will be kept
