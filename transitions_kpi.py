#!/usr/bin/env python
"""
Scrapes and parses information from JIRA's transition states.

Runs the JIRA spider, then parses the output states.json
file to obtain KPI information.

See https://openedx.atlassian.net/wiki/display/OPEN/Tracking+edX+Commitment+To+OSPRs
"""
from __future__ import print_function
from subprocess import check_call

import argparse
import datetime
import json
import sys


EDX_ENGINEERING_STATES = [
    'Needs Triage',
    'Product Review',
    'Community Manager Review',
    'Awaiting Prioritization',
    'Engineering Review',
]


def scrape_jira():
    """
    Re-scrapes jira into states.json
    """
    # Delete content of states.json before re-writing
    with open("states.json", "w"):
        pass

    check_call("scrapy runspider jiraspider.py -o states.json".split(" "))


def engineering_time_spent(state_dict):
    """
    Given a ticket's state dictionary, returns how much engineering time was spent on it.
    Engineering states determined by EDX_ENGINEERING_STATES list.
    """
    # Measurement 1: Average Time Spent by edX Engineering
    # This measurement will sum up the amount of time it takes the engineering team to process OSPR work.
    # AverageTime = sum(amount of time a ticket spends in edX states) / count(all tickets)
    # This will be a rolling average over all tickets currently open, or closed in the past X days.
    # In the initial rollout of this measurement, we'll track for X=14, 30, and 60 days. After we have a few months'
    # worth of data, we can assess what historical interval(s) gives us the most useful, actionable data.
    # This is a measurement across all of engineering.  We are not proposing to measure teams individually.
    total_time = datetime.timedelta(0)
    for state, tdelta in state_dict.iteritems():
        if state in EDX_ENGINEERING_STATES:
            total_time += tdelta

    return total_time


def sanitize_ticket_states(state_dict):
    """
    Converts timedelta strings back into timedeltas.
    These were explicitly serialized as '{0.days}:{0.seconds}'.format(tdelta)
    """
    result = {}
    keys = ['days', 'seconds']
    for state, tdelta in state_dict.iteritems():
        tdelta = [int(x) for x in tdelta.split(':')]
        tdict = {key: value for key, value in zip(keys, tdelta)}
        result[state] = datetime.timedelta(**tdict)
    return result


def parse_jira_info(debug=False, pretty=False):
    """
    Read in and parse states.json
    """
    with open("states.json") as state_file:
        # tickets is a list composed of state dictionaries for each ospr ticket.
        # Keys are: 'issue' -> string, 'states' -> dict, 'labels' -> list,
        # Optional keys are: 'resolution' -> list, 'debug' -> string, 'error' -> string
        tickets = json.load(state_file)

    eng_time_spent = datetime.timedelta(0)
    num_tickets = 0
    # TODO need to get when tickets were merged!
    for ticket in tickets:
        if ticket.get('error', False):
            print("Error in ticket {}: {}".format(ticket['issue'], ticket['error']))
        if debug and ticket.get('debug', False):
            print("Debug: ticket {}: {}".format(ticket['issue'], ticket['debug']))

        if ticket.get('states', False):
            # Sanitize ticket state dict (need to convert time strings to timedeltas)
            ticket['states'] = sanitize_ticket_states(ticket['states'])
            # Calculate total time spent by engineering team on this ticket
            eng_time_spent = engineering_time_spent(ticket['states'])
            num_tickets += 1
        elif debug or pretty:
            print("No states yet for newly-opened ticket {}".format(ticket['issue']))

    # Calculate average engineering time spent
    avg_time = eng_time_spent / num_tickets
    # Pretty print the average time
    days = avg_time.days
    hours, remainder = divmod(avg_time.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    print('\nAverage time spent in engineering review:')
    if pretty:
         print('\t {} days, {} hours, {} minutes, {} seconds'.format(days, hours, minutes, seconds))
    else:
        print('\t {}:{}:{}:{}'.format(days, hours, minutes, seconds))


def main(argv):
    parser = argparse.ArgumentParser(description="Summarize JIRA info.")
    parser.add_argument(
        "--no-scrape", action="store_true",
        help="Don't re-run the scraper, just read the current states.json file"
    )
    parser.add_argument(
        "--debug", action="store_true",
        help="Show debugging messages"
    )
    parser.add_argument(
        "--pretty", action="store_true",
        help="Pretty print output"
    )
    args = parser.parse_args(argv[1:])

    if not args.no_scrape:
        scrape_jira()

    parse_jira_info(args.debug, args.pretty)

if __name__ == "__main__":
    sys.exit(main(sys.argv))
