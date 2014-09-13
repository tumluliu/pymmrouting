""" Find multimodal optimal paths with proper multimodal shortest path
    algorithms wrapped in pymmspa4pg
"""


from ctypes import CDLL, POINTER, \
    c_double, c_char_p, c_int, c_void_p, c_longlong
from pymmrouting.routingresult import RoutingResult, MultimodalPath
from pymmrouting.orm_graphmodel import Edge, OSMLine, Session, get_waypoints
from termcolor import colored
import time


c_mmspa_lib = CDLL('libmmspa4pg.dylib')


class RoutePlanner(object):

    """ Multimodal optimal path planner """

    def __init__(self):
        self.data_source_type = ""
        self.graph_file = None
        # For strict type checking, the arguments and returning types are
        # explictly listed here
        # TODO: mapping c_mmspa_lib interface function to python-style methods
        self.connect_db = c_mmspa_lib.ConnectDB
        c_mmspa_lib.ConnectDB.argtypes = [c_char_p]
        c_mmspa_lib.ConnectDB.restype = c_int
        c_mmspa_lib.CreateRoutingPlan.argtypes = [c_int, c_int]
        c_mmspa_lib.SetModeListItem.argtypes = [c_int, c_int]
        c_mmspa_lib.SetSwitchConditionListItem.argtypes = [c_int, c_char_p]
        # FIXME: the arg type of SetSwitchingConstraint should be
        # VertexValidationChecker callback
        c_mmspa_lib.SetSwitchingConstraint.argtypes = [c_int, c_void_p]
        c_mmspa_lib.SetPublicTransitModeSetItem.argtypes = [c_int, c_int]
        # FIXME: the argtype here should be VertexValidationChecker callback
        c_mmspa_lib.SetTargetConstraint.argtypes = [c_void_p]
        c_mmspa_lib.SetCostFactor.argtypes = [c_char_p]
        c_mmspa_lib.Parse.restype = c_int
        c_mmspa_lib.MultimodalTwoQ.argtypes = [c_longlong]
        c_mmspa_lib.GetFinalPath.argtypes = [c_longlong, c_longlong]
        c_mmspa_lib.GetFinalPath.restype = POINTER(MultimodalPath)
        c_mmspa_lib.GetFinalCost.argtypes = [c_longlong, c_char_p]
        c_mmspa_lib.GetFinalCost.restype = c_double
        c_mmspa_lib.DisposePaths.argtypes = [POINTER(MultimodalPath)]

    def open_datasource(self, ds_type, ds_url):
        self.data_source_type = ds_type.upper()
        if ds_type.upper() == "POSTGRESQL":
            return c_mmspa_lib.ConnectDB(ds_url)
        elif ds_type.upper() == "PLAIN_TEXT":
            self.graph_file = open(ds_url)
            # FIXME: here should return a status code
        return 0

    def close_datasource(self):
        if self.data_source_type == "POSTGRESQL":
            c_mmspa_lib.DisconnectDB()
        elif self.data_source_type == "PLAIN_TEXT":
            self.graph_file.close()

    def assemble_networks(self, plan):
        # print "I am gonna create a routing plan... "
        c_mmspa_lib.CreateRoutingPlan(
            len(plan.mode_list), len(plan.public_transit_set))
        # set mode list

        # print "I am gonna set the mode list items... "
        # print "most list is: " + str(plan.mode_list)
        i = 0
        for mode in plan.mode_list:
            c_mmspa_lib.SetModeListItem(i, mode)
            i += 1

        # set switch conditions and constraints if the plan is multimodal
        # print "I am gonna set the switch conditions and constraints if there is... "
        if len(plan.mode_list) > 1:
            for i in range(len(plan.mode_list) - 1):
                c_mmspa_lib.SetSwitchConditionListItem(
                    i,
                    plan.switch_condition_list[i])
                c_mmspa_lib.SetSwitchingConstraint(
                    i,
                    plan.switch_constraint_list[i])

        # set public transit modes if there are
        if plan.has_public_transit:
            i = 0
            for mode in plan.public_transit_set:
                c_mmspa_lib.SetPublicTransitModeSetItem(i, mode)
                i += 1

        # print "I am gonna set the target constraints if there is... "
        # print "target constraints are: " + str(plan.target_constraint)
        c_mmspa_lib.SetTargetConstraint(plan.target_constraint)
        # print "I am gonna set the const factor ... "
        # print "cost factor is: " + str(plan.cost_factor)
        c_mmspa_lib.SetCostFactor(plan.cost_factor)

        print "start parsing multimodal networks..."
        if c_mmspa_lib.Parse() != 0:
            raise Exception("Assembling multimodal networks failed!")

    def disassemble_networks(self):
        c_mmspa_lib.Dispose()

    def find_path(self, plan):
        # print 'I am gonna find the path!!!!!!!!!!!!!'
        # print "Loading multimodal transportation networks ... ",
        t1 = time.time()
        self.assemble_networks(plan)
        t2 = time.time()
        print colored("done!", "green")
        print "Time consumed: ",
        print colored(str(t2 - t1), "red"),
        print " seconds"
        print "Start calculating multimodal paths ... ",
        t1 = time.time()
        c_mmspa_lib.MultimodalTwoQ(c_longlong(plan.source))
        t2 = time.time()
        print colored("done!", "green")
        print "Calculation time: ",
        print colored(str(t2 - t1), "red"),
        print " seconds"
        final_path = c_mmspa_lib.GetFinalPath(
            c_longlong(
                plan.source), c_longlong(
                plan.target))
        routing_result = self._construct_result(plan, final_path)
        if routing_result.is_existent is True:
            c_mmspa_lib.DisposePaths(final_path)
        self.disassemble_networks()
        return routing_result

    def _construct_result(self, plan, final_path):
        result = RoutingResult()
        result.planned_mode_list = plan.mode_list
        result.description = plan.description
        result.planned_switch_type_list = plan.switch_type_list
        try:
            path_probe = final_path[0]
        except ValueError:
            result.is_existent = False
        else:
            result.is_existent = True
            m_index = 0
            for m in plan.mode_list:
                result.paths_by_vertex_id[m] = []
                for i in range(final_path[m_index].path_segments[0].vertex_list_length):
                    result.paths_by_vertex_id[m].append(
                        final_path[m_index].path_segments[0].vertex_list[i])
                m_index += 1

            # construct final path by raw osm_id of ways
            for m in result.paths_by_vertex_id:
                result.paths_by_link_id[m] = []
                result.paths_by_points[m] = {"type": "LineString",
                                             "coordinates": []}
                mode_path_points = []
                for i in range(len(result.paths_by_vertex_id[m])-1):
                    edge = Session.query(Edge).filter(
                        Edge.from_id == result.paths_by_vertex_id[m][i],
                        Edge.to_id == result.paths_by_vertex_id[m][i+1]).first()
                    result.paths_by_link_id[m].append(int(edge.osm_id))
                    osm_raw_line = Session.query(OSMLine).filter(
                        OSMLine.osm_id == edge.osm_id).first()
                    path_seg_points = get_waypoints(osm_raw_line.way)
                    if i == 1:
                        if (mode_path_points[0] == path_seg_points[0]) or \
                           (mode_path_points[0] == path_seg_points[-1]):
                            mode_path_points.reverse()
                    if i >= 1:
                        if mode_path_points[-1] == path_seg_points[-1]:
                            path_seg_points.reverse()
                    mode_path_points += path_seg_points
                result.paths_by_points[m]['coordinates'] = mode_path_points

            result.length = c_mmspa_lib.GetFinalCost(
                c_longlong(
                    plan.target),
                'distance')
            result.time = c_mmspa_lib.GetFinalCost(
                c_longlong(
                    plan.target),
                'elapsed_time')
            result.walking_length = c_mmspa_lib.GetFinalCost(
                c_longlong(plan.target),
                'walking_distance')
            result.walking_time = c_mmspa_lib.GetFinalCost(
                c_longlong(
                    plan.target),
                'walking_time')
        return result
