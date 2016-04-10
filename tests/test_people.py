"""Tests of people.py"""

import datetime
import os

import pytest

from people import People

@pytest.fixture
def test_data(mocker):
    """Read people.yaml from this directory."""
    mocker.patch.object(People, '_data_dir', os.path.dirname(__file__))

def test_main_singleton_is_a_singleton(test_data):
    p1 = People.people()
    p2 = People.people()
    assert p1 is p2

def test_get_institution(test_data):
    people = People.people()
    assert people.get("ned")['institution'] == "edX"
    assert people.get("db")['institution'] == "Optimists United"

def test_get_non_person(test_data):
    people = People.people()
    ghost = people.get("ghost")
    assert ghost['institution'] == "unsigned"
    assert ghost['agreement'] == "none"

def test_history(test_data):
    people = People.people()

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
