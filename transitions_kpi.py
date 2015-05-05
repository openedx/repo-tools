#!/usr/bin/env python
"""
Scrapes and parses information from JIRA's transition states.

Runs the JIRA spider, then parses the output states.json
file to obtain KPI information.

See https://openedx.atlassian.net/wiki/display/OPEN/Tracking+edX+Commitment+To+OSPRs
"""
from __future__ import print_function
from functools import reduce
from subprocess import check_call

import argparse
import datetime
import dateutil.parser
import json
import operator
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

    print("Running scrapy spider over JIRA...")
    check_call("scrapy runspider jiraspider.py -o states.json".split(" "))
    print("-" * 20)


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


def single_state_time_spent(state_dict, state):
    """
    Given a ticket's state dictionary, returns how much time it spent
    in the given `state`.

    Assumes state_dict has the key `state` present.
    """
    # Measurement 2: Average Time Spent in Scrum Team Backlog
    # For the PRs that need to be reviewed by a scrum team, obtain an average of how long a ticket spends in a team backlog.
    # AverageBacklog = sum(amount of time a ticket spends in "Awaiting Prioritization") /
    #                  count(tickets with a non-zero amount of time spent in "Awaiting Prioritization")
    # This will be a rolling average over all tickets currently open, or closed in the past X days.
    # In the initial rollout of this measurement, we'll track for X=14, 30, and 60 days. After we have a few months'
    # worth of data, we can assess what historical interval(s) gives us the most useful, actionable data.
    return state_dict[state]


def sanitize_ticket_states(state_dict):
    """
    Converts timedelta strings back into timedeltas.
    These were explicitly serialized as '{0.days}:{0.seconds}'.format(tdelta)
    """
    result = {}
    for state, tdelta in state_dict.iteritems():
        tdict = {'days': tdelta[0], 'seconds': tdelta[1]}
        result[state] = datetime.timedelta(**tdict)
    return result


def parse_jira_info(debug=False, pretty=False):
    """
    Read in and parse states.json

    Converts json representations of time to datetime objects, then returns a list of
    ticket dictionaries.
    """
    with open("states.json") as state_file:
        # tickets is a list composed of state dictionaries for each ospr ticket.
        # Keys are: 'issue' -> string, 'states' -> dict, 'labels' -> list,
        # Optional keys are: 'resolution' -> list, 'debug' -> string, 'error' -> string
        tickets = json.load(state_file)

    # Go through tickets and sanitize data, report errors, etc
    for ticket in tickets:
        # Report any errors / debug messages
        if ticket.get('error', False):
            print("Error in ticket {}: {}".format(ticket['issue'], ticket['error']))
        if debug and ticket.get('debug', False):
            print("Debug: ticket {}: {}".format(ticket['issue'], ticket['debug']))

        # Deal with "resolved" datetime
        if ticket.get('resolved', False):
            # Turn str(datetime) back into a datetime object
            ticket['resolved'] = dateutil.parser.parse(ticket['resolved'])
        else:
            # Ticket is not yet resolved. Set "resolved" date to right now, so it'll
            # show up in the filter for being resolved within the past X days (hack for cleaner code)
            ticket['resolved'] = datetime.datetime.now()

        # Sanitize ticket state dict (need to convert time strings to timedeltas)
        if ticket.get('states', False):
            ticket['states'] = sanitize_ticket_states(ticket['states'])
        else:
            # This shouldn't happen so something's going wrong
            print("No states for ticket {}".format(ticket['issue']))

    return tickets


def calculate_kpi(tickets, pretty=False, num_past_days=0):
    """
    Calculates kpi metrics over the given sanitized metrics. Reports on all currently
    opened tickets as well as tickets resolved within num_past_days.

    num_past_days=0 will report on all tickets, regardless of when they were resolved.
    """
    # Set up vars
    triage_time_spent, eng_time_spent, backlog_time, product_time = [], [], [], []

    date_x_days_ago = datetime.datetime.now() - datetime.timedelta(days=num_past_days)

    # Go through tickets again, gathering and reporting information
    for ticket in tickets:
        # If we're restricting to past days, and the ticket was resolved longer ago
        # than our limit, skip it.
        if num_past_days > 0 and ticket['resolved'] < date_x_days_ago:
            continue

        # Get amount of time this spent in "Needs Triage" (roughly, time to first response)
        triage_time_spent.append(single_state_time_spent(ticket['states'], 'Needs Triage'))

        # Calculate total time spent by engineering team on this ticket
        eng_time_spent.append(engineering_time_spent(ticket['states']))

        # Get time spent in backlog
        if ticket['states'].get('Awaiting Prioritization', False):
            backlog_time.append(single_state_time_spent(ticket['states'], 'Awaiting Prioritization'))

        # Get time spent in product review
        if ticket['states'].get('Product Review', False):
            product_time.append(single_state_time_spent(ticket['states'], 'Product Review'))

    teng = avg_time_spent(eng_time_spent, 'Average time spent in edX engineering states', pretty)
    tnt = avg_time_spent(triage_time_spent, 'Average time spent in Needs Triage', pretty)
    tpr = avg_time_spent(product_time, 'Average time spent in product review', pretty)
    tap = avg_time_spent(backlog_time, 'Average time spent in team backlog', pretty)
    if not pretty:
        print('Eng\t| Triage\t| Product\t| Backlog')
        print('{}\t{}\t{}\t{}'.format(teng, tnt, tpr, tap))


def avg_time_spent(time_spent, message, pretty):
    """
    Prints out the average time spent over the number of tickets.
    Message should be the header message to print out.
    """
    # Calculate average engineering time spent
    avg_time = reduce(operator.add, time_spent, datetime.timedelta(0)) / len(time_spent)

    # Pretty print the average time
    days = avg_time.days
    hours, remainder = divmod(avg_time.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if pretty:
        print('\n' + message + ', over {} tickets'.format(len(time_spent)))
        print('\t {} days, {} hours, {} minutes, {} seconds'.format(days, hours, minutes, seconds))
    else:
        return '{}:{}:{}:{}'.format(days, hours, minutes, seconds)


def main(argv):
    """a docstring for main, really?"""
    parser = argparse.ArgumentParser(description="Summarize JIRA info.")
    parser.add_argument(
        "--no-scrape", action="store_true",
        help="Don't re-run the scraper, just read the current states.json file"
    )
    parser.add_argument(
        "--since", metavar="DAYS", type=int, default=0,
        help="Only consider unresolved PRs & PRs closed in the past DAYS days"
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

    tickets = parse_jira_info(args.debug, args.pretty)
    calculate_kpi(tickets, args.pretty, args.since)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
