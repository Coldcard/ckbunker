
# Hacking CKBunker

So you want to improve CKBunker? Sure. Here are some starting points.

## Structure

It's a python program, based on `aiohttp` for async http operation. The web UI is
provided using _Semantic UI_ and _Vue_ for model/view management. HTML pages
are constructed using Jinja templates. Data between
the browser and backend is communicated mainly via a websocket that 
stays open the entire time a page is shown in the browser. 

## Important Dependancies

See `requirements.txt` for complete list, but in summary, here are the major Python packages
we are using.

- `stem`
- `aiohttp`
- `aiohttp-jinja2`
- `ckcc-protocol`
- `pynacl`
- `click`
- `pendulum`
- `requests[socks]`

## Major Files

    webapp.py - Web backend
    chain.py - API access for sending transactions
    chrono.py - Time related stuff
    conn.py - Connection to a Coldcard, somewhat async wrapping for ckcc-protocol
    main.py - Startup code
    persist.py - Data persistance and default settings
    policy.py - Manage HSM policy details.
    status.py - Live state information about the system and attached Coldcard
    torsion.py - Manage Tor hidden service connection (via stem)
    utils.py - My favourite type of code.
    make_captcha.py - Construct the capatcha.
    setup.py - Pip/Pypi glue

    templates/ - Jinja HTML templates, with JS and Vue code mixed in
    static/ - static CSS, JS and font resources (web)
    data/ - encrypted Bunker settings saved at run time.
    docs/ - these docs

# Project Ideas

Looking for something to do?
Here are some loose ends or ideas we haven't been able start:

- Integrate [PSBT faker](https://github.com/Coldcard/psbt_faker) for testing policy.

- Recovery Tool: This will provide a means for you to construct a
PSBT which moves all the funds the system can find on the blockchain
to a new address. Use an onion-enabled block explorer to find UTXO
or maybe some other backend.

- Address Generator: Use this tool to make deposit addresses for
your Coldcard's wallets.


# Code Submission Guidelines

PR's are accepted but...

- Please think of other users: don't remove existing use cases.
- Don't add weird dependancies if easy to avoid.
- Try to match existing coding style.
- Large diffs are hard to accept with security-sensitive projects like this.
- Please start your own fork and own it... we love that too!



