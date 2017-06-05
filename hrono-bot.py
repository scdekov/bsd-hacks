#!/usr/bin/env python
import re
import os
from datetime import date, timedelta
import requests
from subprocess import check_output, call
from collections import defaultdict

import credentials


HRONO_LOGIN_URL = 'http://vm-expert2/Account/LogOn'
HRONO_DALY_REPORT_URL = 'http://vm-expert2/Data/SaveAttendance/95?dayOfMonth={date}&att=1&hours=8'


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


def get_submitted_work(username, from_date='yesterday'):
    submitted_results = check_output([get_p4_command(username, from_date=from_date)], shell=True)

    work_done = defaultdict(list)
    crr_date = ''

    for line in transform_to_result_lines(submitted_results):
        new_date = re.search(r'\d+/\d+/\d+', line)
        if line.startswith('Change') and new_date and new_date.group(0) != crr_date:
            crr_date = new_date.group(0)

        if not line.startswith('Change'):
            work_done[crr_date].append(line)

    return work_done


def get_current_work(username):
    pending_results = check_output([get_p4_command(username, cl_type='pending', from_date='7 days ago')], shell=True)

    current_work = defaultdict(list)
    for line in transform_to_result_lines(pending_results):
        if not line.startswith('Change'):
            current_work['CURRENTLY WORKING ON:'].append(line)

    return current_work


def write_hrono(username):
    p4_login(credentials.P4_LOGIN, credentials.P4_PASS)

    work = get_submitted_work(username, '5 days ago')
    work.update(get_current_work(username))

    session = requests.Session()
    session.post(HRONO_LOGIN_URL, {'UserName': credentials.HRONO_USER, 'Password': credentials.HRONO_PASS})

    for day_ix in range(0, 5):
        day = date.today() - timedelta(days=day_ix)
        day_report = ''.join(work.get(day.strftime('%Y/%m/%d'), []))

        if not day_ix:
            day_report += '\n'.join(work.get('CURRENTLY WORKING ON:', []))

        if not day_report:
            continue

        response = session.post(HRONO_DALY_REPORT_URL.format(date=day.strftime('%Y-%m-%d')),
                                {'report': day_report})

        if response.status_code != 200:
            print '\nERROR:\n'
            print response.content


write_hrono('sdekov')
