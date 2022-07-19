from PyQt5 import QtGui,QtCore,QtWidgets
from PyQt5.QtCore import pyqtSignal
import functools

class FindDialog(QtWidgets.QDialog):
    closing = pyqtSignal()
    select = pyqtSignal(str, str)

    """
    Dialog to find a particular device.
    """
    def __init__(self,device,dvplist,parent=None):
        super(FindDialog,self).__init__(parent)
        self.device = device
        self.setModal(False)
        self.setWindowTitle('Find Device "%s"' % device)
        self.layout = QtWidgets.QVBoxLayout(self)

        # Describe what is going on:
        self.mlabel = QtWidgets.QLabel(self)
        self.mlabel.setText('Matches for "%s" include:' % device)
        self.layout.addWidget(self.mlabel)

        # Create a scroll area with no frame and no horizontal scrollbar
        self.sa = QtWidgets.QScrollArea(self)
        self.sa.setFrameStyle(QtWidgets.QFrame.NoFrame)
        self.sa.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.sa.setWidgetResizable(True)

        # Create a widget for the scroll area and limit its size.
        # Resize events for this widget will be sent to us.
        self.sw = QtWidgets.QWidget(self.sa)
        self.sw.setMaximumHeight((len(dvplist)+1)*20)
        self.sw.installEventFilter(self)
        self.sa.setWidget(self.sw)

        # Create a layout for the widget in the scroll area.
        self.clayout = QtWidgets.QVBoxLayout(self.sw)

        self.layout.addWidget(self.sa)

        for (d,v,p) in dvplist:
            b = QtWidgets.QRadioButton(self)
            b.setMinimumSize(100, 20)
            b.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding,
                                                  QtWidgets.QSizePolicy.MinimumExpanding))
            b.setChecked(False)
            b.setText(d)
            self.clayout.addWidget(b)
            b.vp = (v,p)
            b.toggled.connect(functools.partial(self.toggled, b))

        self.buttonBox = QtWidgets.QDialogButtonBox(self)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.accepted.connect(self.accept)
        self.layout.addWidget(self.buttonBox)

    def toggled(self, b):
        if b.isChecked():
            self.select.emit(b.vp[0], b.vp[1])

    def closeEvent(self, event):
        self.closing.emit()
        self.sw.removeEventFilter(self)
        super(FindDialog,self).closeEvent(event)

    # This is called when we are acting as an eventFilter for the scroll widget.
    def eventFilter(self, o, e):
        if o == self.sw and e.type() == QtCore.QEvent.Resize:
            self.setMinimumWidth(self.sw.minimumSizeHint().width() +
                                 self.sa.verticalScrollBar().width())
        return False
