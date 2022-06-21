from PyQt5 import QtGui,QtCore,QtWidgets


class ConfigureDialog(QtWidgets.QDialog):
    """
    Dialog to move port or device to a specific VLAN
    """
    def __init__(self,misplaced,parent=None):
        super(ConfigureDialog,self).__init__(parent)
        self.misplaced =   misplaced
        self.setModal(True)
        self.setWindowTitle('Configure Switch')
        self.layout = QtWidgets.QVBoxLayout()

        if self.misplaced:
            self.show_ports()
        else:
            self.show_message()
        
        self.buttonBox = QtWidgets.QDialogButtonBox()
        self.buttonBox.addButton(QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.addButton(QtWidgets.QDialogButtonBox.Cancel)
        self.buttonBox.setCenterButtons(True)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.layout.addWidget(self.buttonBox,
                              alignment=QtCore.Qt.AlignCenter)
        self.setLayout(self.layout)


    @property
    def approved_moves(self):
        """
        Checked moves in Dialog
        """
        if not self.misplaced:
            return []

        else:
            moves = [self.misplaced[self.portButtons.id(button)]
                     for button in self.portButtons.buttons()
                     if button.isChecked()]
            return moves

    def show_message(self):
        """
        Show message that no misplaced devices were found
        """
        self.layout.addWidget(QtWidgets.QLabel('No devices found on '\
                                           'improper VLAN'))

    def show_ports(self):
        """
        Show ports that are on the improper VLAN
        """
        self.portButtons = QtWidgets.QButtonGroup()
        self.portButtons.setExclusive(False)
        for i,dev in enumerate(self.misplaced):
            device,port,subnet = dev
            button = QtWidgets.QCheckBox('Configure {:} on port {:} '\
                                     'to subnet {:}'.format(device,
                                                            port,
                                                            subnet))
            button.setChecked(False)
            self.portButtons.addButton(button,i)
            self.layout.addWidget(button)
