from PyQt5 import QtGui,QtCore,QtWidgets

class PasswdDialog(QtWidgets.QDialog):
    """
    Dialog to get a password.
    """
    def __init__(self,parent=None):
        super(PasswdDialog,self).__init__(parent)
        self.setModal(True)
        self.setWindowTitle('Authorization')
        self.layout = QtWidgets.QVBoxLayout(self)

        # Describe what is going on:
        self.label = QtWidgets.QLabel(self)
        self.layout.addWidget(self.label)

        self.nameEdit = QtWidgets.QLineEdit(self)
        self.nameEdit.setEchoMode(QtWidgets.QLineEdit.Password)
        self.layout.addWidget(self.nameEdit)
        
        self.buttonBox = QtWidgets.QDialogButtonBox(self)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.accepted.connect(self.accept)
        self.layout.addWidget(self.buttonBox)
        
def getPassword(prompt):
    d = PasswdDialog()
    d.label.setText(prompt)
    result = d.exec_()
    if result == QtWidgets.QDialog.Accepted:
        return d.nameEdit.text()
    else:
        return None

