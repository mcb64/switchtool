import sys
import logging
import argparse
from os import path
from PyQt5.QtWidgets import QApplication
import psnet.ui as switch_ui

"""
Launch Switch GUI
"""

def main():
    
    log = logging.getLogger('psnet.switch')
    stream = logging.StreamHandler()
    stream.setLevel(logging.WARNING)
    log.addHandler(stream)

    #Parse arguments
    parser = argparse.ArgumentParser()

    parser.add_argument("-s","--switch", type=str,
                       help="Name of switch")

    parser.add_argument("-u","--user",type=str,
                       help="Username for switch login")
    
    parser.add_argument("-p","--password",type=str,
                       help="Password for switch login")
    kwargs = vars(parser.parse_args())
    
    if not kwargs.get('switch'):
        print ('Use --switch argument to provide switch name')
        return None

    #Launch GUI
    app = QApplication(sys.argv)
    widget = switch_ui.SwitchWidget(kwargs['switch'],
                                    user=kwargs.get('user'),
                                    pw=kwargs.get('password'))
    widget.setWindowTitle(kwargs['switch'])
    widget.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
