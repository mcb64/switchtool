#!/reg/g/pcds/pyps/conda/rhel6/envs/pcds/bin/python

###!/usr/bin/env python
import os
import sys
import scp
import utils
import pickle
import logging
from subprocess import CalledProcessError
from argparse import ArgumentParser
from settings import SSH_CONF, LOG_CONF, HOST_IGNORE, CISCO_HOST, ARISTA_HOST, ICX_HOST


LOG = logging.getLogger(LOG_CONF.get('logger_name', __name__))


def parse_cli():
    # grab defaults from the config dict
    def_conf = SSH_CONF.get('config_file')

    # Create the parser
    parser = ArgumentParser(description='A cli tool for dumping the configuration information from Brocade/Foundry switches.')

    # Add the default ssh options
    utils.add_ssh_opts(parser)

    parser.add_argument('-d',
                        '--dest',
                        default=os.getcwd(),
                        help='Destination dir for the config files (default: getcwd)')

    parser.add_argument('-r',
                        '--run-conf',
                        action="store_true",
                        help='Dump run config instead of start config')

    parser.add_argument('-f',
                        '--fail',
                        action="store_true",
                        help='Write out a file containing info on failed hosts')

    # Add the default logger options
    utils.add_log_opts(parser)

    return parser.parse_args()


def main():
    # grab the command line opts
    opts = parse_cli()
    passwd = opts.pswd or utils.passwd_prompt(opts.user)

    # load config info
    if opts.run_conf:
        config = SSH_CONF.get('run_config_file')
        cisco_config = SSH_CONF.get('cisco_run_config_file')
        arista_config = SSH_CONF.get('arista_run_config_file')
        icx_config = SSH_CONF.get('icx_run_config_file')
    else:
        config = SSH_CONF.get('config_file')
        cisco_config = SSH_CONF.get('cisco_config_file')
        arista_config = SSH_CONF.get('arista_config_file')
        icx_config = SSH_CONF.get('icx_config_file')
    config_perms = SSH_CONF.get('config_perms')
    scp_kwargs = {
        'timeout': opts.timeout,
        'cfg_perms': config_perms,
        'private_key': opts.private_key,
    }

    # set levels for loggers that we care about
    LOG.setLevel(utils.log_level_parse(opts.log))

    # check that the destination path exists
    dest_dir = os.path.abspath(opts.dest)
    if not os.path.isdir(dest_dir):
        LOG.critical('The request output directory %s does not exist!', dest_dir)
        return 2

    # if no hosts are specified try to get a list from netconfig
    if opts.hosts is None:
        try:
            LOG.info('Attempting to retrieve a list of switches from netconfig:')
            switches = utils.get_switch_list()
        except (OSError, CalledProcessError) as err:
            LOG.critical('Problem running netconfig: %s', err)
            return 1
        good_switches = [ sw for sw in switches if sw not in HOST_IGNORE ]
        num_sw = len(switches)
        num_sw_good = len(good_switches)
        LOG.info('Found %d switches via netconfig, %d of which are in the ignore list', num_sw, num_sw - num_sw_good)
    else:
        good_switches = opts.hosts
        num_sw_good = len(good_switches)

    # Use scp to dump the switch configurations
    LOG.info('Attempting to dump switch configurations for %d switches:', num_sw_good)
    LOG.debug('----------------------------------------------------------')
    scp_client = scp.SCPHelper(opts.user, passwd, opts.port, config, dest_dir, **scp_kwargs)
    cisco_scp_client = scp.SCPHelper(opts.user, passwd, opts.port, cisco_config, dest_dir, **scp_kwargs)
    arista_scp_client = scp.SCPHelper(opts.user, passwd, opts.port, arista_config, dest_dir, **scp_kwargs)
    icx_scp_client = scp.SCPHelper(opts.user, passwd, opts.port, icx_config, dest_dir, **scp_kwargs)
    fails = 0
    failed_hosts = []
    failed_hosts_fname = os.path.join(dest_dir, SSH_CONF.get('failed_backup_file'))
    for host in good_switches:
        LOG.debug('Attempting to fetch config file for %s', host)
        # Check the type of switch
        if host in CISCO_HOST:
            scp_cmd = cisco_scp_client.get_cisco_cfg
        elif host in ARISTA_HOST:
            scp_cmd = arista_scp_client.get_arista_cfg
        elif host in ICX_HOST:
            scp_cmd = icx_scp_client.get_icx_cfg
        else:
            scp_cmd = scp_client.get_cfg
        # Run the scp command
        if scp_cmd(host) != 0:
            failed_hosts.append(host)
            fails += 1
        LOG.debug('----------------------------------------------------------')
    LOG.info('Successfully retrieved %d of %d switch configs', num_sw_good - fails, num_sw_good)
    
    # Write out list of hosts with failed backups
    if fails > 0 and opts.fail:
        LOG.debug('Writing list of hosts for which the configuration dump failed to %s'%failed_hosts_fname)
        with open(failed_hosts_fname, 'wb') as outf:
            pickle.dump(failed_hosts, outf)

    return fails != 0

if __name__ == '__main__':
    try:
        # set the root logger since this is an entry point
        utils.log_init()
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(1)
