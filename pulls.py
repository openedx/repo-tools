import operator
import pprint

import jreport

import yaml


class JPullRequest(jreport.JObj):
    def __init__(self, issue_data, org_fn=None):
        super(JPullRequest, self).__init__(issue_data)
        self['labels'] = [self.short_label(l['name']) for l in self['labels']]
        if org_fn:
            self['org'] = org_fn(self)

            internal_orgs = {"edX", "Arbisoft", "BNOTIONS", "OpenCraft", "ExtensionEngine"}
            if "osc" in self['labels']:
                self['intext'] = "external"
            elif self['org'] in internal_orgs:
                self['intext'] = "internal"
            else:
                self['intext'] = "external"



def get_pulls(owner_repo, labels=None, state="open", since=None, org=False, pull_details=None):
    raise Exception("This code moved to githubapi.py, fix your program!")
