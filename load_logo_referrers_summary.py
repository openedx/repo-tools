"""
Read a set of logo log files, and count the referrers.

If you get logo log files, they will be a set of files named like this:

    E32IHGJJSQ4SLL.2015-05-24-00.04352996.gz
    E32IHGJJSQ4SLL.2015-05-24-00.13044708.gz
    E32IHGJJSQ4SLL.2015-05-24-00.3b9a7215.gz

This program will read all the *.gz files in the current directory, and
display information about hosts referring to the logos:

                    courses.edx.org: 56148, 32736 ips
              lagunita.stanford.edu: 5965, 4125 ips
          courses.prometheus.org.ua: 3672, 2399 ips
             university.mongodb.com: 3098, 2397 ips
                     localhost:8003: 1940, 30 ips

Each host shows how many hits there were (56148 in the first line) and
from how many unique IP addresses (32736).

Suggested queries:

select domain, min(date) from access_log_aggregate where domain not like '%.amazonaws.com' and domain not rlike '([[:digit:]]+\\.){3}[[:digit:]]+:?' and domain not rlike ':[[:digit:]]+' and domain not like '%.edx.org' group by domain order by min(date);

"""

import collections
import glob
import gzip
import urlparse
import MySQLdb
import os

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

db = MySQLdb.connect(host=os.environ.get("LOGOLOGS_MYSQL_HOST"),
                     user=os.environ.get("LOGOLOGS_MYSQL_USER"),         # your username
                     passwd=os.environ.get("LOGOLOGS_MYSQL_PASSWORD"),  # your password
                     db=os.environ.get("LOGOLOGS_MYSQL_DB"))        # name of the data base

db.get_warnings = True

class LogLine(object):
    def __init__(self, line):
        self.parts = line.split("\t")
        self.parsed = urlparse.urlparse(self.parts[9])

    @property
    def host(self):
        return self.parsed.netloc

    @property
    def client_ip(self):
        return self.parts[4]

    @property
    def uri(self):
        return self.parts[7]

    @property
    def date(self):
        return self.parts[0]

    @property
    def time(self):
        return self.parts[1]


class HostInfo(object):
    def __init__(self):
        self.hits = 0
        self.ips = set()

    def add(self, logline):
        self.hits += 1
        self.ips.add(logline.client_ip)



def is_in_filename_log(cur, log_name):
    select_from_file_hist = "SELECT COUNT(*) FROM filename_log where filename = %s"
    cur.execute(select_from_file_hist, [log_name])
    row = cur.fetchone()
    if(row[0] == 0):
        return False
    else:
        return True

def add_to_filename_log(cur, log_name):
    insert_into_file_hist = "INSERT INTO filename_log (filename) VALUES (%s)"
    cur.execute(insert_into_file_hist, [log_name])

def process_log_file(cur, gz_file, log_name):
    print "Processing %s ..." % log_name
    line_counter = {}
    for line in gz_file:
        if line.startswith('#'):
            continue

        logline = LogLine(line)
        if logline.uri.startswith("/openedx-logos"):
            line_key = "|".join((logline.host, logline.date, log_name))
            if line_counter.has_key(line_key):
                line_counter[line_key] += 1
            else:
                line_counter[line_key] = 1

    for aggregate_line_key in line_counter:
        (host, date, log_name) = aggregate_line_key.split("|")
        line_count = line_counter[aggregate_line_key]
        insert_stmt = "INSERT INTO access_log_aggregate (domain, date, filename, count) values (%s, %s, %s, %s)"
        cur.execute(insert_stmt,  (host, date, log_name, line_count))
        print "Inserted %d rows" % cur.rowcount
    db.commit()

cur = db.cursor()

for gz_name in glob.glob("*.gz"):
    print gz_name
    with gzip.open(gz_name) as gz:
        if(not is_in_filename_log(cur, gz_name)):
            print "%s not found, adding" % gz_name
            add_to_filename_log(cur, gz_name)
            process_log_file(cur, gz, gz_name)
db.close()
