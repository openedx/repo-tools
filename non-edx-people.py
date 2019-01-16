#!/usr/bin/env python
"""Produce a list of the emails of all non-edX people in people.yaml"""
from __future__ import print_function

import yaml

with open("people.yaml") as people_yaml:
    people = yaml.load(people_yaml)
non_edx = (e for e in people.itervalues() if e.get('institution') != 'edX')
email_ok = (e for e in non_edx if e.get('email_ok', True))
emails = (e.get('email', '').strip() for e in email_ok)
print(",\n".join(em for em in emails if em))
