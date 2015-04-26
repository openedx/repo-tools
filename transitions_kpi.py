"""
Scrapes and parses information from JIRA's transition states.

Runs the JIRA spider, then parses the output states.json
file to obtain KPI information.
"""
from __future__ import print_function
from subprocess import check_call

import argparse
import sys


def scrape_jira():
    check_call("scrapy runspider jiraspider.py -o states.json".split(" "))


def parse_jira_info():
    # Read in and parse states.json
    raise NotImplementedError()


def main(argv):
    parser = argparse.ArgumentParser(description="Summarize JIRA info.")
    parser.add_argument(
        "--no-scrape", action="store_true",
        help="Don't re-run the scraper, just read the current states.json file"
    )
    args = parser.parse_args(argv[1:])

    if not args.no_scrape:
        scrape_jira()

    parse_jira_info()

if __name__ == "__main__":
    sys.exit(main(sys.argv))
