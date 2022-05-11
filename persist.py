#!/usr/bin/env python
#
# Persistent data for Bunker itself. Trying to minimize this for privacy.
#
import os, yaml, nacl.secret, logging
from utils import Singleton, xfp2str, json_dumps, json_loads, WatchableMixin
from hashlib import sha256
from objstruct import ObjectStruct

logging.getLogger(__name__).addHandler(logging.NullHandler())

# globals, used system-wide
settings = None
BP = None

# System-wide settings for Bunker itself.
#
class Settings(metaclass=Singleton):

    # web server port 
    PORT_NUMBER = 9823

    # session idle time, before we kick you out and require re-auth (seconds)
    MAX_IDLE_TIME = 10*60

    # max time between showing login page, and the would-be user entering something useful (seconds)
    MAX_LOGIN_WAIT_TIME = 5*60

    # bogus fixed password to get started
    MASTER_PW = 'test1234'

    # default is harder captcha
    EASY_CAPTCHA = False

    # default for "allow reboot of bunker"
    # - can you restart the bunker w/o restarting the Coldcard HSM?
    ALLOW_REBOOTS = True

    # path to data files
    DATA_FILES = './data'

    # endpoint to use for sending txn; we assume it's Explora protocol (Blockstream.info)
    EXPLORA = 'http://explorerzydxu5ecjrkwceayqybizmpjjznk5izmitf2modhcusuqlid.onion'

    # port number for local instance of tord
    # - will try 9051 and 9151
    # - but first /var/run/tor/control as unix socket
    TORD_PORT = 'default'

    # for broadcasting, socks proxy via Tord
    TOR_SOCKS = 'socks5h://127.0.0.1:9150'

    # unix pipe for local Coldcard Simulator
    SIMULATOR_SOCK = '/tmp/ckcc-simulator.sock'

    # delay between retries connecting to missing/awol Coldcard
    RECONNECT_DELAY = 10        # seconds between retries
    PING_RATE = 15              # seconds between pings (CC status checks)
    USB_NCRY_VERSION = 0x01     # default ncry version is 1

    # USB encryption versions (default 1)
    #
    # V2 introduces a new ncry version to close a potential attack vector:
    #
    # A malicious program may re-initialize the connection encryption by sending the ncry command a second time during USB operation.
    # This may prove particularly harmful in HSM mode.
    #
    # Sending version 0x02 changes the behavior in two ways:
    #   * All future commands must be encrypted
    #   * Returns an error if the ncry command is sent again for the duration of the power cycle
    #
    # If using 0x02 and ckbunker is killed - you also need to re-login to Coldcard

    def read(self, fobj):
        t = yaml.safe_load(fobj)
        if not t: return

        for k,v in t.items():
            if k.upper() != k or k[0]=='_':
                logging.error(f"{k}: must be upper case")
                continue
            if not hasattr(self, k):
                logging.error(f"{k}: unknown setting")
                continue

            setattr(self, k, v)

    @classmethod
    def make_sample(cls):
        # produce an example config file
        d = {}
        x = cls()
        for k in dir(x):
            if k.upper() != k or k[0]=='_': continue
            d[k] = getattr(x, k)

        return yaml.safe_dump(d)

    @classmethod
    def startup(cls, config_file=None):
        # creates singleton
        global settings, BP

        # only safe place to create singletons is here
        assert not settings and not BP

        settings = Settings()
        if config_file:
            settings.read(config_file)

        # load defaults into BP 
        BP = BunkerPersistance()
        BP.reset()

# Store some state, encrypted.
# - inial values are the settings, but lower case for some reason
# - some are adjustable on "Bunker Setup" page
class BunkerPersistance(WatchableMixin, dict, metaclass=Singleton):
    fields = ['tor_enabled', 'onion_pk', 'onion_addr', 'allow_reboots',
                'easy_captcha', 'master_pw']

    def __init__(self):
        super(BunkerPersistance, self).__init__()
        self.filename = None
        self.reset()

    def reset(self):
        self.clear()
        self.set_secret(os.urandom(32))
        self.set_defaults()

    def set_defaults(self):
        # defaults here
        for fn in self.fields:
            if fn not in self:
                self[fn] = getattr(settings, fn.upper(), None)

    def set_secret(self, key):
        # setup for reading/writing using indicated key
        assert len(key) == 32

        self.key = key
        self.box = nacl.secret.SecretBox(self.key)
        
        # calc filename
        bn = 'bp-%s.dat' % sha256(sha256(b'salty' + self.key).digest()).hexdigest()[-16:].lower()
        self.filename =  os.path.join(settings.DATA_FILES, bn)

    def open(self, key):
        # Given a private key (via storage locker) open a Nacl secret box
        # and use that for the data.
        self.set_secret(key)

        try:
            with open(self.filename, 'rb') as fp:
                d = self.box.decrypt(fp.read())
            d = json_loads(d)
        except FileNotFoundError:
            logging.info("%s: not found (probably fine)" % self.filename)
            return True

        self.update(d)

        # copy a setting to status (XXX feels wrong)
        from status import STATUS 
        STATUS.tor_enabled = self.get('tor_enabled', False)

        logging.info(f"Got bunker settings from: {self.filename}")

    def save(self):
        fn = self.filename
        tmp = fn + '.tmp'
        with open(tmp, 'wb') as fp:
            d = json_dumps(dict(self)).encode('utf8')
            d = self.box.encrypt(d)
            fp.write(d)

        os.rename(tmp, fn)
        logging.info(f"Saved bunker settings to: {fn}")

        self.notify_watchers()

    def delete_file(self):
        # useful when changing keys; old file won't be readable
        try:
            os.unlink(self.filename)
            logging.info(f"Deleted bunker settings in: {self.filename}")
        except:
            pass


# EOF
