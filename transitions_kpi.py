#!/usr/bin/env python
"""
Scrapes and parses information from JIRA's transition states.

Runs the JIRA spider, then parses the output states.json
file to obtain KPI information.

See https://openedx.atlassian.net/wiki/display/OPEN/Tracking+edX+Commitment+To+OSPRs
"""
from __future__ import print_function
from collections import OrderedDict
from functools import reduce
from subprocess import check_call

import argparse
import datetime
import dateutil.parser
import json
import numpy
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


def get_time_lists(tickets, num_past_days=0):
    """
    Iterates over tickets, collecting lists of how much time was spent in various states.

    Returns: dictionary of {'name': [datetime.timedelta,]}
      - Time each ticket spent in all engineering states
      - Time each ticket spent in triage
      - Time each ticket spent in product review
      - Time each ticket spent in team backlogs
    """
    # Set up vars
    eng_time_spent, triage_time_spent, product_time, backlog_time = [], [], [], []

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

    result = OrderedDict()
    list_order = ['edX engineering states', 'Needs Triage', 'Product Review', 'Team Backlog']
    lists = (eng_time_spent, triage_time_spent, product_time, backlog_time)
    for name, lst in zip(list_order, lists):
        result[name] = lst
    return result


def avg_time_spent(time_spent):
    """
    Returns the average time spent over the number of tickets.
    """
    # Can't use numpy or other standards because sum() won't work with
    # a list of datetime.timedeltas
    return reduce(operator.add, time_spent, datetime.timedelta(0)) / len(time_spent)


def std_dev(time_spent):
    """
    Standard deviation of the list.

    Calculation follows formula std = sqrt(mean( (x - x.mean())**2 ) )
    """
    avg = avg_time_spent(time_spent)
    summation = 0
    for sample in time_spent:
        diff = sample - avg
        summation += diff.total_seconds()**2
    variance = summation / len(time_spent)
    std = int(numpy.sqrt(variance))
    return datetime.timedelta(seconds=std)


def make_percentile(qper):
    """
    Returns a percentile function for the given numeric qper
    qper: Float in range of [0,100]. Percentile to compute which must be
      between 0 and 100 inclusive.
    """
    def percentile(time_spent):
        """
        Returns the qth percentile of the tickets
        """
        seconds_spent = map(datetime.timedelta.total_seconds, time_spent)
        raw_result = numpy.percentile(seconds_spent, qper)
        return datetime.timedelta(seconds=raw_result)
    return percentile


def pretty_print_time(time, message=None):
    """Pretty print the given time"""
    days = time.days
    hours, remainder = divmod(time.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if message is not None:
        print(message)
        print('\t {} days, {} hours, {} minutes, {} seconds'.format(days, hours, minutes, seconds))
    # Print out fractional days things have been in this state
    total = days + hours/24. + minutes/(24.*60) + seconds/(24.*3600)
    return "{:.1f}".format(total)


def get_stats(time_spent, functions, pretty=False):
    """
    Given a list of times and a list of stats functions, prints out all the
    stats over the list (optionally in a pretty format)
    """
    header = ''
    results = ''
    for func, fname in functions:
        output = func(time_spent)
        if pretty:
            msg = '{} time spent'.format(fname)
            pretty_print_time(output, msg)
        else:
            # build up a string to print out.
            header += "{}\t|".format(fname)
            results += "{}\t ".format(pretty_print_time(output))

    if not pretty:
        print(header + 'Num tickets')
        print(results + '{}\n'.format(len(time_spent)))


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
    parser.add_argument(
        "--average", action="store_true",
        help="Print out the average time spent in each of 4 states"
    )
    parser.add_argument(
        "--median", action="store_true",
        help="Print out the median time spent in each of 4 states"
    )
    parser.add_argument(
        "--percentile", type=float,
        help="Print out the qth percentile of all tickets in each state"
    )
    parser.add_argument(
        "--std-dev", action="store_true",
        help="Print out the standard deviation across the data"
    )
    parser.add_argument(
        "--max", action="store_true",
        help="Show the maximum time in the series"
    )
    parser.add_argument(
        "--min", action="store_true",
        help="Show the minimum time in the series"
    )
    parser.add_argument(
        "--all", action="store_true",
        help="Show all statistics"
    )

    args = parser.parse_args(argv[1:])

    # Parse out what functions we want to gather for this report
    functions = []

    if args.average or args.all:
        functions.append((avg_time_spent, 'Average'))

    if args.median or args.all:
        median_time_spent = make_percentile(50)
        functions.append((median_time_spent, 'Median'))

    if args.percentile or args.all:
        pnum = args.percentile or 95
        pfunc = make_percentile(pnum)
        functions.append((pfunc, '{}%'.format(pnum)))

    if args.std_dev or args.all:
        functions.append((std_dev, 'StdDev'))

    if args.max or args.all:
        functions.append((lambda lst: max(lst), 'Max'))

    if args.min or args.all:
        functions.append((lambda lst: min(lst), 'Min'))

    if len(functions) == 0:
        print("Alert: No statistical functions specified. Please use '--help' to see which are available, or use '--all' to run all.")
        return

    # Scrape jira unless told otherwise
    if not args.no_scrape:
        scrape_jira()

    # Parse states.json into times list
    tickets = parse_jira_info(args.debug, args.pretty)
    # Gets {'list name': list}
    ticket_lists = get_time_lists(tickets, args.since)
    for list_name, time_spent in ticket_lists.iteritems():
        print("-" * 40)
        num_tix = len(time_spent)
        print("Statistics for '{}', over {} tickets".format(list_name, num_tix))
        print("-" * 40)
        get_stats(time_spent, functions, args.pretty)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
