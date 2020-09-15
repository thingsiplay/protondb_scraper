#!/usr/bin/python3

""" Scrape data from ProtonDB webpage and save results to json file.

    All pages starting from
    https://www.protondb.com/explore?page=0&sort=wilsonRating
    with increasing 'page=0' number will be scraped.  Information is
    extracted into a new database file in json format.  It will open
    a browser and scroll down while reading game data, page by page.
    See commandline options to customize settings.

    Requirements
    ------------
    Linux
        Only Ubuntu 18.04 operating systems are tested so far.
    Python
        https://www.python.org/downloads/
    Selenium
        https://pypi.org/project/selenium/
    geckodriver
        https://github.com/mozilla/geckodriver/releases

    Usage
    -----
        pdbscraper.py
        pdbscraper.py -h
        pdbscraper.py --test
        pdbscraper.py -o file.json -m 10 -w 0.2 -z -p
"""

import argparse
import os.path
import sys
import json
import datetime
from time import sleep

from selenium import webdriver
from selenium.webdriver import Firefox
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException


def get_arguments():
    """ Analyzes the args of program and converts it to a dictionary.

        Returns
        -------
        dict
            Contains key/value pairs of arguments.  Any unset argument
            from commandline has the None-value.
    """
    parser = argparse.ArgumentParser(
        prog='pdbscraper',
        usage='%(prog)s [OPTION]',
        description='Scrape data from ProtonDB webpage and save results '
                    'to json file.',
        epilog='Needs: Python 3.6, selenium 3.141, geckodriver 0.27')
    parser.add_argument(
        '--version', '-v', action='version', version='%(prog)s 2.0')
    parser.add_argument(
        '--config', '-c', metavar='FILE', required=False, type=str,
        help='Read additional settings file in json format, displayed '
             'with --printconfig.')
    parser.add_argument(
        '--output', '-o', metavar='FILE', required=False, type=str,
        help='Name of the database file to create.  Defaults to: '
             '"protondb-{sort}-{date}.json" in current working directory.')
    parser.add_argument(
        '--driver', metavar='FILE', required=False, type=str,
        help='Path to installed Firefox webdriver for selenium.  Defaults to: '
             '/usr/local/bin/geckodriver')
    parser.add_argument(
        '--optimize', '-z', action='store_true', required=False,
        help='Use optimized Firefox driver settings with a new profile. '
             'for faster loading.  Includes preventing images from loading '
             'and other stuff.  Default is disabled.')
    parser.add_argument(
        '--source', '-u', metavar='URL', required=False, type=str,
        help='Starting page to scrape.  Additional url key and values are '
             'added.  Normally this does not need to be changed, but can be '
             'required in the future.  Defaults to: '
             'https://www.protondb.com/explore')
    parser.add_argument(
        '--sort', '-s', metavar='TYPE', required=False, type=str,
        choices=['recentlyImproved', 'wilsonRating', 'playerCount',
                 'userScore', 'mostBorked', 'fixWanted'],
        help='The sorting of games by ProtonDB webpage.  Possible options: '
             'recentlyImproved, wilsonRating, playerCount, userScore, '
             'mostBorked, fixWanted.  Defaults to: wilsonRating')
    parser.add_argument(
        '--native', '-n', action='store_true', required=False,
        help='includeNative Linux games when building the page lists for '
             'processing.  Default is to not include.')
    parser.add_argument(
        '--maxpages', '-m', metavar='NUM', required=False, type=int,
        help='Number of pages to process and scrape.  Each page has 50 game '
             'entries (at cell mode).  Defaults to: 20')
    parser.add_argument(
        '--initpage', '-i', metavar='NUM', required=False, type=int,
        help='Starting page number to scrape.  Defaults to 0, which is the '
             'first page number.')
    parser.add_argument(
        '--pagedown', '-d', metavar='NUM', required=False, type=int,
        help='Clicks pagedown key a few times to reach end of page, so every '
             'game is covered correctly.  This may need adjustments for '
             'different desktop resolutions.  Defaults to: 10')
    parser.add_argument(
        '--wait', '-w', metavar='SECONDS', required=False, type=float,
        help='Seconds to wait before start of processing the page and after '
             'each pagedown.  Sometimes the program needs waiting until next '
             'operation is ready.  Time is in float format.  Defaults to: 0.4')
    parser.add_argument(
        '--printconfig', '-p', action='store_true', required=False,
        help='Prints the current settings to terminal in json format.  This '
             'can also be used to write settings file by redirecting through '
             'a pipe into a file.  Default is not to print.')
    parser.add_argument(
        '--test', action='store_true', required=False,
        help='Preset to overwrite a few settings for testing reasons. '
             'Disables optimize settings, set wait to 1, maxpages to 2 '
             'pagedown to 10, prints configuration and ignores output file. '
             'High priority.')
    parser.add_argument(
        '--fast', action='store_true', required=False,
        help='Preset to overwrite a few settings for faster operating. '
             'Forces optimize settings and sets wait to 0.1.  Also a few '
             'extra checks are skipped too.  Highest priority.')
    # Convert to dict.
    parser_dict = vars(parser.parse_args())
    # Special handling of store_true parameters.  Convert false values to None.
    # Later in program None valued arguments will be ignored.  This way they do
    # not interfere or override with defaults and config file.
    if not parser_dict['native']:
        parser_dict['native'] = None
    if not parser_dict['printconfig']:
        parser_dict['printconfig'] = None
    if not parser_dict['optimize']:
        parser_dict['optimize'] = None
    if not parser_dict['test']:
        parser_dict['test'] = None
    if not parser_dict['fast']:
        parser_dict['fast'] = None
    return parser_dict


def get_settings(arguments_settings):
    """ Combines settings from various places and creates a dict.

        There are multiple stages with priorities to overwrite.
            0. First it creates default values as a base starting point.
            1. Configuration file set from commandline is loaded up.
               It uses all found key and values to overwrite the base
               settings.
            2. Then settings fetched from commandline arguments are used
               to overwrite all current settings again, over base and
               config.
            3. In the last stage any presets will be used to overwrite
               a few settings with a fixed set of values.

        Parameters
        ----------
        arguments_settings : dict
            The commandline arguments to overwrite settings in stage 2.

        Returns
        -------
        dict
            Key/value pair with current settings.
    """
    # Internal default values. (priority low)
    settings = {}
    settings['config'] = None
    settings['output'] = None
    settings['driver'] = '/usr/local/bin/geckodriver'
    settings['optimize'] = False
    settings['source'] = 'https://www.protondb.com/explore'
    settings['sort'] = 'wilsonRating'
    settings['native'] = False
    settings['maxpages'] = 20  # 50 games per page
    settings['initpage'] = 0  # 0=first page, 1=second page
    settings['pagedown'] = 10
    settings['wait'] = 0.4
    settings['printconfig'] = False
    settings['test'] = False
    settings['fast'] = False
    # Config file. (priority mid)
    try:
        if arguments_settings['config']:
            with open(arguments_settings['config'], 'r') as file:
                config_settings = file.read()
                config_settings = json.loads(config_settings)
                settings.update(config_settings)
    except FileNotFoundError:
        print('Config file not found:', settings['config'])
    # Users's program arguments. (priority high)
    for key, value in arguments_settings.items():
        if value is not None:
            settings[key] = value
    # Presets with special behaviour and to force settings. (priority highest)
    if settings['test']:
        settings['optimize'] = False
        settings['maxpages'] = 2
        settings['initpage'] = 0
        settings['pagedown'] = 10
        settings['wait'] = 1
        settings['output'] = None
        settings['printconfig'] = True
    # Build up default output filename.
    elif not settings['output']:
        s_sort = settings['sort']
        d_today = str(datetime.datetime.utcnow().date())
        settings['output'] = f'protondb-{s_sort}-{d_today}.json'
    if settings['fast']:
        settings['optimize'] = True
        settings['wait'] = 0.1
    return settings


# https://stackoverflow.com/questions/7157994/do-not-want-the-images-to-load-and-css-to-render-on-firefox-in-selenium-webdrive
# by Eray Erdin
def get_firefox_profile(optimize=True):
    """ Creates a Firefox profile for use with selenium webdriver.

        Parameters
        ----------
        optimize : bool
            If True, then additional preference configurations will be
            set, with high speed optimizations in mind.  Most notably
            images will not be loaded.

        Returns
        -------
        webdriver.FirefoxProfile
            Use this as an argument when calling the webdriver:

                selenium.webdriver.Firefox(firefox_profile=profile)
    """
    profile = webdriver.FirefoxProfile()
    if optimize:
        profile.set_preference('network.http.pipelining', True)
        profile.set_preference('network.http.proxy.pipelining', True)
        profile.set_preference('network.http.pipelining.maxrequests', 8)
        profile.set_preference('content.notify.interval', 500000)
        profile.set_preference('content.notify.ontimer', True)
        profile.set_preference('content.switch.threshold', 250000)
        # Increase the cache capacity.
        profile.set_preference('browser.cache.memory.capacity', 65536)
        profile.set_preference('browser.startup.homepage', 'about:blank')
        # Disable reader, we won't need that.
        profile.set_preference('reader.parse-on-load.enabled', False)
        # Duck pocket too!
        profile.set_preference('browser.pocket.enabled', False)
        profile.set_preference('loop.enabled', False)
        # Text on Toolbar instead of icons
        profile.set_preference('browser.chrome.toolbar_style', 1)
        # Don't show thumbnails on not loaded images.
        profile.set_preference('browser.display.show_image_placeholders', False)
        # Don't show document colors.
        profile.set_preference('browser.display.use_document_colors', False)
        # Don't load document fonts.
        profile.set_preference('browser.display.use_document_fonts', 0)
        # Use system colors.
        profile.set_preference('browser.display.use_system_colors', True)
        # Autofill on forms disabled.
        profile.set_preference('browser.formfill.enable', False)
        # Delete temprorary files.
        profile.set_preference('browser.helperApps.deleteTempFileOnExit', True)
        profile.set_preference('browser.shell.checkDefaultBrowser', False)
        profile.set_preference('browser.startup.homepage', 'about:blank')
        # blank
        profile.set_preference('browser.startup.page', 0)
        # Disable tabs, We won't need that.
        profile.set_preference('browser.tabs.forceHide', True)
        # Disable autofill on URL bar.
        profile.set_preference('browser.urlbar.autoFill', False)
        # Disable autocomplete on URL bar.
        profile.set_preference('browser.urlbar.autocomplete.enabled', False)
        # Disable list of URLs when typing on URL bar.
        profile.set_preference('browser.urlbar.showPopup', False)
        # Disable search bar.
        profile.set_preference('browser.urlbar.showSearch', False)
        # Addon update disabled
        profile.set_preference('extensions.checkCompatibility', False)
        profile.set_preference('extensions.checkUpdateSecurity', False)
        profile.set_preference('extensions.update.autoUpdateEnabled', False)
        profile.set_preference('extensions.update.enabled', False)
        profile.set_preference('general.startup.browser', False)
        profile.set_preference('plugin.default_plugin_disabled', False)
        # Image load disabled again
        profile.set_preference('permissions.default.image', 2)
    return profile


def create_database(settings):
    """ Opens webdriver and analyzes each page to scrape the data.

        This is the meat of the application.  It will open a Firefox
        browser with seleniums webdriver.  Then the key page down is send
        a few times, to reach the end of the document, so the DOM will be
        created fully.  Then all game container are analyzed to read out
        the desired information about the games.

        Parameters
        ----------
        settings : dict
            The application settings created previously.

        Returns
        -------
        list
            Each element in the list is a dict of game data.
    """

    def get_game_data(game_container):
        """ Extract game specific data for each container. """
        # title and appid
        css = 'span[class^="GameSlice__Title"]'
        e_title = game_container.find_element(By.CSS_SELECTOR, css)
        game_title = e_title.find_element(By.CSS_SELECTOR, 'a').text
        appid = e_title.find_element(By.CSS_SELECTOR, 'a')
        appid = os.path.basename(appid.get_attribute('href'))
        # rating
        css = 'span[class^="Summary__GrowingSpan"]'
        e_summary = game_container.find_element(By.CSS_SELECTOR, css)
        rating = e_summary.text
        # reports
        css = 'div[class*="GameSlice__Expander-"]'
        e_expander = game_container.find_element(By.CSS_SELECTOR, css)
        reports_count = e_expander.find_element_by_tag_name('span').text
        # Wedding of data.
        game_data = {}
        game_data['appid'] = appid
        game_data['title'] = game_title
        game_data['rating'] = rating
        game_data['reports'] = reports_count
        return game_data

    def page_select_layout_cell(driver):
        """ Finds and clicks layout switcher to 'cell'-mode. """
        # Make sure cell is selected, not card.
        body = driver.find_element_by_tag_name('body')
        # Upper right layout buttons.
        css = 'div[class*="Explore__EndJustified"]'
        layout = body.find_element(By.CSS_SELECTOR, css)
        # M3=cell, M4=card
        css = 'path[d^="M3 "]'
        svg = layout.find_element(By.CSS_SELECTOR, css)
        svg.click()
        sleep(settings['wait'])
        return svg

    def page_scroll_down(driver, settings):
        """ Sends page down key periodically to reach bottom. """
        # Scroll down, so additional DOM data is loaded up into browser.
        html = driver.find_element(By.CSS_SELECTOR, 'html')
        for _ in range(settings['pagedown']):
            html.send_keys(Keys.PAGE_DOWN)
            sleep(settings['wait'])
        return html

    def page_load(url):
        """ Loads driver from url and waits until its ready. """
        driver.get(url)
        sleep(1)
        if not settings['fast']:
            sleep(settings['wait'])
        # Make sure to continue only, if page is loaded up.
        css = 'div[class*="GameLayout__Container"]'
        for _ in range(5):
            sleep(settings['wait'])
            try:
                if driver.find_element(By.CSS_SELECTOR, css):
                    break
            except NoSuchElementException:
                pass
        return driver

    # database will be a list of game entries, filled up by analyzing pages.
    database = []
    # Setup and start the driver process as a whole.
    webdriver_options = Options()
    webdriver_options.page_load_strategy = 'eager'
    with Firefox(executable_path=settings['driver'],
                 options=webdriver_options,
                 firefox_profile=get_firefox_profile(settings['optimize'])
                 ) as driver:
        # Analyze each page with the current driver.
        for url in build_url_list(settings):
            # Load page and scroll down slowly, to ensure all DOM data is
            # loaded up into browser.
            driver = page_load(url)
            if not settings['fast']:
                driver.implicitly_wait(1)  # !Do not mix with WebDriverWait!
                page_select_layout_cell(driver)
            html = page_scroll_down(driver, settings)
            # Analyze every game container.  Layout needs to be in type="cell"
            # mode, not in type="card".  Currently this is the default.
            css = 'div[class*="GameCell__Container-"]'
            for game_container in html.find_elements(By.CSS_SELECTOR, css):
                database.append(get_game_data(game_container))
    return database


def build_url_list(settings):
    """ Build up the correct url format for all pages.

    Parameters
    ----------
    settings : dict
        The application settings created previously.

    Returns
    -------
    list
        Each element in the list is a string of urls to scrape.
    """
    s_source = settings['source']
    s_sort = settings['sort']
    s_native = settings['native']
    options = f'&sort={s_sort}'
    if s_native:
        options += '&selectedFilters=includeNative'
    url_list = []
    init = settings['initpage']
    for index in range(settings['maxpages']):
        url_list.append(s_source + '?page=' + str(index + init) + options)
    return url_list


def add_header_data(database, settings, addendum=None):
    """ Adds additional meta data and settings to the database.

    Parameters
    ----------
    database : list
        Previously created database with all game entries.
    settings : dict
        The application settings created previously.
    addendum : dict or None
        As a dict it will be added to the meta data, before settings
        take place.

    Returns
    -------
    list
        Same list of dict with game entries, but with added header as
        first entry.
    """
    meta = {}
    meta['creator'] = 'https://github.com/thingsiplay/protondb_scraper'
    meta['timestamp'] = str(datetime.datetime.utcnow())
    if addendum:
        meta.update(addendum)
    meta.update(settings)
    database.insert(0, meta)
    return database


def write_database(database, settings):
    """ Convert the database into json-string and write to file.

    Parameters
    ----------
    database : list
        Previously created database with all game entries.
    settings : dict
        The application settings created previously.

    Returns
    -------
    str or None
        Full path to the created file or None otherwise.
    """
    file_path = None
    try:
        with open(settings['output'], 'w') as file:
            file.write(get_jsonstring(database))
            file_path = os.path.abspath(file.name)
    except IsADirectoryError:
        print('Cannot write output file as:', settings['output'])
    except PermissionError:
        print('No permission to write output file to:', settings['output'])
    return file_path


def get_jsonstring(settings):
    """ Convert dict to json formatted string. """
    return json.dumps(settings, sort_keys=False, indent=4)


def main():
    """ Calls all important functions and displays how many games are
        processd.  Also the full path to the database file is shown too.
    """
    # Preparation.
    arguments = get_arguments()
    settings = get_settings(arguments)
    # After creating and displaying the settings, it shouldn't be modified.
    if settings['printconfig']:
        print(get_jsonstring(settings))
    # Build up database.
    database = create_database(settings)
    database = add_header_data(database, settings)
    # Save database as json file, if not in test mode.
    if not settings['test']:
        database_path = write_database(database, settings)
    else:
        database_path = ''
    # Final conclusion.  Note -1 for meta entry.
    print(len(database) - 1, 'games processed in:', database_path)
    return 0


if __name__ == '__main__':
    # Check exit code in Linux shell with (0=success): echo $?
    sys.exit(main())
