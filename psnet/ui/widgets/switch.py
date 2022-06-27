import sys
import logging
from PyQt5 import QtGui,QtCore,QtWidgets
from PyQt5.QtCore import pyqtSlot,pyqtSignal

from .vlan import VlanWidget
from ...EpicsQT.qlogdisplay import QLogDisplay
from .. import dialogs
from ...switch.switch import Switch

class SwitchWidget(QtWidgets.QWidget):
    
    _vlan = {}
    
    misplaced = pyqtSignal(str)
    updated   = pyqtSignal()

    def __init__(self,switch,user=None,pw=None,parent=None):
        super(SwitchWidget,self).__init__(parent=parent)
        self.resize(600,700)
        self._switch = PyQtSwitch(switch,user=user,pw=pw,parent=self)
        self.updated.connect(self.refresh)
        self.switch_label = QtWidgets.QLabel(switch)
        title_font = QtGui.QFont()
        title_font.setPointSize(20)
        title_font.setBold(True)
        self.switch_label.setFont(title_font)
        self._vlanTab     = QtWidgets.QTabWidget(parent=self)
        
        #Log Handler
        switch_log = logging.getLogger('psnet.switch')
        self.log = QLogDisplay()
        self.log.addLog(switch_log,level=logging.INFO)

        
        #Move  Layout
        self.utilities = QtWidgets.QGroupBox('Utilities')
        self.survey_button = QtWidgets.QPushButton('Survey')
        self.survey_button.clicked.connect(self.survey)
        self.move_button = QtWidgets.QPushButton('Move Port')
        self.move_button.clicked.connect(self.move_port)
        self.configure_button = QtWidgets.QPushButton('Auto Configure')
        self.configure_button.clicked.connect(self.auto_configure)
        
        self.move_layout = QtWidgets.QHBoxLayout()
        self.move_layout.addWidget(self.survey_button)
        self.move_layout.addWidget(self.move_button)
        self.move_layout.addWidget(self.configure_button)
        
        self.utilities.setLayout(self.move_layout)

        #Search Layout 
        self.portCombo = QtWidgets.QComboBox()
        self.portCombo.activated[str].connect(self.find_port)
        self.deviceCombo = QtWidgets.QComboBox()
        self.deviceCombo.activated[str].connect(self.find_device)
        
        self.search_layout = QtWidgets.QHBoxLayout()
        self.search_layout.addStretch(2)
        self.search_layout.addWidget(QtWidgets.QLabel('Find Port: '))
        self.search_layout.addWidget(self.portCombo)
        self.search_layout.addStretch(1)
        self.search_layout.addWidget(QtWidgets.QLabel('Find Device: '))
        self.search_layout.addWidget(self.deviceCombo)
        self.search_layout.addStretch(2)
        
        #Overall Layout
        self.lay = QtWidgets.QVBoxLayout()
        self.lay.addWidget(self.switch_label,
                           alignment=QtCore.Qt.AlignCenter)
        self.lay.addWidget(self.log)
        self.lay.addWidget(self.utilities)
        self.lay.addLayout(self.search_layout)
        self.lay.addWidget(self._vlanTab)
        self.setLayout(self.lay)
        
        #Load Switch Information
        self._switch.update()


    def survey(self):
        """
        Survey the switch for devices on the wrong subnet
        """
        devices = self._switch.survey()
        for device in devices:
            self.misplaced.emit(device)


    @pyqtSlot(str)
    def find_device(self,device):
        """
        Find a device on the switch and select it
        """
        device = str(device)
        vlan,port = self._switch.find_device(device)
        if vlan and port:
            self.select_vlan(vlan,port=port)
        

    @pyqtSlot(str)
    def find_port(self,port):
        """
        Find a port on the switch and select it
        """
        port = str(port)
        vlan = self._switch.find_port(port)
        if vlan:
            self.select_vlan(vlan,port=port)


    @pyqtSlot()
    def refresh(self):
        """
        Reload all of the VLAN information
        """
        self._vlanTab.clear()
        self.portCombo.clear()
        self.deviceCombo.clear()
        
        switch = VlanWidget(parent=self)
        self.misplaced.connect(switch.highlight_device)
        switch.add_ports(self._switch.ports)
        switch.add_devices(self._switch.devices)
        switch.add_unknown(self._switch.unknown_devices)
        self._vlanTab.addTab(switch,'Complete Switch')
        switch.resize(switch.maximumSize())

        for vlan_no,subnet  in self._switch.subnets:
            tab = 'VLAN {:} - {:}'.format(vlan_no,subnet)
            vlan = getattr(self._switch,
                           self._switch._vlan_alias.format(vlan_no))
            vlan_table = VlanWidget(parent=self)
            self.misplaced.connect(vlan_table.highlight_device)
            self._vlan[vlan_no] = vlan_table

            vlan_table.add_ports(vlan.ports)
            vlan_table.add_devices(vlan._devices)
            vlan_table.add_unknown(vlan._unknown)
            vlan_table.resize(vlan_table.maximumSize())
            self._vlanTab.addTab(vlan_table,tab)
        

        devices = []
        ports   = []

        for vlan in self._switch._vlan:
            for device in vlan.devices:
                devices.append(device)
            for port in vlan.ports:
                ports.append(port)

        
        self.portCombo.addItems(sorted(ports))
        self.deviceCombo.addItems(sorted(devices))


    def select_vlan(self,vlan_no,port=None):
        """
        Select a VLAN in the tab
        """
        if vlan_no in self._vlan.keys():
            vlan = self._vlan[vlan_no]
            self._vlanTab.setCurrentWidget(vlan)
            if port:
                self._vlanTab.currentWidget().select_port(port)


    def move_port(self):
        """
        Launch Dialog to move port
        """

        dialog  = dialogs.MoveDialog(self._switch.ports,
                                     self._switch.devices,
                                     self._switch.subnets,
                                     parent=self) 
        if dialog.exec_():
            port,vlan = dialog.current_move
            self._switch.move_port(port,vlan)

    
    def auto_configure(self): 
        """
        Launch the Auto-Configuration dialog
        """
        devices = self._switch.survey()
        

        if devices:
            ports   = [self._switch.find_device(dev)[1] for dev in devices]
            subnets = [self._switch.find_subnet_for_host(dev)[1] for dev in devices]
            devices = zip(devices,ports,subnets)
        
        dialog = dialogs.ConfigureDialog(devices,parent=self)

        if dialog.exec_():
            approved = dialog.approved_moves
            for move in approved:
                device,port,subnet = move
                self._switch.move_device(device,subnet=subnet)


class PyQtSwitch(Switch):


    def __init__(self,switchname,user='admin',pw=None,parent=None):
        self.parent = parent
        super(PyQtSwitch,self).__init__(switchname,user=user,pw=pw,
                                        load_connections=False)
        
    def update(self):
        """
        Update switch configuration and emit signal
        """
        super(PyQtSwitch,self).update()
        if self.parent:
            self.parent.updated.emit()