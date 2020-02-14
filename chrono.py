#
# Time/data related functions. Trying hard not to rewrite existing things.
#
# Everything should be stored/calculated in UTC.
#
import time, datetime, calendar, pendulum
from email.utils import formatdate as rfc_format

def NOW():
    # Use this for everything.
    return pendulum.now()

def TIME_AGO(**kws):
    # Return a time in past, like TIME_AGO(hours=3)
    return pendulum.now() - datetime.timedelta(**kws)

def TIME_FUTURE(**kws):
    # Return a time in future, like TIME_FUTURE(hours=3)
    return pendulum.now() + datetime.timedelta(**kws)

def as_time_t(dt):
    " convert datetime into unix timestamp (all UTC)"
    if hasattr(dt, 'timestamp'):
        # expected case for Pendulum values
        return dt.timestamp()
    else:
        return calendar.timegm(dt.utctimetuple())

def from_time_t(time_t):
    " convert unix timestamp into datetime (all UTC)"
    return pendulum.from_timestamp(time_t)

def from_iso(s):
    # Convert from ISO8601, and capture TZ
    return pendulum.parse(s)

# EOF
