#!/usr/bin/env python
#
# Interface to STEM and from that to Tord and the Tor network.
#
# Refs:
# - <https://stem.torproject.org/tutorials/over_the_river.html#ephemeral-hidden-services>
#
import logging, asyncio
from utils import json_loads, json_dumps, Singleton
from concurrent.futures import ThreadPoolExecutor
from persist import settings
from status import STATUS

logging.getLogger(__name__).addHandler(logging.NullHandler())

executor = ThreadPoolExecutor(max_workers=10)

class TorViaStem(metaclass=Singleton):
    def __init__(self):
        self.controller = None
        self.service = None

    async def startup(self):
        # just test if we can see tord
        await self.connect(raise_on_error=False)

    def get_current_addr(self):
        # return onion address we are currently on, or None
        if not self.service: 
            return None
        return self.service.service_id + '.onion'

    async def connect(self, raise_on_error=True):
        from stem.connection import connect

        if self.controller:
            return self.controller

        def doit():
            self.controller = connect(control_port=('127.0.0.1', settings.TORD_PORT))

            if self.controller:
                logging.info("Tord version: " + str(self.controller.get_version()))
            else:
                logging.error("Unable to connect to local 'tord' server")
                if raise_on_error:
                    raise RuntimeError("No local 'tord' server")


            return self.controller

        loop = asyncio.get_running_loop()
        rv = await loop.run_in_executor(executor, doit)

        STATUS.tord_good = bool(rv)
        STATUS.notify_watchers()

    async def pick_onion_addr(self):

        c = await self.connect()

        def doit():
            # let Tor pick the key, since they don't document their tricky stuff
            s = self.controller.create_ephemeral_hidden_service({80: 1},
                    detached=False,
                    await_publication=False, key_content='ED25519-V3')

            rv = (s.service_id+'.onion', s.private_key)

            # kill it immediately
            self.controller.remove_ephemeral_hidden_service(s.service_id)

            return rv

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(executor, doit)

    async def stop_tunnel(self):
        # hang up if running
        if not self.service:
            return

        def doit():
            if self.service:
                logging.info(f"Disconnecting previous service at: {self.service.service_id}.onion")
                self.controller.remove_ephemeral_hidden_service(self.service.service_id)
                self.service = None

        STATUS.onion_addr = None
        STATUS.notify_watchers()

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(executor, doit)

    async def start_tunnel(self):
        from persist import BP, settings

        c = await self.connect()

        def doit():
            if self.service:
                logging.info(f"Disconnecting previous service at: {self.service.service_id}.onion")
                self.controller.remove_ephemeral_hidden_service(self.service.service_id)
                self.service = None

            # give Tor the key from earlier run
            k = BP['onion_pk']
            s = self.controller.create_ephemeral_hidden_service({80: settings.PORT_NUMBER},
                    detached=False, discard_key=True,
                    await_publication=True, key_type='ED25519-V3', key_content=k)

            addr = s.service_id+'.onion' 
            assert addr == BP['onion_addr'], f"Mismatch, got: {addr} not {BP.onion_addr} expected"

            self.service = s

            return addr

        loop = asyncio.get_running_loop()
        addr = await loop.run_in_executor(executor, doit)

        STATUS.onion_addr = addr
        STATUS.notify_watchers()


TOR = TorViaStem()


if __name__ == '__main__':
    controller = connect()

    if not controller:
        sys.exit(1)  # unable to get a connection

    print('Your tord is version: %s' % controller.get_version())

    #d = controller.get_hidden_service_descriptor('explorernuoc63nb.onion')
    d = controller.get_hidden_service_descriptor('explorerzydxu5ecjrkwceayqybizmpjjznk5izmitf2modhcusuqlid.onion')
    print("obj = %r" % d)
    print("pubkey = %r" % d.permanent_key)
    print("published = %r" % d.published)

    service = controller.create_ephemeral_hidden_service({80: 5000}, await_publication = True, key_content = 'ED25519-V3')
    print("Started a new hidden service with the address of %s.onion" % service.service_id)

    print('%s %s' % (service.private_key_type, service.private_key))


    controller.close()

# EOF
