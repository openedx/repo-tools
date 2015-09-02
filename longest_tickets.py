#!/usr/bin/env python
"""
Parses JIRA a little to get at specific dates, quickly.
Doesn't run the scraper, run transitions_kpi.py to get that
"""
from transitions_kpi import parse_jira_info, engineering_time_spent, scrape_jira

import argparse
import datetime
import sys


# Valid open states in the ospr jira ticket workflow
OSPR_STATES = [
    'Needs Triage',
    'Waiting on Author',
    'Blocked by Other Work',
    'Product Review',
    'Community Manager Review',
    'Awaiting Prioritization',
    'Engineering Review',
    'All Engineering',
    'All',
]


def longest_open_per_state(tickets, current=True):
    """
    Returns the amount of time & ticket # for the longest amt of time
    spent in engineering overall, triage, and awaiting prioritization.

    current: only report on currently open tickets
    """
    leng, ltri, lap = datetime.timedelta(0), datetime.timedelta(0), datetime.timedelta(0)
    tixe = tixt = tixap = ''
    for ticket in tickets:
        if current and ticket.get('resolution', False):
            continue

        teng = engineering_time_spent(ticket['states'])
        if teng and teng > leng:
            leng = teng; tixe = ticket['issue']

        ttri = ticket['states'].get('Needs Triage', False)
        if ttri and ttri > ltri:
            ltri = ttri; tixt = ticket['issue']

        tap = ticket['states'].get('Awaiting Prioritization', False)
        if tap and tap > lap:
            lap = tap; tixap = ticket['issue']

    if current:
        print("Longest amount spent in each state, over currently-open tickets:")
    else:
        print("Historic longest time tickets:")
    print("Longest amount spent in Engineering states: {} ({})".format(leng, tixe))
    print("Longest amount spent in Needs Triage: {} ({})".format(ltri, tixt))
    print("Longest amount spent in Awaiting Prioritization: {} ({})".format(lap, tixap))


def all_with_length(tickets, state):
    """
    Show currently-open tickets in the given state, sorted by amount of time they've been there.
    """
    if state not in OSPR_STATES:
        print("Validation error: Unrecognized state '{}'".format(state))
        print("Valid states are: {}".format(OSPR_STATES))
        return
    target_tickets = []
    for ticket in tickets:
        if ticket.get('current', None) == state:
            target_tickets.append((ticket['issue'], ticket['states'][state]))
        elif state == 'All Engineering' and not ticket.get('resolution', False):
            target_tickets.append(
                (ticket['issue'], engineering_time_spent(ticket['states']), ticket['current'])
            )
        elif state == 'All' and not ticket.get('resolution', False):
            total_time = datetime.timedelta(0)
            for __, tdelta in ticket['states'].iteritems():
                total_time += tdelta
            target_tickets.append(
                (ticket['issue'], total_time, ticket['current'])
            )

    # sort these by how long they've been open.
    target_tickets.sort(key=lambda x: x[1])
    target_tickets.reverse()
    if state == 'All Engineering' or state == 'All':
        print("Issue Number (Time Spent in {}) - Current state".format(state))
        for issue, time, current in target_tickets:
            print("{} ({}) - {}".format(issue, time, current))
        return

    print("Issue Number (Time Spent in {})".format(state))
    for issue, time in target_tickets:
        print("{} ({})".format(issue, time))


def main(argv):
    """a docstring for main, really?"""
    parser = argparse.ArgumentParser(description="Get information about the tickets open the longest :(\nDefaults to --state='All'")

    parser.add_argument(
        "--scrape", action="store_true",
        help="Rescrape JIRA"
    )

    parser.add_argument(
        "--longest", action="store_true",
        help="Show the longest amount of time spent in each state, over currently-open tickets"
    )
    parser.add_argument(
        "--historic", action="store_true", default=False,
        help="Show the historic longest open tickets, per state"
    )
    parser.add_argument(
        "--state", type=str,
        help="Show currently-open tickets in the given state, sorted by amount of time they've been there."
    )

    args = parser.parse_args(argv[1:])

    if args.scrape:
        scrape_jira()

    tickets = parse_jira_info()
    if args.state:
        # TODO (potentially) report over historic data
        all_with_length(tickets, args.state)

    elif args.longest or args.historic:
        current = not args.historic
        longest_open_per_state(tickets, current)

    else:
        all_with_length(tickets, 'All')


if __name__ == "__main__":
    sys.exit(main(sys.argv))
