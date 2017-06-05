#!/usr/bin/env python
import re
import os
from datetime import date
import requests
from subprocess import check_output, call
from collections import defaultdict

import credentials


# TODO : move all p4 functions in separate file
def p4_login(username, password):
    # 0 means success and 1 fail
    env_vars = os.environ.copy()
    env_vars['P4USER'] = username

    call('p4 logout', shell=True)
    fail = call('echo "{password}" | p4 login'.format(password=password), shell=True, env=env_vars)
    if fail:
        raise Exception("can't login in perforce")


def transform_to_result_lines(result):
    return filter(bool, map(str.strip, result.split("\n")))


def get_p4_command(username, cl_type='submitted', from_date='yesterday'):
    return "p4 changes -s {cl_type} -l -u {username} @$(date --date='{from_date}' +%Y/%m/%d),@now"\
        .format(username=username, cl_type=cl_type, from_date=from_date)


def report_daily_for(username):
    submitted_results = check_output([get_p4_command(username)], shell=True)
    pending_results = check_output([get_p4_command(username, cl_type='pending', from_date='7 days ago')], shell=True)

    work_done = defaultdict(list)
    crr_date = ''

    for line in transform_to_result_lines(submitted_results):
        new_date = re.search(r'\d+/\d+/\d+', line)
        if line.startswith('Change') and new_date and new_date.group(0) != crr_date:
            crr_date = new_date.group(0)

        if not line.startswith('Change'):
            work_done[crr_date].append(line)

    for line in transform_to_result_lines(pending_results):
        if not line.startswith('Change'):
            work_done['CURRENTLY WORKING ON:'].append(line)

    text_template = '<https://vectorworks.slack.com/team/{user}|@{user}> daily report for {date}'

    report_data = {
        'text': text_template.format(user=username, date=date.today()),
        'color': 'good',
        'fields': [
            {'title': title, 'value': '\n-'.join([''] + value)} for title, value in work_done.iteritems()
        ]
    }

    response = requests.post(credentials.SLACK_HOOK_URL, json=report_data)
    if response.status_code != 200:
        print '\nERROR:\n'
        print response.content


def report_daily(usernames):
    p4_login(credentials.P4_LOGIN, credentials.P4_PASS)
    for username in usernames:
        report_daily_for(username)


report_daily(['sdekov', 'dpaskov', 'gdimitrova', 'kdimitrov'])
