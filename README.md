# <i>CKBunker</i>

![Screen Shot of CKBunker](docs/screen-shot.jpg)

- [CKBunker preview screencast (youtube)](https://www.youtube.com/watch?v=0bHhZbYOiSM)
- [Usage examples](examples.md) for HSM/CKBunker.
- [Documentation Website](https://ckbunker.com)
- [Github for CKBunker](https://github.com/Coldcard/ckbunker).
psbt.md

## Full Documentation

1. [Installation](docs/install.md)
2. [Setup Bunker](docs/setup.md)
2. [HSM Policy](docs/policy.md)
2. [PSBT Signing](docs/psbt.md)
2. [Message Signing](docs/msg-signing.md)
2. [Contributing Code](docs/hacking.md) 

## What is the Coinkite Bunker?

It's a python program that you run on a computer attached to a
Coldcard. It will setup and operate the Coldcard in "HSM Mode" where
it signs without a human pressing the OK key.  To keep your
funds safe, the Coldcard implements a complex set of spending rules
which cannot be changed once HSM mode is started.

Using the `tord` (Tor deamon) you already have, the CK Bunker can
make itself available as a hidden service for remote access over
Tor.  A pretty website for setup and operation allows access to all
HSM-related Coldcard features, including:

- transaction signing, by uploading a PSBT; can broadcast signed txn using Blockstream.info (onion)
- define policy rules, spending limits, velocity controls, logging policy
- user setup (TOTP QR scan to enroll on Coldcard, or random passwords (Coldcard) or known password

The bunker encrypts its own settings and stores the private key for
that inside Coldcard's storage locker (which is kept inside the
secure element of the Coldcard). The private key for the onion
service, for example, is protected by that key.

## What is Coldcard?

Coldcard is a Cheap, Ultra-secure & Opensource Hardware Wallet for Bitcoin.
Get yours at [ColdcardWallet.com](http://coldcardwallet.com)

Learn more about the [Coldcard HSM-related features](https://coldcardwallet.com/docs/ckbunker-hsm).

[Follow @COLDCARDwallet on Twitter](https://twitter.com/coldcardwallet) to keep up
with the latest updates and security alerts. 

## FAQ

### Will HSM mode be supported on Mk1 or Mk2?

Sorry no. CK Bunker only works on Mk3 because we need the extra RAM
and the newer features of the 608 secure element.

### What is HSM?

"Hardware Security Module"

Learn more about the [Coldcard in HSM Mode](https://coldcardwallet.com/docs/ckbunker-hsm)

## Quotes

> "Basically the cost of a Bitcoin HSM with custom policies is now the cost of a coldcard and you don't need a thirty party to maintain it." - Francis P.
