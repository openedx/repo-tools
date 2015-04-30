"""
Spider to scrape JIRA for transitions in and out of states.

Usage: `scrapy runspider jiraspider.py -o states.json`
"""
from __future__ import print_function
from collections import namedtuple

import datetime
import dateutil.parser
import re

from jira.client import JIRA

import scrapy
from scrapy.http import Request


SERVER = 'https://openedx.atlassian.net'

# Regex to match the duration field ("14d 22h 5m", "2h 33m", or "1m 10s")
DURATION_REGEX = re.compile(r'((?P<days>\d+?)d)?((?P<hours>\d+?)h)?((?P<minutes>\d+?)m)?((?P<seconds>\d+?)s)?')

# All states in the ospr jira ticket workflow
OSPR_STATES = [
    'Needs Triage',
    'Waiting on Author',
    'Blocked by Other Work',
    'Product Review',
    'Community Manager Review',
    'Awaiting Prioritization',
    'Engineering Review',
    'Merged',
    'Rejected',
]

# Sometimes, tickets have other states (perhaps they were moved from one project to the OSPR project).
# Map those states to equivalent OSPR workflow states.
STATE_MAP = {
    'Open': 'Awaiting Prioritization',
    'Ready for Grooming': 'Awaiting Prioritization',
    'Groomed': 'Awaiting Prioritization',
    'In Backlog': 'Awaiting Prioritization',
    'Engineering Code Review': 'Engineering Review',
}

IssueFields = namedtuple('IssueFields', ['key', 'labels', 'issuetype'])


def extract_fields(issue):
    """
    Extracts JIRA issue fields and returns an IssueFields object
    """
    key = issue.key
    labels = issue.fields.labels
    issuetype = issue.fields.issuetype.name
    return IssueFields(key, labels, issuetype)


def jira_issues(server_url, project_name):
    """
    Get JIRA issue keys for a project on a server.

    Returns a list of IssueFields such as:
    [IssueFields(key='OSPR-456', labels=['Dedx'], issuetype=u'Sub-task'),
     IssueFields(key='OSPR-458', labels=[], issuetype=u'Pull Request Review')]
    """
    jira = JIRA({'server': server_url})
    issues = jira.search_issues('project = {}'.format(project_name), maxResults=None)
    return [extract_fields(iss) for iss in issues]


class IssueStateDurations(scrapy.Item):
    """Scrapy item class. Defines fields that will be json-serialized."""
    # String: JIRA issue key, eg "OSPR-1"
    issue = scrapy.Field()
    # Dictionary: States: amount of time ([days, seconds] format) spent in that state, eg
    # {"Waiting on Author": [0, 72180], "Needs Triage": [1, 38520]}
    states = scrapy.Field()
    # List: Labels present on the ticket, if any, eg ["TNL"]
    labels = scrapy.Field()
    # String: any debug information the parser outputs on this entry
    debug = scrapy.Field()
    # String: any error information the parser outputs on this entry
    error = scrapy.Field()
    # Resolution date - serialized datetime
    resolved = scrapy.Field()
    # List [str, str]: Resolution transition of the issue, if resolved, eg
    # ["Waiting on Author", "Merged"] indicates that the issue was merged from
    # the "Waiting on Author" state.
    resolution = scrapy.Field()


class JiraSpider(scrapy.Spider):
    """Scrapy spider for scraping JIRA"""
    name = 'jiraspider'
    default_time = datetime.timedelta(0)
    onemin = datetime.timedelta(**{'minutes': 1})

    def start_requests(self):
        """Scrapy method. Starts the spider."""
        issues = jira_issues(SERVER, 'OSPR')
        requests = []
        for issue in issues:
            # TODO (potentially) ignore subtasks, or do something with them? (issue.issuetype)
            request = Request(
                "{}/browse/{}?page=com.googlecode.jira-suite-utilities:transitions-summary-tabpanel".format(SERVER, issue.key)
            )
            request.meta['issue_key'] = issue.key
            request.meta['labels'] = issue.labels
            requests.append(request)

        return requests

    def parse(self, response):
        """
        Parses a single response into an IssueStateDurations() object.
        Returns the object itself.

        (this function must be named as such for the scrapy spider to properly work)
        """
        # Set up item to hold info from the response
        item = IssueStateDurations()
        item['issue'] = response.meta['issue_key']
        item['labels'] = response.meta['labels']
        item['debug'] = ''
        item['error'] = ''

        states = {}
        transitions = response.xpath('.//table[tr/th[text()="Time In Source Status"]]/tr[td]')
        if not transitions:
            # Generally this means that the ticket is newly-opened
            item['debug'] += "DEBUG: Could not find any transitions for key {}".format(item['issue'])
            return item

        # Parse each transition, pulling out the source status & how much time was spent in that status
        for trans in self.clean_transitions(transitions, item):
            (source_status, dest_status, duration) = trans

            # need to account for the fact that states can be revisited, along different transition arrow
            # parse the time into a datetime.timedelta object
            duration_datetime = self.parse_duration(duration)
            # ignore states that we spent less than one minute in (often this is just because transitioning
            # through JIRA states is stupid, or botbro is stupid)
            if source_status != 'Needs Triage' and duration_datetime < self.onemin:
                item['debug'] += "Ignoring state ({}) of length {}".format(source_status, duration)
                continue

            # Add the amount of time spent in source status to any previous recorded time we've spent there
            states[source_status] = states.get(source_status, self.default_time) + duration_datetime
            self.validate_tdelta(
                states[source_status],
                item,
                'adding src status time: {}'.format(duration_datetime)
            )

        # Need to consider current state ('dest_status'), as well.

        # get "Last Execution Date" time -- in a terribly shitty format.
        trans_date = transitions[-1].xpath('td[5]/text()').extract()[0].strip()
        try:
            last_execution_date = self.parse_last_execution_time(trans_date)
        except ValueError:
            # couldn't parse the last execution time for some reason. Log error and continue.
            item['error'] += 'ERROR: failed to parse last execution date from date {date}\n'.format(
                dest=dest_status,
                date=trans_date
            )
            last_execution_date = None

        if dest_status in ['Merged', 'Rejected']:
            # If the ticket's been resolved (merged or closed), store the resolution as a tuple of
            # (source, result) so we can get not just resolution but previous state prior to resolution
            item['resolution'] = (source_status, dest_status)
            # Also store when it was resolved
            if last_execution_date:
                item['resolved'] = str(last_execution_date)

        else:
            if last_execution_date:
                current_duration = datetime.datetime.now() - last_execution_date
                self.validate_tdelta(
                    current_duration,
                    item,
                    'cd: now() minus last time, {}'.format(last_execution_date)
                )
                states[dest_status] = states.get(dest_status, self.default_time) + current_duration
                self.validate_tdelta(
                    states[dest_status],
                    item,
                    'getting dest status {}, duration {}'.format(dest_status, current_duration)
                )

        # json-serialize each timedelta ('xx:yy', xx days, yy seconds) (skipping useconds)
        item['states'] = {}
        for (state, tdelta) in states.iteritems():
            item['states'][state] = [tdelta.days, tdelta.seconds]

        # If we didn't find any debugs or errors, remove before returning
        if item['debug'] == '':
            del item['debug']
        if item['error'] == '':
            del item['error']

        return item

    def clean_transitions(self, transitions, item):
        """
        Parse each transition, discarding any transitions that go in/out of the "Verified" state
        and cleaning up other random states that may have been introduced

        See https://openedx.atlassian.net/browse/OSPR-369
        """
        cleaned = []
        for trans in transitions:
            try:
                source_status = trans.xpath('td[1]/table/tr/td[2]/text()').extract()[0].strip()
                dest_status = trans.xpath('td[1]/table/tr/td[5]/text()').extract()[0].strip()
                # Discard transitions that go in/out of the "Verified" state
                if source_status == "Verified" or dest_status == "Verified":
                    continue

                source_status = self.remap_states(source_status, item)
                dest_status = self.remap_states(dest_status, item)
                duration = trans.xpath('td[2]/text()').extract()[0].strip()
                # print('*'*10 + source_status + '->' + dest_status + '; ' + duration)
                cleaned.append((source_status, dest_status, duration))

            except Exception as err:
                item['error'] += "ERROR in clean_transactions: {}".format(err)
                continue

        return cleaned

    def remap_states(self, status, item):
        """
        Cleans up messy data by remapping other board's states into OSPR states.

        Logs debug messages for any states we don't know about.
        """
        if status in STATE_MAP.keys():
            return STATE_MAP[status]

        elif status not in OSPR_STATES:
            # emit error message if we find an unexpected state
            item['error'] += "ERROR: Found unexpected state '{}'!".format(status)

        return status

    def parse_duration(self, duration):
        """
        Parses the duration time that we scrape from the "Time in Source Status" field.

        Will be in one of 3 forms: "14d 22h 5m", "2h 33m", or "1m 10s".

        We discard the seconds, and turn the d/h/m into a datetime.timedelta
        """
        duration = duration.replace(' ', '')
        parts = DURATION_REGEX.match(duration)
        td_dict = {}
        for (name, value) in parts.groupdict().iteritems():
            if value:
                td_dict[name] = int(value)

        return datetime.timedelta(**td_dict)

    def parse_last_execution_time(self, etime):
        """
        parses the "last execution time" field in JIRA, which is a terrible format, either:
        if over a week ago:
        - 02/Apr/15 10:11 AM
        if within the past week:
        - Saturday 9:23 AM
        if yesterday:
        - Yesterday 11:05 AM
        if today:
        - Today 9:09 AM

        Returns a datetime.datetime object representing when the last execution time occured
        """
        # dateutil.parser.parse will do all the formats we need except the "Yesterday"
        if 'Today' in etime:
            # For things that happend "Today", we can parse using the fuzzy flag.
            return dateutil.parser.parse(etime, fuzzy=True)

        if 'Yesterday' in etime:
            today = datetime.datetime.now()
            yesterday = '{0.month}/{1}/{0.year}'.format(today, today.day - 1)
            etime = etime.replace('Yesterday', yesterday)

        # This is sometimes returning dates in the future when the day is
        # specified as an abstract day such as "Wednesday"
        parsed_dt = dateutil.parser.parse(etime)
        # if it's a date in the future, take it back 7 days
        if parsed_dt > datetime.datetime.now():
            parsed_dt = parsed_dt + datetime.timedelta(**{'days': -7})

        return parsed_dt

    def validate_tdelta(self, tdelta, item, msg):
        """
        Validates that the given timedelta is a positive quantity.
        Logs a debug message if not.
        """
        if tdelta < datetime.timedelta(0):
            item['debug'] += 'DEBUG: negative time found. {}'.format(msg)
