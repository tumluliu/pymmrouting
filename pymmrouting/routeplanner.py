""" Find multimodal optimal paths with proper multimodal shortest path
    algorithms wrapped in pymmspa4pg
"""


from ctypes import CDLL, POINTER, \
    c_double, c_char_p, c_int, c_void_p, c_longlong
from .routingresult import RoutingResult, RawMultimodalPath, ModePath
from .orm_graphmodel import Session, Mode, SwitchType
from .settings import PGBOUNCER_CONF, LIB_MMSPA_CONF
from operator import itemgetter
import time
import logging

logger = logging.getLogger(__name__)

c_mmspa_lib = CDLL(LIB_MMSPA_CONF["filename"])
# Read modes and switch_types from database instead of hard coding it here
MODES = {
    str(m_name): m_id
    for m_name, m_id in
    Session.query(Mode.mode_name, Mode.mode_id)
}
SWITCH_TYPES = {
    str(t_name): t_id
    for t_name, t_id in
    Session.query(SwitchType.type_name, SwitchType.type_id)
}


class MultimodalRoutePlanner(object):

    """ Multimodal optimal path planner """

    def __init__(self, datasource_type='POSTGRESQL'):
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
        c_mmspa_lib.GetFinalPath.restype = POINTER(RawMultimodalPath)
        c_mmspa_lib.GetFinalCost.argtypes = [c_longlong, c_char_p]
        c_mmspa_lib.GetFinalCost.restype = c_double
        c_mmspa_lib.DisposePaths.argtypes = [POINTER(RawMultimodalPath)]
        pg_conn_str = \
            "host = '" + PGBOUNCER_CONF['host'] + "' " + \
            "user = '" + PGBOUNCER_CONF['username'] + "' " + \
            "port = '" + PGBOUNCER_CONF['port'] + "' " + \
            "dbname = '" + PGBOUNCER_CONF['database'] + "'"
        self.open_datasource(datasource_type, pg_conn_str)
        self.graph_file = None

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.cleanup()

    def open_datasource(self, ds_type, ds_url):
        self.data_source_type = ds_type.upper()
        if ds_type.upper() in ["POSTGRESQL", "POSTGRES"]:
            ret_code = c_mmspa_lib.ConnectDB(ds_url)
            if ret_code != 0: raise Exception("[FATAL] Open datasource failed")
        elif ds_type.upper() == "PLAIN_TEXT":
            self.graph_file = open(ds_url)
            # FIXME: here should return a status code

    def cleanup(self):
        if self.data_source_type in ["POSTGRESQL", "POSTGRES"]:
            c_mmspa_lib.DisconnectDB()
        elif self.data_source_type == "PLAIN_TEXT":
            self.graph_file.close()

    def assemble_networks(self, plan):
        logger.info("Create a routing plan. ")
        c_mmspa_lib.CreateRoutingPlan(
            len(plan.mode_list), len(plan.public_transit_set))
        # set mode list

        logger.info("Set the mode list items. ")
        logger.debug("Mode list is: %s", plan.mode_list)
        i = 0
        for mode in plan.mode_list:
            c_mmspa_lib.SetModeListItem(i, mode)
            i += 1

        # set switch conditions and constraints if the plan is multimodal
        if len(plan.mode_list) > 1:
            logger.info("Set the switch conditions and constraints... ")
            for i in range(len(plan.mode_list) - 1):
                c_mmspa_lib.SetSwitchConditionListItem(i,
                    plan.switch_condition_list[i])
                c_mmspa_lib.SetSwitchingConstraint(i,
                    plan.switch_constraint_list[i])

        # set public transit modes if there are
        if plan.has_public_transit:
            i = 0
            for mode in plan.public_transit_set:
                c_mmspa_lib.SetPublicTransitModeSetItem(i, mode)
                i += 1

        logger.info("Set the target constraints if there is... ")
        logger.debug("Target constraints are: %s", plan.target_constraint)
        c_mmspa_lib.SetTargetConstraint(plan.target_constraint)
        logger.info("Set the const factor ... ")
        logger.debug("Cost factor is: %s", plan.cost_factor)
        c_mmspa_lib.SetCostFactor(plan.cost_factor)

        logger.info("Start parsing multimodal networks...")
        if c_mmspa_lib.Parse() != 0:
            raise Exception("Assembling multimodal networks failed!")

    def disassemble_networks(self):
        c_mmspa_lib.Dispose()

    def batch_find_path(self, plans):
        result_dict = { "routes": []}
        for p in plans:
            result = self.find_path(p)
            result_dict["routes"] += result["routes"]
            result_dict['source'] = result['source']
            result_dict['target'] = result['target']
        return self._refine_results(result_dict, plans)

    def _refine_results(self, results, plans):
        refined_results = []
        for i, r in enumerate(results['routes']):
            if r['existence'] == False:
                continue
            if MODES['public_transportation'] in plans[i].mode_list:
                # Claim using public transit
                real_modes = [f['properties']['mode']
                              for f in r['geojson']['features']
                              if f['properties']['type'] == 'path']
                pt_modes = ['suburban', 'underground', 'tram', 'bus']
                # Eliminate the result claiming using public transit but actually
                # does not
                if (set(real_modes).isdisjoint(set(pt_modes))):
                    # It claims using public transit but no public transit station
                    # is found in the result path. Such a path will be eliminated.
                    continue
            refined_results.append(r)
        refined_results.sort(key=itemgetter('duration'))
        results['routes'] = refined_results
        return results

    def find_path(self, plan):
        logger.info("Start path finding...")
        logger.debug("source: %s", str(plan.source))
        logger.debug("target: %s", str(plan.target))
        logger.info("Loading multimodal transportation networks ... ")
        t1 = time.time()
        self.assemble_networks(plan)
        t2 = time.time()
        logger.info("done!")
        logger.info("Finish assembling multimodal networks, time consumed: %s seconds", (t2 - t1))
        logger.info("Calculating multimodal paths ... ")
        t1 = time.time()
        c_mmspa_lib.MultimodalTwoQ(c_longlong(plan.source['properties']['id']))
        t2 = time.time()
        logger.info("Finish calculating multimodal paths, time consumed: %s seconds", (t2 - t1))
        final_path = c_mmspa_lib.GetFinalPath(c_longlong(plan.source['properties']['id']),
                                              c_longlong(plan.target['properties']['id']))
        routing_result = self._construct_result(plan, final_path)
        if routing_result.is_existent is True:
            c_mmspa_lib.DisposePaths(final_path)
        self.disassemble_networks()
        del plan.source['properties']['id']
        del plan.target['properties']['id']
        return {
            "routes": [routing_result.to_dict()],
            "source": plan.source,
            "target": plan.target
        }

    def _construct_result(self, plan, final_path):
        """ Construct a bundle of routing plan and result
        """
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
                logger.info("Constructing path for mode %s", m)
                mp = ModePath(m)
                logger.debug("Mode path vertex id list before construction: %s",
                             mp.vertex_id_list)
                for i in range(
                    final_path[m_index].path_segments[0].vertex_list_length):
                    v = final_path[m_index].path_segments[0].vertex_list[i]
                    mp.vertex_id_list.append(v)
                m_index += 1
                logger.debug("vertex id list for mode %s: %s",
                             m, mp.vertex_id_list)
                result.mode_paths.append(mp)
            logger.debug("vertex id list before unfolding: %s",
                         result.path_by_vertices)
            result.unfold_sub_paths()
            logger.debug("vertex id list after unfolding: %s",
                         result.path_by_vertices)
            result.length = c_mmspa_lib.GetFinalCost(
                c_longlong(plan.target['properties']['id']), 'distance')
            result.time = c_mmspa_lib.GetFinalCost(
                c_longlong(plan.target['properties']['id']), 'duration')
            result.walking_length = c_mmspa_lib.GetFinalCost(
                c_longlong(plan.target['properties']['id']), 'walking_distance')
            result.walking_time = c_mmspa_lib.GetFinalCost(
                c_longlong(plan.target['properties']['id']), 'walking_duration')
        return result
