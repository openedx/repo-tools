"""
Spider to scrape JIRA for transitions in and out of states.

Usage: `scrapy runspider jiraspider.py -o states.json`
"""
from __future__ import print_function

import datetime
import json
import re

from jira.client import JIRA

import scrapy
from scrapy.http import Request


SERVER = 'https://openedx.atlassian.net'
TIME_REGEX = re.compile(r'((?P<days>\d+?)d)?((?P<hours>\d+?)h)?((?P<minutes>\d+?)m)?((?P<seconds>\d+?)s)?')


def jira_issue_keys(server_url, project_name):
    """Get a list of JIRA issue keys for a project on a server."""
    jira = JIRA({ 'server': server_url })
    issues = jira.search_issues('project = {}'.format(project_name), maxResults=None)
    return [iss.key for iss in issues]


class IssueStateDurations(scrapy.Item):
    issue = scrapy.Field()
    states = scrapy.Field()


class JiraSpider(scrapy.Spider):
    name = 'jiraspider'
    default_time = datetime.timedelta(0)

    def start_requests(self):
        keys = jira_issue_keys(SERVER, 'OSPR')
        requests = []
        for key in keys:
            request = Request("{}/browse/{}?page=com.googlecode.jira-suite-utilities:transitions-summary-tabpanel".format(SERVER, key))
            request.meta['issue_key'] = key
            requests.append(request)

        return requests

    def parse(self, response):
        item = IssueStateDurations()
        item['issue'] = response.meta['issue_key']
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

        # json-serialize each timedelta ('xx:yy', xx days, yy seconds)
        item['states'] = {}
        for (state, tdelta) in states.iteritems():
            item['states'][state] = '{0.days}:{0.seconds}'.format(tdelta)

        return item

    def parse_time(self, duration):
        duration = duration.replace(' ', '')
        parts = TIME_REGEX.match(duration)
        td_dict = {}
        for (name, value) in parts.groupdict().iteritems():
            if value:
                td_dict[name] = int(value)

        return datetime.timedelta(**td_dict)
