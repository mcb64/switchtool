import re
import logging

from . import command
from . import utils

class Surveyer(object):
    """
    Class to survey devices on switch.
    """
    _vlan_format = None
    _port_format = None
    _cmd_runner  = None
    
    def __init__(self,user,pw,enablepw,port=None,timeout=None):
        self.user    = user
        self.pw      = pw
        self.enablepw= enablepw
        self.port    = port
        self.timeout = timeout
        self._vlan_cmd = ['show vlan']
        self._mac_cmd  = ['show mac-address']
        self._vlan_formatter = None

    def show_vlan(self,host,vlan_no=None):
        """
        Create a dictionary of each VLAN with untagged ports. If a specific
        VLAN is not specified, all VLAN on the switch will be queried

        host (str)    - Name of host
        vlan_no (str) - Number of vlan to be observed.
        """
        vlan_info = {}
        cmd  = self._vlan_cmd
        
        if vlan_no:
            cmd[0] = '{:} {:}'.format(cmd[0].rstrip('\n'),vlan_no) 
        
        cmdr  = self._cmd_runner(self.user,self.pw,self.enablepw,self.port,
                                    cmd,timeout=self.timeout)
        #Parse output
        out_code,raw_vlan = cmdr.run(host)
        if self._vlan_formatter is not None:
            raw_vlan = self._vlan_formatter(raw_vlan)
        vlan = self._vlan_format.findall(raw_vlan)
        
        for vlan_no,raw_ports in vlan:
            ports = self._port_format.findall(raw_ports)
            vlan_info[vlan_no] = ports
        return vlan_info

    def show_mac(self,host,vlan_no=None):
        """
        Create a dictionary of MAC addresses found on each port.
        """
        mac_info = {}
        cmd      = self._mac_cmd
        if vlan_no:
            cmd[0] = '{:} vlan {:}'.format(cmd[0].rstrip('\n'),vlan_no) 
        
        cmdr     = self._cmd_runner(self.user,
                                    self.pw,
                                    self.enablepw,
                                    self.port,
                                    cmd,timeout=self.timeout)
        out_code,raw_mac = cmdr.run(host)
        with open("am", "w") as f:
            f.write(raw_mac)

        #Parse output
        mac = self._mac_format.findall(raw_mac) 
        return dict([(j,utils.convert_eth(i)) for i,j in mac])

    # Let's claim no one needs an enable command by default!
    def check_mode(self, host):
        return False

class BrocadeSurveyer(Surveyer):

    _vlan_format = re.compile(r'PORT-VLAN ([\d]+), Name [\D]+,.+?\r\n(.+?)Monitoring',re.DOTALL)
    _port_format = re.compile(r'Untagged Ports: \(U(\d+)/M(\d+)\)(.+)\r') 
    _mac_format  = re.compile(r'([\S]{14})[\s]+?([\S]+)[\s]+?Dynamic')  
    _cmd_runner  = command.BrocadeCommandRunner 
    
    def __init__(self,user,pw,enablepw,port=22,timeout=None):
        super(BrocadeSurveyer,self).__init__(user,pw,enablepw,port=port,
                                             timeout=timeout)
   
    def show_vlan(self,host,vlan_no=None):
        ''' Python 2.7 :  for vlan,port_info in vlan_info.iteritems(): '''
        ''' Python 3.5 :  for vlan,port_info in vlan_info.items():     '''
        """
        Create a dictionary of each VLAN with untagged ports.

        An extra complication is added because of the way the ports are
        displayed by the Brocade.
        """
        vlan_info = super(BrocadeSurveyer,self).show_vlan(host,vlan_no=vlan_no)
        #for vlan,port_info in vlan_info.iteritems():
        for vlan,port_info in vlan_info.items():
            full_ports = []
            if port_info:
                for line in port_info:
                    stack  = list(line[:2])
                    for port in re.findall(r'([\d]+)',line[2]):
                        full_ports.append('/'.join(stack+[port])) 
            vlan_info[vlan] = full_ports
        return vlan_info


class RuckusSurveyer(Surveyer):

    _vlan_format = re.compile(r'PORT-VLAN ([\d]+), Name [\D]+,.+?\r\n(.+?)Monitoring',re.DOTALL)
    _port_format = re.compile(r'Untagged Ports: \(U(\d+)/M(\d+)\)(.+)\r') 
    _mac_format  = re.compile(r'([\S]{14})[\s]+?([\S]+)[\s]+?Dynamic')  
    _cmd_runner  = command.RuckusCommandRunner 

    def __init__(self,user,pw,enablepw,port=22,timeout=None):
        super(RuckusSurveyer,self).__init__(user,pw,enablepw,port=port,
                                           timeout=timeout)
    
    def show_vlan(self,host,vlan_no=None):
        ''' Python 2.7 :  for vlan,port_info in vlan_info.iteritems(): '''
        ''' Python 3.5 :  for vlan,port_info in vlan_info.items():     '''
        """
        Create a dictionary of each VLAN with untagged ports.

        An extra complication is added because of the way the ports are
        displayed by the Brocade.
        """
        vlan_info = super(RuckusSurveyer,self).show_vlan(host,vlan_no=vlan_no)
        #for vlan,port_info in vlan_info.iteritems():
        for vlan,port_info in vlan_info.items():
            full_ports = []
            if port_info:
                for line in port_info:
                    stack  = list(line[:2])
                    for port in re.findall(r'([\d]+)',line[2]):
                        full_ports.append('/'.join(stack+[port])) 
            vlan_info[vlan] = full_ports
        return vlan_info

    # Return True if we need to enable!
    def check_mode(self, host):
        cmdr  = self._cmd_runner(self.user,self.pw,self.enablepw,self.port,
                                 ["show clock"],timeout=self.timeout)
        cmdr.run(host)
        return cmdr.mode == '>'
        

class CiscoSurveyer(Surveyer):

    _vlan_format = re.compile(r'([\d]+).+active[\s]+(.+)')
    _port_format = re.compile(r'(Gi0/[\d]{1:2})')
    _mac_format  = re.compile(r' [\d]{3}[\s]+?(\S+)[\s]+?DYNAMIC[\s]+(.+)')
    _cmd_runner  = command.CiscoCommandRunner 

    def __init__(self,user,pw,enablepw,port=22,timeout=None):
        super(CiscoSurveyer,self).__init__(user,pw,enablepw,port=port,
                                           timeout=timeout)


class AristaSurveyer(Surveyer):

    _vlan_format = re.compile(r'([\d]+).*active(.*)')
    _port_format = re.compile(r'(Et[\d]{1,2})')
    _mac_format  = re.compile(r' [\d]{3}[\s]+?(\S+)[\s]+?DYNAMIC[\s]+(\S+)')
    _cmd_runner  = command.AristaCommandRunner 

    def __init__(self,user,pw,enablepw,port=22,timeout=None):
        super(AristaSurveyer,self).__init__(user,pw,enablepw,port=port,
                                            timeout=timeout)
        self._mac_cmd = ['show mac address-table']
        self._vlan_formatter = self.__vlan_format

    def __vlan_format(self, l1):
        ll = l1.split("\n")
        cont = False
        l2 = ""
        for l in ll:
            if cont and len(l) > 0 and l[0] >= '0' and l[0] <= '9':
                l2 += "\n"
                cont = False
            if len(l) > 0 and l[0] >= '0' and l[0] <= '9':
                l2 += l.strip()
                cont = True
            elif cont:
                l2 += ", " + l.strip()
        return l2
