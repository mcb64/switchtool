#!/reg/g/pcds/pyps/conda/rhel6/envs/pcds/bin/python

###!/usr/bin/env python
import sys
import utils
import logging
import argparse
from subprocess import CalledProcessError
from settings import LOG_CONF, HOST_IGNORE, DIGI_HOST_IGNORE, MOXA_HOST_IGNORE


LOG = logging.getLogger(LOG_CONF.get('logger_name', __name__))


def list_switches():
    LOG.info('Attempting to retrieve a list of switches from netconfig:')
    switches = utils.get_switch_list()
    good_switches = [ sw for sw in switches if sw not in HOST_IGNORE ]
    num_sw = len(switches)
    num_sw_good = len(good_switches)
    LOG.info('Found %d switches via netconfig, %d of which are in the ignore list', num_sw, num_sw - num_sw_good)

    return switches


def list_digis():
    LOG.info('Attempting to retrieve a list of Digi PSs and CPs from netconfig:')
    digis = utils.get_digi_list()
    good_digis = [ digi for digi in digis if digi not in DIGI_HOST_IGNORE ]
    num_digi = len(digis)
    num_digi_good = len(good_digis)
    LOG.info('Found %d Digi PSs and CPs via netconfig, %d of which are in the ignore list', num_digi, num_digi - num_digi_good)

    return digis

def list_moxas():
    LOG.info('Attempting to retrieve a list of Moxas from netconfig:')
    moxas = utils.get_digi_list()
    good_moxas = [ moxa for moxa in moxas if moxa not in MOXA_HOST_IGNORE ]
    num_moxa = len(moxas)
    num_moxa_good = len(good_moxas)
    LOG.info('Found %d Moxas via netconfig, %d of which are in the ignore list', num_moxa, num_moxa - num_moxa_good)

    return moxa

def parse_cli():
    # Create the parser
    parser = argparse.ArgumentParser(description='A cli tool for listing switches and digis on the network.')

    subparsers = parser.add_subparsers(help='available device types to list')
    
    switch_parser = subparsers.add_parser('switch', help='lists switches found in netconfig')
    switch_parser.set_defaults(func=list_switches)

    digi_parser = subparsers.add_parser('digi', help='lists digi portservers and connectports found in netconfig')
    digi_parser.set_defaults(func=list_digis)

    # Add the default logger options
    utils.add_log_opts(parser)

    return parser.parse_args()


def main():
    # grab the command line opts
    args = parse_cli()

    # set levels for loggers that we care about
    LOG.setLevel(utils.log_level_parse(args.log))

    try:
        devices = args.func()
    except (OSError, CalledProcessError) as err:
        LOG.critical('Problem running netconfig: %s', err)
        return 1

    # get root logger and change handler format strings
    root_log = LOG.parent
    for handler in root_log.handlers:
        handler.setFormatter(None)

    # print out device names
    for device in devices:
        LOG.info(device)


if __name__ == '__main__':
    try:
        # set the root logger since this is an entry point
        utils.log_init('%(levelname)s:%(message)s')
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(1)
