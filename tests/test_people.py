"""Tests of people.py"""

import datetime
import unittest

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

class PeopleTest(unittest.TestCase):
    def test_main_singleton_is_a_singleton(self):
        p1 = People.people()
        p2 = People.people()
        self.assertIs(p1, p2)

    def test_get_institution(self):
        people = People.from_string(SAMPLE_PEOPLE)
        self.assertEqual(people.get("ned")['institution'], "edX")
        self.assertEqual(people.get("db")['institution'], "Optimists United")

    def test_get_non_person(self):
        people = People.from_string(SAMPLE_PEOPLE)
        ghost = people.get("ghost")
        self.assertEqual(ghost['institution'], "unsigned")
        self.assertEqual(ghost['agreement'], "none")

    def test_history(self):
        people = People.from_string(SAMPLE_PEOPLE)

        def ned_then(year):
            ned = people.get("ned", datetime.datetime(year, 1, 1))
            return ned['institution']

        self.assertEqual(ned_then(2015), "edX")
        self.assertEqual(ned_then(2014), "edX")
        self.assertEqual(ned_then(2013), "edX")
        self.assertEqual(ned_then(2012), "freelance")
        self.assertEqual(ned_then(2011), "freelance")
        self.assertEqual(ned_then(2010), "Hewlett Packard")
        self.assertEqual(ned_then(2009), "Hewlett Packard")
        self.assertEqual(ned_then(2008), "Hewlett Packard")
        self.assertEqual(ned_then(2007), "Tabblo")
        self.assertEqual(ned_then(2006), "Kubi Software")
        self.assertEqual(ned_then(2005), "Kubi Software")
        self.assertEqual(ned_then(2004), "Kubi Software")
        self.assertEqual(ned_then(2003), "Kubi Software")
        self.assertEqual(ned_then(2002), "Kubi Software")
        self.assertEqual(ned_then(2001), "Blue Ripple")
        self.assertEqual(ned_then(2000), "Blue Ripple")
