#
# Store and watch all **status** values in system. 
#
import sys, logging, asyncio
from pprint import pprint, pformat
from decimal import Decimal
from chrono import NOW
from objstruct import ObjectStruct
from hashlib import sha256
from copy import deepcopy
from utils import WatchableMixin

logging.getLogger(__name__).addHandler(logging.NullHandler())

class SystemStatus(WatchableMixin, ObjectStruct):

    def __init__(self):
        # define all values here. keep simple, small!
        # - values must be JSON-able.
        super(SystemStatus, self).__init__()

        self.connected = False
        self.serial_number = None

        #self.xfp = None

        self.hsm = dict(users=[], wallets=[])            # short for "hsm_status"
        self.is_testnet = False

        # storage locker has been read ok.
        self.sl_loaded = False

        # user doesn't want Tor regardless of other settings (also disables login process)
        self.force_local_mode = False

        # we are in setup mode
        self.setup_mode = False

        # PSBT related
        self._pending_psbt = None            # raw binary
        self.psbt_hash = None                # hex digits (sha256)
        self.psbt_size = None                # size of binary
        self.local_code = None               # string of 6 digits 
        self.psbt_preview = None             # text
        self.busy_signing = False

        # tor related
        self.tord_good = False          # local tord control connection good
        self.onion_addr = None          # our present onion addr, if any
        self.tor_enabled = False        # config calls for tor (ie. BP['tor_enabled'])

        # list of structs about creditials given by remote users
        self.pending_auth = []

    def reset_pending_auth(self):
        # clear and setup pending auth list
        from persist import BP

        # make a list of users that might need to auth
        ul = self.hsm.get('users')
        if not ul:
            if BP.get('policy'):
                ul = set()
                try:
                    for r in BP['policy']['rules']:
                        ul.union(r.users)
                except KeyError: pass
                ul = list(sorted(ul))

        # they might have picked privacy over UX, so provide some "slots"
        # regardless of above.
        if not ul:
            ul = ['' for i in range(5)]

        # construct an obj for UX purposes, but keep the actual secrets separate
        self.pending_auth = [ObjectStruct(name=n, has_name=bool(n),
                                            has_guess='', totp=0) for n in ul]
        self._auth_guess = [None]*len(ul)


    def clear_psbt(self):
        # wipe knowledge of PSBT
        self._pending_psbt = None
        self.psbt_hash = None
        self.psbt_size = None
        self.local_code = None
        self.psbt_preview = None

    def import_psbt(self, psbt):
        from ckcc.utils import calc_local_pincode
        from utils import cleanup_psbt
        from binascii import b2a_hex

        self.clear_psbt()

        self._pending_psbt = cleanup_psbt(psbt)

        self.psbt_size = len(self._pending_psbt)

        hh = sha256(self._pending_psbt).digest()
        self.psbt_hash = b2a_hex(hh).decode('ascii')

        # local PIN code will be wrong/stale now.
        if self.hsm and self.hsm.get('next_local_code'):
            self.local_code = calc_local_pincode(hh, self.hsm.next_local_code)

        logging.info("Imported PSBT with hash: " + self.psbt_hash)

    def as_dict(self):
        # we stream changes to web clients, so provide JSON
        return dict((k, deepcopy(self[k])) 
                        for k in self.keys() if k[0] != '_' and not callable(self[k]))


# singleton
STATUS = SystemStatus()

# EOF
