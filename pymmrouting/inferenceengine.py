"""
Infer feasible routing plans according to user preferences
"""

import json
# from ctypes import *
from pymmrouting.datamodel import VERTEX_VALIDATION_CHECKER
from pymmrouting.orm_graphmodel import SwitchType, Mode, Session, \
    Vertex, StreetJunction

INTERNAL_SRID = 4326
# Read modes and switch_types from database instead of hard coding it here
MODES         = {str(m_name): m_id
                 for m_name, m_id in
                 Session.query(Mode.mode_name, Mode.mode_id)}
SWITCH_TYPES  = {str(t_name): t_id
                 for t_name, t_id in
                 Session.query(SwitchType.type_name, SwitchType.type_id)}


class RoutingPlan(object):

    """
    A plan of routing including transportation tools to use
    during the trip
    """
    mode_list = []
    switch_type_list = []
    switch_condition_list = []
    switch_constraint_list = []
    target_constraint = None
    public_transit_set = []
    cost_factor = ''
    description = ''
    source = 0
    target = 0

    def __init__(self, desc, source, target, modes, cost,
                 switch_types=[], switch_conditions=[],
                 switch_constraints=[], target_constraint=None,
                 public_transits=[]):
        self.description = desc
        self.source = source
        self.target = target
        self.mode_list = modes
        self.cost_factor = cost
        self.switch_type_list = switch_types
        self.switch_condition_list = switch_conditions
        self.switch_constraint_list = switch_constraints
        self.target_constraint = target_constraint
        self.public_transit_set = public_transits

    @property
    def is_multimodal(self):
        return True if (len(self.mode_list) >= 2) or \
            (MODES['public_transportation'] in self.mode_list) else False

    @property
    def has_public_transit(self):
        return True if MODES['public_transportation'] in self.mode_list \
                    else False


class RoutingPlanInferer(object):

    """
    Infer the feasible routing plans according to routing options
    """

    def __init__(self):
        self.options = {}

    def load_routing_options_from_file(self, options_file_path):
        with open(options_file_path) as options_file:
            self.options = json.load(options_file)

    def load_routing_options_from_string(self, options_json_string):
        self.options = json.loads(options_json_string)

    def _reproject(self, old_x, old_y, old_srid, new_srid):
        # TODO: transform coordinate from given srid to 4326 in lon and lat
        return old_x, old_y

    def _geodecode(self, address):
        return 0, 0

    def _get_lon_lat_position(self, position_info):
        if position_info['type'] == 'coordinate':
            lon, lat = self._reproject(position_info['value']['x'],
                                       position_info['value']['y'],
                                       position_info['value']['srid'],
                                       INTERNAL_SRID)
        elif position_info['type'] == 'address':
            # TODO: Do geo-decoding to get the geo-coordinate
            lon, lat = self._geodecode(position_info['value'])
        return {"lon": lon, "lat": lat}

    def _find_candidate_vertices(self, location):
        point = 'POINT(' + str(location['lon']) + ' ' + \
            str(location['lat']) + ')'
        nearest_neighbor = Session.query(StreetJunction).order_by(
            StreetJunction.the_geom.distance_box(point)).first()
        node_id = nearest_neighbor.nodeid
        candidate_vertices = Session.query(Vertex).filter(
            Vertex.vertex_id % 10000000 == node_id).all()
        return {v.mode_id: v.vertex_id for v in candidate_vertices}

    def _get_cost_factor(self, objective):
        if objective == 'shortest': return 'length'
        elif objective == 'fastest': return 'speed'
        return 'speed'

    def _find_valid_source_target_pairs(self, sources, targets, modes,
                                        public_transit_modes=[]):
        s_mode = modes[0]
        t_mode = modes[-1]
        st_pairs = []
        if (s_mode != MODES['public_transportation']) and \
                (t_mode != MODES['public_transportation']):
            source = sources[s_mode] if s_mode in sources else None
            target = targets[t_mode] if t_mode in targets else None
            if (not source is None) and (not target is None):
                st_pairs.append({"source": source, "target": target})
        elif (s_mode == MODES['public_transportation']) and \
                (t_mode != MODES['public_transportation']):
            target = targets[t_mode] if t_mode in targets else None
            source_list = [sources[m] \
                           for m in public_transit_modes + [MODES['foot']] \
                           if m in sources]
            if (not target is None) and (len(source_list) > 0):
                st_pairs = map(lambda s: {"source": s, "target": target},
                                    source_list)
        elif (s_mode != MODES['public_transportation']) and \
                (t_mode == MODES['public_transportation']):
            source = sources[s_mode] if s_mode in sources else None
            target_list = [targets[m] \
                           for m in public_transit_modes + [MODES['foot']] \
                           if m in targets]
            if (not source is None) and (len(target_list) > 0):
                st_pairs = map(lambda t: {"source": source, "target": t},
                                    target_list)
        elif (s_mode == MODES['public_transportation']) and \
                (t_mode == MODES['public_transportation']):
            source_list = [sources[m] \
                           for m in public_transit_modes + [MODES['foot']] \
                           if m in sources]
            target_list = [targets[m] \
                           for m in public_transit_modes + [MODES['foot']] \
                           if m in targets]
            if (len(source_list) > 0) and (len(target_list) > 0):
                st_pairs = [{"source": s, "target": t} for s in source_list \
                                 for t in target_list]
        return st_pairs



    def generate_routing_plan(self):
        if self.options == {}:
            raise Exception('Empty routing options!')
        source_lon_lat = self._get_lon_lat_position(self.options['source'])
        target_lon_lat = self._get_lon_lat_position(self.options['target'])
        candidate_sources = self._find_candidate_vertices(source_lon_lat)
        candidate_targets = self._find_candidate_vertices(target_lon_lat)
        cost_factor = self._get_cost_factor(self.options['objective'])
        plans = []
        if self.options['objective'] == 'fastest':
            if len(self.options['available_public_modes']) == 0:
                if not self.options['has_private_car']:
                    # only can walk, mono-modal routing
                    st_pairs = self._find_valid_source_target_pairs(
                        candidate_sources, candidate_targets, [MODES['foot']])
                    for st in st_pairs:
                        plans.append(RoutingPlan(
                            'Walking', st['source'], st['target'],
                            [MODES['foot']], cost_factor))
                    return plans
                if self.options['has_private_car'] and \
                        (not self.options['need_parking']):
                    # somebody else will be the driver
                    # the car can be parked temporarily anywhere
                    # There are 3 possible mode combinations in this case:
                    # car; foot; car-foot with geo_connection as Switch Point
                    # 1st: car only
                    st_pairs = self._find_valid_source_target_pairs(
                        candidate_sources, candidate_targets, [MODES['private_car']])
                    for st in st_pairs:
                        car_plan = RoutingPlan(
                            'Take a car', st['source'], st['target'],
                            [MODES['private_car']], cost_factor)
                        if 'driving_distance_limit' in self.options:
                            car_plan.target_constraint = VERTEX_VALIDATION_CHECKER(
                                    lambda v: 0 if v[0].distance <= float(
                                        self.options['driving_distance_limit']) *
                                    1000.0 else -1)
                        plans.append(car_plan)
                    # 2nd: foot only
                    st_pairs = self._find_valid_source_target_pairs(
                        candidate_sources, candidate_targets, [MODES['foot']])
                    for st in st_pairs:
                        plans.append(RoutingPlan(
                            'Walking', st["source"], st["target"],
                            [MODES['foot']], cost_factor))
                    # 3rd: car-foot with geo_connection as Switch Point
                    type_id = SWITCH_TYPES['geo_connection']
                    st_pairs = self._find_valid_source_target_pairs(
                        candidate_sources, candidate_targets,
                        [MODES['private_car'], MODES['foot']])
                    for st in st_pairs:
                        car_foot_plan = RoutingPlan(
                            'By car first, then walking without parking',
                            st['source'], st['target'],
                            [MODES['private_car'], MODES['foot']],
                            cost_factor, [type_id],
                            ["type_id=" + str(type_id) + " AND is_available=true"])
                        # FIXME: It is unreasonable to use driving distance limit
                        # as the extream driving distance because the driver can
                        # not drive any more after the passenger leaves. So it
                        # must be convenient to leave some gas for the driver.
                        # remaining_gas_factor = 0.75
                        if 'driving_distance_limit' in self.options:
                            car_foot_plan.switch_constraint_list = [
                                VERTEX_VALIDATION_CHECKER(
                                    lambda v: 0 if v[0].distance <= float(
                                        self.options['driving_distance_limit']) *
                                    1000.0 else -1)]
                        else:
                            car_foot_plan.switch_constraint_list = [None]
                        plans.append(car_foot_plan)
                    return plans

                if self.options['has_private_car'] and self.options['need_parking']:
                    # the user may be the driver
                    # and he/she surely need a parking lot for the car
                    # There are also 2 possible mode combinations in this case:
                    # foot; car-foot with parking as Switch Point
                    # 1st: foot only
                    st_pairs = self._find_valid_source_target_pairs(
                        candidate_sources, candidate_targets, [MODES['foot']])
                    for st in st_pairs:
                        plans.append(RoutingPlan(
                            'Walking', st["source"], st["target"],
                            [MODES['foot']], cost_factor))
                    # 2nd: car-foot with parking lots as Switch Point
                    type_id = SWITCH_TYPES['car_parking']
                    st_pairs = self._find_valid_source_target_pairs(
                        candidate_sources, candidate_targets,
                        [MODES['private_car'], MODES['foot']])
                    for st in st_pairs:
                        car_foot_plan = RoutingPlan(
                            'Driving, parking and walking',
                            st['source'], st['target'],
                            [MODES['private_car'], MODES['foot']],
                            cost_factor, [type_id],
                            ["type_id=" + str(type_id) + " AND is_available=true"])
                        remaining_gas_factor = 0.5
                        if 'driving_distance_limit' in self.options:
                            car_foot_plan.switch_constraint_list = [
                                VERTEX_VALIDATION_CHECKER(
                                    lambda v: 0 if v[0].distance <= float(
                                        self.options['driving_distance_limit']) *
                                    1000.0 * remaining_gas_factor else -1)]
                        else:
                            car_foot_plan.switch_constraint_list = [None]
                        plans.append(car_foot_plan)
                    return plans
            else:
                # can use public transportation system
                if not self.options['has_private_car']:
                    # the user can walk or take public transportation
                    # 2 possible mode combinations:
                    # 1. foot;
                    # 2. PT
                    #
                    # 1: foot only
                    st_pairs = self._find_valid_source_target_pairs(
                        candidate_sources, candidate_targets, [MODES['foot']])
                    for st in st_pairs:
                        plans.append(RoutingPlan(
                            'Walking', st["source"], st["target"],
                            [MODES['foot']], cost_factor))
                    # 2: public transportation
                    public_modes = [MODES[m] for m in \
                                    self.options['available_public_modes']]
                    st_pairs = self._find_valid_source_target_pairs(
                        candidate_sources, candidate_targets,
                        [MODES['public_transportation']], public_modes)
                    for st in st_pairs:
                        public_plan = RoutingPlan(
                            'Walking and taking public transit',
                            st['source'], st['target'],
                            [MODES['public_transportation']], cost_factor)
                        public_plan.public_transit_set = public_modes
                        plans.append(public_plan)
                    return plans

            if self.options['has_private_car'] and \
                    (not self.options['need_parking']):
                # somebody else will be the driver
                # the car can be parked temporarily anywhere
                # There are 5 possible mode combinations in this case:
                # 1. car;
                # 2. foot;
                # 3. car-foot with geo_connection as Switch Point;
                # 4. PT;
                # 5. car-PT with geo_connection as Switch Point;
                # 6. car-PT with kiss+R as Switch Point;
                #
                # 1: car only
                st_pairs = self._find_valid_source_target_pairs(
                    candidate_sources, candidate_targets, [MODES['private_car']])
                for st in st_pairs:
                    car_plan = RoutingPlan(
                        'Take a car', st['source'], st['target'],
                        [MODES['private_car']], cost_factor)
                    if 'driving_distance_limit' in self.options:
                        car_plan.target_constraint = VERTEX_VALIDATION_CHECKER(
                                lambda v: 0 if v[0].distance <= float(
                                    self.options['driving_distance_limit']) *
                                1000.0 else -1)
                    plans.append(car_plan)
                # 2: foot only
                st_pairs = self._find_valid_source_target_pairs(
                    candidate_sources, candidate_targets, [MODES['foot']])
                for st in st_pairs:
                    plans.append(RoutingPlan(
                        'Walking', st["source"], st["target"],
                        [MODES['foot']], cost_factor))
                # 3: car-foot with geo_connection as Switch Point
                type_id = SWITCH_TYPES['geo_connection']
                st_pairs = self._find_valid_source_target_pairs(
                    candidate_sources, candidate_targets,
                    [MODES['private_car'], MODES['foot']])
                for st in st_pairs:
                    car_foot_plan = RoutingPlan(
                        'By car first, then walking without parking',
                        st['source'], st['target'],
                        [MODES['private_car'], MODES['foot']],
                        cost_factor, [type_id],
                        ["type_id=" + str(type_id) + " AND is_available=true"])
                    if 'driving_distance_limit' in self.options:
                        car_foot_plan.switch_constraint_list = [
                            VERTEX_VALIDATION_CHECKER(
                                lambda v: 0 if v[0].distance <= float(
                                    self.options['driving_distance_limit']) *
                                1000.0 else -1)]
                    else:
                        car_foot_plan.switch_constraint_list = [None]
                    plans.append(car_foot_plan)
                # 4: public transportation
                public_modes = [MODES[m] for m in \
                                self.options['available_public_modes']]
                st_pairs = self._find_valid_source_target_pairs(
                    candidate_sources, candidate_targets,
                    [MODES['public_transportation']], public_modes)
                for st in st_pairs:
                    public_plan = RoutingPlan(
                        'Walking and taking public transit',
                        st['source'], st['target'],
                        [MODES['public_transportation']], cost_factor)
                    public_plan.public_transit_set = public_modes
                    plans.append(public_plan)
                # 5: car-PT with geo_connection as Switch Point
                type_id = SWITCH_TYPES['geo_connection']
                public_modes = [MODES[m] for m in \
                                self.options['available_public_modes']]
                st_pairs = self._find_valid_source_target_pairs(
                    candidate_sources, candidate_targets,
                    [MODES['private_car'], MODES['public_transportation']],
                    public_modes)
                for st in st_pairs:
                    car_public_plan1 = RoutingPlan(
                        'Driving and taking public transit',
                        st['source'], st['target'],
                        [MODES['private_car'], MODES['public_transportation']],
                        cost_factor, [type_id],
                        ["type_id=" + str(type_id) + " AND is_available=true"])
                    car_public_plan1.public_transit_set = public_modes
                    if 'driving_distance_limit' in self.options:
                        car_public_plan1.switch_constraint_list = [
                            VERTEX_VALIDATION_CHECKER(
                                lambda v: 0 if v[0].distance <= float(
                                    self.options['driving_distance_limit']) *
                                1000.0 else -1)]
                    else:
                        car_public_plan1.switch_constraint_list = [None]
                    plans.append(car_public_plan1)
                # 6: car-PT with kiss+R as Switch Point
                type_id = SWITCH_TYPES['kiss_and_ride']
                public_modes = [MODES[m] for m in \
                                self.options['available_public_modes']]
                st_pairs = self._find_valid_source_target_pairs(
                    candidate_sources, candidate_targets,
                    [MODES['private_car'], MODES['public_transportation']],
                    public_modes)
                for st in st_pairs:
                    car_public_plan2 = RoutingPlan(
                        'Driving and taking public transit via Kiss+R',
                        st['source'], st['target'],
                        [MODES['private_car'], MODES['public_transportation']],
                        cost_factor, [type_id],
                        ["type_id=" + str(type_id) + " AND is_available=true"])
                    car_public_plan2.public_transit_set = public_modes
                    if 'driving_distance_limit' in self.options:
                        car_public_plan2.switch_constraint_list = [
                            VERTEX_VALIDATION_CHECKER(
                                lambda v: 0 if v[0].distance <= float(
                                    self.options['driving_distance_limit']) *
                                1000.0 else -1)]
                    else:
                        car_public_plan2.switch_constraint_list = [None]
                    plans.append(car_public_plan2)
                return plans

            if self.options['has_private_car'] and self.options['need_parking']:
                # the user may be the driver
                # and he/she surely need a parking lot for the car
                # There are 5 possible mode combinations in this case:
                # 1. foot;
                # 2. car-foot with parking as Switch Point;
                # 3. PT;
                # 4. car-PT with parking as Switch Points;
                # 5. car-PT with P+R as Switch Points;
                #
                # 1: foot only
                st_pairs = self._find_valid_source_target_pairs(
                    candidate_sources, candidate_targets, [MODES['foot']])
                for st in st_pairs:
                    plans.append(RoutingPlan(
                        'Walking', st['source'], st['target'],
                        [MODES['foot']], cost_factor))
                # 2: car-foot with parking lots as Switch Point
                type_id = SWITCH_TYPES['car_parking']
                st_pairs = self._find_valid_source_target_pairs(
                    candidate_sources, candidate_targets,
                    [MODES['private_car'], MODES['foot']])
                for st in st_pairs:
                    car_foot_plan = RoutingPlan(
                        'Driving, parking and walking',
                        st['source'], st['target'],
                        [MODES['private_car'], MODES['foot']],
                        cost_factor, [type_id],
                        ["type_id=" + str(type_id) + " AND is_available=true"])
                    remaining_gas_factor = 0.5
                    if 'driving_distance_limit' in self.options:
                        car_foot_plan.switch_constraint_list = [
                            VERTEX_VALIDATION_CHECKER(
                                lambda v: 0 if v[0].distance <= float(
                                    self.options['driving_distance_limit']) *
                                1000.0 * remaining_gas_factor else -1)]
                    else:
                        car_foot_plan.switch_constraint_list = [None]
                    plans.append(car_foot_plan)
                # 3: public transportation
                public_modes = [MODES[m] for m in \
                                self.options['available_public_modes']]
                st_pairs = self._find_valid_source_target_pairs(
                    candidate_sources, candidate_targets,
                    [MODES['public_transportation']], public_modes)
                print st_pairs
                for st in st_pairs:
                    print st
                    public_plan = RoutingPlan(
                        'Walking and taking public transit',
                        st['source'], st['target'],
                        [MODES['public_transportation']], cost_factor)
                    public_plan.public_transit_set = public_modes
                    plans.append(public_plan)
                # 4: car-PT with parking as Switch Point
                type_id = SWITCH_TYPES['car_parking']
                public_modes = [MODES[m] for m in \
                                self.options['available_public_modes']]
                st_pairs = self._find_valid_source_target_pairs(
                    candidate_sources, candidate_targets,
                    [MODES['private_car'], MODES['public_transportation']],
                    public_modes)
                for st in st_pairs:
                    car_public_plan1 = RoutingPlan(
                        'Driving, parking and taking public transit',
                        st['source'], st['target'],
                        [MODES['private_car'], MODES['public_transportation']],
                        cost_factor, [type_id],
                        ["type_id=" + str(type_id) + " AND is_available=true"])
                    car_public_plan1.public_transit_set = public_modes
                    if 'driving_distance_limit' in self.options:
                        car_public_plan1.switch_constraint_list = [
                            VERTEX_VALIDATION_CHECKER(
                                lambda v: 0 if v[0].distance <= float(
                                    self.options['driving_distance_limit']) *
                                1000.0 else -1)]
                    else:
                        car_public_plan1.switch_constraint_list = [None]
                    plans.append(car_public_plan1)
                # 5: car-PT with P+R as Switch Point
                type_id = SWITCH_TYPES['park_and_ride']
                public_modes = [MODES[m] for m in \
                                self.options['available_public_modes']]
                st_pairs = self._find_valid_source_target_pairs(
                    candidate_sources, candidate_targets,
                    [MODES['private_car'], MODES['public_transportation']],
                    public_modes)
                for st in st_pairs:
                    car_public_plan1 = RoutingPlan(
                        'Driving, parking and taking public transit',
                        st['source'], st['target'],
                        [MODES['private_car'], MODES['public_transportation']],
                        cost_factor, [type_id],
                        ["type_id=" + str(type_id) + " AND is_available=true"])
                    car_public_plan1.public_transit_set = public_modes
                    if 'driving_distance_limit' in self.options:
                        car_public_plan1.switch_constraint_list = [
                            VERTEX_VALIDATION_CHECKER(
                                lambda v: 0 if v[0].distance <= float(
                                    self.options['driving_distance_limit']) *
                                1000.0 else -1)]
                    else:
                        car_public_plan1.switch_constraint_list = [None]
                    plans.append(car_public_plan1)
                return plans

            elif self.options['objective'] == 'shortest':
                if not self.options['can_use_public']:
                    if not self.options['has_private_car']:
                        # no car, walk only
                        st_pairs = self._find_valid_source_target_pairs(
                            candidate_sources, candidate_targets, [MODES['foot']])
                        for st in st_pairs:
                            plans.append(RoutingPlan(
                                'Walking', st['source'], st['target'],
                                [MODES['foot']], cost_factor))
                    else:
                        # car
                        st_pairs = self._find_valid_source_target_pairs(
                            candidate_sources, candidate_targets, [MODES['private_car']])
                        for st in st_pairs:
                            car_plan = RoutingPlan(
                                'Take a car', st['source'], st['target'],
                                [MODES['private_car']], cost_factor)
                            if 'driving_distance_limit' in self.options:
                                car_plan.target_constraint = VERTEX_VALIDATION_CHECKER(
                                        lambda v: 0 if v[0].distance <= float(
                                            self.options['driving_distance_limit']) *
                                        1000.0 else -1)
                            plans.append(car_plan)
                        # foot
                        st_pairs = self._find_valid_source_target_pairs(
                            candidate_sources, candidate_targets, [MODES['foot']])
                        for st in st_pairs:
                            plans.append(RoutingPlan(
                                'Walking', st['source'], st['target'],
                                [MODES['foot']], cost_factor))
                        return plans
                else:
                    # TODO: finish this branch
                    return []
