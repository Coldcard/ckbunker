# (c) Copyright 2020 by Coinkite Inc. This file is part of Coldcard <coldcardwallet.com>
# and is covered by GPLv3 license found in COPYING.
#
# utils.py
#
import json, struct, logging, asyncio
from binascii import b2a_hex
from objstruct import ObjectStruct
from decimal import Decimal

B2A = lambda x: b2a_hex(x).decode('ascii')

def xfp2str(xfp):
    # Standardized way to show an xpub's fingerprint... it's a 4-byte string
    # and not really an integer. Used to show as '0x%08x' but that's wrong endian.
    return b2a_hex(struct.pack('<I', xfp)).decode('ascii').upper()

def json_dumps(obj, **k):
    def hook(dd):
        if isinstance(dd, Decimal):
            return float(dd)
        if hasattr(dd, 'strftime'):
            return str(dd)       # isoformat
        logging.error("Unhandled JSON type: %r" % dd)
        raise TypeError

    k['default'] = hook

    return json.dumps(obj, **k)

def json_loads(*a, **k):
    # more useful args for json.loads
    k.setdefault('object_hook', ObjectStruct)
    k.setdefault('parse_float', Decimal)
    return json.loads(*a, **k)    

def pformat_json(o):
    # for humans, who might pipe JSON around and debug it first
    return json_dumps(o, sort_keys=True, indent=2)

# from <https://stackoverflow.com/questions/6760685>
# use like this:
#       class Foo(metaclass=Singleton): ...
#
class Singleton(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]

def setup_logging(level=logging.INFO, debug=True, syslog=False):
    # get logging working for simple test code
    # - also used for normal logging

    handlers = None
    if syslog:
        # this shows up in /var/log/user.log
        from logging.handlers import SysLogHandler
        handlers = [ SysLogHandler('/dev/log')]

    logging.basicConfig(format="%(asctime)-11s %(message)s",
                            datefmt="[%d/%m/%Y-%H:%M:%S]", level=level, handlers=handlers)

    # maybe?
    #import warnings
    #warnings.simplefilter("ignore")

    # kill log noise about _UnixReadPipeTransport
    logging.getLogger('asyncio').setLevel(level=logging.WARN)

    # kill noise from STEM (tor wrapper)
    from stem.util.log import get_logger as sgl
    sgl().setLevel(level=logging.WARN)

    if 0:
        # disable access logging
        logging.getLogger('aiohttp.access').setLevel(level=logging.WARN)

def cleanup_psbt(psbt):
    from base64 import b64decode
    from binascii import a2b_hex
    import re
    from hashlib import sha256

    # we have the bytes, but might be encoded as hex or base64 inside
    taste = psbt[0:10]
    if taste.lower() == b'70736274ff':
        # Looks hex encoded; make into binary again
        hx = ''.join(re.findall(r'[0-9a-fA-F]*', psbt.decode('ascii')))
        psbt = a2b_hex(hx)
    elif taste[0:6] == b'cHNidP':
        # Base64 encoded input
        psbt = b64decode(psbt)

    if psbt[0:5] != b'psbt\xff':
        raise ValueError("File does not have PSBT magic number at start.")

    return psbt

class WatchableMixin:
    # add a consistent way to block for changes on an object

    def __init__(self, *a, **k):
        self._update_event = asyncio.Event()
        super(WatchableMixin, self).__init__(*a,**k)

    def notify_watchers(self):
        # unblock anyone watching us

        self._update_event.set()
        self._update_event.clear()

    async def wait(self):
        await self._update_event.wait()
        return self


# EOF
