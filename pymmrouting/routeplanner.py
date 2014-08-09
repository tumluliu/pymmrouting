""" Find multimodal optimal paths with proper multimodal shortest path
    algorithms wrapped in pymmspa4pg
"""


from pymmspa4pg import multimodal_twoq, get_final_path
from pymmrouting.routingresult import RoutingResult

class RoutePlanner(object):

    """ Multimodal optimal path planner """

    def __init__(self, dataset):
        self.stub = ""

    def find_path(self, plan):
        multimodal_twoq(plan.source)
        paths = get_final_path(plan.target)
        results = RoutingResult()
        results.paths = paths
        return results

