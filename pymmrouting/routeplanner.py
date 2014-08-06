""" Find multimodal optimal paths with proper multimodal shortest path
    algorithms wrapped in pymmspa4pg
"""


from pymmspa4pg import multimodal_twoq
from pymmrouting.routingresult import RoutingResult

class RoutePlanner(object):

    """ Multimodal optimal path planner """

    def __init__(self):
        self.stub = ""

    def do_routing(self, source, target):
        multimodal_twoq(source)
        paths = get_final_path(target)
        results = RoutingResult()
        results.paths = paths
        return results

