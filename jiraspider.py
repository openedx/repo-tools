"""
Spider to scrape JIRA for transitions in and out of states.

Usage: `scrapy runspider jiraspider.py -o states.json`
"""
from __future__ import print_function
from collections import namedtuple

import datetime
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
    issue = scrapy.Field()
    states = scrapy.Field()
    labels = scrapy.Field()


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
        item = IssueStateDurations()
        item['issue'] = response.meta['issue_key']
        item['labels'] = response.meta['labels']
        states = {}

        transitions = response.xpath('.//table[tr/th[text()="Time In Source Status"]]/tr[td]')
        for trans in transitions:
            source_status = trans.xpath('td[1]/table/tr/td[2]/text()').extract()[0].strip()
            duration = trans.xpath('td[2]/text()').extract()[0].strip()
            # need to account for the fact that states can be revisited, along different transition arrow
            duration_datetime = self.parse_time(duration)
            try:
                states[source_status] = states.get(source_status, self.default_time) + duration_datetime
            except Exception:
                src = states.get(source_status, self.default_time)
                print('source status: {} {}'.format(src, type(src)))
                print('duration: {} {}'.format(duration, type(duration)))
                return

        # TODO need to consider current state, unless in "merged" or "closed"
        # we're in final state so get dest_status
        dest_status = trans.xpath('td[1]/table/tr/td[5]/text()').extract()[0].strip()
        if dest_status in ['Merged', 'Closed']:
            # Store the resolution as a tuple of (source, result) so we can get not just resolution but previous state before resolution
            states['Resolution'] = (source_status, dest_status)
        else:
            # get "Last Execution Date" time -- in a terribly shitty format.
            trans_date = trans.xpath('td[5]/text()').extract()[0].strip()
        #    current_duration = datetime.datetime.now() - self.parse_last_execution_time(trans_date)
        #    states[dest_status] = states.get(dest_status, self.default_time) + current_duration

        # json-serialize each timedelta ('xx:yy', xx days, yy seconds) (skipping useconds)
        item['states'] = {}
        for (state, tdelta) in states.iteritems():
            item['states'][state] = '{0.days}:{0.seconds}'.format(tdelta)

        return item

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
        raise NotImplementedError()
