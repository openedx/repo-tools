import json

from jira.client import JIRA

import scrapy
from scrapy.http import Request


SERVER = 'https://openedx.atlassian.net'


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
        item['states'] = states = {}

        transitions = response.xpath('.//table[tr/th[text()="Time In Source Status"]]/tr[td]')
        for trans in transitions:
            source_status = trans.xpath('td[1]/table/tr/td[2]/text()').extract()[0].strip()
            duration = trans.xpath('td[2]/text()').extract()[0].strip()
            states[source_status] = duration

        return item
