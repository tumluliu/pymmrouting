#__all__ = ['routeplanner', 'inferenceengine', 'routingresult',
#           'switchcondition', 'datamodel']

__title__ = 'pymmrouting'
__version__ = '0.3.1'
__author__ = 'LIU Lu'
__license__ = 'The MIT License'
__copyright__ = 'Copyright 2014-2015 LIU Lu'

__all__ = ['routeplanner', 'inferenceengine', 'routingresult',
           'switchcondition']

from .routeplanner import MultimodalRoutePlanner
from .inferenceengine import RoutingPlan, RoutingPlanInferer
from .routingresult import RoutingResult
from .switchcondition import SwitchCondition
#from pymmrouting.datamodel import MultimodalNetwork

# Set default logging handler to avoid "No handler found" warnings.
import logging
try:  # Python 2.7+
    from logging import NullHandler
except ImportError:
    class NullHandler(logging.Handler):
        def emit(self, record):
            pass

logging.getLogger(__name__).addHandler(NullHandler())
