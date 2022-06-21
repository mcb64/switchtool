#!/reg/g/pcds/pyps/conda/rhel6/envs/pcds/bin/python

###!/usr/bin/env python
import os
import sys
import utils
import pickle
import logging
import telnet
from argparse import ArgumentParser
from subprocess import CalledProcessError
from settings import TELNET_CONF, LOG_CONF, DIGI_HOST_IGNORE, MOXA_HOST_IGNORE, DIGI_HOST_CONNECTPORTS
import requests
import subprocess

# Create Logger object with name switch scripts
LOG = logging.getLogger(LOG_CONF.get('logger_name', __name__))


def parse_cli():
    # Create the parser
    parser = ArgumentParser(description='A cli tool for dumping the configuration information from Digi PortServers and ConnectPorts.')

    # Add the default ssh options
    utils.add_telnet_opts(parser)

    parser.add_argument('-d',
                        '--dest',
                        default=os.getcwd(),
                        help='Destination dir for the config files (default: getcwd)')

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

    # config grabber cmd
    config_cmd_CP = TELNET_CONF.get('config_cmd_CP')
    config_cmd_PS = TELNET_CONF.get('config_cmd_PS')
    config_perms = TELNET_CONF.get('config_perms')

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
            LOG.info('Attempting to retrieve a list of Terminal Servers from netconfig:')
            #digis = utils.get_digi_list()
            tservers = utils.get_digi_list()
        except (OSError, CalledProcessError) as err:
            LOG.critical('Problem running netconfig: %s', err)
            return 1
        
        good_tservers = [ tserver for tserver in tservers if tserver not in DIGI_HOST_IGNORE and MOXA_HOST_IGNORE]
        good_tservers.sort()
        
        digis = [i for  i in tservers if 'digi' in i]
        good_digis = [i for  i in good_tservers if 'digi' in i]
        good_digis.sort()
        num_digi = len(digis)
        num_digi_good = len(good_digis)

        moxas = [i for  i in tservers if 'moxa' in i]
        good_moxas = [i for  i in good_tservers if 'moxa' in i]
        good_moxas.sort()        
        num_moxa = len(moxas)
        num_moxa_good = len(good_moxas)

        LOG.info('Found %03d Digis via netconfig, %02d of which are in the ignore list', num_digi, num_digi - num_digi_good)
        LOG.info('Found %03d Moxas via netconfig, %02d of which are in the ignore list', num_moxa, num_moxa - num_moxa_good)
    else:
        # TODO: need to implement for Moxas...
        good_digis = opts.hosts
        num_digi_good = len(good_digis)

    # Use telnet to dump the digi configurations
    LOG.info('Attempting to dump configurations for %d Digis and %d Moxas' % (num_digi_good, num_moxa_good))
    LOG.debug('----------------------------------------------------------')
     
    
    # Hard coding the Digi type for now...might want to change in the future
    telnet_client_CP = telnet.TelnetHelper(opts.user, passwd, opts.port, config_cmd_CP, dest_dir, digi_type='CP', timeout=opts.timeout, cfg_perms=config_perms)
    telnet_client_PS = telnet.TelnetHelper(opts.user, passwd, opts.port, config_cmd_PS, dest_dir, digi_type='PS', timeout=opts.timeout, cfg_perms=config_perms)
    digi_fails = 0
    moxa_fails = 0
    failed_hosts = []
    failed_hosts_fname = os.path.join(dest_dir, TELNET_CONF.get('failed_backup_file'))
    
    # joining the lists:
    good_hosts = good_digis + good_moxas
    for host in good_hosts:        
        LOG.debug('Attempting to fetch config file for %s', host)
        if 'moxa' in host: # Using http and javascript methods
            try:            
                moxacfg = _backup_moxa(host)
                if moxacfg is not False:
                    with open(os.path.join(dest_dir, '%s.cfg' % host), 'wb') as f:
                        f.write(moxacfg)
                    os.chmod(os.path.join(dest_dir, '%s.cfg' % host), config_perms)
                else:
                    failed_hosts.append(host)
                    moxa_fails += 1
            except:
                LOG.debug('Error accessing %s' % host)
                failed_hosts.append(host)
                moxa_fails += 1
                continue
        else:    
            # Run telnet command for ConnectPort or PortServer
            if host in DIGI_HOST_CONNECTPORTS:
                good = telnet_client_CP.get_cfg(host)
            else:
                good = telnet_client_PS.get_cfg(host)
            if good != 0:
                failed_hosts.append(host)
                digi_fails += 1
            LOG.debug('----------------------------------------------------------')
    
    LOG.info('Successfully retrieved %03d of %03d Digi PS & CP configs', num_digi_good - digi_fails, num_digi_good)
    LOG.info('Successfully retrieved %03d of %03d Moxa configs', num_moxa_good - moxa_fails, num_moxa_good)
    # Write out list of hosts with failed backups
    if (digi_fails > 0 or moxa_fails > 0) and opts.fail:
        LOG.debug('Writing list of hosts for which the configuration dump failed to %s' % failed_hosts_fname)
        with open(failed_hosts_fname, 'wb') as outf:
            pickle.dump(failed_hosts, outf)

    return (digi_fails != 0) and (moxa_fails != 0)

def _backup_moxa(moxa, moxapass = 'moxa'):
    ''' Gets moxa configuration and returns config binary file: moxacfg'''    
    try:
        #print('Retrieving configuration from %s', moxa)
        script_dir = os.path.dirname(__file__)
        s          = requests.Session()        
        login_page = s.get("http://%s/" % moxa)
        ltext      = login_page.text
        chpattern  = "name=FakeChallenge value="
        chstart    = ltext.index(chpattern) + len(chpattern)
        chend      = ltext.index(">", chstart)
        challenge  = ltext[chstart:chend]  
        #md5pwd     = subprocess.check_output(["node", "moxapwd.js", moxapass, challenge])
        md5pwd     = subprocess.check_output(["node", "%s/moxapwd.js" % script_dir, moxapass, challenge])
        post_data = {
        'Username'      : 'admin', 
        'Password'      : '',
        'MD5Password'   : md5pwd,
        'FakeChallenge' : challenge,
        'Submit.x'      : '51',
        'Submit.y'      : '17',
        'Submit'        : 'Login'}
        
        s.post("http://%s/" % moxa, post_data)

        # Find the correct MOXA model:
        main = s.get("http://%s/main.htm" % moxa)
        model = main.text.split('Model name</TD><TD')[1].split('column_text_no_bg>')[1].split('</TD>')[0].replace(" ", "")      
        print('---- %-20s Model %s' % (moxa, model))
            
        config_resp = s.get("http://%s/ConfExp.htm" % moxa)
        cfg_text    = config_resp.text        
    
        if 'NP6610' in model:
            moxacfg = s.post("http://%s/Config.txt" % moxa, data = { "Submit": "Download"  })
        elif 'NP6650' in model:
            cfg_pattern = "name=csrf_token value="
            crb_start   = cfg_text.index(cfg_pattern) + len(cfg_pattern)
            crb_end     = cfg_text.index(">", crb_start)
            crb         = cfg_text[crb_start:crb_end]    
            moxacfg = s.post("http://%s/Config.txt" % moxa, data = { "Submit": "Download", "csrf_token" : crb  })
        else:
            print ('MOXA model to be implemented..')
            return False
 
    except socket.error as err:
        print('Failure connecting to %s: %s' % (moxa, err))
        print('Skipping file transfer for %s' % moxa)
        return False

    except EOFError as eof_err:
        print('Connection to %s closed unexpectedly: %s'% (moxa, eof_err))
        print('Skipping file transfer for %s'% moxa)
        return False

    return moxacfg.content

# def _backup_moxa(moxa, moxapass = 'moxa'):    
#     ''' Gets moxa configuration and returns config binary file: moxacfg'''
#     script_dir = os.path.dirname(__file__)
#     s          = requests.Session()
#     login_page = s.get("http://%s/" % moxa)
#     ltext      = login_page.text
#     chpattern  = "name=FakeChallenge value="
#     chstart    = ltext.index(chpattern) + len(chpattern)
#     chend      = ltext.index(">", chstart)
#     challenge  = ltext[chstart:chend]  
#     md5pwd     = subprocess.check_output(["node", "%s/moxapwd.js" % script_dir, moxapass, challenge])
#     
# #     first_resp = s.post("http://%s/" % moxa, data={
# #     'Username'      : 'admin', 
# #     'Password'      : '',
# #     'MD5Password'   : md5pwd,
# #     'FakeChallenge' : challenge,
# #     'Submit.x'      : '51',
# #     'Submit.y'      : '17',
# #     'Submit'        : 'Login'})
#     print('------- moxa: %s\n' % moxa) 
#     data_6650={
#     'Username'      : 'admin', 
#     'Password'      : '',
#     'MD5Password'   : md5pwd,
#     'FakeChallenge' : challenge,
#     'Submit.x'      : '51',
#     'Submit.y'      : '17',
#     'Submit'        : 'Login'}
# 
# #     data_6610={
# #     'Username'      : 'admin', 
# #     'Password'      : '',
# #     'MD5Password'   : md5pwd,
# #     'FakeChallenge' : challenge,
# #     'Submit.x'      : '39',
# #     'Submit.y'      : '21',
# #     'Submit'        : 'Login'}
# 
#     first_resp = s.post("http://%s/" % moxa, data_6650)    
#     config_resp = s.get("http://%s/ConfExp.htm" % moxa)
#     cfg_text    = config_resp.text        
#     
#     # Find the correct MOXA model:
#     main = s.get("http://%s/main.htm" % moxa)
#     model = main.text.split('Model name</TD><TD')[1].split('column_text_no_bg>')[1].split('</TD>')[0]
#     
#     print('---- %s Model\n' % moxa, model)
#     
#     
#     if model is 'NP6610':
#         moxacfg = s.post("http://%s/Config.txt" % moxa, data = { "Submit": "Download"  })
#     elif model is 'NP6650':
#         cfg_pattern = "name=csrf_token value="
#         crb_start   = cfg_text.index(cfg_pattern) + len(cfg_pattern)
#         crb_end     = cfg_text.index(">", crb_start)
#         crb         = cfg_text[crb_start:crb_end]    
#         moxacfg = s.post("http://%s/Config.txt" % moxa, data = { "Submit": "Download", "csrf_token" : crb  })
#     else:
#         print ('MOXA model to be implemented..')
#         moxacfg = None    
#     
#     
# 
# 
# 
#     
# #     try:        
# #         first_resp = s.post("http://%s/" % moxa, data_6650)    
# #         config_resp = s.get("http://%s/ConfExp.htm" % moxa)
# #         cfg_text    = config_resp.text        
# #         cfg_pattern = "name=csrf_token value="
# #         crb_start   = cfg_text.index(cfg_pattern) + len(cfg_pattern)
# #         crb_end     = cfg_text.index(">", crb_start)
# #         crb         = cfg_text[crb_start:crb_end]
# #     except:
# #         first_resp = s.post("http://%s/" % moxa, data_6610)    
# #         config_resp = s.get("http://%s/ConfExp.htm" % moxa)
# #         cfg_text    = config_resp.text 
# #         
# #         print('---- cfg_text\n', cfg_text)
# #                
# #         cfg_pattern = "name=csrf_token value="
# #         crb_start   = cfg_text.index(cfg_pattern) + len(cfg_pattern)
# #         crb_end     = cfg_text.index(">", crb_start)
# #         crb         = cfg_text[crb_start:crb_end]
#         
#     
# 
#     return moxacfg

if __name__ == '__main__':
    try:
        # set the root logger since this is an entry point
        utils.log_init()
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(1)
