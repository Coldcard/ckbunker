# (c) Copyright 2020 by Coinkite Inc. This file is part of Coldcard <coldcardwallet.com>
# and is covered by GPLv3 license found in COPYING.
#
# chain.py --- API to blockstream stuff
#
import sys, os, asyncio, logging, requests
from objstruct import ObjectStruct
from persist import settings
from status import STATUS
from binascii import b2a_hex, a2b_hex
from utils import json_loads

logging.getLogger(__name__).addHandler(logging.NullHandler())

def broadcast_txn(txn):
    # take bytes and get them shared over P2P to the world
    # - raise w/ text about what happened if it fails
    # - limited docs: <https://github.com/Blockstream/esplora/blob/master/API.md>
    ses = requests.session()
    ses.proxies = dict(http=settings.TOR_SOCKS)
    ses.headers.clear()     # hide user-agent

    url = settings.EXPLORA
    url += '/api/tx' if not STATUS.is_testnet else '/testnet/api/tx'

    assert '.onion/' in url, 'dude, your privacy'
    logging.warning(f"Sending txn via: {url}")
    resp = ses.post(url, data=b2a_hex(txn).decode('ascii'))

    msg = resp.text

    if not resp.ok:
        # content is like:
        #       sendrawtransaction RPC error: {"code":-22,"message":"TX decode failed"}
        # which is a text thing, including some JSON from bitcoind?

        if '"message":' in msg:
            try:
                prefix, rest = msg.split(': ', 1)
                j = json_loads(rest)
                if prefix == 'sendrawtransaction RPC error':
                    msg = j.message
                else:
                    msg = prefix + ': ' + j.message
            except:
                pass

        msg = f"Transaction broadcast FAILED: {msg}"
        logging.error(msg)
        return msg

    # untested
    msg = f"Transaction broadcast success: {msg}"
    logging.info(msg)

    return msg

def link_to_txn(txn_hash):
    path = '/tx/' if not STATUS.is_testnet else '/testnet/tx/'
    assert len(txn_hash) == 64
    return settings.EXPLORA + path + txn_hash
    

if __name__ == '__main__':
    # test code
    r = broadcast_txn(b'sdhffkhjkdfshdfshjdfshdfkshdfs')

# EOF
