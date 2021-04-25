# !/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Filename: scheduler.py
# Project: yscheduler
# Author: Brian Cherinka
# Created: Saturday, 3rd April 2021 10:21:36 am
# License: BSD 3-clause "New" or "Revised" License
# Copyright (c) 2021 Brian Cherinka
# Last Modified: Saturday, 3rd April 2021 10:21:36 am
# Modified By: Brian Cherinka


from __future__ import print_function, division, absolute_import

import logging
import json
import click
import time
import datetime
from logging.handlers import TimedRotatingFileHandler
from selenium import webdriver
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support import expected_conditions as EC

# create logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
fh = TimedRotatingFileHandler('yscheduler.log', when='midnight')
fh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s: %(message)s'))
ch = logging.StreamHandler()
ch.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
logger.addHandler(ch)
logger.addHandler(fh)


# set locations
locations = {"Waverly": '506', "Towson": '502', 'Druid Hill': '499', 'Parkville': '503'}

# get preferences
with open('prefs.json', 'r') as f:
    prefs = json.loads(f.read())


def get_driver(location='Waverly', headless=False):
    chrome_options = Options()
    chrome_options.headless = headless
    driver = webdriver.Chrome(options=chrome_options)

    loc = locations.get(location, None)
    if not loc:
        logger.error(f'Location {location} not found in list of locations.')
        return None

    logger.info(f'Setting location: {location}')

    url = f"https://app.appointmentking.com/scheduler_self_service.php?domid={loc}"
    driver.get(url)

    return driver


def submit_info(driver, user):

    logger.info(f'Submitting info for user: {user.get("first_name")}')

    # fill out user info
    elem = driver.find_element_by_name("first_name")
    elem.clear()
    elem.send_keys(user.get('first_name'))
    elem = driver.find_element_by_name("last_name")
    elem.clear()
    elem.send_keys(user.get('last_name'))
    elem = driver.find_element_by_name("dob_year")
    elem.clear()
    elem.send_keys(user.get('dob_year'))
    elem = driver.find_element_by_name("dob_day")
    elem.clear()
    elem.send_keys(user.get('dob_day'))
    elem = driver.find_element_by_name("email")
    elem.clear()
    elem.send_keys(user.get('email'))
    elem = driver.find_element_by_name("phone")
    elem.clear()
    elem.send_keys(user.get('phone'))

    select = Select(driver.find_element_by_id('dob_month'))
    month_idx = int(user.get('dob_month'))
    select.select_by_index(month_idx)

    elem = driver.find_element_by_name("submitbtn_login")
    elem.click()

    # select relevant Y facility
    select = Select(driver.find_element_by_id('trainer-filter'))
    select.select_by_index(1)

    # update and get availabilities
    elem = driver.find_element_by_class_name("update-button")
    elem.click()


def get_preferred_times(date):
    defaults = ['4:00 PM', '5:00 PM', '6:00 PM']
    # use the current date or an input date string
    if not date:
        date = datetime.datetime.now()
    else:
        date = datetime.datetime.strptime(date, '%A, %b %d, %Y')

    # return weekend or weekday preferred times
    if date.date().weekday() >= 5:
        return prefs.get('preferred_weekend_times', defaults)
    else:
        return prefs.get('preferred_weekday_times', defaults)


def check_results(driver, test=None):
    # find relevant dates/times
    elem = driver.find_element_by_id("results")
    res = elem.find_elements_by_class_name('get-list-result-row')
    if not res:
        logger.warning('No available dates or times')
        driver.close()

    available_dates = [r.find_element_by_class_name('date-legend').text for r in res]
    logger.info(f"Available Dates: {available_dates}")

    # don't actually book yet
    test = test

    booked_date = None
    booked_time = None
    for r in res:
        date = r.find_element_by_class_name('date-legend').text
        preferred_times = get_preferred_times(date)
        logger.info(f'\nLooking for times on {date}')
        logger.info(f'\nPreferred times: {preferred_times}')
        select = Select(r.find_element_by_class_name('time'))
        times = [o.text for o in select.options]
        if not times:
            logger.warning('No times available!')
            continue

        logger.info(f'Available times: {times}')
        for pref in preferred_times:
            try:
                select.select_by_visible_text(pref)
            except NoSuchElementException as err:
                logger.info(f'Preferred time {pref} is not available.')
                continue
            else:
                logger.info(f'Selected time {pref}.  Booking it!')
                book_btn = r.find_element_by_class_name("book-btn")
                booked_date = date
                booked_time = pref
                if not test:
                    book_btn.click()

                    #WebDriverWait(driver, 3).until(EC.alert_is_present())

                    # clear the alerts
                    try:
                        obj = driver.switch_to.alert
                        obj.accept()
                    except EC.NoAlertPresentException:
                        pass

                    try:
                        obj = driver.switch_to.alert
                        obj.accept()
                    except EC.NoAlertPresentException:
                        pass
                break
    return booked_date, booked_time

def get_booked_appointments(driver):

    # get booked appointments
    elem = driver.find_element_by_class_name('bookedTab')
    elem.click()
    time.sleep(1)
    elem = driver.find_element_by_id('bookedContainer')
    booked = elem.find_elements_by_class_name('bookedAppt')

    if not booked:
        logger.warning('No bookings found!')
        return None

    appts = []
    for book in booked:
        bdate = book.find_element_by_class_name('booked-appt-date').text
        btime = book.find_element_by_class_name('booked-appt-time').text
        appts.append((bdate, btime))
    logger.info(f'Booked appts: {appts}')
    return appts


def get_user(user=None, first=None, last=None, dob=None, email=None, phone=None):
    with open('users.json', 'r') as f:
        users = json.loads(f.read())

    assert user or (first and last and dob and email and phone), 'must specify some user info'

    if user:
        assert user in users, f'user {user} not found in users.json'
        return users.get(user, None)

    month, day, year = dob.split('/')
    if len(year) == 2:
        year = f'19{year}'

    return {'first_name': first, 'last_name': last, 'dob_year': year,
            'dob_day': day, 'dob_month': month, 'email': email, 'phone': phone}


def run_schedule(location=None, headless=None, user=None, first=None, last=None,
                 dob=None, email=None, phone=None, test=None):
    """ run the y scheduler """

    # skip times 8 pm and 5 am
    now = datetime.datetime.now()
    if now.hour >= 20 or now.hour <= 5:
        return

    driver = get_driver(location=location, headless=headless)
    user = get_user(user=user, first=first, last=last, dob=dob, email=email, phone=phone)
    submit_info(driver, user)
    time.sleep(1)
    booked_date, booked_time = check_results(driver, test=test)
    logger.info(f'Booked for : {booked_date}, {booked_time}')
    return booked_date, booked_time


def check_booked(location=None, headless=None, user=None, first=None, last=None,
                 dob=None, email=None, phone=None):

    driver = get_driver(location=location, headless=headless)
    user = get_user(user=user, first=first, last=last, dob=dob, email=email, phone=phone)
    submit_info(driver, user)
    time.sleep(1)
    booking = get_booked_appointments(driver)
    logger.info(f'Found booking for: {booking}')
    return booking

@click.group('yscheduler')
def cli():
    pass

@cli.command('book', short_help='Schedule a booking at the Y swim lane')
@click.option('-l', '--location', default='Waverly', help='Y location to schedule')
@click.option('-d', '--headless', default=False, help='Run in headless browser mode', is_flag=True)
@click.option('-u', '--user', default='Brian', help='user name from users.json file to lookup')
@click.option('-f', '--first', default=False, help='First name of user')
@click.option('-s', '--last', default=False, help='Last name of user')
@click.option('-b', '--dob', default=False, help='date of birth of user, as x/x/xx')
@click.option('-e', '--email', default=False, help='email of user')
@click.option('-p', '--phone', default=False, help='phone number of user, as xxx-xxx-xxxx')
@click.option('-t', '--test', default=False, help='run a test without actually booking', is_flag=True)
def yschedule(location, headless, user, first, last, dob, email, phone, test):
    run_schedule(location=location, headless=headless, user=user, first=first, last=last,
                 dob=dob, email=email, phone=phone, test=test)


@cli.command('check', short_help='Check for existing bookings of a Y swim lane')
@click.option('-l', '--location', default='Waverly', help='Y location to schedule')
@click.option('-d', '--headless', default=False, help='Run in headless browser mode', is_flag=True)
@click.option('-u', '--user', default='Brian', help='user name from users.json file to lookup')
@click.option('-f', '--first', default=False, help='First name of user')
@click.option('-s', '--last', default=False, help='Last name of user')
@click.option('-b', '--dob', default=False, help='date of birth of user, as x/x/xx')
@click.option('-e', '--email', default=False, help='email of user')
@click.option('-p', '--phone', default=False, help='phone number of user, as xxx-xxx-xxxx')
def yschedule(location, headless, user, first, last, dob, email, phone):
    check_booked(location=location, headless=headless, user=user, first=first, last=last,
                 dob=dob, email=email, phone=phone)


if __name__ == '__main__':
    cli()


