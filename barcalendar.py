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

# Options
START_YEAR = 2016
END_YEAR = 2024
LTS_ONLY = True


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

cal = Calendar(START_YEAR, END_YEAR)

# Open edX releases
names = [
    ('Aspen', 2014, 10),
    ('Birch', 2015, 2),
    ('Cypress', 2015, 8),
    ('Dogwood', 2016, 2),
    ('Eucalyptus', 2016, 8),
    ('Ficus', 2017, 2),
    ('Ginkgo', 2017, 8),
    ('Hawthorn', 2018, 8),
    ('Ironwood', 2019, 3),
    ('Juniper', 2019, 10),
    ]
future = ['Koa', 'Lilac', 'Maple'] + list('NOPQRST')
releases = list(itertools.chain(names, [(name, None, None) for name in future]))
last = (None, None)
for (name, year, month), (_, nextyear, nextmonth) in zip(releases, releases[1:]):
    if year is None:
        year, month = last
        month += 6
        yearplus, month = divmod(month, 12)
        year += yearplus
    if nextyear is None:
        length = 6
    else:
        length = (nextyear * 12 + nextmonth) - (year * 12 + month)
    cal.bar(name, start=(year, month), length=length, color="#fce5cd")
    last = (year, month)

# Django releases
django_releases = [
    ('1.8', 2015, 4, True),
    ('1.9', 2016, 1, False),
    ('1.10', 2016, 8, False),
    ('1.11', 2017, 4, True),
    ('2.0', 2018, 1, False),
    ('2.1', 2018, 8, False),
    ('2.2', 2019, 4, True),
    ('3.0', 2020, 1, False),
    ('3.1', 2020, 8, False),
    ('3.2', 2021, 4, True),
    ('4.0', 2022, 1, False),
]
for name, year, month, lts in django_releases:
    if LTS_ONLY and not lts:
        continue
    length = 3*12 if lts else 16
    color = "#44b78b" if lts else "#c9f0df"
    cal.bar(f"Django {name}", start=(year, month), length=length, color=color)

# Python releases
python_releases = [
    ('2.7', 2010, 7, 2019, 12),
    ('3.5', 2015, 9, 2020, 9),          # https://www.python.org/dev/peps/pep-0478/
    ('3.6', 2016, 12, 2021, 12),        # https://www.python.org/dev/peps/pep-0494/
    ('3.7', 2018, 6, 2023, 6),          # https://www.python.org/dev/peps/pep-0537/
    ('3.8', 2019, 10, 2024, 10),        # https://www.python.org/dev/peps/pep-0569/
]
for name, syear, smonth, eyear, emonth in python_releases:
    cal.bar(f"Python {name}", start=(syear, smonth), end=(eyear, emonth), color="#ffd545")

# Ubuntu releases
for year, month in itertools.product(range(16, 23), [4, 10]):
    name = "Ubuntu {:d}.{:02d}".format(year, month)
    lts = (year % 2 == 0) and (month == 4)
    if LTS_ONLY and not lts:
        continue
    length = 5*12 if lts else 9
    color = "#E95420" if lts else "#F4AA90"     # http://design.ubuntu.com/brand/colour-palette
    cal.bar(name, (2000+year, month), length=length, color=color)

# Node releases: https://github.com/nodejs/Release
node_releases = [
    ('6.x', 2016, 4, 2019, 4),
    ('8.x', 2017, 5, 2019, 12),
    ('10.x', 2018, 4, 2021, 4),
    ('12.x', 2019, 4, 2022, 4),
]
for name, syear, smonth, eyear, emonth in node_releases:
    cal.bar(f"Node {name}", start=(syear, smonth), end=(eyear, emonth), color="#2f6c1b")


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

function makeBarCalendar() {
  var sheet = SpreadsheetApp.getActiveSheet();
  var range = sheet.getDataRange();
  sheet.setColumnWidths(range.getColumn(), range.getWidth(), 12);
  sheet.setRowHeights(range.getRow(), range.getHeight(), 18);
  range.setFontSize(9);
  mergeRangeBars(range);
  sheet.setFrozenRows(2);
}
"""
# Also in the sheet:
# Open Script Editor. Select makeBarCalendar. Click the Run button. It's slow, be patient.
# Turn off gridlines
# Row 1: center and bold.
# Conditional formatting for row 2:
#   "Custom formula is:"
#   =(year(now())-$A$1)*12 + (month(now())) = column()
#   color red

# for row 1:
#   =(year(now())-$A$1)*12+1 = column()
#
# Put a dark outline around the current boxes by hand.
