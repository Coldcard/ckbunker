# Copyright 2020 by Coinkite Inc. This file is covered by license found in COPYING-CC.
#
# Connection to Coldcard (and/or simulator).
#
import asyncio, logging, os
from utils import Singleton, xfp2str, json_loads, json_dumps
from status import STATUS
from persist import settings, BP
from binascii import a2b_hex
import policy
from objstruct import ObjectStruct
from hmac import HMAC
from hashlib import sha256
from concurrent.futures import ThreadPoolExecutor

from ckcc.protocol import CCProtocolPacker, CCFramingError
from ckcc.protocol import CCProtoError, CCUserRefused
from ckcc.constants import USB_NCRY_V2
from ckcc.client import ColdcardDevice
from ckcc.constants import (USER_AUTH_TOTP, USER_AUTH_HMAC, USER_AUTH_SHOW_QR, MAX_USERNAME_LEN)
from ckcc.utils import calc_local_pincode

logging.getLogger(__name__).addHandler(logging.NullHandler())

executor = ThreadPoolExecutor(max_workers=5)

# if you see this, it means the USB plug is fell out!
class MissingColdcard(RuntimeError):
    pass

#logging.info("fd = %d" % open('/dev/null').fileno())

class Connection(metaclass=Singleton):

    def __init__(self, serial):
        self.serial = serial
        self.dev = None
        self.dev_key = None
        self.lock = asyncio.Lock()
        self.sign_lock = asyncio.Lock()
        self._conn_broken(setup_time=True)

    async def run(self):
        # connect to, and maintain a connection to a single Coldcard

        logging.info("Connecting to Coldcard.")

        while 1:
            try:
                if not self.serial and os.path.exists(settings.SIMULATOR_SOCK):
                    # if simulator is running, just use it.
                    sn = settings.SIMULATOR_SOCK
                else:
                    sn = self.serial

                ncry_ver = settings.USB_NCRY_VERSION
                d = ColdcardDevice(sn=sn, ncry_ver=ncry_ver)
                logging.info(f"Found Coldcard {d.serial}. USB encryption version: {ncry_ver}")

                await asyncio.get_running_loop().run_in_executor(executor, d.check_mitm)

                async with self.lock:
                    self.dev = d
            except:
                logging.error("Cannot connect to Coldcard (will retry)", exc_info=0)
                await asyncio.sleep(settings.RECONNECT_DELAY)
                continue

            # stay connected, and check we are working periodically
            logging.info(f"Connected to Coldcard {self.dev.serial}.")

            STATUS.connected = True

            # read static info about coldcard
            STATUS.xfp = xfp2str(self.dev.master_fingerprint)
            STATUS.serial_number = self.dev.serial
            STATUS.is_testnet = (self.dev.master_xpub[0] == 't')
            STATUS.hsm = {}
            STATUS.reset_pending_auth()
            STATUS.notify_watchers()
            await self.hsm_status()

            while 1:
                await asyncio.sleep(settings.PING_RATE)
                try:
                    # use long timeout here, even tho simple command, because the CC may
                    # we working on something else right now (thinking).
                    h = await self.send_recv(CCProtocolPacker.hsm_status(), timeout=20000)
                    logging.info("ping ok")
                    await self.hsm_status(h)
                except MissingColdcard:
                    self._conn_broken()
                    break
                except:
                    logging.error("Ping failed", exc_info=1)

    def _conn_broken(self, setup_time=False):
        # our connection is lost, so clear/reset system state
        if self.dev:
            self.dev.close()
            self.dev = None

        STATUS.connected = False
        STATUS.xfp = None
        STATUS.serial_number = None
        STATUS.is_testnet = False
        STATUS.hsm = {}
        STATUS.reset_pending_auth()

        if not setup_time:
            BP.reset()

        STATUS.notify_watchers()

    async def activated_hsm(self):
        # just connected to a Coldcard w/ HSM active already
        # - ready storage locker, decrypt and use those settings
        logging.info("Coldcard now in HSM mode. Fetching storage locker.")

        try:
            sl = await self.get_storage_locker()
        except CCProtoError as exc:
            if 'consumed' in str(exc):
                import os, sys
                msg = "Coldcard refused access to storage locker. Reboot it and enter HSM again"
                logging.error(msg)
                print(msg, file=sys.stderr)
                sys.exit(1)
            else:
                raise
            
        try:
            import policy
            xk = policy.decode_sl(sl)
        except:
            logging.error("Unable to parse contents of storage locker: %r" % sl)
            return

        if BP.open(xk):
            # unable to read our settings specific to this CC? Go to defaults
            # or continue?
            logging.error("Unable to read bunker settings for this Coldcard; forging on")
        else:
            STATUS.sl_loaded = True

        if BP.get('tor_enabled', False) and not (STATUS.force_local_mode or STATUS.setup_mode):
            # get onto Tor as a HS
            from torsion import TOR
            STATUS.tor_enabled = True
            logging.info(f"Starting hidden service: %s" % BP['onion_addr'])
            asyncio.create_task(TOR.start_tunnel())

        h = STATUS.hsm
        if ('summary' in h) and h.summary and not BP.get('priv_over_ux') and not BP.get('summary'):
            logging.info("Captured CC's summary of the policy")
            BP['summary'] = h.summary
            BP.save()

        STATUS.reset_pending_auth()
        STATUS.notify_watchers()

    async def send_recv(self, msg, **kws):
        # a more-async version of ColdcardDevice.send_recv?

        if not self.dev or not STATUS.connected:
            raise MissingColdcard
        
        try:
            def doit():
                return self.dev.send_recv(msg, **kws)

            # we do need this lock
            async with self.lock:
                return await asyncio.get_running_loop().run_in_executor(executor, doit)

        except CCFramingError:
            self._conn_broken()
            raise MissingColdcard
        except (CCProtoError, CCUserRefused):
            raise
        except BaseException as exc:
            logging.error(f"Error from Coldcard: {exc} (for msg: {msg!r}")
            self._conn_broken()
            raise MissingColdcard

    async def hsm_status(self, h=None):
        # refresh HSM status
        b4 = STATUS.hsm.get('active', False)

        try:
            b4_nlc = STATUS.hsm.get('next_local_code')
            h = h or (await self.send_recv(CCProtocolPacker.hsm_status()))
            STATUS.hsm = h = json_loads(h)
            STATUS.notify_watchers()
        except MissingColdcard:
            h = {}

        if h.get('next_local_code') and STATUS.psbt_hash:
            if b4_nlc != h.next_local_code:
                STATUS.local_code = calc_local_pincode(a2b_hex(STATUS.psbt_hash), h.next_local_code)
        else:
            # won't be required
            STATUS.local_code = None

        # has it just transitioned into HSM mode?
        if STATUS.connected and STATUS.hsm.active and not b4:
            await self.activated_hsm()

        return STATUS.hsm
            
    async def hsm_start(self, new_policy=None):
        args = []
        if new_policy is not None:
            # must upload it first
            data = json_dumps(new_policy).encode('utf8')
            args = self.dev.upload_file(data)

            # save a trimmed copy of some details, if they want that
            bk = policy.desensitize(new_policy)
            BP['summary'] = None
            if not bk.get('priv_over_ux'):
                BP['priv_over_ux'] = False
                BP['policy'] = bk       # full copy
                BP['xfp'] = xfp2str(self.dev.master_fingerprint)
                BP['serial'] = self.dev.serial
            else:
                BP['priv_over_ux'] = True
                BP['policy'] = None
                BP['xfp'] = None
                BP['serial'] = None

            BP.save()

        try:
            await self.send_recv(CCProtocolPacker.hsm_start(*args))
        except CCProtoError as exc:
            msg = str(exc)
            logging.error("Coldcard didn't like policy: %s" % msg)
            raise RuntimeError(str(msg))

    async def delete_user(self, username):
        await self.send_recv(CCProtocolPacker.delete_user(username))

    async def create_user(self, username, authmode, new_pw=None):
        # typically we'll let Coldcard pick password
        if authmode == USER_AUTH_HMAC and new_pw:
            secret = self.dev.hash_password(new_pw.encode('utf8'))
        else:
            secret = b''

        await self.send_recv(CCProtocolPacker.create_user(username, authmode, secret))
    
    async def user_auth(self, username, token, totp, psbt_hash):
        if len(token) == 6 and token.isdigit():
            # assume TOTP if token (password) is 6-numeric digits
            totp_time = totp or int(time.time() // 30)
            token = token.encode('ascii')
        else:
            # assume it's a raw password. need to hash it up
            # TODO: move this hashing into browser
            secret = self.dev.hash_password(token.encode('utf8'))
            token = HMAC(secret, msg=psbt_hash, digestmod=sha256).digest()
            totp_time = 0

        await self.send_recv(CCProtocolPacker.user_auth(username.encode('ascii'), token, totp_time))

    async def get_storage_locker(self):
        return await self.send_recv(CCProtocolPacker.get_storage_locker())

    async def sign_psbt(self, data, finalize=False, flags=0x0):
        # upload it first

        async with self.sign_lock:
            sz, chk = self.dev.upload_file(data)
            assert chk == a2b_hex(STATUS.psbt_hash)

            await self.send_recv(CCProtocolPacker.sign_transaction(sz, chk, finalize, flags))

            # wait for it to finish
            return await self.wait_and_download(CCProtocolPacker.get_signed_txn())

    async def wait_and_download(self, req, fn=1):
        # Wait for user action (sic) on the device... by polling w/ indicated request
        # - also download resulting file

        while 1:
            await asyncio.sleep(0.250)
            done = await self.send_recv(req, timeout=None)
            if done == None:
                continue
            break

        if len(done) != 2:
            logging.error('Coldcard failed: %r' % done)
            raise RuntimeError(done)

        result_len, result_sha = done

        # download the result.
        result = self.dev.download_file(result_len, result_sha, file_number=fn)

        return result

    async def sign_text_msg(self, msg, subpath, addr_fmt):
        # send text and path to sign with; no policy check

        msg = msg.encode('ascii')

        async with self.sign_lock:
            try:
                await self.send_recv(CCProtocolPacker.sign_message(msg, subpath, addr_fmt))

                while 1:
                    await asyncio.sleep(0.250)
                    done = await self.send_recv(CCProtocolPacker.get_signed_msg(), timeout=None)
                    if done == None:
                        continue
                    break

            except CCUserRefused:
                raise RuntimeError("Coldcard refused request based on policy.")

        if len(done) != 2:
            logging.error('Coldcard failed: %r' % done)
            raise RuntimeError(done)

        addr, sig = done

        return sig, addr



# EOF
