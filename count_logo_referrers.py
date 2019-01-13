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

"""
from __future__ import print_function

import collections
import glob
import gzip
import urlparse

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


class HostInfo(object):
    def __init__(self):
        self.hits = 0
        self.ips = set()

    def add(self, logline):
        self.hits += 1
        self.ips.add(logline.client_ip)


def gz_lines(gz_name):
    with gzip.open(gz_name) as gz:
        for line in gz:
            if not line.startswith('#'):
                yield line

def all_gz_lines():
    for gz_name in glob.glob("*.gz"):
        for line in gz_lines(gz_name):
            yield line

uris = collections.Counter()
hosts = collections.defaultdict(HostInfo)
for line in all_gz_lines():
    logline = LogLine(line)
    if logline.uri.startswith("/openedx-logos"):
        uris[logline.uri] += 1
        hosts[logline.host].add(logline)

hostinfos = sorted(hosts.iteritems(), key=lambda name_info: name_info[1].hits, reverse=True)
for name, info in hostinfos:
    print("{:>60}: {}, {} ips".format(name, info.hits, len(info.ips)))

print("-" * 50)
for uri, count in uris.most_common():
    print("{:<50}: {}".format(uri, count))
