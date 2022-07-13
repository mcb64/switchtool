from PyQt5 import QtGui,QtCore,QtWidgets

class MoveDialog(QtWidgets.QDialog):
    """
    Dialog to move port or device to a specific VLAN
    """
    def __init__(self,ports,devices,subnets,parent=None):
        super(MoveDialog,self).__init__(parent)
        self.ports = ports
        self.devices = devices
        self.subnets = subnets
        
        self.setModal(True)
        self.setWindowTitle('Move Port')
        #Setup Combo Boxes
        self.portBox = QtWidgets.QComboBox(self)
        self.portBox.currentIndexChanged[str].connect(self.select_device)
        self.devBox  = QtWidgets.QComboBox(self)
        self.devBox.addItem('-',userData=None)
        self.devBox.currentIndexChanged[str].connect(self.select_port)

        for port in ports:
            self.portBox.addItem(port)
        
        for device in devices.keys():
            if device:
                self.devBox.addItem(device,
                                    userData=devices[device]['port'])
         
        self.vlanBox   = QtWidgets.QComboBox(self)
        for vlan,subnet in self.subnets:
            self.vlanBox.addItem('VLAN {:} - {:}'.format(vlan,subnet),
                                 userData=vlan)
        
        self.buttonBox = QtWidgets.QDialogButtonBox()
        self.buttonBox.addButton(QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.addButton(QtWidgets.QDialogButtonBox.Cancel)
        self.buttonBox.setCenterButtons(True)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        #Selection layout
        self.lay = QtWidgets.QHBoxLayout()
        self.lay.addWidget(QtWidgets.QLabel('Move Port: '))
        self.lay.addWidget(self.portBox)
        self.lay.addWidget(QtWidgets.QLabel('or Device: '))
        self.lay.addWidget(self.devBox)
        self.lay.addWidget(self.vlanBox)
    
        #Total Layout
        self.total_lay = QtWidgets.QVBoxLayout()
        self.total_lay.addLayout(self.lay)
        self.total_lay.addWidget(self.buttonBox,
                                 alignment=QtCore.Qt.AlignCenter)
        self.setLayout(self.total_lay)
            
    def current_move(self):
        """
        Return the port and desired VLAN from the dialog
        """
        vlan = self.vlanBox.currentIndex()
        return (str(self.portBox.currentText()),
                str(self.vlanBox.itemData(vlan)))

    @QtCore.pyqtSlot(str)
    def select_port(self,device):
        """
        Select a port on the VLAN Combo Box
        """
        if device in self.devices.keys():
            i = self.portBox.findText(self.devices[str(device)]['port'])
            if i != -1:
                self.portBox.setCurrentIndex(i)


    @QtCore.pyqtSlot(str)
    def select_device(self,port):
        """
        Select a device on the device combo box
        """
        i = self.devBox.findData(QtCore.QVariant(port))
        if i != -1:
            self.devBox.setCurrentIndex(i)
        else:
            self.devBox.setCurrentIndex(0)
