import datetime
import functools
import pprint
import string

import colors
import dateutil.parser
import requests
from urlobject import URLObject
import yaml
from .util import paginated_get


class JObj(object):
    def __init__(self, obj):
        self.obj = obj

    def __repr__(self):
        return u"jreport.{cls}({obj!r})".format(
            cls=self.__class__.__name__, obj=self.obj,
        )

    def __getitem__(self, key):
        val = self.obj
        for k in key.split("."):
            val = val[k]
        return val

    def __setitem__(self, key, value):
        assert "." not in key
        self.obj[key] = value

    def get(self, *args, **kwargs):
        return self.obj.get(*args, **kwargs)

    def __contains__(self, item):
        return item in self.obj

    def format(self, fmt):
        return string.Formatter().vformat(fmt, (), JFormatObj(self.obj))

    def pprint(self):
        pprint.pprint(self.obj)


class JFormatObj(object):
    def __init__(self, obj):
        self.obj = obj

    def __repr__(self):
        return u"jreport.{cls}({obj!r})".format(
            cls=self.__class__.__name__, obj=self.obj,
        )

    def __getitem__(self, key):
        if key == "":
            return ""
        if key.startswith("'"):
            return key.strip("'")
        return Formattable(self.obj[key])


@functools.total_ordering
class Formattable(object):
    def __init__(self, v):
        self.v = v

    def __repr__(self):
        return u"jreport.{cls}({v!r})".format(
            cls=self.__class__.__name__, v=self.v,
        )

    def __eq__(self, other):
        return self.v == other.v

    def __lt__(self, other):
        return self.v < other.v

    def __str__(self):
        return str(self.v)

    def __getattr__(self, a):
        return Formattable(self.v[a])

    def __format__(self, spec):
        v = self.v
        for spec in spec.split(':'):
            try:
                v = format(v, spec)
            except ValueError:
                # Hmm, must be a custom one.
                if spec.startswith("%"):
                    v = format(dateutil.parser.parse(v), spec)
                elif spec in colors.COLORS:
                    v = colors.color(unicode(v), fg=spec)
                elif spec in colors.STYLES:
                    v = colors.color(v, style=spec)
                elif spec == "ago":
                    v = ago(v)
                elif spec == "oneline":
                    v = " ".join(v.split())
                elif spec == "pad":
                    v = " " + v + " "
                elif spec == "spacejoin":
                    v = " ".join(v)
                else:
                    raise Exception("Don't know formatting {!r}".format(spec))
        return v

def english_units(num, unit, brief):
    if brief:
        return "{num}{unit}".format(num=num, unit=unit[0])
    else:
        s = "" if num == 1 else "s"
        return "{num} {unit}{s}".format(num=num, unit=unit, s=s)

def ago(v, detail=2, brief=True):
    """Convert a datetime string into a '4 hours ago' string."""
    then = dateutil.parser.parse(v)
    then = then.replace(tzinfo=None)
    now = datetime.datetime.utcnow()
    delta = now-then
    chunks = []
    if delta.days:
        chunks.append(english_units(delta.days, "day", brief))
    hours, minutes = divmod(delta.seconds, 60*60)
    minutes, seconds = divmod(minutes, 60)
    if hours:
        chunks.append(english_units(hours, "hour", brief))
    if minutes:
        chunks.append(english_units(minutes, "minute", brief))
    if seconds:
        chunks.append(english_units(seconds, "second", brief))
    return " ".join(chunks[:detail])


class JReport(object):
    def __init__(self, debug=""):
        # If there's an auth.yaml, use it!
        self.auth = {}
        try:
            auth_file = open("auth.yaml")
        except IOError:
            pass
        else:
            with auth_file:
                self.auth = yaml.load(auth_file)

        self.debug = debug or ""
        if "http" in self.debug:
            # Yuck, but this is what requests says to do.
            import httplib
            httplib.HTTPConnection.debuglevel = 1

    def __repr__(self):
        return u"jreport.{cls}({debug!r})".format(
            cls=self.__class__.__name__, debug=self.debug,
        )

    def _prep(self, url, auth, params):
        url = URLObject(url).set_query_params(params or {})
        if not auth:
            auth = tuple(self.auth.get(url.hostname, {}).get("auth", ()))
        return url, auth

    def get_json_array(self, url, auth=None, params=None):
        url, auth = self._prep(url, auth, params)
        debug = ("json" in self.debug)
        return [JObj(item) for item in paginated_get(url, debug=debug, auth=auth)]

    def get_json_object(self, url, auth=None, params=None):
        url, auth = self._prep(url, auth, params)
        result = requests.get(url, auth=auth).json()
        if "json" in self.debug:
            pprint.pprint(result)
        return JObj(result)
