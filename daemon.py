# !/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Filename: daemon.py
# Project: yscheduler
# Author: Brian Cherinka
# Created: Wednesday, 7th April 2021 10:06:24 pm
# License: BSD 3-clause "New" or "Revised" License
# Copyright (c) 2021 Brian Cherinka
# Last Modified: Wednesday, 7th April 2021 10:06:24 pm
# Modified By: Brian Cherinka


from __future__ import print_function, division, absolute_import

import os
import sys
import time
import sched, time
import schedule

from scheduler import run_schedule, logger
from daemonocle.cli import cli



def cb_shutdown(message, code):
    """ daemonocle shutdown code """
    logger.info('Daemon is stopping')
    logger.debug(message)


def test():
    logger.info('test')

def run_set():
    for user in ['Brian', 'Lizzie']:
        bd, bt = run_schedule(location='Waverly', user=user, headless=True)
        bd, bt = run_schedule(location='Towson', user=user, headless=True)


# set the schedule
schedule.every().hour.do(run_set)


@cli(name='yscheduler', shutdown_callback=cb_shutdown, pid_file=os.path.join(os.path.dirname(__file__), 'yscheduler.pid'), detach=True)
def daemon():
    logger.info('Daemon is starting')

    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == '__main__':
    daemon()
