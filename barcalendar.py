#!/usr/bin/env python3.6
"""
Write JavaScript code to be pasted into a Google Sheet to draw a calendar.

0. Update the data. Search for "Editable content" below.
1. Run this program.  It prints JavaScript code. Copy it.
2. Open a Google Sheet, either the existing Support Windows spreadsheet
    (https://docs.google.com/spreadsheets/d/11DheEtMDGrbA9hsUvZ2SEd4Cc8CaC4mAfoV8SVaLBGI)
    or a new spreadsheet.
3. If the current tab isn't empty, open a new tab (Add Sheet).
4. Open the script editor (Tools - Script Editor).
5. If there's any code there, delete it.
6. Paste the JavaScript code this program wrote.
7. Save the code.  The function picker at the top should select makeBarCalendar.
8. Click the Run tool on the toolbar.
9. Your sheet should now be populated with a beautiful calendar.

"""

import colorsys
import datetime
import itertools


def css_to_rgb(hex):
    assert hex[0] == "#"
    return [int(h, 16)/255 for h in [hex[1:3], hex[3:5], hex[5:7]]]

def rgb_to_css(r, g, b):
    return "#" + "".join(f"{int(v*255):02x}" for v in (r, g, b))

def lighten(css, amount=0.5):
    """Make a CSS color some amount lighter."""
    h, l, s = colorsys.rgb_to_hls(*css_to_rgb(css))
    lighter = colorsys.hls_to_rgb(h, l + (1 - l) * amount, s)
    return rgb_to_css(*lighter)


def darken(css, amount=0.5):
    """Make a CSS color some amount darker."""
    h, l, s = colorsys.rgb_to_hls(*css_to_rgb(css))
    lighter = colorsys.hls_to_rgb(h, l - l * amount, s)
    return rgb_to_css(*lighter)


class BaseCalendar:
    def __init__(self, start, end):
        self.start = start
        self.end = end
        self.width = 12 * (end - start + 1)

    def column(self, year, month):
        return (year - self.start) * 12 + month - 1

    def bar(self, name, start, end=None, length=None, **kwargs):
        istart = self.column(*start)
        if length is None:
            iend = self.column(*end)
        else:
            iend = istart + length - 1
        if istart >= self.width:
            return  # bar is entirely in the future.
        if iend < 0:
            return  # bar is entirely in the past.
        istart = max(0, istart)
        iend = min(self.width - 1, iend)
        if end and end[0] == 3000:
            kwargs.update(indefinite=True)
        self.rawbar(istart, iend, name, **kwargs)


class GsheetCalendar(BaseCalendar):
    def __init__(self, start, end):
        super().__init__(start, end)
        self.currow = 1
        self.cycling = None
        self.gaps = []
        self.prologue()

    def prologue(self):
        print(f"""\
            function makeBarCalendar() {{
            var sheet = SpreadsheetApp.getActiveSheet();
            sheet.getDataRange().deleteCells(SpreadsheetApp.Dimension.ROWS);
            """)

    def epilog(self):
        print(f"""\
            range = sheet.getDataRange();
            sheet.setColumnWidths(range.getColumn(), range.getWidth(), 12);
            sheet.setRowHeights(range.getRow(), range.getHeight(), 18);
            range.setFontSize(9);
            """)
        for gap_row in self.gaps:
            print(f"""\
                sheet.setRowHeight({gap_row}, 6);
            """)
        print(f"""\
            var keepRows = 10;
            var tooMany = sheet.getMaxRows() - range.getLastRow() - keepRows;
            if (tooMany > 0) {{
                sheet.deleteRows(range.getLastRow() + keepRows + 1, tooMany);
            }}
            var keepCols = 1;
            var tooMany = sheet.getMaxColumns() - range.getLastColumn() - keepCols;
            if (tooMany > 0) {{
                sheet.deleteColumns(range.getLastColumn() + keepCols + 1, tooMany);
            }}

            for (var c = 12; c <= range.getLastColumn(); c += 12) {{
                sheet.getRange(1, c, sheet.getMaxRows(), 1)
                    .setBorder(null, null, null, true, null, null, "black", null);
            }}

            }}
            """)

    def years_months(self):
        yearrow = self.currow
        monthrow = self.currow + 1
        self.currow += 2

        print(f"""\
            sheet.insertColumns(1, {(self.end - self.start + 1) * 12});
            """)

        for year in range(self.start, self.end+1):
            iyear = self.column(year, 1) + 1
            print(f"""\
                sheet.getRange({yearrow}, {iyear}, 1, 12)
                    .merge()
                    .setBorder(null, null, null, true, null, null, "black", null)
                    .setValue("{year}");
                for (m = 0; m < 12; m++) {{
                    sheet.getRange({monthrow}, {iyear}+m).setValue("JFMAMJJASOND"[m]);
                }}
                """);
        print(f"""\
            sheet.getRange({yearrow}, 1, 1, {self.width})
                .setFontWeight("bold")
                .setHorizontalAlignment("center");
            sheet.getRange({monthrow}, 1, 1, {self.width})
                .setHorizontalAlignment("center");
            """);
        print(f"""\
            var rules = sheet.getConditionalFormatRules();
            rules.push(
            SpreadsheetApp.newConditionalFormatRule()
                .whenFormulaSatisfied("=(year(now())-$A$1)*12+1 = column()")
                .setBackground("#E9CECE")
                .setRanges([sheet.getRange({yearrow}, 1, 1, {self.width})])
                .build()
            );
            rules.push(
            SpreadsheetApp.newConditionalFormatRule()
                .whenFormulaSatisfied("=(year(now())-$A$1)*12 + (month(now())) = column()")
                .setBackground("#E9CECE")
                .setRanges([sheet.getRange({monthrow}, 1, 1, {self.width})])
                .build()
            );
            sheet.setConditionalFormatRules(rules);
            """)

    def rawbar(self, istart, iend, name, color=None, text_color=None, current=False, indefinite=False):
        formatting = ""
        if color:
            if current:
                color = darken(color, .15)
            formatting += f""".setBackground({color!r})"""
        if text_color:
            formatting += f""".setFontColor({text_color!r})"""
        if current:
            formatting += f""".setBorder(true, true, true, true, null, null, "black", SpreadsheetApp.BorderStyle.SOLID_MEDIUM)"""
            formatting += f""".setFontWeight("bold")"""
        if indefinite:
            iend = self.width - 24
        print(f"""\
            sheet.getRange({self.currow}, {istart + 1}, 1, {iend - istart + 1})
                .merge()
                {formatting}
                .setValue({name!r});
            """)
        if indefinite:
            for i in range(4):
                bg = lighten(color, amount=(i+1)/5)
                print(f"""\
                    sheet.getRange({self.currow}, {self.width - 22 + i * 3}, 1, 3)
                        .merge()
                        .setBackground({bg!r});
                    """)
            print(f"""\
                sheet.getRange({self.currow}, {self.width - 10}, 1, 1)
                    .setValue("(indefinite end)");
                """)
        self.next_bar()

    def set_cycling(self, cycling):
        if cycling:
            self.top_cycling_row = self.currow
        else:
            self.currow = self.top_cycling_row + self.cycling
        self.cycling = cycling

    def next_bar(self):
        self.currow += 1
        if self.cycling:
            if self.currow >= self.top_cycling_row + self.cycling:
                self.currow = self.top_cycling_row

    def gap_line(self):
        self.gaps.append(self.currow)
        self.currow += 1

    def text_line(self, text):
        print(f"""\
            sheet.getRange({self.currow}, 1).setValue({text!r})
            """)
        self.currow += 1

    def section_note(self, text):
        print(f"""\
            sheet.getRange({self.currow}, {self.width - 10}).setValue({text!r});
            """)

    def freeze_here(self):
        print(f"""\
            sheet.setFrozenRows({self.currow - 1});
            """)

    def column_marker(self, column):
        print(f"""\
            sheet.getRange(1, {column}, sheet.getMaxRows(), 1)
                .setBorder(false, false, false, true, false, false, "black", SpreadsheetApp.BorderStyle.DASHED);
            """)

    def write(self):
        self.epilog()


# ==== Editable content ====

# Global Options
START_YEAR = 2017
END_YEAR = 2025
LTS_ONLY = True

# The current versions of everything.  Use the same strings as the keys in the various sections below.
CURRENT = {
    "Open edX": "Juniper",
    "Python": "3.5",
    "Django": "2.2",
    "Ubuntu": "16.04",
    "Node": "12.x",
    "Mongo": "3.6",
    "MySQL": "5.6",
    "elasticsearch": "1.5",
    "ruby": "2.5",
}

cal = GsheetCalendar(START_YEAR, END_YEAR)
cal.years_months()


# Open edX releases
cal.section_note("https://edx.readthedocs.io/projects/edx-developer-docs/en/latest/named_releases.html")
cal.set_cycling(3)
names = [
    # (Name, Year, Month) when the release happened.
    ('Aspen', 2014, 10),
    ('Birch', 2015, 2),
    ('Cypress', 2015, 8),
    ('Dogwood', 2016, 2),
    ('Eucalyptus', 2016, 8),
    ('Ficus', 2017, 2),
    ('Ginkgo', 2017, 8),
    ('Hawthorn', 2018, 8),
    ('Ironwood', 2019, 3),
    ('Juniper', 2020, 6),
    ]
# https://www.treenames.net/common_tree_names.html
future = ['Koa', 'Lilac', 'Maple', 'Nutmeg', 'Olive'] + list('PQRSTUVWXYZ')
target_length = 6 # months per release

releases = list(itertools.chain(names, [(name, None, None) for name in future]))
last = (None, None)
last_current = False
for (name, year, month), (_, nextyear, nextmonth) in zip(releases, releases[1:]):
    if year is None:
        year, month = last
        month += target_length
        yearplus, month = divmod(month, 12)
        year += yearplus
    if nextyear is None:
        length = target_length
    else:
        length = (nextyear * 12 + nextmonth) - (year * 12 + month)
    current = (name==CURRENT["Open edX"])
    cal.bar(name, start=(year, month), length=length, color="#fce5cd", current=current)
    if last_current:
        cal.column_marker(cal.column(year, month) + length)
    last = (year, month)
    last_current = current

cal.set_cycling(None)
cal.freeze_here()
cal.text_line(
    "This calendar is part of OEP-10, please don't change it without considering the impact there." +
    " Last updated {:%d-%b-%Y}".format(datetime.datetime.now())
)

# Django releases
cal.section_note("https://www.djangoproject.com/download/#supported-versions")
django_releases = [
    # (Version, Year, Month, Is_LTS) when the release happened.
    #('1.8', 2015, 4, True),
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
    cal.bar(f"Django {name}", start=(year, month), length=length, color=color, current=(name==CURRENT["Django"]))
cal.gap_line()

# Python releases
python_releases = [
    # Version, and Year-Month for start and end of support.
    #('2.7', 2010, 7, 2019, 12),
    ('3.5', 2015, 9, 2020, 9),          # https://www.python.org/dev/peps/pep-0478/
    #('3.6', 2016, 12, 2021, 12),        # https://www.python.org/dev/peps/pep-0494/
    #('3.7', 2018, 6, 2023, 6),          # https://www.python.org/dev/peps/pep-0537/
    ('3.8', 2019, 10, 2024, 10),        # https://www.python.org/dev/peps/pep-0569/
    ('3.9', 2020, 10, 2025, 10),        # https://www.python.org/dev/peps/pep-0596/
]
for name, syear, smonth, eyear, emonth in python_releases:
    cal.bar(f"Python {name}", start=(syear, smonth), end=(eyear, emonth), color="#ffd545", current=(name==CURRENT["Python"]))
cal.gap_line()

# Ubuntu releases
ubuntu_nicks = {                        # https://wiki.ubuntu.com/Releases
    '16.04': 'Xenial Xerus',
    '18.04': 'Bionic Beaver',
    '20.04': 'Focal Fossa',
}

for year, month in itertools.product(range(16, 23), [4, 10]):
    name = "{:d}.{:02d}".format(year, month)
    lts = (year % 2 == 0) and (month == 4)
    if LTS_ONLY and not lts:
        continue
    length = 5*12 if lts else 9
    color = "#E95420" if lts else "#F4AA90"     # http://design.ubuntu.com/brand/colour-palette
    nick = ubuntu_nicks.get(name, '')
    if nick:
        nick = f" {nick}"
    cal.bar(f"Ubuntu {name}{nick}", (2000+year, month), length=length, color=color, text_color="white", current=(name==CURRENT["Ubuntu"]))
cal.gap_line()

# Node releases
cal.section_note("https://github.com/nodejs/Release")
node_releases = [
    #('6.x', 2016, 4, 2019, 4),
    #('8.x', 2017, 5, 2019, 12),
    ('10.x', 2018, 4, 2021, 4),
    ('12.x', 2019, 4, 2022, 4),
    ('14.x', 2020, 4, 2023, 4),
]
for name, syear, smonth, eyear, emonth in node_releases:
    cal.bar(f"Node {name}", start=(syear, smonth), end=(eyear, emonth), color="#2f6c1b", text_color="white", current=(name==CURRENT["Node"]))
cal.gap_line()

# Mongo releases
cal.section_note("https://www.mongodb.com/support-policy")      # search for MongoDB Server
mongo_releases = [
    #('3.0', 2015, 3, 2018, 2),
    #('3.2', 2015, 12, 2018, 9),
    #('3.4', 2016, 11, 2020, 1),
    ('3.6', 2017, 11, 2021, 4),
    ('4.0', 2018, 6, 2022, 1),
    ('4.2', 2019, 8, 3000, 1),
]
for name, syear, smonth, eyear, emonth in mongo_releases:
    cal.bar(f"Mongo {name}", start=(syear, smonth), end=(eyear, emonth), color="#4da65a", current=(name==CURRENT["Mongo"]))
cal.gap_line()

# MySQL releases
cal.section_note("https://endoflife.software/applications/databases/mysql")
mysql_releases = [
    ('5.6', 2013, 2, 2021, 2),
    ('5.7', 2015, 10, 2023, 10),
    ('8.0', 2018, 4, 3000, 1),
]
for name, syear, smonth, eyear, emonth in mysql_releases:
    cal.bar(f"MySQL {name}", start=(syear, smonth), end=(eyear, emonth), color="#b9dc48", current=(name==CURRENT["MySQL"]))
cal.gap_line()

# elasticsearch releases
cal.section_note("https://www.elastic.co/support/eol")
es_releases = [
    ('1.5', 2015, 3, 2016, 9),
    ('1.7', 2015, 7, 2017, 1),
    ('2.4', 2016, 8, 2018, 2),
    ('5.6', 2017, 9, 2019, 3),
    ('6.8', 2019, 5, 2020, 11),
    ('7.8', 2020, 6, 2021, 12),
]
for name, syear, smonth, eyear, emonth in es_releases:
    cal.bar(f"elasticsearch {name}", start=(syear, smonth), end=(eyear, emonth), color="#4595ba", current=(name==CURRENT["elasticsearch"]))
cal.gap_line()

# ruby
cal.section_note("https://www.ruby-lang.org/en/downloads/branches/")
ruby_releases = [
    #('2.3', 2015, 12, 2019, 3),
    #('2.4', 2016, 12, 2020, 3),
    ('2.5', 2017, 12, 3000, 1),
    ('2.6', 2018, 12, 3000, 1),
]
for name, syear, smonth, eyear, emonth in ruby_releases:
    cal.bar(f"ruby {name}", start=(syear, smonth), end=(eyear, emonth), color="#DE3F24", current=(name==CURRENT["ruby"]))
cal.gap_line()


cal.text_line("")
cal.text_line("Created by https://github.com/edx/repo-tools/blob/master/barcalendar.py")

cal.write()
