from PyQt5 import QtCore, QtGui
from PyQt5.QtWidgets import QTableWidget,QTableWidgetItem,QSizePolicy

class VlanWidget(QTableWidget):

    _column_names = ('Port','VLAN','Device Name',
                     'Ethernet Address')
    """
    Table to display a group of Ports
    """
    def __init__(self,parent=None):
        self._ports = []
        self._devices = {}
        self._portWidgets = {}
        
        super(VlanWidget,self).__init__(0,len(self._column_names),parent=parent)
        self.setHorizontalHeaderLabels(self._column_names)
        self.setSizePolicy(QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding))

    def add_ports(self,ports):
        """
        Add a list of port information to the table
        """
        self.clearContents()
        self._ports = ports
        for port in ports:
            self.add_port(port)
#        self.resizeColumnsToContents()
    
    def add_port(self,port):
        """
        Add a port to the table
        """
        port_entry = QTableWidgetItem(port)
        self._portWidgets[port] = port_entry

        new_row    = self.rowCount()
        self.insertRow(new_row)
        self.setItem(new_row,0,port_entry)


    def add_devices(self,devices):
        """
        Add a dictionary of devices to the Table
        """
        self._devices = devices
        for device,device_info in self._devices.items():
            self.add_device(device_info['ethernet_address'],
                            device_info['port'],
                            device_info['vlan'],
                            device = device)
        self.resizeColumnsToContents()


    def add_device(self,mac,port,vlan,device=''):
        """
        Add a device to the table
        """
        row = self._portWidgets[port].row()
        self.setItem(row,1,QTableWidgetItem(vlan))
        self.setItem(row,2,QTableWidgetItem(device))
        self.setItem(row,3,QTableWidgetItem(mac))

    
    def add_unknown(self,macs):
        """
        Add a dictionary of mac addresses to the table.
        """
        self._ethernet = macs
        for mac,device_info in self._ethernet.items():
            self.add_device(mac,
                            device_info['port'],
                            device_info['vlan'])
    

    def select_port(self,port):
        """
        Select a port
        """
        if port in self._portWidgets:
            row = self._portWidgets[port].row()
            self.selectRow(row)


    @QtCore.pyqtSlot(str)
    def highlight_device(self,device):
        if device in self._devices.keys():
            port = self._devices[str(device)]['port']
            row = self._portWidgets[port].row()
            for i in range(len(self._column_names)):
                item = self.item(row,i)
                if item:
                    item.setBackground(QtGui.QBrush(QtCore.Qt.yellow))
