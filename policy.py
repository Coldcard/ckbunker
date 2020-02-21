#!/usr/bin/env python
#
# policy.py -- code which knows various details about HSM policy as defined by Coldcard.
#
import re, logging
from decimal import Decimal
from objstruct import ObjectStruct
from persist import BP, settings
from base64 import b64encode, b64decode

logging.getLogger(__name__).addHandler(logging.NullHandler())

def invalid_pincode(code):
    return (not code) or (len(code) != 6) or (not code.isdigit())

def web_cleanup(p):
    # takes policy details from Vue/Semantic/web browser format into proper JSON-able dict
    # - final product should serialize into something the Coldcard will accept

    def relist(n):
        # split on spaces or commas, assume values don't have either; trim whitespace
        if n is None: return n
        return [i for i in re.split(r' |,|\n', n) if i]

    for fn in ['msg_paths', 'share_xpubs', 'share_addrs']:
        p[fn] = relist(p.get(fn, None))

    p.period = int(p.period) if p.period else None

    for idx, rule in enumerate(p.rules):
        for fn in ['whitelist', 'users']:
            rule[fn] = relist(rule[fn])

        # change from BTC to satoshis (send as string here)
        for fn in ['per_period', 'max_amount']:
            v = rule.get(fn, None) or None
            if v is not None:
                try:
                    v = Decimal(v)
                except:
                    raise ValueError(f"Rule #{idx+1} field {fn} is invalid: {rule[fn]}")
                rule[fn] = int(v * Decimal('1E8'))
            else:
                # cleans up empty strings
                rule[fn] = None

        # text to number
        if not rule.users:
            rule.pop('min_users')
        else:
            rule.min_users = len(rule.users) if rule.min_users == 'all' else int(rule.min_users)

    if p.pop('ewaste_enable', False):
        p.boot_to_hsm = 'xyzzy'     # impossible to enter
        assert invalid_pincode(p.boot_to_hsm)
    else:
        p.boot_to_hsm = p.get('boot_to_hsm') or None
        if p.boot_to_hsm:
            assert not invalid_pincode(p.boot_to_hsm), \
                "Boot to HSM code must be 6 numeric digits."

    return p

def web_cookup(proposed):
    # converse of above: take Coldcard policy file, and rework it so
    # Vue can display on webpage

    p = ObjectStruct.promote(proposed)

    def unlist(n):
        if not n: return ''
        return ','.join(n)

    for fn in ['msg_paths', 'share_xpubs', 'share_addrs']:
        p[fn] = unlist(p.get(fn))

    for rule in p.rules:
        for fn in ['whitelist', 'users']:
            rule[fn] = unlist(rule.get(fn))

        for fn in ['per_period', 'max_amount']:
            if rule[fn] is not None:
                rule[fn] = str(Decimal(rule[fn]) / Decimal('1E8'))

        if 'min_users' not in rule:
            rule.min_users = 'all'
        else:
            rule.min_users = str(rule.min_users)

    if ('boot_to_hsm' in p) and p.boot_to_hsm and invalid_pincode(p.boot_to_hsm):
        p.ewaste_enable = True
    else:
        p.ewaste_enable = False

    return p
    

def desensitize(policy):
    # remove the most sensitive stuff in the policy.
    bk = policy.copy()
    bk.pop('set_sl', None)
    bk.pop('allow_sl', None)
    bk.pop('boot_to_hsm', None)

    return bk

def decode_sl(xk):
    # Unpack what we saved into the Storage Locker
    # - 32 bytes of nacl secret box for BunkerPersistance, plus "Bunk" prefix => 36 bytes
    # - base64 encoded => 48 bytes (and has no padding)
    assert len(xk) == 48, repr(xk)
    xk = b64decode(xk)
    assert xk[0:4] == b'Bunk'
    rv = xk[4:]
    assert len(rv) == 32

    return rv

def update_sl(proposed):
    # We control the set_sl/allow_sl values solely for bunker purposes (sl=storage locker)

    # try to use any value already provided (but unlikely)
    xk = proposed.get('set_sl', None) or None
    if xk:
        try:
            xk = decode_sl(xk)
        except:
            logging.error("Unable to decode existing storage locker; replacing", exc_info=1)
            xk = None

    if not xk:
        if not BP.key or BP.is_default_secret():
            # pick a new key
            logging.info("Making new secret for holding Bunker settings")
            xk = BP.new_secret()
        else:
            # keep using same key
            xk = BP.key

        assert len(xk) == 32
        proposed['set_sl'] = b64encode(b'Bunk' + xk).decode('ascii')

    if xk != BP.key:
        # re-use existing key, and switch over to using new/eixsting key
        BP.delete_file()
        BP.set_secret(xk)
        BP.save()
    else:
        logging.info("Re-using old secret for holding Bunker settings")
        
    # simple fixed value for how many times we can re-read the storage locker
    proposed['allow_sl'] = 13 if BP.get('allow_reboots', True) else 1
            

# EOF
