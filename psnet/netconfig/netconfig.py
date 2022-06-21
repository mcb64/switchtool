import sys
import time
import logging
import fnmatch
import subprocess

from . import host
from . import parsing

module_logger = logging.getLogger(__name__)

class NetConfig(object):
    """
    Python API for NetConfig.

    :param auto_load: Whether or not to automatically load all of the NetConfig
                      information into dictionaries. By default, this should always
                      be True
    :type auto_load:  bool

    :param infer_location: Whether or not to parse NetConfig for additional
                           information including rack, building, and hutch
    :type infer_location:  bool
    """
    _loadtime = None 
    _nodes    = {} 
    _mac      = {}   
    
    def __init__(self,auto_load=True,infer_location=False):
        if auto_load:
            self.load_nodes(infer_location=infer_location)


    def load_nodes(self,infer_location=False):
        """
        Load all of Netconfig into underlying Python dictionaries.
        
        :param infer_location: Whether or not to parse NetConfig for additional
                               information including rack, building, and hutch
        :type infer_location:  bool
        """
        module_logger.debug('Loading NetConfig information...')
        #raw   = subprocess.check_output("netconfig search '*'",shell=True)
        raw   = subprocess.check_output(["/reg/common/tools/bin/netconfig", "search", "*"]).decode('utf-8')
        hosts = parsing.parse_netconfig(raw)
        self._nodes.update(hosts)
        
        for device,info in self._nodes.items():
            try:
                self._mac.update({info['ethernet_address'].lower():device})
            except KeyError:
                module_logger.debug('{:} has no ethernet '\
                                    'address listed'.format(device))
        
        module_logger.info('Succesfully loaded NetConfig information')
        
        if infer_location:                                   #This still needs to be worked on
            for node,info in self._nodes.items():            #I will probably wait until the 
                for attr in ['name','alias','description',   #the time comes to integrate PyQT
                             'cnames','subnet','location']:  #Rack Profiles into the home screen
                    if attr == 'cnames':
                        search_func = parsing.parse_cname
                    else:
                        search_func = parsing.search_location
                    
                    info.update(search_func(info.get(attr)))

            module_logger.debug('Parsed netconfig information for '\
                               'relevant location phrases')
        self._loadtime = time.time()


    def find_hosts(self,key,as_list=False,as_dict=False,as_object=False):
        """
        Find hosts by name from cached NetConfig information.

        The return type is determined by the keyword entries. By default the 
        search will return a dictionary with matching host names as keys and
        information as sub-dictionaries. 

        An exact host name can be requested or glob patterns

        :param key:  Search parameter. Can either be a name or a glob pattern
        :type  key:  str

        :param as_list: If True, the results are returned as a list of host
                        names
        :type  as_list: bool

        :param as_dict: If True, the results are returned as a dictionary
                        of host names and information. This is the default
                        behavior
        :type as_dict:  bool

        :param as_object: If True, the results are returned as either a Host
                          Group object, or a single Host if just one results
                          is returned.
        :type as_object: bool
        """
        if not any([as_list,as_dict,as_object]):
            module_logger.debug('No output mode selected, so by default '\
                                'will return as a dictionary')
            as_dict = True

        if not self._loadtime:
            self.load_nodes()
        
        hosts = self._nodes.keys()
        matches = fnmatch.filter(hosts,key)

        module_logger.debug('Found {:} that match {:}'.format(str(len(matches)),key))
        
        if not matches:
            return None

        if as_list:
            return matches
        
        match_info = dict([(node,self._nodes[node]) for node in matches])

        if as_dict:
            return match_info
        
        if as_object:
            if len(matches)>1:
                return host.HostGroup(match_info)
            else:
                return host.Host(list(match_info.keys())[0],
                                 list(match_info.values())[0])

    @property
    def searchable_attributes(self):
        """
        List of attributes within NetConfig
        """
        attrs = set(['name'])
        for node,info  in self._nodes.items():
            attrs.update(info.keys())
        return sorted(list(attrs))


    def search(self,as_list=False,as_dict=False,as_object=False,**kwargs):
        """
        Look in the collection of nodes for hosts with matching attributes.
        
        Each attribute must match a NetConfig keyword with lower case lettering
        and underscores in place of spaces. If you would like to view these
        simply look at the :attr:`.searchable_attributes` property of the Netconfig
        object. The corresponding value for each attribute can be a glob
        pattern if an exact match is not needed
        
        :param as_list: If True, the results are returned as a list of host
                        names
        :type  as_list: bool

        :param as_dict: If True, the results are returned as a dictionary
                        of host names and information. This is the default
                        behavior
        :type as_dict:  bool

        :param as_object: If True, the results are returned as either a
                          :py:class:'host.HostGroup' object, or a single Host
                          if just one results is returned.
        :type as_object: bool
        
        :param kwargs: Attribute/value pairs to search the NetConfig database
        """
        if not kwargs:
            module_logger.warn('No attributes specified')
            return {}

        if not any([as_list,as_dict,as_object]):
            module_logger.debug('No output mode selected, so by default '\
                                'will return as a dictionary')
            as_dict = True
        
        if not self._loadtime:
            self.load_nodes()
        
        hosts = self._nodes.copy()
        
        for node,host_info in hosts.items():
            for param,search_param  in kwargs.items():
                if param == 'name':
                    match_value = node
                else:
                    match_value = host_info.get(param)

                if not match_value or not fnmatch.filter([match_value.lower()],
                                                         search_param.lower()):
                    del hosts[node]
                    break
         

        module_logger.debug('Found {:} matches for search parameters'.format(str(len(hosts))))
        
        if not hosts:
            return {}

        if as_list:
            return sorted(hosts.keys())

        if as_dict:
            return hosts

        if as_object:
            if len(hosts)>1:
                return host.HostGroup(hosts)
            else:
                return host.Host(hosts)

