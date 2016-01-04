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

        # v2 of mmspa library API

        # Function of initializing the library,preparing and caching mode
        # graph data
        # extern int MSPinit(const char *pgConnStr);
        self.msp_init = c_mmspa_lib.MSPinit
        self.msp_init.argtypes = [c_char_p]
        self.msp_init.restype = c_int
        # Functions of creating multimodal routing plan
        # extern void MSPcreateRoutingPlan(int modeCount, int publicModeCount);
        self.msp_createroutingplan = c_mmspa_lib.MSPcreateRoutingPlan
        self.msp_createroutingplan.argtypes = [c_int, c_int]
        # extern void MSPsetMode(int index, int modeId);
        self.msp_setmode = c_mmspa_lib.MSPsetMode
        self.msp_setmode.argtypes = [c_int, c_int]
        # extern void MSPsetPublicTransit(int index, int modeId);
        self.msp_setpublictransit = c_mmspa_lib.MSPsetPublicTransit
        self.msp_setpublictransit.argtypes = [c_int, c_int]
        # extern void MSPsetSwitchCondition(int index, const char *spCondition);
        self.msp_setswitchcondition = c_mmspa_lib.MSPsetSwitchCondition
        self.msp_setswitchcondition.argtypes = [c_int, c_char_p]
        # extern void MSPsetSwitchConstraint(int index, VertexValidationChecker callback);
        # FIXME: the arg type of SetSwitchingConstraint should be
        # VertexValidationChecker callback
        self.msp_setswitchconstraint = c_mmspa_lib.MSPsetSwitchConstraint
        self.msp_setswitchconstraint.argtypes = [c_int, c_void_p]
        # extern void MSPsetTargetConstraint(VertexValidationChecker callback);
        # FIXME: the argtype here should be VertexValidationChecker callback
        self.msp_settargetconstraint = c_mmspa_lib.MSPsetTargetConstraint
        self.msp_settargetconstraint.argtypes = [c_void_p]
        # extern void MSPsetCostFactor(const char *costFactor);
        self.msp_setcostfactor = c_mmspa_lib.MSPsetCostFactor
        self.msp_setcostfactor.argtypes = [c_char_p]
        # Function of assembling multimodal graph set for each routing plan
        # extern int MSPassembleGraphs();
        self.msp_assemblegraphs = c_mmspa_lib.MSPassembleGraphs
        self.msp_assemblegraphs.restype = c_int
        # Functions of finding multimodal shortest paths
        # extern Path **MSPfindPath(int64_t source, int64_t target);
        self.msp_findpath = c_mmspa_lib.MSPfindPath
        self.msp_findpath.argtypes = [c_longlong, c_longlong]
        self.msp_findpath.restype = POINTER(RawMultimodalPath)
        # extern void MSPtwoq(int64_t source);
        self.msp_twoq = c_mmspa_lib.MSPtwoq
        self.msp_twoq.argtypes = [c_longlong]
        # Functions of fetching and releasing the path planning results
        # extern Path **MSPgetFinalPath(int64_t source, int64_t target);
        self.msp_getfinalpath = c_mmspa_lib.MSPgetFinalPath
        self.msp_getfinalpath.argtypes = [c_longlong, c_longlong]
        self.msp_getfinalpath.restype = POINTER(RawMultimodalPath)
        # extern double MSPgetFinalCost(int64_t target, const char *costField);
        self.msp_getfinalcost = c_mmspa_lib.MSPgetFinalCost
        self.msp_getfinalcost.argtypes = [c_longlong, c_char_p]
        self.msp_getfinalcost.restype = c_double
        # extern void MSPclearPaths(Path **paths);
        self.msp_clearpaths = c_mmspa_lib.MSPclearPaths
        self.msp_clearpaths.argtypes = [POINTER(RawMultimodalPath)]
        # Function of disposing the library memory
        # extern void MSPclearGraphs();
        self.msp_cleargraphs = c_mmspa_lib.MSPclearGraphs
        # extern void MSPclearRoutingPlan();
        self.msp_clearroutingplan = c_mmspa_lib.MSPclearRoutingPlan
        # extern void MSPfinalize();
        self.msp_finalize = c_mmspa_lib.MSPfinalize
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
            ret_code = self.msp_init(ds_url)
            if ret_code != 0:
                raise Exception(
                    "[FATAL] Open datasource and caching mode graphs failed")
        elif ds_type.upper() == "PLAIN_TEXT":
            self.graph_file = open(ds_url)
            # FIXME: here should return a status code

    def cleanup(self):
        if self.data_source_type in ["POSTGRESQL", "POSTGRES"]:
            self.msp_finalize()
        elif self.data_source_type == "PLAIN_TEXT":
            self.graph_file.close()

    def prepare_routingplan(self, plan):
        logger.info("Create a routing plan. ")
        self.msp_createroutingplan(
            len(plan.mode_list), len(plan.public_transit_set))
        # set mode list

        logger.info("Set the mode list items. ")
        logger.debug("Mode list is: %s", plan.mode_list)
        i = 0
        for mode in plan.mode_list:
            self.msp_setmode(i, mode)
            i += 1

        # set switch conditions and constraints if the plan is multimodal
        if len(plan.mode_list) > 1:
            logger.info("Set the switch conditions and constraints... ")
            for i in range(len(plan.mode_list) - 1):
                self.msp_setswitchcondition(i, plan.switch_condition_list[i])
                self.msp_setswitchconstraint(i, plan.switch_constraint_list[i])

        # set public transit modes if there are
        if plan.has_public_transit:
            i = 0
            for mode in plan.public_transit_set:
                self.msp_setpublictransit(i, mode)
                i += 1

        logger.info("Set the target constraints if there is... ")
        logger.debug("Target constraints are: %s", plan.target_constraint)
        self.msp_settargetconstraint(plan.target_constraint)
        logger.info("Set the const factor ... ")
        logger.debug("Cost factor is: %s", plan.cost_factor)
        self.msp_setcostfactor(plan.cost_factor)

        # logger.info("Start parsing multimodal networks...")
        # if self.msp_assemblegraphs() != 0:
            # raise Exception("Assembling multimodal networks failed!")

    def disassemble_networks(self):
        self.msp_cleargraphs()

    def batch_find_path(self, plans):
        result_dict = {"routes": []}
        for p in plans:
            result = self.find_path(p)
            result_dict["routes"] += result["routes"]
            result_dict['source'] = result['source']
            result_dict['target'] = result['target']
        return self._refine_results(result_dict, plans)

    def _refine_results(self, results, plans):
        refined_results = []
        for i, r in enumerate(results['routes']):
            if r['existence'] is False:
                continue
            if MODES['public_transportation'] in plans[i].mode_list:
                # Claim using public transit
                real_modes = [f['properties']['mode']
                              for f in r['geojson']['features']
                              if f['properties']['type'] == 'path']
                pt_modes = ['suburban', 'underground', 'tram', 'bus']
                # Eliminate the result claiming using public transit but
                # actually does not
                if (set(real_modes).isdisjoint(set(pt_modes))):
                    # It claims using public transit but no public transit
                    # station is found in the result path. Such a path will
                    # be eliminated.
                    continue
            refined_results.append(r)
        refined_results.sort(key=itemgetter('duration'))
        results['routes'] = refined_results
        return results

    def find_path(self, plan):
        logger.info("Start path finding...")
        logger.debug("source: %s", str(plan.source))
        logger.debug("target: %s", str(plan.target))
        # logger.info("Loading multimodal transportation networks ... ")
        # t1 = time.time()
        self.prepare_routingplan(plan)
        # t2 = time.time()
        # logger.info("done!")
        # logger.info("Finish assembling multimodal networks, time consumed: %s seconds", (t2 - t1))
        logger.info("Calculating multimodal paths ... ")
        t1 = time.time()
        # self.msp_twoq(c_longlong(plan.source['properties']['id']))
        final_path = self.msp_findpath(c_longlong(plan.source['properties']['id']),
                                       c_longlong(plan.target['properties']['id']))
        t2 = time.time()
        logger.info("Finish calculating multimodal paths, time consumed: %s seconds", (t2 - t1))
        routing_result = self._construct_result(plan, final_path)
        if routing_result.is_existent is True:
            self.msp_clearpaths(final_path)
        self.disassemble_networks()
        self.msp_clearroutingplan()
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
                for i in range(final_path[m_index].path_segments[0].vertex_list_length):
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
            result.length = self.msp_getfinalcost(
                c_longlong(plan.target['properties']['id']), 'distance')
            result.time = self.msp_getfinalcost(
                c_longlong(plan.target['properties']['id']), 'duration')
            result.walking_length = self.msp_getfinalcost(
                c_longlong(plan.target['properties']['id']), 'walking_distance')
            result.walking_time = self.msp_getfinalcost(
                c_longlong(plan.target['properties']['id']), 'walking_duration')
        return result
