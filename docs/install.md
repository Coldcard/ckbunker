# Installation

## Check-out and Setup

Do a checkout, recursively to get all the submodules:

    git clone --recursive https://github.com/Coldcard/ckbunker.git

Then:

- `virtualenv -p python3 ENV` (Python 3.7 or higher is required)
- `source ENV/bin/activate` (or `source ENV/bin/activate.csh` based on shell preference)
- `pip install -r requirements.txt`
- `pip install --editable .`

## Operational Requirements

You will need:

- this code (see above)
- a Mk3 Coldcard connected via USB, running
  [firmware version 3.1.0 or later](https://coldcardwallet.com/docs/upgrade)
- `tord` (Tor program)
- an Internet connection
- a Tor-capable browser, like "Tor Browser" or Tails.
- (optional) a microSD card, for logging of transactions on Coldcard
- (optional, recommended) a mobile phone with TOTP 2FA app, like Google Authenticator or FreeOTP

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
mode, Tor connections are disabled, as is the login screen. There is no
security and it's meant for initial setup of the Coldcard and Bunker.

You would typically use the setup mode for picking the onion address, the
master login password and all the details of the HSM policy.

```sh
$ ckbunker setup
```

Open this URL in your local web browser (must be same machine):
<http://localhost:9823>

Once the Coldcard is running in HSM mode, with your policy installed,
it makes sense to operate in normal "run" mode. This enables a simple
login screen to keep out visitors:

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



## Other Command Line Options

```sh
% ckbunker run --help
Usage: ckbunker run [OPTIONS]

  Start the CKBunker for normal operation

Options:
  -l, --local                 Don't enable Tor (onion) access: just be on localhost
  -f, --psbt filename.psbt    Preload first PSBT to be signed
  -c, --config-file FILENAME
  --help                      Show this message and exit.

```

You can specify a PSBT file for immediate use. That file will be "uploaded"
and be ready to sign, but the system operates normally from there. You can
upload further PSBT files and so on.

```sh
% ckbunker setup --help
Usage: ckbunker setup [OPTIONS]

  Configure your transaction signing policy, install it and then operate.

Options:
  -l, --local                 Don't enable Tor (onion) access: just be on localhost
  -c, --config-file FILENAME
  --help                      Show this message and exit.
```

Both forms take an optional config file. It's simple YAML and allows
you to change the web server port number and similar values.
The values that can be configured are defined in `persist.py` in
the `Settings` class. See also `example-settings.yaml`.



# Next Steps

[Bunker setup](setup.md)
