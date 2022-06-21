"""
Configuration for the Switch dumper scripts
"""
import stat
import logging

# Logging configuration
LOG_CONF = {
    'logger_name'     : 'switch-scripts',
    'root_log_level'  : logging.WARN, # Set the root logger's level to warn
    'log_level'       : 'INFO', # this is a string since its a default for the cli opt
}

# SSH settings for connecting to the switches
SSH_CONF = {
    'username'               : 'pcds',
    'password'               : None,
    'port'                   : 22,
    'config_perms'           : stat.S_IRUSR | stat.S_IRGRP | stat.S_IWUSR,
    'config_file'            : 'startConfig',
    'run_config_file'        : 'runConfig',
    'cisco_config_file'      : 'startup-config',
    'cisco_run_config_file'  : 'running-config',
    'arista_config_file'     : 'startup-config',
    'arista_run_config_file' : 'running-config',
    'icx_config_file'        : 'configuration',
    'icx_run_config_file'    : 'running-config',
    'switch_con_host'        : 'pscron',
    'timeout'                : 2.5,
    'private_key'            : False,
    'failed_backup_file'     : 'failed_backups.pkl',
}

# Telnet setting for connection to digis
TELNET_CONF = {
    'username'          : 'root',
    'password'          : None,
    'port'              : 23,
    'config_perms'      : stat.S_IRUSR | stat.S_IRGRP | stat.S_IWUSR,
    'config_cmd_PS'     : 'cpconf term',
    'config_cmd_CP'     : 'backup print',
    'digi_con_host'     : 'pscron',
    'timeout'           : 2.5,
    'failed_backup_file': 'failed_digi_backups.pkl',
}

# Settings for netconfig
NETCONFIG_CONF = {
    'script'         : '/reg/common/tools/bin/netconfig',
    'cmd'            : 'search',
    'cmd_view'       : 'view',
    'params'         : ['--brief'],
    'switch_searches': ['*switch*'],
    'switch_subnets' : ['swhmgt.pcdsn'],
    #'digi_searches'  : ['*digi*', '*serialsrv*'],
    'digi_searches'  : ['*digi-*', '*serialsrv*', '*moxa-*'],
    'digi_subnets'   : [],
    'digi_macs'      : '^00:40:9[dD]:',
    'exclude_pattern': '^ibswitch-.*',
}

# Config directories tracked by svn
SVN_CONF = {
    'config_dir': 'configs',
    'script_dir': 'bin',
}

# Switches with entries in netconfig that this script should not try to dump
HOST_IGNORE = [
    'switch-ana-row40', # seems to require root to view config
    'switch-ana-mezz', # seems to require root to view config
    # Special switches
    'switch-tst-lab2-atca01',
    'switch-tst-lab2-atca02',
    'switch-tst-lab2-fez2',
    'switch-smblade-sm15',
    'switch-10gb-smblade-sm15',
    'switch-mec-cr', # here until know why this ICX is not responding all the time...
    'switch-pcdsn', # still need to be installed correctly
    'switch-ana-mezza2', # this switch has problems
    'switch-xpp-srvroom-daq', #new switch need to be checked why it's not backing up
    'switch-tst-vdx01', #new switch need new code to get the configuration. Postponed now.
    'switch-ana-vdx01', #new switch need new code to get the configuration. Postponed now.
]

# Digi PortServers with entries in netconfig that this script should not try to dump
DIGI_HOST_IGNORE = [
    #'ioc-ics-mecrptest2',
    'delaygen-sxr-03',
    'delaygen-sxr-02',
    'delaygen-sxr-01',
    'delaygen-amo-02',
    'delaygen-amo-01',
    #'scope-cxi-portable02',
    'digi-tst-208',
    'digi-tst-130',
    'digi-tst-r219',   # Connect Port and not a Port Server model has a different backup command
    'digi-tst-nathan', # Digi that is in b750 Ray's people.
    'moxa-tst-b750',   # Ray's group moxa
]

# Moxa Terminal Servers with entries in netconfig that this script should not try to dump
MOXA_HOST_IGNORE = [
    'moxa-tst-b750',   # Ray's group moxa
]

# Switches with entries in netconfig that are portable that the script should not complain if missing
HOST_PORTABLE = [
    'switch-daq-portable1',
    'switch-daq-portable2',
]

# Digi PortServers with entries in netconfig that are portable that the script should not complain if missing
DIGI_HOST_PORTABLE = [
    'digi-xcs-23',
    'digi-xpp-sds',
    'digi-mec-pci01',
    'digi-mec-pci02',
    'digi-sxr-rci-01',
    'digi-tst-88',
    'digi-tst-vtc',
    'digi-det-rowland01',
    'digi-det-portable1',
    'digi-det-pnccd01',
    'digi-sds-01',
    'digi-sxd-spec',
    'digi-xcs-24-not-used', # renamed by Rajan June 2018
    'digi-xcs-25-not-used', # renamed by Rajan June 2018
]

# Digi that are actually ConnectPorts instead of PortServers
DIGI_HOST_CONNECTPORTS = [
    'digi-sxr-02',
]

# A list of all Cisco switches - we don't buy these anymore and alternative backup is needed
CISCO_HOST = [
    'switch-fee-alcove',
    'switch-fee-near',
    'switch-fee-far',
]

# A list of all Arista switches - generally used on the analysis and some daq switches
ARISTA_HOST = [
    'switch-ana-srvroom',
    'switch-ana-row40',
    'switch-ana-mezz',
]

# A list of 'special' Brocade switches that have broken scp support
ICX_HOST = [
    'switch-mfx-h45',
    'switch-cxi-mezz-daq',
    'switch-amo-srvroom-daq',
    'switch-ana-row40-2',
    'switch-mec-cr',
    'switch-ana-mezz2', 
    'switch-xpp-srvroom-daq',
]

# Configuration settings for audit script when it sends emails
EMAIL_CONF = {
    'sender_email'   : 'pcdsroot@slac.stanford.edu',
    'recipient_email': ['pcds-it-l@slac.stanford.edu'],
    'cc_email'       : ['snelson@slac.stanford.edu'],
    #'cc_email'       : ['ddamiani@slac.stanford.edu', 'perazzo@slac.stanford.edu', 'paiser@slac.stanford.edu'],
    'hutches'        : ['lfe','kfe','tmo','rix','xpp','xrt','xcs','mfx','cxi','mec','det','las','hpl','sds','tst'],
    'hutches_recpt'  : {'lfe' : ['pcds-it@slac.stanford.edu' ] ,
                        'kfe' : ['pcds-it@slac.stanford.edu' ] ,
                        'tmo' : ['aegger@slac.stanford.edu' ] ,
                        'rix' : ['jjoshi@slac.stanford.edu' ] ,
                        'xpp' : ['snelson@slac.stanford.edu' ] ,
                        'xrt' : ['pcds-it@slac.stanford.edu' ] ,
                        'xcs' : ['jjoshi@slac.stanford.edu' ] ,
                        'mfx' : ['mcbrowne@slac.stanford.edu'] ,
                        'cxi' : ['aegger@slac.stanford.edu'  ] ,
                        'mec' : ['mcbrowne@slac.stanford.edu'] ,
                        'det' : ['philiph@slac.stanford.edu' ] ,
                        'las' : ['mcbrowne@slac.stanford.edu'] ,
                        'hpl' : ['kmecseki@slac.stanford.edu'] ,
                        'sds' : ['awallace@slac.stanford.edu'] ,
                        'tst' : ['pcds-it@slac.stanford.edu'  ] ,
                       },
    'hutches_cc'     : {'lfe' : ['aegger@slac.stanford.edu','jjoshi@slac.stanford.edu','mcbrowne@slac.stanford.edu'] ,
                        'kfe' : ['aegger@slac.stanford.edu','jjoshi@slac.stanford.edu'] ,
                        'tmo' : ['adpai@slac.stanford.edu'] ,
                        'rix' : ['nwbrown@slac.stanford.edu'] ,
                        'xpp' : ['sheppard@slac.stanford.edu'] ,
                        'xrt' : ['aegger@slac.stanford.edu','jjoshi@slac.stanford.edu','mcbrowne@slac.stanford.edu'] ,
                        'xcs' : ['rajan-01@slac.stanford.edu'] ,
                        'mfx' : ['sheppard@slac.stanford.edu'] ,
                        'cxi' : ['rajan-01@slac.stanford.edu'] ,
                        'mec' : ['sfsyunus@slac.stanford.edu'] ,
                        'det' : ['nakahara@slac.stanford.edu'] ,
                        'las' : ['bhill@slac.stanford.edu'  ] ,
                        'hpl' : ['pcds-it@slac.stanford.edu'] ,
                        'sds' : ['pcds-it@slac.stanford.edu'] ,                   
                        'tst' : ['pcds-it@slac.stanford.edu'] ,
                       },
}

# Settings for the config backup script
BACKUP_CONF = {
    'device': 'switch',
    'device_mapping': {
        'switch': ('dumper', SSH_CONF.get('switch_con_host') , SSH_CONF.get('failed_backup_file')   , HOST_PORTABLE),
        'digi'  : ('digi'  , TELNET_CONF.get('digi_con_host'), TELNET_CONF.get('failed_backup_file'), DIGI_HOST_PORTABLE),
    },
}


