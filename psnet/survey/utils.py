import re
import logging
import getpass
from subprocess import Popen, PIPE, CalledProcessError
from .settings import NETCONFIG_CONF, LOG_CONF, SSH_CONF, TELNET_CONF
# import sys


# Create Logger object with name switch scripts
LOG = logging.getLogger(LOG_CONF.get('logger_name', __name__))


# Mac matching regex
__HOST_REGEX = re.compile('^(?P<host>\S*):$')
__MAC_REGEX  = re.compile('^\s*Ethernet Address: (?P<mac>\S*)$')


def convert_eth(ethernet):
    """
    Convert MAC-address separated by decimal to colon.
    """
    parts = ethernet.split('.')
    return ':'.join([part[:2]+':'+part[2:] for part in parts])


def _get_ethe_addr(netconf_data):
    last_host = None
    mac_pairs = []

    for line in netconf_data.split('\n'):
        host_match = __HOST_REGEX.match(line)
        if host_match:
            last_host = host_match.group('host')
        else:
            mac_match = __MAC_REGEX.match(line)
            if mac_match:
                if last_host is not None:
                    mac_pairs.append((last_host, mac_match.group('mac')))
                    last_host = None

    return mac_pairs


def _query_netconfig(cmd, search, params, excludes, mac_filter):
    ''' From Python 2.7 to Python 3.5 issues:'''
    ''' Needed to add ".decode("utf-8")" to stdout to convert bytes to str '''
    proc = Popen(cmd + [search] + params, stdout=PIPE, stderr=PIPE)
    (stdout, stderr) = proc.communicate()

    if proc.returncode != 0:
        raise CalledProcessError(proc.returncode, cmd)
    
    if mac_filter:
        return [ host for host, mac in _get_ethe_addr(stdout.decode("utf-8")) if host != '' and not excludes.match(host) and mac_filter.match(mac)]
    else:
        return [ host for host in stdout.decode("utf-8").split('\n') if host != '' and not excludes.match(host) ]

def get_device_list(searches, subnets, mac_pattern=None):
    netconf_cmd = [NETCONFIG_CONF.get('script'), NETCONFIG_CONF.get('cmd')]
    netconf_param = []
    netconf_out = []
    mac_filter = re.compile(mac_pattern) if mac_pattern else None
    excludes = re.compile(NETCONFIG_CONF.get('exclude_pattern'))
        
    mac_filter = None
    
    # if not filtering on mac add '--brief' param
    if mac_filter is None:
        netconf_param += NETCONFIG_CONF.get('params')
    
    for search in searches:
        if subnets:
            for subnet in subnets:
                #print("%s %s %s %s %s" % (netconf_cmd, search, netconf_param + ['--subnet', subnet], excludes, mac_filter))
                netconf_out += _query_netconfig(netconf_cmd, search, netconf_param + ['--subnet', subnet], excludes, mac_filter)        
        else:
            #print("here %s %s %s %s %s" % (netconf_cmd, search, netconf_param, excludes, mac_filter))
            netconf_out += _query_netconfig(netconf_cmd, search, netconf_param, excludes, mac_filter)
    
    #print("GET_DEVICE_LIST: \n", netconf_out)
    
    #print("GET_DEVICE_LIST(SET): \n", set(netconf_out))
    
    return sorted(set(netconf_out))


def get_info_location(search, subnets=None, mac_pattern=None):
    ''' Extracts name, Location and Description contents from netconfig view command '''
    netconf_cmd = [NETCONFIG_CONF.get('script'), NETCONFIG_CONF.get('cmd_view')]
    netconf_param = []
    name = '' 
    Location = ''
    Description = ''
    mac_filter = re.compile(mac_pattern) if mac_pattern else None
    excludes = re.compile(NETCONFIG_CONF.get('exclude_pattern'))
    
    # Extract contents in the fields: name, Location and Description
    netconf_view = '\n'.join(_query_netconfig(netconf_cmd, search, netconf_param, excludes, mac_filter)) 
    
    b = netconf_view.split('\n')
         
    for f in b:        
        if '\tname:' in f:
            name = f.split(':')[1].lstrip()
        if '\tLocation:' in f:
            Location = f.split(':')[1].lstrip()
        if '\tDescription:' in f:
            Description = f.split(':')[1].lstrip()
     
    return [name, Location, Description]
    

# def get_info_location_list(searches, subnets=None, mac_pattern=None):
#     ''' Extracts name, Location and Description contents from netconfig view command '''
#     ''' NOT USED HERE '''
#     netconf_cmd = [NETCONFIG_CONF.get('script'), NETCONFIG_CONF.get('cmd_view')]
#     netconf_param = []
#     netconf_out = []
#     mac_filter = re.compile(mac_pattern) if mac_pattern else None
#     excludes = re.compile(NETCONFIG_CONF.get('exclude_pattern'))
# 
#     for search in searches:
#         # Extract contents in the fields: name, Location and Description
#         #print((netconf_cmd, search, netconf_param, excludes, mac_filter))
#         #netconf_view = _query_netconfig(netconf_cmd, search, netconf_param, excludes, mac_filter)
#         # supose that answer comes with '\n'
#         #print (netconf_view)
#         return False
#         b = netconf_view.split('\n')         
#         for f in b:
#             if ' Location:' in f:
#                 l = f.split(':')[1]
#             if ' Description:' in f:
#                 d = f.split(':')[1]
#             if ' name:' in f:
#                 n = f.split(':')[1]
#             print ([n,l,d])
#             netconf_out.append([n,l,d])
# 
#     return set(netconf_out)

def get_digi_info_location(failed_host):
    return get_info_location(failed_host) 

# def get_digi_info_location_list(failed_host):
#     ''' NOT USED HERE '''
#     return get_info_location_list(failed_host) 

def get_switch_list():
    return get_device_list(NETCONFIG_CONF.get('switch_searches'), NETCONFIG_CONF.get('switch_subnets'))


def get_digi_list():
    return get_device_list(NETCONFIG_CONF.get('digi_searches'), NETCONFIG_CONF.get('digi_subnets'), mac_pattern=NETCONFIG_CONF.get('digi_macs'))


def passwd_prompt(user):
    if user is None:
        prompt = 'Password for user: '
    else:
        prompt = 'Password for user \'%s\': '%user
    return getpass.getpass(prompt)


def log_init(format_str='%(asctime)s:%(levelname)s:%(message)s'):
    logging.basicConfig(format=format_str,
                        level=LOG_CONF.get('root_log_level', logging.WARN))


def log_level_parse(log_level):
    return getattr(logging, log_level.upper(), LOG_CONF.get('root_log_level', logging.WARN))


def add_log_opts(parser):
    # grab defaults from the config dict
    def_log = LOG_CONF.get('log_level')

    parser.add_argument('-l',
                        '--log',
                        metavar='LOG',
                        default=def_log,
                        help='The logging level of the script (default %s)'%def_log)


def add_ssh_opts(parser):
    # grab defaults from the config dict
    def_user = SSH_CONF.get('username')
    def_pw = SSH_CONF.get('password')
    def_port = SSH_CONF.get('port')
    def_timeout = SSH_CONF.get('timeout')
    def_private_key = SSH_CONF.get('private_key')

    parser.add_argument('-u',
                        '--user',
                        default=def_user,
                        help='The switch connection username (default: %s)'%def_user)

    parser.add_argument('-P',
                        '--pswd',
                        default=def_pw,
                        help='The switch connection password (default: %s)'%def_pw)

    parser.add_argument('-p',
                        '--port',
                        metavar='PORT',
                        default=def_port,
                        type=int,
                        help='The switch connection port (default: %d)'%def_port)
 
    parser.add_argument('--timeout',
                        metavar='TIMEOUT',
                        default=def_timeout,
                        type=int,
                        help='The switch connection timeout in seconds (default: %d)'%def_timeout)

    key_parser = parser.add_mutually_exclusive_group(required=False)
    key_parser.add_argument('--private-key',
                            dest='private_key',
                            action='store_true',
                            help='Enable private keys for authentication - only works for passwordless private keys%s'%(' (default)' if def_private_key else ''))
    key_parser.add_argument('--no-private-key',
                            dest='private_key',
                            action='store_false',
                            help='Disable private keys for authentication%s'%('' if def_private_key else ' (default)'))
    parser.set_defaults(private_key=def_private_key)

    parser.add_argument('--hosts',
                        metavar='HOST',
                        nargs='*',
                        help='The hosts to run the commands on (default: all switches found in netconfig)')


def add_telnet_opts(parser):
    # grab defaults from the config dict
    def_user = TELNET_CONF.get('username')
    def_pw = TELNET_CONF.get('password')
    def_port = TELNET_CONF.get('port')
    def_timeout = TELNET_CONF.get('timeout')

    parser.add_argument('-u',
                        '--user',
                        default=def_user,
                        help='The Digi connection username (default: %s)'%def_user)

    parser.add_argument('-P',
                        '--pswd',
                        default=def_pw,
                        help='The Digi connection password (default: %s)'%def_pw)

    parser.add_argument('-p',
                        '--port',
                        metavar='PORT',
                        default=def_port,
                        type=int,
                        help='The Digi connection port (default: %d)'%def_port)

    parser.add_argument('--timeout',
                        metavar='TIMEOUT',
                        default=def_timeout,
                        type=int,
                        help='The switch connection timeout in seconds (default: %d)'%def_timeout)

    parser.add_argument('--hosts',
                        metavar='HOST',
                        nargs='*',
                        help='The hosts to run the commands on (default: all Digi PortServers/ConnectPorts found in netconfig)')


def add_con_opts(parser):
    group = parser.add_argument_group('remote connection options', description='options for connecting to the remote devices to be backed up')
    group.add_argument('-u',
                       '--user',
                       help='The remote connection username')

    group.add_argument('-P',
                       '--pswd',
                       help='The remote connection password')

    group.add_argument('-p',
                       '--port',
                       metavar='PORT',
                       type=int,
                       help='The remote connection port')

    group.add_argument('--timeout',
                       metavar='TIMEOUT',
                       type=int,
                       help='The remote connection timeout in seconds')

    group.add_argument('--hosts',
                       metavar='HOST',
                       nargs='*',
                       help='The hosts to run backups on (default: all devices found in netconfig)')

    group.add_argument('--dump-host',
                       metavar='DUMP_HOST',
                       help='Run the configuration dumper script on specified host')
