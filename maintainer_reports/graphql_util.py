"""
A collection of utility functions for interacting with the GitHub
GraphQL API.
"""
import os
from time import sleep

import click
import requests
from dateutil.rrule import MONTHLY, rrule
from requests.adapters import HTTPAdapter, Retry
from dotenv import load_dotenv

DATE_MASK='%Y-%m-%d'

# Added for GCP support, should consider implications for 
# running locally.
load_dotenv()
GH_BEARER_TOKEN = os.getenv('GH_BEARER_TOKEN')

if not GH_BEARER_TOKEN:
    raise Exception("Didn't find the GH_BEARER_TOKEN set in the environment")

HEADERS = {"Authorization": f"Bearer {GH_BEARER_TOKEN}"}
END_POINT="https://api.github.com/graphql"

# Seconds to throttle between calls
SLEEP_BETWEEN_CALLS=8

def run_query_with_retry(query):
    """
    Runs a GitHub GraphQL query automatically retrying failed queries up to 
    5 times with backoff.
    """

    # Utilizing Requests sessions to retry with backoff for specific status codes.
    # GitHub's API is pretty flakey and even with this configurations failure 
    # occasionally occur.
    s = requests.Session()
    retries = Retry(total=10, backoff_factor=5, status_forcelist=[ 502, 503, 504 ])
    s.mount('https://', HTTPAdapter(max_retries=retries))

    request = s.post(END_POINT, json={'query': query}, headers=HEADERS)

    if request.status_code == 200:
        return request.json()
    else:
        raise Exception(f"GraphQL call failed, returning status code of {request.status_code}")


def retrieve_paginated_results(query):
    """
    Github GraphQL queries are paginated and retreiving all results requires
    following the page references provided in each subsequent response.  This
    function aggregates all results across the pages and returns a single array 
    containing all the results.
    """

    starting_end_cursor = "null"

    data = run_query_with_retry(query.replace("_END_CURSOR_",starting_end_cursor))
    results = data["data"]["search"]["nodes"]
    has_next_page = data["data"]["search"]["pageInfo"]["hasNextPage"]

    while has_next_page:

        click.echo("Handling next page")

        end_cursor = data["data"]["search"]["pageInfo"]["endCursor"]
        sleep(SLEEP_BETWEEN_CALLS)

        data = run_query_with_retry(query=query.replace("_END_CURSOR_",'"' + end_cursor + '"'))

        results = results + data["data"]["search"]["nodes"]

        has_next_page = data["data"]["search"]["pageInfo"]["hasNextPage"]

    return results

def date_slice_query(query, start_date, end_date, time_bucket=MONTHLY):
    """
    Runs a query over a set of smaller timespans to provide flexibility and reduce 
    errors interacting with the flakey GraphQL service offered by GitHub.
    """
    query_start_date = None

    for bucket in rrule(time_bucket, dtstart=start_date, until=end_date):
        
        results = []

        if not query_start_date:
            query_start_date = bucket
        else:
            
            sleep(SLEEP_BETWEEN_CALLS)

            click.echo(f"Handling date range {query_start_date.strftime(DATE_MASK)} to {bucket.strftime(DATE_MASK)}")

            results = results + retrieve_paginated_results(query.replace("_RANGE_", query_start_date.strftime(DATE_MASK) + ".." + bucket.strftime(DATE_MASK)))

            query_start_date = bucket
    
    return results
