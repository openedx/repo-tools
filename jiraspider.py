"""
Spider to scrape JIRA for transitions in and out of states.

Usage: `scrapy runspider jiraspider.py -o states.json`
"""
from __future__ import print_function
from collections import namedtuple

import datetime
import dateutil.parser
import json
import re

from jira.client import JIRA

import scrapy
from scrapy.http import Request


SERVER = 'https://openedx.atlassian.net'
TIME_REGEX = re.compile(r'((?P<days>\d+?)d)?((?P<hours>\d+?)h)?((?P<minutes>\d+?)m)?((?P<seconds>\d+?)s)?')

IssueFields = namedtuple('IssueFields', ['key', 'labels', 'issuetype'])


def extract_fields(issue):
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
    jira = JIRA({ 'server': server_url })
    issues = jira.search_issues('project = {}'.format(project_name), maxResults=None)
    return [extract_fields(iss) for iss in issues]


class IssueStateDurations(scrapy.Item):
    # String: JIRA issue key, eg "OSPR-1"
    issue = scrapy.Field()
    # Dictionary: States: amount of time ("days:seconds" format) spent in that state, eg
    # {"Waiting on Author": "0:72180", "Needs Triage": "1:38520"}
    states = scrapy.Field()
    # List: Labels present on the ticket, if any, eg ["TNL"]
    labels = scrapy.Field()
    # String: any debug information the parser outputs on this entry
    debug = scrapy.Field()
    # String: any error information the parser outputs on this entry
    error = scrapy.Field()
    # List [str, str]: Resolution transition of the issue, if resolved, eg
    # ["Waiting on Author", "Merged"] indicates that the issue was merged from
    # the "Waiting on Author" state.
    resolution = scrapy.Field()


class JiraSpider(scrapy.Spider):
    name = 'jiraspider'
    default_time = datetime.timedelta(0)

    def start_requests(self):
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

        # Parse each transition, pulling out the source status & how much time was spent in that status
        for trans in self.clean_transitions(transitions, item):
            # TODO how do we want to handle ones that are closed and reopened (eg https://openedx.atlassian.net/browse/OSPR-415) -- possibly just leave to parsing later on
            source_status = trans.xpath('td[1]/table/tr/td[2]/text()').extract()[0].strip()
            duration = trans.xpath('td[2]/text()').extract()[0].strip()

            # need to account for the fact that states can be revisited, along different transition arrow
            # parse the time into a datetime.timedelta object
            duration_datetime = self.parse_time(duration)

            # Add the amount of time spent in source status to any previous recorded time we've spent there
            states[source_status] = states.get(source_status, self.default_time) + duration_datetime

        # Need to consider current state, as well. We're in final state so get dest_status
        dest_status = trans.xpath('td[1]/table/tr/td[5]/text()').extract()[0].strip()
        # item['debug'] += "dest_status is: " + dest_status
        if dest_status in ['Merged', 'Rejected']:
            # If the ticket's been resolved (merged or closed), store the resolution as a tuple of
            # (source, result) so we can get not just resolution but previous state prior to resolution
            item['resolution'] = (source_status, dest_status)

        else:
            # get "Last Execution Date" time -- in a terribly shitty format.
            trans_date = trans.xpath('td[5]/text()').extract()[0].strip()
            try:
                current_duration = datetime.datetime.now() - self.parse_last_execution_time(trans_date)
            except ValueError:
                # couldn't parse the last execution time for some reason. Log error and continue.
                item['error'] += 'Error parsing transition into {dest} from date {date}\n'.format(
                    dest=dest_status,
                    date=trans_date
                )
            else:
                states[dest_status] = states.get(dest_status, self.default_time) + current_duration

        # json-serialize each timedelta ('xx:yy', xx days, yy seconds) (skipping useconds)
        item['states'] = {}
        for (state, tdelta) in states.iteritems():
            item['states'][state] = '{0.days}:{0.seconds}'.format(tdelta)

        return item


    def clean_transitions(self, transitions, item):
        """
        Parse each transition, discarding any transitions that go in/out of the "Verified" state
        and cleaning up other random states that may have been introduced

        See https://openedx.atlassian.net/browse/OSPR-369
        """
        # TODO: States to clean up: "Open", "Ready for Grooming", "In Backlog"
        # TODO: emit debug message if we find an unexpected state
        cleaned = []
        for trans in transitions:
            source_status = trans.xpath('td[1]/table/tr/td[2]/text()').extract()[0].strip()
            dest_status = trans.xpath('td[1]/table/tr/td[5]/text()').extract()[0].strip()
            if source_status == "Verified" or dest_status == "Verified":
                continue
            cleaned.append(trans)

        return cleaned

    def parse_time(self, duration):
        """
        Parses the duration time that we scrape from the "Time in Source Status" field.

        Will be in one of 3 forms: "14d 22h 5m", "2h 33m", or "1m 10s".

        We discard the seconds, and turn the d/h/m into a datetime.timedelta
        """
        duration = duration.replace(' ', '')
        parts = TIME_REGEX.match(duration)
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

        Returns a datetime.datetime object representing whe the last execution time occured
        """
        # dateutil.parser.parse will do all the formats we need except the "Yesterday"
        if 'Today' in etime:
            # For things that happend "Today", we can parse using the fuzzy flag.
            return dateutil.parser.parse(etime, fuzzy=True)

        if 'Yesterday' in etime:
            today = datetime.datetime.now()
            yesterday = '{0.month}/{1}/{0.year}'.format(today, today.day - 1)
            etime = etime.replace('Yesterday', yesterday)

        return dateutil.parser.parse(etime)
