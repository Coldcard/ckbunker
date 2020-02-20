# <i>CK Bunker</i>

![](/static/screen-shot.jpg)

- [CKBunker Docs](https://coldcardwallet.com/docs/ckbunker-hsm)
- [Github repo for CKBunker](https://github.com/Coldcard/ckbunker).
- [CKBunker preview screencast](https://www.youtube.com/watch?v=0bHhZbYOiSM)

## What is the Coinkite Bunker?

"Basically the cost of a Bitcoin [HSM](#what-is-hsm) with custom policies is now the cost of a coldcard and you don't need a thirty party to maintain it." - Francis P.

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

The bunker encrypts its own settings and stores the private key for that inside Coldcard's
storage locker (which is inside the secure element). The private key for the onion
service, for example, is held on the bunker's disk encrypted like that.

## What is Coldcard?

Coldcard is a Cheap, Ultra-secure & Opensource Hardware Wallet for Bitcoin.
Get yours at [ColdcardWallet.com](http://coldcardwallet.com)

[Follow @COLDCARDwallet on Twitter](https://twitter.com/coldcardwallet) to keep up
with the latest updates and security alerts. 

## Check-out and Setup

Do a checkout, recursively to get all the submodules:

    git clone --recursive https://github.com/Coldcard/ckbunker.git

Then:

- `virtualenv -p python3 ENV` (Python 3.7 or higher is required)
- `source ENV/bin/activate` (or `source ENV/bin/activate.csh` based on shell preference)
- `pip install -r requirements.txt`
- `pip install --editable .`

## Usage

The executable is called `ckbunker`:

```sh
$ ckbunker --help
Usage: ckbunker [OPTIONS] COMMAND [ARGS]...

Options:
  -s, --serial HEX  Operate on specific unit (default: first found)
  --help            Show this message and exit.

Commands:
  list     List all attached Coldcard devices
  example  Show an example config file, using the default values
  run      Start the CKBunker for normal operation
  setup    Configure your transaction signing policy, install it and then...
```

There are two modes for the Bunker: "setup" and "run mode". In setup
mode, Tor connections are disabled, as is the login screen.

You would typically use the setup mode for picking the onion address, the
master login password and all the details of the HSM policy.

```sh
$ ckbunker setup
```

Open this URL in your local web browser (must be same machine):
<http://localhost:9823>

Once the Coldcard is running in HSM mode, with your policy installed,
it makes sense to operate in normal "run" mode:

```sh
$ ckbunker run
```

You may also run with remote connections (and login) disabled. This would be useful
if you have some existing web proxy already in place.

```sh
$ ckbunker --local run
```

## Tor Use

To access over Tor as a hidden service, you must have `tord` running
on the same machine. For desktop systems, keeping TorBrowser open
is enough to acheive this. On servers, start tord with default options,
and ckbunker will use the control port (localhost port 9051 or 9151).

If you use the bunker to broadcast the final (signed) transaction,
the socks proxy of tord (port 9050) will also be used.


## Operational Requirements

You will need:

- this code
- a Coldcard connected via USB
- `tord` (Tor program)
- Internet connection
- a Tor-capable brwoser, like "Tor Browser" or Tails.
- (optional) a microSD card, for logging of transactions on Coldcard


## Example use cases

### Sign small transactions with just a password

You can set a password and have your Coldcard sign anything below a custom amount provided you enter that password.
Or instead require you to type a pin into the Coldcard for verification. [6102](https://twitter.com/6102bitcoin/status/1228425672827293696)

### 2/2 multisig with geographic separation and specific spending rules

You can use another Coldcard and program it to make sure no transactions get through that don't adhere to a set of rules you set in advance. This uses 2/2 multisig (meaning your regular wallet is the first and the Coldcard is the second, both needed to send any transaction).

Your regular wallet will sign any transaction you send, but the Coldcard is like a security guard that won't also sign the transaciton unless it follows the rules you set. Rules can include where the bitcoins go (so if an attacker tries to steal your BTC using your main wallet, the Coldcard won't sign).

Rules could also include a time of day or a max amount per day (or any other period of time). For a long-term hodl you might not want to let anyone be able to send the whole amount at once.

What's cool is that this Coldcard could be located anywhere in the world and still sign your transaction.

Because we give the Coldcard a set of rules we can let it execute automatically and sign any transaction that your main wallet presents, as long as the transaction follows whatever rules you set. An attacker would have to nab both your main wallet and the Coldcard (and possibly even reprogram the CC).

While a geographically distributed 2/2 multi-sig is already possible today, it would require someone on the other end to click the buttons and co-sign. As this is pre-programmed it can run automatically and sign any TX within the rules.

[Ben Prentice](https://twitter.com/mrcoolbp/status/1228868296486924289)

### Geographic separation

Advanced: Your Coldcard could be in another country; you can lock Coldcard (boot-to-HSM™ feature). Remote hands can do power cycles if needed & keep Bunker running.  Video-conference with them to send  6-digit code to complete a PSBT authentication (entered on Coldcard keypad). [DocHex](https://twitter.com/DocHex/status/1228392653592649728)


### Freeze your warm wallet

The HSM policy on your Coldcard could enable spending to just one single cold-storage address (via a whitelist). When your warm wallet is in danger, pull this cord to collect all UTXOs and send them to safety, signed, unattended, by the COLDCARDwallet
[DocHex](https://twitter.com/DocHex/status/1228394738841157632)

### Meet-me-in-the-Bunker™

Time-based 2FA code from the phones of 3 of these 5 executives needed to authorize spending; Each exec connects to Bunker at the same time, checks proposed transaction and adds their OTP code. Only the Coldcard and exec's phone knows the shared 2FA secret. [DocHex](https://twitter.com/DocHex/status/1228395590662397953)
·

### Text message signing

You can disable PSBT signing completely and allow automatic signatures on text messages. This turn the Coldcard wallet
 into an HSM for Bitcoin-based auth/attestations. Can be limited to specific BIP32 subpath derivations. Same with address generation/derived XPUBS. [DocHex](https://twitter.com/DocHex/status/1228396805102194688)
 
 
### Storage Locker™

There is a locker of about 400 bytes of secret storage in the Mk3 secure element. CK Bunker uses this to hold the secret that encrypts bunker's settings (when at rest), such as the private key for the address of the Tor hidden service. So a corrupt LEA <!-- what is LEA? --> can't impersonate your bunker after capture. [DocHex](https://twitter.com/DocHex/status/1228398842313310208)

### Multsig

Heard you like co-signing! All the Bunker/HSM features work with multisig (P2SH / P2WSH) so maybe you're automatically co-signing some complex multisig from a CasaHODL quorum. [DocHex](https://twitter.com/DocHex/status/1228403787955687427)




## FAQ

### Will HSM mode be supported on Mk1 or Mk2[?](https://twitter.com/orcitis/status/1228418529302433792)

Sorry no. CK Bunker only works on Mk3 because we need the extra RAM and the newer features of the 608a secure element.

### What is HSM?

Hardware Security Module
