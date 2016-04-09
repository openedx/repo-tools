"""Tests of people.py"""

import datetime

from people import People

SAMPLE_PEOPLE = """\
ned:
    institution: edX
    before:
        2012-10-01:
            institution: freelance
        2010-12-01:
            institution: Hewlett Packard
        2007-05-01:
            institution: Tabblo
        2006-01-09:
            institution: Kubi Software
        2001-09-24:
            institution: Blue Ripple
db:
    institution: Optimists United
"""

def test_main_singleton_is_a_singleton():
    p1 = People.people()
    p2 = People.people()
    assert p1 is p2

def test_get_institution():
    people = People.from_string(SAMPLE_PEOPLE)
    assert people.get("ned")['institution'] == "edX"
    assert people.get("db")['institution'] == "Optimists United"

def test_get_non_person():
    people = People.from_string(SAMPLE_PEOPLE)
    ghost = people.get("ghost")
    assert ghost['institution'] == "unsigned"
    assert ghost['agreement'] == "none"

def test_history():
    people = People.from_string(SAMPLE_PEOPLE)

    def ned_then(year):
        ned = people.get("ned", datetime.datetime(year, 1, 1))
        return ned['institution']

    assert ned_then(2015) == "edX"
    assert ned_then(2014) == "edX"
    assert ned_then(2013) == "edX"
    assert ned_then(2012) == "freelance"
    assert ned_then(2011) == "freelance"
    assert ned_then(2010) == "Hewlett Packard"
    assert ned_then(2009) == "Hewlett Packard"
    assert ned_then(2008) == "Hewlett Packard"
    assert ned_then(2007) == "Tabblo"
    assert ned_then(2006) == "Kubi Software"
    assert ned_then(2005) == "Kubi Software"
    assert ned_then(2004) == "Kubi Software"
    assert ned_then(2003) == "Kubi Software"
    assert ned_then(2002) == "Kubi Software"
    assert ned_then(2001) == "Blue Ripple"
    assert ned_then(2000) == "Blue Ripple"
