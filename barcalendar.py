#!/usr/bin/env python3.6
"""
Make a csv file that can be imported into Google Sheets, and then manipulated
with the Javascript code at the end of this file.  The result is a calendar
with bars indicating support windows of various pieces of software.

It's kind of silly how it works now, with a csv file output.  It would make
more sense to just output a list of bars to draw, and then use the Javascript
to draw them.

"""

import csv
import datetime
import itertools
import sys

EXTEND = '-'

class Calendar:
    def __init__(self, start, end):
        self.start = start
        self.blanks = [''] * 12 * (end - start + 1)
        self.rows = []
        years = []
        months = []
        for year in range(start, end+1):
            years.append(year)
            years.extend([EXTEND]*11)
            months.extend("JFMAMJJASOND")
        self.rows.append(years)
        self.rows.append(months)

    def bar(self, name, start, end=None, length=None, color=None):
        row = list(self.blanks)
        year, month = start
        istart = (year - self.start) * 12 + month - 1
        if length is None:
            eyear, emonth = end
            iend = (eyear - self.start) * 12 + emonth - 1
        else:
            iend = istart + length - 1
        if istart >= len(row):
            return  # bar is entirely in the future.
        if iend < 0:
            return  # bar is entirely in the past.
        istart = max(0, istart)
        iend = min(len(row)-1, iend)
        if color is not None:
            name += "|" + color
        row[istart] = name
        for ii in range(istart+1, iend+1):
            row[ii] = EXTEND
        self.rows.append(row)

    def write(self, outfile):
        writer = csv.writer(outfile)
        for row in self.rows:
            writer.writerow(row)

cal = Calendar(2016, 2024)

# Open edX releases
names = ["Dogwood", "Eucalyptus", "Ficus", "Ginkgo", "Hawthorn", "Ironwood"]
letters = "JKLMNOPQRST"
releases = itertools.chain(names, letters)
for i, rel in enumerate(releases):
    year = i // 2 + 2016
    month = i % 2 * 6 + 1
    cal.bar(rel, start=(year, month), length=6, color="#fce5cd")

# Django releases  dark: #0c48cc light: #44b78b lighter: #c9f0df
django_releases = [
    ('1.8', 2015, 4, True),
    ('1.9', 2016, 1, False),
    ('1.10', 2016, 8, False),
    ('1.11', 2017, 4, True),
    ('2.0', 2018, 1, False),
    ('2.1', 2018, 8, False),
    ('2.2', 2019, 4, True),
    ('3.0', 2020, 1, False),
]
for name, year, month, lts in django_releases:
    length = 3*12 if lts else 16
    color = "#44b78b" if lts else "#c9f0df"
    cal.bar(f"Django {name}", start=(year, month), length=length, color=color)

# Python releases
python_releases = [
    ('2.7', 2010, 7, 2020, 1),
    ('3.3', 2012, 9, 2017, 9),
    ('3.4', 2014, 3, 2019, 3),
    ('3.5', 2015, 9, 2020, 9),
    ('3.6', 2016, 12, 2021, 12),
    ('3.7', 2018, 6, 2023, 6),
]
for name, syear, smonth, eyear, emonth in python_releases:
    cal.bar(f"Python {name}", start=(syear, smonth), end=(eyear, emonth), color="#ffd545")

# Ubuntu releases
for year, month in itertools.product(range(12, 30), [4, 10]):
    name = "Ubuntu {:d}.{:02d}".format(year, month)
    lts = (year % 2 == 0) and (month == 4)
    length = 5*12 if lts else 9
    color = "#E95420" if lts else "#F4AA90"     # http://design.ubuntu.com/brand/colour-palette
    cal.bar(name, (2000+year, month), length=length, color=color)


cal.write(sys.stdout)


# The code for Google Sheets to turn this output into something nice.
"""
function mergeRangeBars(range) {
  var sheet = range.getSheet();
  for (var r = range.getRow(); r <= range.getLastRow(); r++) {
    for (var c = range.getColumn(); c <= range.getLastColumn(); c++) {
      var firstValue = sheet.getRange(r, c).getValue();
      if (firstValue !== "") {
        // Start of a range, look for dashes
        cend = c+1;
        while (sheet.getRange(r, cend).getValue() === "-") {
          cend++;
        }
        cend--;
        var fullRange = sheet.getRange(r, c, 1, cend-c+1);
        if (cend != c) {
          fullRange.merge();
        }
        // Apply colors
        if (typeof firstValue === 'string') {
          var parts = firstValue.split('|');
          fullRange.setValue(parts[0]);
          if (parts.length > 1) {
            fullRange.setBackground(parts[1]);
          }
        }
      }
    }
  }
}

function doActive() {
  var range = SpreadsheetApp.getActiveSheet().getActiveRange();
  mergeRangeBars(range);
}

function doAll() {
  range = SpreadsheetApp.getActiveSheet().getDataRange();
  mergeRangeBars(range);
}

function createHeaders() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheets()[0];

  // Freezes the first two rows
  sheet.setFrozenRows(2);
}
"""
