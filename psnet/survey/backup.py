#!/reg/g/pcds/pyps/conda/rhel6/envs/pcds/bin/python

###!/usr/bin/env python
"""
Script for committing updated configurations to svn. Assumes that it is within
a working copy of the svn repository.
"""
import os
import sys
import utils
import pysvn
import socket
import pickle
import smtplib
import logging
import datetime
import time
from subprocess import check_call, CalledProcessError
from settings import SVN_CONF, LOG_CONF, EMAIL_CONF, BACKUP_CONF
from argparse import ArgumentParser
from email.mime.text import MIMEText


LOG = logging.getLogger(LOG_CONF.get('logger_name', __name__))


DEV_STRS = {
    'switch': {
        'base': 'switch',
        'suffix': 'es',
    }, 
    'digi': {
        'base': 'terminal server',
        'suffix': 's',
    },
    'default': {
        'suffix': 's',
    },
}


class SVNClient(object):
    """Simple wrapper object for svn operations"""

    def __init__(self, repodir):
        self.repodir = repodir
        self.client = pysvn.Client()
        self.url = self.client.info(self.repodir).url
        self.tagging_base_url = None
        if self.url.endswith('/trunk'):
            self.tagging_base_url = self.url.rsplit('/', 1)[0]

    def update(self):
        """Update the local working copy"""
        self.client.update(self.repodir)

    def add(self, path):
        """Add file/dir - path relative to repodir"""
        self.client.add(os.path.join(self.repodir, path))

    def commit(self, path, msg):
        """Commit file/dir - path relative to repodir"""
        return self.client.checkin([os.path.join(self.repodir, path)], msg)

    def tag(self, tag_name, rev, msg):
        """Tagged the named revision of the repo"""
        def get_log_message():
            return True, msg
        self.client.callback_get_log_message = get_log_message
        self.client.copy('%s/trunk'%self.tagging_base_url, '%s/tags/%s'%(self.tagging_base_url,tag_name), rev)

    def status(self, path):
        """Dir to check status on - path relative to repodir"""
        diff = self.client.status(os.path.join(self.repodir, path))
        new_files = [f.path for f in diff if f.text_status == pysvn.wc_status_kind.unversioned]
        mod_files = [f.path for f in diff if f.text_status == pysvn.wc_status_kind.modified]
        con_files = [f.path for f in diff if f.text_status == pysvn.wc_status_kind.conflicted]
        return new_files, mod_files, con_files


def get_device_str(dev_type, upper=True, plural=True):
    """Converts device type name into printable string form for emails"""
    if dev_type in DEV_STRS:
        base = DEV_STRS[dev_type]['base']
        suffix = DEV_STRS[dev_type]['suffix']
    else:
        base = dev_type
        suffix = DEV_STRS['default']['suffix']

    dev_str = base.title() if upper else base

    if plural:
        return dev_str + suffix
    else:
        return dev_str


def confirm(msg, batch):
    """Prompts user for confirmation depending on batch mode"""
    if batch:
        return True

    choices = {
        'yes': True,
        'y': True,
        'no': False,
        'n': False,
    }

    sys.stdout.write(msg)
    while True:
        choice = input().lower()
        if choice in choices:
            return choices[choice]
        else:
            sys.stdout.write('Please answer \'yes\' or \'no\' ')


def send_status_emails(news, mods, conflicts, dev_type):
    sender = EMAIL_CONF.get('sender_email')
    recpt = EMAIL_CONF.get('recipient_email')
    cc = EMAIL_CONF.get('cc_email')

    changes = [
        (news, "New"),
        (mods, "Updated"),
        (conflicts, "SVN Conflicts"),
    ]

    msg_formatted = ''
    num_changes = len(news) + len(mods) + len(conflicts)
    title = 'Configuration changes were detected in %d %s.\n'%(num_changes, get_device_str(dev_type, plural=(num_changes!=1), upper=False))
    for switches, msg in changes:
        for switch in switches:
            msg_formatted += '%s: %s\n'%(os.path.basename(switch), msg)

    msg = MIMEText('%s\n%s with changed configuration:\n-----------------------\n%s'%(title, get_device_str(dev_type), msg_formatted))
    msg['Subject'] = 'PCDS %s Configuration Changes Report'%get_device_str(dev_type, plural=False)
    msg['From'] = sender
    msg['To'] = ', '.join(recpt)
    msg['CC'] = ', '.join(cc)

    s = smtplib.SMTP('localhost')
    s.sendmail(sender, recpt + cc, msg.as_string())
    s.quit()


def send_failure_emails(failed_hosts, dev_type):
    num_fails = len(failed_hosts)
    if num_fails == 0:
        return False
    # Adding personalized POC emails:
    send_failure_emails_to_poc(failed_hosts, dev_type)
    
    sender = EMAIL_CONF.get('sender_email')
    recpt  = EMAIL_CONF.get('recipient_email')
    cc     = EMAIL_CONF.get('cc_email')
    
    msg_formatted = ''
    #num_fails = len(failed_hosts)
    title = 'Configuration backup failures occurred for %d %s.\n'%(num_fails, get_device_str(dev_type, plural=(num_fails!=1), upper=False))
    for failed_host in failed_hosts:
        msg_formatted += '%s\n'%failed_host

    msg = MIMEText('%s\n%s with a failed backup attempt:\n-----------------------\n%s'%(title, get_device_str(dev_type), msg_formatted))
    msg['Subject'] = 'PCDS %s Configuration Failures Report'%get_device_str(dev_type, plural=False)
    msg['From'] = sender
    msg['To'] = ', '.join(recpt)
    msg['CC'] = ', '.join(cc)

    s = smtplib.SMTP('localhost')
    s.sendmail(sender, recpt + cc, msg.as_string())
    s.quit()

def send_failure_emails_to_poc(failed_hosts, dev_type):
    sender = EMAIL_CONF.get('sender_email')
    recpt = EMAIL_CONF.get('recipient_email')
    cc = EMAIL_CONF.get('cc_email')
    hutches = EMAIL_CONF.get('hutches')
    hutches_recpt = EMAIL_CONF.get('hutches_recpt')
    hutches_cc = EMAIL_CONF.get('hutches_cc')

    msg_formatted = ''     
    num_fails = len(failed_hosts)
    if num_fails:
        failed_hosts.sort()
        for hutch in hutches:
            num_fails = ' '.join(failed_hosts).count(hutch)            
            if num_fails:
                title = 'Configuration backup failures occurred for %d %s.\n'%(num_fails, get_device_str(dev_type, plural=(num_fails!=1), upper=False))
                                
                for failed_host in failed_hosts:
                    if hutch in failed_host:
                        [name, Description, Location] = utils.get_digi_info_location(failed_host)
                        msg_formatted += ' %s | %s | %s\n' % (failed_host, Description, Location)
                    
            
                msg = MIMEText('%s\n%s with a failed backup attempt:\n--------------------------------\n%s'%(title, get_device_str(dev_type), msg_formatted))
                msg['Subject'] = 'PCDS %s Configuration Failures Report'%get_device_str(dev_type, plural=False)
                msg['From'] = sender
                recpt = hutches_recpt[hutch]
                cc    = hutches_cc[hutch]
                msg['To'] = ', '.join(recpt)              
                msg['CC'] = ', '.join(cc)
                
                #print (msg.as_string())
                s = smtplib.SMTP('localhost')
                s.sendmail(sender, recpt + cc, msg.as_string())
                s.quit()
                
                msg_formatted = ''

def update_svn(svn, batch, svn_ci, tag, email, dev_type):
    # Update subversion
    config_dir = SVN_CONF.get('config_dir')
    svn.update()
    (news, mods, conflicts) = svn.status(config_dir)

    # Send status email if there are changes and emails are enabled
    if email and len(news) + len(mods) + len(conflicts) > 0:
        send_status_emails(news, mods, conflicts, dev_type)

    if len(conflicts) > 0:
        LOG.critical('Aborting - Merge conflicts in the repository: %s', conflicts)
        return 1

    # If there are updates in the repo commit add tag
    if len(news) + len(mods) > 0:
        # Check if the user is root which can't update svn - we don't want the cron job to commit changes
        if os.geteuid() == 0:
            LOG.info('Script run as root - Not committing config changes: %d new and %d modified files', len(news), len(mods))
            return 0

        LOG.info('Found config changes: %d new and %d modified files', len(news), len(mods))
        
        # Add the unversioned files
        for fpath in news:
            svn.add(fpath)
        # Now commit the changes
        cur_time = datetime.datetime.now()
        if svn_ci:
            LOG.debug('Attempting to commit changes into svn')
            if confirm('Do you wish to commit the changes (y/N)? ', batch):
                rev = svn.commit(config_dir, cur_time.strftime('Updated configuration files for %Y-%m-%d %H:%M:%S'))
                LOG.debug('Successfully commited configuration changes. Repo is at revision %s', rev.number)

                # Tag the changes in svn
                if tag and confirm('Do you wish to tag the changes (y/N)? ', batch):
                    tag_name = cur_time.strftime(dev_type + 'conf-%Y:%m:%d:%H:%M:%S')
                    LOG.info('Taggings revision %s as tags/%s', rev.number, tag_name)
                    svn.tag(tag_name, rev, cur_time.strftime('Tagging configuration files for %Y-%m-%d %H:%M:%S'))
                    LOG.debug('Successfully tagged revision %s as tags/%s', rev.number, tag_name)
        else:
            LOG.debug('Skipping committing changes to svn')

    else:
        LOG.info('No changes to commit')

    return 0


def main():
    # grab defaults from the config dict
    def_log = LOG_CONF.get('log_level')
    def_devtype = BACKUP_CONF.get('device')
    dev_choices = BACKUP_CONF.get('device_mapping').keys()

    # Parse the cli opts
    parser = ArgumentParser(description='A cli tool for dumping the configuration information from switches and'\
                              ' committing the dumps to svn.')

    back_group = parser.add_argument_group('backup options', description='options for backing up the configurations')

    back_group.add_argument('-b',
                            '--batch',
                            action="store_true",
                            help='Runs the script in batch mode - no prompts')

    back_group.add_argument('-s',
                            '--svn-ci',
                            action="store_true",
                            help='Commit config changes to svn')

    back_group.add_argument('-t',
                            '--tag',
                            action="store_true",
                            help='Make a tag of any svn commits')

    back_group.add_argument('-c',
                            '--choice',
                            default=def_devtype,
                            choices=dev_choices,
                            help='Choice of type of device to backup (default: %s)'%def_devtype)

    back_group.add_argument('-e',
                            '--email',
                            action="store_true",
                            help='Flag to enable sending of status emails')

    # Add the default ssh options
    utils.add_con_opts(parser)

    # Add the default logger options
    utils.add_log_opts(parser)

    opts = parser.parse_args()

    # set levels for loggers that we care about
    LOG.setLevel(utils.log_level_parse(opts.log))

    # Find the svn repo dir we care about (one that contains 'configs' and 'scripts')
    checkout_dir = os.path.realpath(os.path.join(os.path.dirname(__file__), os.pardir))

    # The directory containing the configuration files
    config_dir = os.path.join(checkout_dir, SVN_CONF.get('config_dir'))

    # Create svn wrapper object
    svn = SVNClient(checkout_dir)
    svn.update()

    # Construct the proper command string to run
    dumper_info = BACKUP_CONF.get('device_mapping').get(opts.choice)
    if dumper_info is None:
        LOG.critical('Invalid backup choice: %s', opts.choice)
        return 1
    dumper_script, dumper_host, dumper_fail_file, dumper_portable = dumper_info
    # Override dumper host if cli option is passed
    if opts.dump_host is not None:
        dumper_host = opts.dump_host

    # See if password should be prompted for
    if opts.batch:
        if opts.pswd is None:
            LOG.critical('Batch mode was requested, but no default password is set or passed to the script!')
            return 1
        else:
            passwd = opts.pswd
    else:
        passwd = opts.pswd or utils.passwd_prompt(opts.user)

    dumper_cmd = [
        os.path.join(checkout_dir, SVN_CONF.get('script_dir'), dumper_script), 
        '-d',
        config_dir,
        '--fail',
    ]

    # Send the optional params if they were specified
    opt_append_scheme = [
        (opts.user, '-u', None),
        (passwd, '-P', None),
        (opts.port, '-p', str),
        (opts.timeout, '--timeout', str),
        (opts.log, '--log', None),
    ]
    for val, flag, transf in opt_append_scheme:
        if val is not None:
            dumper_cmd += [flag, val if transf is None else transf(val)]
    # Send the '--hosts' param if this was specified
    if opts.hosts is not None:
        dumper_cmd += (['--hosts'] + opts.hosts)

    # Check if the switch connection host is the current machine
    if socket.gethostname() == dumper_host:
        try:
            LOG.info('Running the configuration dumper script on localhost')
            #check_call(dumper_cmd)
            check_call(dumper_cmd, timeout=600)
        except OSError as err:
            LOG.critical('Problem running the config dumper: %s', err)
            return 1
        except CalledProcessError:
            LOG.warning('Unable to dump some configuration files!')
    else:
        try:
            # Grab config info for machine for running dumps
            host = dumper_host
            remote_cmd = ['ssh', host, ' '.join(dumper_cmd)]
            LOG.info('Running the configuration dumper script on %s', host)
            #check_call(remote_cmd)
            check_call(remote_cmd, timeout=600)
        except OSError as err:
            LOG.critical('Failure running the config transfer on host %s: %s', host, err)
            return 1
        except CalledProcessError:
            LOG.warning('Unable to dump some configuration files!')
        # Touch all the files in the configs dir to force NFS cache dump
        file_join = lambda f: os.path.join(config_dir, f)
        for conf_file in  (file_join(f) for f in os.listdir(config_dir) if os.path.isfile(file_join(f))):
            with open(conf_file, 'a'):
                os.utime(conf_file, None)

    # Check for a pickle file with info from the dump job
    fail_hosts_fname = os.path.join(config_dir, dumper_fail_file)
    if os.path.exists(fail_hosts_fname):
        with open(fail_hosts_fname, 'rb') as infile:
            failed_hosts = pickle.load(infile)
        # Remove the pickle file after consuming
        os.remove(fail_hosts_fname)
        # Check for portable devices whose failures should be ignored
        portable_hosts = [ host for host in failed_hosts if host in dumper_portable]
        failed_hosts = [ host for host in failed_hosts if host not in dumper_portable]
        LOG.info('Portable devices with unfetchable configurations: %s', portable_hosts)
        LOG.warning('Devices with unfetchable configurations: %s', failed_hosts)
        # Send a separate email about devices where the backup failed
        if opts.email:
            send_failure_emails(failed_hosts, opts.choice)

    # Update subversion
    try:
        return update_svn(svn, opts.batch, opts.svn_ci, opts.tag, opts.email, opts.choice)
    except pysvn.ClientError as err:
        LOG.critical('There was a problem excuting a subversion command: %s', err)
        return 1


if __name__ == '__main__':
    try:
        # set the root logger since this is an entry point
        utils.log_init()
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(1)
