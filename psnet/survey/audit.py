#!/reg/g/pcds/pyps/conda/rhel6/envs/pcds/bin/python

###!/usr/bin/env python

import os
import sys
import scp
import time
import utils
import shutil
import smtplib
import logging
import filecmp
import tempfile
from email.mime.text import MIMEText
from subprocess import CalledProcessError
from argparse import ArgumentParser
from settings import SSH_CONF, LOG_CONF, HOST_IGNORE, CISCO_HOST, ARISTA_HOST, ICX_HOST, EMAIL_CONF


LOG = logging.getLogger(LOG_CONF.get('logger_name', __name__))


def parse_cli():
    # Create the parser
    parser = ArgumentParser(description='A cli tool for checking for unsaved configurations on switches.')

    # Add the default ssh options
    utils.add_ssh_opts(parser)

    parser.add_argument('-e',
                      '--email',
                      action="store_true",
                      help='Flag to enable sending of warning emails')

    # Add the default logger options
    utils.add_log_opts(parser)

    return parser.parse_args()


def send_warn_emails(failed_hosts, total_num):
    ''' Python 2.7 :  for host, reason in failed_hosts.iteritems(): '''
    ''' Python 3.5 :  for host, reason in failed_hosts.items():     '''        

    sender = EMAIL_CONF.get('sender_email')
    recpt = EMAIL_CONF.get('recipient_email')
    cc = EMAIL_CONF.get('cc_email')

    fail_formatted = ''
    title = 'Problems were seen in %d out of %d switches checked.\n'%(len(failed_hosts), total_num)
    #for host, reason in failed_hosts.iteritems():
    for host, reason in failed_hosts.items():        
        fail_formatted += '%-25s %s\n'%(host+':', reason)
    
    msg = MIMEText('%-25s\nSwitches with problems:\n-----------------------\n%s'%(title, fail_formatted))
    msg['Subject'] = 'PCDS Switch Issues Report'
    msg['From'] = sender
    msg['To'] = ', '.join(recpt)
    msg['CC'] = ', '.join(cc)

    s = smtplib.SMTP('localhost')
    s.sendmail(sender, recpt + cc, msg.as_string())
    s.quit()


def main():
    # load config info
    run_config = SSH_CONF.get('run_config_file')
    start_config = SSH_CONF.get('config_file')
    cisco_run_config = SSH_CONF.get('cisco_run_config_file')
    cisco_start_config = SSH_CONF.get('cisco_config_file')
    arista_run_config = SSH_CONF.get('arista_run_config_file')
    arista_start_config = SSH_CONF.get('arista_config_file')
    icx_run_config = SSH_CONF.get('icx_run_config_file')
    icx_start_config = SSH_CONF.get('icx_config_file')

    # grab the command line opts
    opts = parse_cli()
    passwd = opts.pswd or utils.passwd_prompt(opts.user)

    # set up the keyword args for the scp class
    scp_kwargs = {
        'timeout': opts.timeout,
        'private_key': opts.private_key,
    }

    # set levels for loggers that we care about
    LOG.setLevel(utils.log_level_parse(opts.log))

    # create a temporary dir for doing placing config files
    dest_dir = tempfile.mkdtemp()

    # if no hosts are specified try to get a list from netconfig
    if opts.hosts is None:
        try:
            LOG.info(80 *'-')
            LOG.info('Attempting to retrieve a list of switches from netconfig:')
            switches = utils.get_switch_list()
        except (OSError, CalledProcessError) as err:
            LOG.critical('Problem running netconfig: %s', err)
            return 1
        good_switches = [ sw for sw in switches if sw not in HOST_IGNORE ]
        num_sw = len(switches)
        num_sw_good = len(good_switches)
        LOG.info('Found %d switches via netconfig, %d of which are in the ignore list', num_sw, num_sw - num_sw_good)
        LOG.info(80 *'-')
    else:
        good_switches = opts.hosts.sort() # EP : added .sort() 10/19/2018
        num_sw_good = len(good_switches)

    # Use scp to dump the switch configurations
    LOG.info('Attempting to audit switch configurations for %d switches:', num_sw_good)
    LOG.debug('----------------------------------------------------------')
    scp_run = scp.SCPHelper(opts.user, passwd, opts.port, run_config, dest_dir, '%s-run.cfg', **scp_kwargs)
    scp_start = scp.SCPHelper(opts.user, passwd, opts.port, start_config, dest_dir, '%s-start.cfg', **scp_kwargs)
    cisco_scp_run = scp.SCPHelper(opts.user, passwd, opts.port, cisco_run_config, dest_dir, '%s-run.cfg', **scp_kwargs)
    cisco_scp_start = scp.SCPHelper(opts.user, passwd, opts.port, cisco_start_config, dest_dir, '%s-start.cfg', **scp_kwargs)
    arista_scp_run = scp.SCPHelper(opts.user, passwd, opts.port, arista_run_config, dest_dir, '%s-run.cfg', **scp_kwargs)
    arista_scp_start = scp.SCPHelper(opts.user, passwd, opts.port, arista_start_config, dest_dir, '%s-start.cfg', **scp_kwargs)
    icx_scp_run = scp.SCPHelper(opts.user, passwd, opts.port, icx_run_config, dest_dir, '%s-run.cfg', **scp_kwargs)
    icx_scp_start = scp.SCPHelper(opts.user, passwd, opts.port, icx_start_config, dest_dir, '%s-start.cfg', **scp_kwargs)

    #TODO:
    """
    LOG.info(80 *'=')
    LOG.info('Command issues:')
    LOG.info('STANDARD (Brocade) switches:')
    LOG.info('\t%s %s %s %s %s %s' % (opts.user, passwd, opts.port, run_config, dest_dir, '%s-run.cfg'))
    
    LOG.info('\t', opts.user, passwd, opts.port, start_config, dest_dir, '%s-start.cfg', **scp_kwargs)
    LOG.info('ICX switches:')
    LOG.info('\t', opts.user, passwd, opts.port, icx_run_config, dest_dir, '%s-run.cfg', **scp_kwargs)
    LOG.info('\t', opts.user, passwd, opts.port, icx_start_config, dest_dir, '%s-start.cfg', **scp_kwargs)
    LOG.info('CISCO switches:')
    LOG.info('\t', opts.user, passwd, opts.port, cisco_run_config, dest_dir, '%s-run.cfg', **scp_kwargs)
    LOG.info('\t', opts.user, passwd, opts.port, cisco_start_config, dest_dir, '%s-start.cfg', **scp_kwargs)
    LOG.info('ARISTA switches:')
    LOG.info('\t', opts.user, passwd, opts.port, arista_run_config, dest_dir, '%s-run.cfg', **scp_kwargs)
    LOG.info('\t', opts.user, passwd, opts.port, icx_start_config, dest_dir, '%s-start.cfg', **scp_kwargs)
    
    LOG.info(80 *'=')
    """
    
    fails = 0
    failed_hosts = {}
    for host in good_switches:
        status = True
        # don't put this in the same if statement - switch doesn't like simultaneous connections
        LOG.debug('Attempting to fetch config files for %s', host)
        """ For tests
        if host in ICX_HOST:
            scp_run_cmd = icx_scp_run.get_icx_cfg
            scp_start_cmd = icx_scp_start.get_icx_cfg
        else:
            continue
        """
        
        
        
        # Check the type of switch
        if host in CISCO_HOST:
            scp_run_cmd = cisco_scp_run.get_cisco_cfg
            scp_start_cmd = cisco_scp_start.get_cisco_cfg
        elif host in ARISTA_HOST:
            scp_run_cmd = arista_scp_run.get_arista_cfg
            scp_start_cmd = arista_scp_start.get_arista_cfg
        elif host in ICX_HOST:
            scp_run_cmd = icx_scp_run.get_icx_cfg
            scp_start_cmd = icx_scp_start.get_icx_cfg
        else:
            scp_run_cmd = scp_run.get_cfg
            scp_start_cmd = scp_start.get_cfg
        
        
        
        # Run the scp commands
        status = status and scp_run_cmd(host) == 0
        print ('RUN___status = %d' % status)
        time.sleep(0.25)
        status = status and scp_start_cmd(host) == 0
        print ('START_status = %d' % status)
        if status:
            if filecmp.cmp(os.path.join(dest_dir, '%s-run.cfg'%host), os.path.join(dest_dir, '%s-start.cfg'%host)):
                LOG.debug('The running and save configurations match for %s', host)
            else:
                fails +=1
                failed_hosts[host] = 'unsaved-config'
                LOG.error('The running and saved configurations do not match for %s', host)
        else:
            fails += 1
            failed_hosts[host] = 'unfetchable-config'
            LOG.error('Failure downloading config files for %s. No comparison can be performed!', host)

        LOG.debug('----------------------------------------------------------')

    LOG.info('Running config matches saved config for %d of %d switches', num_sw_good - fails, num_sw_good)
    if len(failed_hosts) > 0:
        LOG.error('Switches with failures: %s', failed_hosts)

    if opts.email and len(failed_hosts) > 0:
        send_warn_emails(failed_hosts, num_sw_good)

    # cleanup temp directory
    shutil.rmtree(dest_dir)

    return fails != 0

if __name__ == '__main__':
    try:
        # set the root logger since this is an entry point
        utils.log_init()
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(1)
