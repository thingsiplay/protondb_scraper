#!/usr/bin/python3

""" Scrapes ProtonDB explore page and saves information to json file. """

"""
Copyright (C) 2020 Tuncay D

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
"Software"), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE X CONSORTIUM BE LIABLE FOR ANY
CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

Except as contained in this notice, the name(s) of the above copyright
holders shall not be used in advertising or otherwise to promote the sale,
use or other dealings in this Software without prior written
authorization.
"""

import json
import re
import os.path
import time
from datetime import date

from selenium.webdriver import Firefox
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options

# str
# Base url to start parsing.  Usually shouldn't be changed.
# Default = 'https://www.protondb.com/explore'
settings_url = 'https://www.protondb.com/explore'

# int
# How many pages should be parsed.  50 titles per page are listed.
# Default=20
settings_page_count = 20

# How many times pagedown should be pressed, so all data is loaded up?
# int
# Default = 10
settins_pagedown_count = 10

# Sorting algorithm of ProtonDB.
# str
# sort='recentlyImproved', 'wilsonRating', 'playerCount', 'userScore',
# 'mostBorked', 'fixWanted'
# Default = 'wilsonRating'
settings_sort = 'wilsonRating'

# Include Linux native games: True, False
# bool
# Default = False
settings_native = False

# Wait seconds before processing after first page load.
# int
# Default = 1
wait_driver = 1

# Wait seconds before each pagedown event.
# int
# Default = 1
wait_pagedown = 1

# str
# Output filename of json file.
# Default = 'protondb'
settings_output_file = f'protondb-{settings_sort}-{str(date.today())}.json'

# Build up options.
settings_options = f'&sort={settings_sort}'
if settings_native:
    settings_options += '&selectedFilters=includeNative'

# Build up urls for all pages to scrape.
settings_url_list = []
for index in range(settings_page_count):
    settings_url_list.append(settings_url + '?page=' + str(index) + settings_options)

# Additional options for webdriver.
webdriver_options = Options()
webdriver_options.page_load_strategy = 'eager'

all_data = []
total_games_processed = 0
with Firefox(executable_path='/usr/local/bin/geckodriver',
             options=webdriver_options) as driver:
    for url in settings_url_list:
        # Load page.
        driver.get(url)
        time.sleep(wait_driver)

        # Scroll down, so additional data is loaded up into browser.
        for _ in range(settins_pagedown_count):
            driver.find_element(By.CSS_SELECTOR, '*').send_keys(Keys.PAGE_DOWN)
            time.sleep(wait_pagedown)
        body = driver.find_element_by_tag_name('body')

        # Analyze and parse the html.
        for game_container in body.find_elements(By.CSS_SELECTOR, 'div[class*="GameCell__Container-"]'):
            element_title = game_container.find_element(By.CSS_SELECTOR, 'span[class^="GameSlice__Title"]')
            element_summary = game_container.find_element(By.CSS_SELECTOR, 'span[class^="Summary__GrowingSpan"]')
            element_expander = game_container.find_element(By.CSS_SELECTOR, 'div[class*="GameSlice__Expander-"]')

            steam_appid = os.path.basename(element_title.find_element(By.CSS_SELECTOR, 'a').get_attribute('href'))
            protondb_rating = element_summary.text
            game_title = element_title.find_element(By.CSS_SELECTOR, 'a').text
            protondb_reports_count = element_expander.find_element_by_tag_name('span').text

            game_data = {}
            game_data['steam_appid'] = steam_appid
            game_data['game_title'] = game_title
            game_data['protondb_rating'] = protondb_rating
            game_data['protondb_reports_count'] = protondb_reports_count
            game_data['protondb_link'] = f'https://www.protondb.com/app/{steam_appid}'
            game_data['steam_link'] = f'https://store.steampowered.com/app/{steam_appid}'
            all_data.append(game_data)
driver.quit()

meta_data = {}
meta_data['creator'] = 'protondb_scraper.py'
meta_data['source'] = settings_url
meta_data['date_created'] = str(date.today())

all_data.insert(0, meta_data)

with open(settings_output_file, 'w') as file:
    file.write(json.dumps(all_data, sort_keys=False, indent=4))
