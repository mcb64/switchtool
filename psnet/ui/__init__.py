import sys

#Find Logging Widget Currently in trendahl home area
LOG_PATH = '/opt/psnet/EpicsQT/'
sys.path.insert(0,LOG_PATH)

from . import widgets,dialogs

from .widgets.switch import SwitchWidget

__all__ = ['widgets','dialogs']
