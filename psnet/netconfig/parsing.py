import re

hutches = {'AMO':1,'SXR':2,'XPP':3,'XCS':4,'MFX':4.5,'CXI':5,'MEC':6}


def parse_netconfig(s):
    """
    Parse a Netconfig search result and return a dictionary of host names
    matched with NetConfig information
    """
    results = {}
    name = re.compile(r'\n(\S+?):\n')
    devices = name.findall(s)
    info    = name.split(s)
    info    = [piece for piece in info if piece and piece not in devices]
    search  = zip(devices,info)
    
    for (device,info) in search:
        results[device] = {}
        info = info.replace('\n\t\t',' ')
        key  = re.compile(r'\t(.+?): (.+?)[\n?]')
        search_results = key.findall(info)
        for (param,result) in search_results:
            results[device][param.lower().replace(' ','_')] = result

    return results


def parse_subnet(subnet):
    """
    Parse the name of a subnet to find which hutch the device is in.
    """
    hutch = re.findall(r'cds-(\S){3}.pcdsn',subnet)
    if hutch:
        hutch = hutch[0]
    else:
        hutch = hutch.upper()
    return {'hutch':hutch}


def search_location(s):
    """
    Search a string for possible location information.
    """

    keys  = {'building' : r'[Bb]{1}(\d{3})',
             'rack'     : r'([rR{1}]\d{2}[AaBb]?)',
             'elevation': r'[Ee]{1}(\d{2}[BbFf]?)',
             'hutch'    : r'[Hh]{1}([4.5]*[\d]{0,2}?)'}

    found = {}
    
    if not s:
        return found

    #Look for hutch names    
    hutch = [name for name in hutches.keys() if name in s.upper()]
    if hutch:
        hutch_name = hutch[0]
    else:
        hutch_name = None

    #Look for other location information
    for attr, key in keys.items():
        search = re.findall(key,s)
        if search:
            search = search[0]
        else:
            search = None
        found[attr] = search
    
    orientation = None
    for side in ('front','back'):
        if found.get('elevation') and \
           found['elevation'][-1] == side[0] or \
           side in s.lower():
            found['orientation'] = side
    
    found['orientation'] = orientation
    
    #Translate Hutch ID number
    if found.get('hutch') and not hutch_name:
        try:
            hutch_name = [id for id in hutches.values() 
                          if id==found.get('hutch')][0]
        except IndexError:
#            print 'Hutch {:} is not a valid hutch I.D'.format(found.get('hutch'))
            hutch_name = None

    else:
        found['hutch'] = hutch_name
    

   
        
    return found


def parse_cname(cname):
    """
    Gather location information including hutch, rack and elevation from cname.
    """
    if not cname:
        return {}

    matches = re.findall(r'[\D]+?-([\D]{3})-([R][\d]{2}[AB]?)-([\d]{2}[BF]?)',
            cname,flags=re.I)
    if matches:
        hutch_id,rack,elevation = matches[0]
        print(hutch_id)
        return {'hutch':hutch_id,'rack':rack,'elevation':elevation}
    else:
        return {}

    


