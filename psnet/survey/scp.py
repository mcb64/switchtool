import re
import os
import stat
import time
import socket
import shutil
import logging
import tempfile
import paramiko
from paramiko.ssh_exception import SSHException
from settings import LOG_CONF


LOG = logging.getLogger(LOG_CONF.get('logger_name', __name__))

####TIMEOUT = 60 # timeout for ordinary while loops in seconds

class SCPHelper(object):
    def __init__(self, user, pw, port, cfg_name, dest_dir, dest_file='%s.cfg', timeout=None, cfg_perms=None, private_key=False):
        self.user = user
        self.pw = pw
        self.port = port
        self.timeout = timeout
        self.private_key = private_key
        self.dest_dir = dest_dir
        self.dest_file = dest_file
        self.cfg_name = cfg_name
        if cfg_perms is None:
            self.cfg_perms = stat.S_IRUSR | stat.S_IRGRP | stat.S_IWUSR | stat.S_IROTH
        else:
            self.cfg_perms = cfg_perms
        self.cmd = 'scp -f %s'%cfg_name
        self.arista_cmd = 'show %s | no-more'%cfg_name
        self.icx_cmd = 'show %s'%cfg_name
        self.cisco_cmds = [
            ('enable', False),
            ('terminal length 0', False),
            ('show %s'%cfg_name, True),
            ('exit', False),
        ]
        self.arista_re = re.compile('^!\sCommand:\sshow %s'%cfg_name)
        self.arista_modtime_re = re.compile('^!\sStartup-config\slast\smodified\sat\s+(?P<date>.*)\sby\s')
        self.prot_re = re.compile('^C[0-7]{4}\s\d+\s%s.cfg$'%cfg_name)
        self.pw_prompt = re.compile('(?:P|p)assword:')
        self.prompt = '^SSH@%s#(?P<cmd>.*)'
        self.page_cont_re = re.compile('--More--, next page: Space, next line: Return key, quit: Control-c\b[ \b]+\b(?P<data>.*)')
        self.header_re = re.compile('^ver\s[\w\.]+')
        self.connect_kwargs = {
            'timeout': self.timeout,
            'look_for_keys': self.private_key,
        }
        self._config()

    def _config(self):
        self.ssh = paramiko.SSHClient()
        self.ssh.load_system_host_keys()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    def get_arista_cfg(self, host):
        # Temporary file for writing the config to
        LOG.info('Getting configuration %-8s : %s' % ('ARISTA', host))
        temp_path = None

        try:
            LOG.debug('Retrieving configuration file %s from %s', self.cfg_name, host)
            # Connect and send the command over ssh
            self.ssh.connect(host, self.port, self.user, self.pw, **self.connect_kwargs)
            LOG.info('ARISTA %s' % self.arista_cmd)
            (stdin, stdout, stderr) = self.ssh.exec_command('%s\n'%self.arista_cmd)
            # Should return a header of the form:
            # ! Command: <cmd>
            echo_header = stdout.readline()
            if self.arista_re.match(echo_header):
                # Read the output of the show command into a temporary file
                with tempfile.NamedTemporaryFile('w', delete=False) as outf:
                    LOG.debug('Transfering configuration file to %s', outf.name)
                    temp_path = outf.name
                    # Check if there is leading modified time line otherwise write it to config
                    mod_time = stdout.readline()
                    mod_time_match = self.arista_modtime_re.match(mod_time)
                    if mod_time_match:
                        LOG.debug('Config last modified on %s', mod_time_match.group('date'))
                    else:
                        outf.write(mod_time)
                    # Read in the rest of the output now
                    for line in stdout.readlines():
                        outf.write(line)

                # If we got here its safe to overwrite the cfg with the temp one
                shutil.copy(temp_path, os.path.join(self.dest_dir, self.dest_file%host))
                os.chmod(os.path.join(self.dest_dir, self.dest_file%host), self.cfg_perms)

                return 0
            else:
                LOG.error('Problem running command \'%s\': %s', self.arista_cmd, echo_header)
                LOG.error('Skipping file transfer for %s', host)
                return 1
        except (SSHException, socket.error) as err:
            LOG.error('Failure connecting to %s: %s', host, err)
            LOG.error('Skipping file transfer for %s', host)
            return 1
        except IOError as io_err:
            LOG.error('Failure writting %s config to disk: %s', host, io_err)
            LOG.error('Skipping file transfer for %s', host)
            return 1
        finally:
            self.ssh.close()
            if temp_path is not None and os.path.exists(temp_path):
                os.remove(temp_path)

            
    def get_cisco_cfg(self, host):
        ''' Python 2.7 data = chan.recv(1024)                 '''
        ''' Python 3.5 data = chan.recv(1024).decode("utf-8") '''
        LOG.info('Getting configuration %-8s : %s' % ('CISCO', host))
        # Temporary file for writing the config to
        temp_path = None

        try:
            self.ssh.connect(host, self.port, self.user, self.pw, **self.connect_kwargs)
            chan = self.ssh.invoke_shell()
            ssh_out = chan.makefile('rb', 8192)
            try:
                with tempfile.NamedTemporaryFile('w', delete=False) as outf:
                    # Save the path to the new temporary file
                    temp_path = outf.name
                    for cmd, wout in self.cisco_cmds:
                        chan.send('%s\n'%cmd)
                        time.sleep(.15)
                        LOG.info('CISCO %s' % cmd)
                        while chan.recv_ready():
                            if wout:
                                # consume the command echo back
                                ssh_out.readline()
                                # Loop until we reach teh end of the config file
                                LOG.debug('Retrieving configuration file %s from %s', self.cfg_name, host)
                                LOG.debug('Transfering configuration file to %s', outf.name)
                                conf_begin_seen = False
                                while True:
                                    #line = ssh_out.readline()
                                    line = ssh_out.readline().decode("utf-8")                                    
                                    if conf_begin_seen:
                                        outf.write(line)
                                        if line == '\r\n' or line == '\n':
                                            wout = False
                                            break
                                    else:
                                        if line == '!\r\n' or line == '!\n':
                                            outf.write(line)
                                            conf_begin_seen = True
                            else:
                                data = chan.recv(1024).decode("utf-8")
                                if self.pw_prompt.search(data):
                                    chan.send('%s\n'%self.pw)

                time.sleep(.25)
                if chan.exit_status_ready():
                    # If we got here its safe to overwrite the cfg with the temp one
                    shutil.copy(temp_path, os.path.join(self.dest_dir, self.dest_file%host))
                    os.chmod(os.path.join(self.dest_dir, self.dest_file%host), self.cfg_perms)

                    return chan.recv_exit_status()
                else:
                    LOG.error('Connection to %s did not exit properly', host)
                    return 1
            finally:
                chan.close()
        except (SSHException, socket.error) as err:
            LOG.error('Failure connecting to %s: %s', host, err)
            LOG.error('Skipping file transfer for %s', host)
            return 1
        except IOError as io_err:
            LOG.error('Failure writting %s config to disk: %s', host, io_err)
            LOG.error('Skipping file transfer for %s', host)
            return 1
        finally:
            self.ssh.close()
            if temp_path is not None and os.path.exists(temp_path):
                os.remove(temp_path)

    def get_cfg(self, host):        
        LOG.info('Getting configuration %-8s : %s' % ('STANDARD', host))        
        # Temporary file for writing the config too
        temp_path = None

        try:
            self.ssh.connect(host, self.port, self.user, self.pw, **self.connect_kwargs)
            LOG.info('STANDARD %s' % self.cmd)
            (stdin, stdout, stderr) = self.ssh.exec_command(self.cmd)
            # Write a newline to stin to start the switches dump
            stdin.write('\n')
            # If there is no stderr then write out
            # first line of stdout should be the scp protocol message:
            # Cmmmm <length> <filename> where mmmm is the file mode
            prot_msg = stdout.readline()
            if self.prot_re.match(prot_msg):
                LOG.debug('Retrieving configuration file %s from %s', self.cfg_name, host)
                LOG.debug('Successful scp connection to %s', host)
                with tempfile.NamedTemporaryFile('w', delete=False) as outf:
                    # Save the path to the new temporary file
                    LOG.debug('Transfering configuration file to %s', outf.name)
                    temp_path = outf.name
                    for line in stdout.readlines():
                        # The scp data is null terminated, so we can stop there
                        if line == '\0':
                            break
                        outf.write(line)

                # If we got here its safe to overwrite the cfg with the temp one
                shutil.copy(temp_path, os.path.join(self.dest_dir, self.dest_file%host))
                os.chmod(os.path.join(self.dest_dir, self.dest_file%host), self.cfg_perms)

                return 0
            else:
                LOG.error('Invalid scp protocol msg: %s', prot_msg)
                LOG.error('Skipping file transfer for %s', host)
                return 1
        except (SSHException, socket.error) as err:
            LOG.error('Failure connecting to %s: %s', host, err)
            LOG.error('Skipping file transfer for %s', host)
            return 1
        except IOError as io_err:
            LOG.error('Failure writting %s config to disk: %s', host, io_err)
            LOG.error('Skipping file transfer for %s', host)
            return 1
        finally:
            self.ssh.close()
            if temp_path is not None and os.path.exists(temp_path):
                os.remove(temp_path)

    def get_icx_cfg(self, host):
        ''' Python 2.7  matcher = prompt_re.match(line.rstrip())    '''
        '''             line = ssh_out.readline()                   '''
        ''' Python 3.5  tmp_line = line.decode("utf-8")             '''
        '''             matcher = prompt_re.match(tmp_line.rstrip())'''
        '''             line = ssh_out.readline().decode("utf-8")   '''             
        LOG.info('Getting configuration %-8s : %s' % ('ICX', host))
        prompt_re = re.compile(self.prompt%host)
        # Temporary file for writing the config too
        temp_path = None

        try:
            self.ssh.connect(host, self.port, self.user, self.pw, **self.connect_kwargs)
            chan = self.ssh.invoke_shell()
            ssh_out = chan.makefile('rb', 8192)
            # Manually print the config and parse through it
            seen_echo = False
            seen_prompt = False
            seen_header = False
            # Send command to show config
            LOG.debug('Retrieving configuration file %s from %s', self.cfg_name, host)
            
            chan.send('%s\r\n'%self.icx_cmd)
            LOG.info('ICX %s' % self.icx_cmd)
            
            # Read until we see the echo of the config command
            while not seen_echo:
                if chan.recv_ready():
                    line = ssh_out.readline()
                    print ('LINE', host, line)
                    tmp_line = line.decode("utf-8") # convert to string
                    #matcher = prompt_re.match(line.rstrip())
                    #matcher = prompt_re.match(line.decode("utf-8").rstrip())
                    matcher = prompt_re.match(tmp_line.rstrip())
                    ####print('EP: tmp_line.rstrip() ', tmp_line.rstrip())
                    ####print('EP: matcher ', matcher)
                    
                    print ('TMP_LINE', host, tmp_line)
                    if matcher and matcher.group('cmd') == self.icx_cmd:
                        seen_echo = True
                
            
            
            # Sort of ugly but ensures we won't block on the last line of output of the config
            chan.send(' \r\n')
            # Open output file and start reading data into it
            with tempfile.NamedTemporaryFile('w', delete=False) as outf:
                # Save the path to the new temporary file
                LOG.debug('Transfering configuration file to %s', outf.name)
                
                temp_path = outf.name
                while not seen_prompt:                    
                    if chan.recv_ready():
                        #line = ssh_out.readline()
                        line = ssh_out.readline().decode("utf-8")
                        print(host, 'ICX_LINE', line)
                        if seen_header:
                            page_cont = self.page_cont_re.match(line)
                            if page_cont:
                                chan.send(' \r\n')
                                outf.write(page_cont.group('data')+'\n')
                            elif prompt_re.match(line):
                                seen_prompt = True
                            else:
                                outf.write(line)
                        else:
                            if self.header_re.match(line):
                                outf.write(line)
                                seen_header = True

            # The somewhat ugly exit process for these switches...
            chan.send('exit\r\n')
            # set a timeout in case switch never responds after first exit
            chan.settimeout(0.25)
            
            try:                
                if not chan.exit_status_ready():
                    chan.send('exit\r\n')
            except socket.timeout:
                # if this timedout then its likely exited
                pass
            
            # If we got here its safe to overwrite the cfg with the temp one
            shutil.copy(temp_path, os.path.join(self.dest_dir, self.dest_file%host))
            os.chmod(os.path.join(self.dest_dir, self.dest_file%host), self.cfg_perms)
            print ('THE PROBLEM IS HERE: switch-ana-mezz2 doesn\'t issue the correct exit status')
            print ('ICX_CHAN.RECV_EXIT_STATUS', chan.recv_exit_status())
            return chan.recv_exit_status()
        except (SSHException, socket.error) as err:
            LOG.error('Failure connecting to %s: %s', host, err)
            LOG.error('Skipping file transfer for %s', host)
            return 1
        except IOError as io_err:
            LOG.error('Failure writting %s config to disk: %s', host, io_err)
            LOG.error('Skipping file transfer for %s', host)
            return 1
        finally:
            self.ssh.close()
            if temp_path is not None and os.path.exists(temp_path):
                os.remove(temp_path)
