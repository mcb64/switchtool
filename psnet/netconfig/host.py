import logging
import functools
import subprocess

from . import netconfig

module_logger = logging.getLogger(__name__)

class Host(object):
    """
    Class to represent a host found in NetConfig.

    :param host_name: The name of the host
    :type  host_name: str

    :param host_info: A dictionary of attributes and values for this specific
                      host
    :type  host_info: dict
    """
    def __init__(self,host_name,host_info):
        self.name = host_name
        self._info = host_info
        
        for attr,value in host_info.items():
            setattr(self,attr.lower().replace(' ','_'),value)


    @classmethod
    def from_hostname(host_class,name):
        """
        Load a host object by name
        
        :param name: The name of the host in NetConifg
        :type  name: str

        :return: A Host object
        """
        nc = netconfig.NetConfig()
        host_info = nc.find_hosts(name,as_dict=True)
        
        if not host_info:
            module_logger.error('No hosts found fitting name '\
                                '{:}'.format(name))
            return None

        if len(host_info) > 1:
            module_logger.error('Multiple hosts fitting name {:}, '\
                                'please use the Host Group object'.format(name))
            return None
        else:
            return Host(name,list(host_info.values())[0])


    def ping(self,wait=1):
        """
        Ping device.

        :param wait: Wait for this many seconds for response.
        :type  wait: int

        :return: Whether or not device was responsive within the wait period.
        :rtype:  bool
        """
        ping_response = subprocess.call(['ping','-c1','-w{:}'.format(wait),
                                        '{:}'.format(self.name)],
                                        stdout=subprocess.PIPE)
        if ping_response == 0:
            module_logger.info('{:} was responsive to ping'.format(self.name))
            return True

        module_logger.warn('{:} was unresponsive to ping'.format(self.name))
        return False
   

    def show_info(self):
        """
        Print a readable version of hosts information
        """
        print(self)
   
   
    def __str__(self):
        """
        Modify string representation of the device to show information.
        """
        sorted_keys = list(sorted(self._info.keys()))
        #Header
        readback  = '\nInformation for {:}\n'.format(self.name)
        readback +='-'*79
        #Print information in alphabetical order
        for key in sorted_keys:
            readback +='\n{:20}  {:30}'.format(key,str(self._info[key]))
        
        return readback


    def __repr__(self):
        return '<{:} with IP {:} and Ethernet Address {:}'.format(self.name,
                                                                   self.ip,
                                                                   self.ethernet_address)



class HostGroup(object):
    """
    A group of nodes assembled into a single object.

    This class is useful when grouping a number of hosts together with a shared
    attribute, such as a subnet or location

    :param hosts: A  dictionary of host names with a sub-dictionary containing
                  each hosts information.
    :type hosts: dict
    """
    def __init__(self,hosts):
        
        self._hosts = dict([(node,Host(node,node_info)) 
                            for node,node_info in hosts.items()])
        for node,host in self._hosts.items():
            setattr(self,node.replace('-','_'),host)

    @classmethod
    def from_search(group_class,**kwargs):
        """
        Load a Host Group object using the same functionality as
        :func:'netconfig.NetConfig.search'
    
        :return: A Host Group object
        """
        nc = netconfig.NetConfig()
        group = nc.search(as_object=True,**kwargs)
        if not group:
            module_logger.error('No hosts found fitting keyword descriptions')
            return None
        
        return group


    def ping_group(self,wait=1):
        """
        Ping all of the hosts in the group.
        
        :param wait: Wait for this many seconds for response
        :type  wait: int

        :return: A dictionary of ping results, with each host name in the group
                 and a True/False value whether they were responsive to the ping
        :rtype:  bool
        
        """
        pings = [(name,self._hosts[name].ping(wait=1))
                 for name in sorted(self._hosts.keys())] 
        return dict(pings)
