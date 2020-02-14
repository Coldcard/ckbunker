#!/usr/bin/env python
#
# (c) Copyright 2020 by Coinkite Inc. This file is part of Coldcard <coldcardwallet.com>
# and is covered by GPLv3 license found in COPYING.
#
# Main entry-point for project.
#
# To use this, install with:
#
#   pip install --editable .
#
# That will create the command "ck-bunker" in your path.
#
import os, sys, click, hid, asyncio, logging
from pprint import pformat, pprint

global force_serial
force_serial = None

from ckcc.protocol import CCProtocolPacker
from ckcc.protocol import CCProtoError, CCUserRefused, CCBusyError
from ckcc.client import ColdcardDevice, COINKITE_VID, CKCC_PID


# Options we want for all commands
@click.group()
@click.option('--serial', '-s', default=None, metavar="HEX",
                    help="Operate on specific unit (default: first found)")
def main(serial):
    global force_serial
    force_serial = serial

@main.command('list')
def _list():
    "List all attached Coldcard devices"

    count = 0
    for info in hid.enumerate(COINKITE_VID, CKCC_PID):
        #click.echo("\nColdcard {serial_number}:\n{nice}".format(
        #                    nice=pformat(info, indent=4)[1:-1], **info))
        click.echo(info['serial_number'])
        count += 1

    if not count:
        click.echo("(none found)")

@main.command('example')
def example_config():
    "Show an example config file, using the default values"

    from persist import Settings
    
    click.echo(Settings.make_sample())

@main.command('run')
@click.option('--local', '-l', default=False, is_flag=True,
                    help="Don't enable Tor (onion) access: just be on localhost")
@click.option('--psbt', '-f', metavar="filename.psbt",
                        help="Preload first PSBT to be signed", default=None,
                        type=click.File('rb'))
@click.option('--config-file', '-c', type=click.File('rt'), required=False)
def start_service(local=False, config_file=None, psbt=None):
    "Start the CK-Bunker for normal operation"

    if psbt:
        psbt = psbt.read()

    asyncio.run(startup(False, local, config_file, psbt), debug=True)

@main.command('setup')
@click.option('--local', '-l', default=False, is_flag=True,
                    help="Don't enable Tor (onion) access: just be on localhost")
@click.option('--config-file', '-c', type=click.File('rt'), required=False)
def setup_hsm(local=False, config_file=None):
    "Configure your transaction signing policy, install it and then operate."

    asyncio.run(startup(True, local, config_file, None), debug=True)

async def startup(setup_mode, force_local_mode, config_file, first_psbt):
    # All startup/operation code

    loop = asyncio.get_running_loop()
    if loop.get_debug():
        # quiet noise about slow stuff
        loop.slow_callback_duration = 10

    from utils import setup_logging
    setup_logging()

    from persist import Settings
    Settings.startup(config_file)

    aws = []

    # copy some args into status area
    from status import STATUS
    STATUS.force_local_mode = force_local_mode
    STATUS.setup_mode = setup_mode

    # preload the contents of a PSBT
    if first_psbt:
        STATUS.import_psbt(first_psbt)

    from torsion import TOR
    aws.append(TOR.startup())

    from conn import Connection
    aws.append(Connection(force_serial).run())

    import webapp
    aws.append(webapp.startup(setup_mode))
    

    await asyncio.gather(*aws)


# EOF
