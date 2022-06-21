import logging
from PyQt5 import QtGui,QtCore,QtWidgets

class QtHandler(logging.Handler):

    def __init__(self,signal):
        logging.Handler.__init__(self,level=logging.DEBUG)
        self.signal  = signal
        self.setFormatter(logging.Formatter('%(levelname)s'\
                                            '- %(message)s'))
    def emit(self,record):
        """
        Emit PyQt signal
        """
        msg = self.format(record)
        self.signal.emit(msg,record.levelno)


class QLogDisplay(QtWidgets.QWidget):
   
    __pyqtSignals__ = ("newRecord(str,int)")
    
    _levels = {logging.DEBUG    :{'Name':'DEBUG','Color':QtCore.Qt.darkGreen},
               logging.INFO     :{'Name':'INFO','Color':QtCore.Qt.darkBlue}, 
               logging.WARNING  :{'Name':'WARNING','Color':QtCore.Qt.blue},
               logging.ERROR    :{'Name':'ERROR','Color':QtCore.Qt.red},
               logging.CRITICAL :{'Name':'CRITICAL','Color':QtCore.Qt.darkRed},
              }

    newRecord = QtCore.pyqtSignal(str,int)

    def __init__(self,parent=None):
        super(QLogDisplay,self).__init__(parent=parent)
        
        #Create handler 
        self.logs = []
        self.handler = QtHandler(self.newRecord)

        #Text Display
        self.monocolor = False #Controls text coloring
        self.text = QtWidgets.QTextEdit(parent=self)
        self.text.setBackgroundRole(QtGui.QPalette.Dark)
        self.text.setReadOnly(True)

        self.newRecord.connect(self.appendText) 
        
        #Option Buttons
        self.clear = QtWidgets.QPushButton('Clear')
        self.clear.clicked.connect(self.text.clear)

        self.setlevel = QtWidgets.QLabel('Set Level: ')
        self.setchoice = QtWidgets.QComboBox()
        for lvl,info in sorted(self._levels.items(),key=lambda x: x):
            choice = info['Name']
            self.setchoice.addItem(choice)
        
        self.setchoice.currentIndexChanged.connect(self.adjustLevel)
        

        self.adjustLevel(2)
        self.buttons = QtWidgets.QHBoxLayout()
        self.buttons.addStretch(2)
        self.buttons.addWidget(self.setlevel)
        self.buttons.addWidget(self.setchoice)
        self.buttons.addWidget(self.clear)
        self.buttons.addStretch(2)

        #Create Layout
        self.lay = QtWidgets.QVBoxLayout()
        self.lay.addWidget(self.text)
        self.lay.addLayout(self.buttons)
        self.setLayout(self.lay)
        

    def addLog(self,log,level=None):
        """
        Provide a Python Logger object to be displayed
        """
        log.addHandler(self.handler)
        self.logs.append(log)
        
        #Set default level 
        if not level: #If not default level
            level = logging.WARNING
        try:
            levels = [lvl for lvl,info in sorted(self._levels.items(),key=lambda x: x)]
            idx    = levels.index(level)
            self.setchoice.setCurrentIndex(idx)
        
        except ValueError:
            raise ValueError('Default level provided is not valid')


    def allowTextColoring(self,choice):
        """
        Set choice of plain or colored text
        """
        self.monocolor = choice

    
    @QtCore.pyqtSlot(int)
    def adjustLevel(self,index):
        """
        Adjust the logging level to that displayed in the choice QComboBox
        """
        level,info = sorted(self._levels.items(),key=lambda x: x)[index]
        for log in self.logs:
            log.setLevel(level)


    @QtCore.pyqtSlot(str,int)
    def appendText(self,msg,level):
        """
        Add text to the end of the log
        """
        if not self.monocolor:
            clr = self._levels[level]['Color']
        else:
            clr = QtCore.Qt.darkGray
        
        self.text.moveCursor(QtGui.QTextCursor.End)
        self.text.setTextColor(QtGui.QColor(clr))
        self.text.append(msg)


if __name__ == '__main__':

    import sys

    app =  QtGui.QApplication(sys.argv)
    
    
    #Test Log
    log = logging.getLogger('TEST')
    test = QtWidgets.QPushButton('Test')

    def logprint():
        log.debug('This is a test')
        log.info('Please do not panic')
        log.warn('Though please pay attention')
        log.error('There are errors happening')
        log.critical('Help')

    test.clicked.connect(logprint)

    #Create Log Widget
    qlog = QLogDisplay()
    qlog.addLog(log,level=logging.INFO)
    
    #Create layout
    main = QtWidgets.QWidget()
    lay  = QtWidgets.QVBoxLayout()
    lay.addWidget(qlog)
    lay.addWidget(test)
    main.setLayout(lay)
    main.show()

    sys.exit(app.exec_())
