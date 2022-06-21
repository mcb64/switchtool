import re
import os
import stat
import socket
import shutil
import logging
import tempfile
import telnetlib
from settings import LOG_CONF


LOG = logging.getLogger(LOG_CONF.get('logger_name', __name__))


class TelnetHelper(object):
    def __init__(self, user, pw, port, cfg_cmd, dest_dir, digi_type, dest_file='%s.cfg', timeout=None, cfg_perms=None):
        self.user = user
        self.pw = pw
        self.port = port
        self.timeout = timeout
        self.dest_dir = dest_dir
        self.dest_file = dest_file
        self.cfg_cmd = cfg_cmd
        self.digi_type = digi_type
        if cfg_perms is None:
            self.cfg_perms = stat.S_IRUSR | stat.S_IRGRP | stat.S_IWUSR | stat.S_IROTH
        else:
            self.cfg_perms = cfg_perms
        self.tn_prompt = '#> '
        self.lo_prompt = 'login: '
        self.pw_prompt = 'password: '
        self.newline_split = re.compile('\r?\n')
        if self.digi_type == 'PS':
            self.cmd_list = [
                ('login: ', self.user),
                ('password: ', self.pw),
                (self.tn_prompt, self.cfg_cmd),
                ('%s\r\n\r\n'%self.cfg_cmd, None),
                (self.tn_prompt, 'exit'),
            ]
        elif self.digi_type == 'CP':
            self.cmd_list = [
                ('login: ', self.user),
                ('password: ', self.pw),
                (self.tn_prompt, self.cfg_cmd),
                ('%s\r\n'%self.cfg_cmd, None),
                (self.tn_prompt, 'exit'),
            ]
        else:
            self.cmd_list = []
        self.tn = telnetlib.Telnet()

    def get_cfg(self, host):
        # if MOXA in host then skip this module:
        if 'moxa' in host:
            return 0
        # Temporary file for writing the config to
        temp_path = None

        try:
            LOG.debug('Retrieving configuration from %s', host)
            self.tn.open(host, self.port, self.timeout)
            LOG.debug('Successful telnet connection to %s', host)
            # Container for useful telnet output
            tn_out = None
            keep_next_out = False
            # ConnectPorts and PortServers have different formatting
            if (self.digi_type != 'PS') and (self.digi_type != 'CP'):
                LOG.error('Unknown Digi type selected! %s', self.digi_type)
                LOG.error('Skipping file transfer for %s', host)
                return 1
            for prompt, reply in self.cmd_list:
                ### cur_out = self.tn.read_until(prompt) # Python 2.7
                cur_out = self.tn.read_until(prompt.encode())
                if keep_next_out:
                    tn_out = cur_out
                    keep_next_out = False
                # if there is no reply string then we should keep next output
                if reply is None:
                    keep_next_out = True
                else:
                    ### self.tn.write('%s\n' % reply) # Ptyhon 2.7
                    reply = '%s\n' % reply
                    reply = reply.encode()
                    self.tn.write(reply)
            # open temporary output file to write the config to
            with tempfile.NamedTemporaryFile('w', delete=False) as outf:
                # Save the path to the new temporary file
                temp_path = outf.name
                LOG.debug('Transfering configuration file to %s', outf.name)
                for line in self.newline_split.split(tn_out.decode()):
                    if line != '\r%s'%self.tn_prompt and line != '%s'%self.tn_prompt:
                        outf.write('%s\n'%line)

            # If we got here its safe to overwrite the cfg with the temp one
            shutil.copy(temp_path, os.path.join(self.dest_dir, self.dest_file%host))
            os.chmod(os.path.join(self.dest_dir, self.dest_file%host), self.cfg_perms)

            return 0
        except socket.error as err:
            LOG.error('Failure connecting to %s: %s', host, err)
            LOG.error('Skipping file transfer for %s', host)
            return 1
        except EOFError as eof_err:
            LOG.error('Connection to %s closed unexpectedly: %s', host, eof_err)
            LOG.error('Skipping file transfer for %s', host)
            return 1
        except IOError as io_err:
            LOG.error('Failure writing %s config to disk: %s', host, io_err)
            LOG.error('Skipping file transfer for %s', host)
            return 1
        finally:
            self.tn.close()
            if temp_path is not None and os.path.exists(temp_path):
                os.remove(temp_path)
