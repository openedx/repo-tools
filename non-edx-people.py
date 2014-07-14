"""Produce a list of the emails of all non-edX people in people.yaml"""

import yaml

with open("people.yaml") as people_yaml:
   people = yaml.load(people_yaml)
non_edx = (e for e in people.itervalues() if e.get('institution') != 'edX')
emails = (e['authors_entry'].partition('<')[2].strip(">") for e in non_edx)
print ",\n".join(em for em in emails if em.strip())
