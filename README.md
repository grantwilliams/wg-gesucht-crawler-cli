# WG-Gesucht-Crawler
Crawls the WG-Gesucht site for new apartment listings and send a message to the poster,
based off your saved filters and saved text.

Uses Tkinter for the GUI and Requests + BeautifulSoup to crawl the site.

## Use
Install the Python packages in the 'requirements.txt' and run then 'main.py'

Enter your email address and password that you use for wg-gesucht.de (will be saved
locally so you don't have to type it every time you run it)
Make sure you have 1 or more filters created and that you have saved a template text
on your wg-gesucht account.

Then just leave it running in the background, it will check for new apartment listings
every 5 minutes, and message any new ones that appear.

It will also create a folder with the apartment ads that you can view offline, in case
the poster removes their ad before you get a chance to look at it, which can happen
if the poster receives a lot a messages in a short amount of time.

**Getting Caught with reCAPTCHA**
I've made the crawler sleep for 5-8 seconds between each request to try and avoid their reCAPTCHA,
but if the crawler does get caught, you can sign into your wg-gesucht account manually through the
browser and solve the reCAPTCHA, then start the crawler again.
If it continues to happen, you can also increase the sleep time in the 'get_page' function in
'wg_gesucht.py'