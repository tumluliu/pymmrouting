"""
Infer feasible routing plans according to user preferences
"""

import json
# from ctypes import *
from pymmrouting.datamodel import VERTEX_VALIDATION_CHECKER
from pymmrouting.orm_graphmodel import SwitchType, Mode, Session

INTERNAL_SRID = 4326
# Read modes and switch_types from database instead of hard coding it here
MODES         = {str(m_name): m_id
                 for m_name, m_id in
                 Session.query(Mode.mode_name, Mode.mode_id)}
SWITCH_TYPES  = {str(t_name): t_id
                 for t_name, t_id in
                 Session.query(SwitchType.type_name, Mode.type_id)}


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
    source = {}
    target = {}

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
        return False if (len(self.mode_list) == 1) or \
            (MODES['public_transportation'] in self.mode_list) else True

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

    def generate_routing_plan(self):
        if self.options == {}:
            raise Exception('Empty routing options!')
        source = self._get_lon_lat_position(self.options['source'])
        target = self._get_lon_lat_position(self.options['target'])
        if self.options['objective'] == 'shortest':
            cost_factor = 'length'
        elif self.options['objective'] == 'fastest':
            cost_factor = 'speed'
        if self.options['objective'] == 'fastest':
            if len(self.options['available_public_modes']) == 0:
                if not self.options['has_private_car']:
                    # only can walk, mono-modal routing
                    foot_plan = RoutingPlan(
                        'Walking', source, target, [MODES['foot']], cost_factor)
                    return [foot_plan]
                if self.options['has_private_car'] and \
                        (not self.options['need_parking']):
                    # somebody else will be the driver
                    # the car can be parked temporarily anywhere
                    # There are 3 possible mode combinations in this case:
                    # car; foot; car-foot with geo_connection as Switch Point
                    # 1st: car only
                    car_plan = RoutingPlan('Take a car', source, target,
                                           [MODES['private_car']], cost_factor)
                    if 'driving_distance_limit' in self.options:
                        car_plan.target_constraint = VERTEX_VALIDATION_CHECKER(
                                lambda v: 0 if v[0].distance <= float(
                                    self.options['driving_distance_limit']) *
                                1000.0 else -1)
                    # 2nd: foot only
                    foot_plan = RoutingPlan('Walking', source, target,
                                            [MODES['foot']], cost_factor)
                    # 3rd: car-foot with geo_connection as Switch Point
                    type_id = SWITCH_TYPES['geo_connection']
                    car_foot_plan = RoutingPlan(
                        'By car first, then walking without parking',
                        source, target, [MODES['private_car'], MODES['foot']],
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
                    return [car_plan, foot_plan, car_foot_plan]

                if self.options['has_private_car'] and self.options['need_parking']:
                    # the user may be the driver
                    # and he/she surely need a parking lot for the car
                    # There are also 2 possible mode combinations in this case:
                    # foot; car-foot with parking as Switch Point
                    # 1st: foot only
                    foot_plan = RoutingPlan('Walking', source, target,
                                            [MODES['foot']], cost_factor)
                    # 2nd: car-foot with parking lots as Switch Point
                    type_id = SWITCH_TYPES['car_parking']
                    car_foot_plan = RoutingPlan(
                        'Driving, parking and walking', source, target,
                        [MODES['private_car'], MODES['foot']],
                        cost_factor, [type_id],
                        ["type_id=" + str(type_id) + " AND is_available=true"])
                    if 'driving_distance_limit' in self.options:
                        car_foot_plan.switch_constraint_list = [
                            VERTEX_VALIDATION_CHECKER(
                                lambda v: 0 if v[0].distance <= float(
                                    self.options['driving_distance_limit']) *
                                1000.0 / 2 else -1)]
                    else:
                        car_foot_plan.switch_constraint_list = [None]
                    return [foot_plan, car_foot_plan]
            else:
                # can use public transportation system
                if not self.options['has_private_car']:
                    # the user can walk or take public transportation
                    # 2 possible mode combinations:
                    # 1. foot;
                    # 2. PT
                    #
                    # 1: foot only
                    foot_plan = RoutingPlan(
                        'Walking', source, target, [MODES['foot']], cost_factor)
                    # 2: public transportation
                    public_plan = RoutingPlan(
                        'Walking and taking public transit', source, target,
                        [MODES['public_transportation']], cost_factor)
                    public_plan.public_transit_set = [
                        MODES[m] for m in self.options['available_public_modes']]
                    return [foot_plan, public_plan]

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
                car_plan = RoutingPlan('Take a car', source, target,
                                        [MODES['private_car']], cost_factor)
                if 'driving_distance_limit' in self.options:
                    car_plan.target_constraint = \
                        VERTEX_VALIDATION_CHECKER(
                            lambda v: 0 if v[0].distance <= float(
                                self.options['driving_distance_limit']) *
                            1000.0 else -1)
                # 2: foot only
                foot_plan = RoutingPlan(
                    'Walking', source, target, [MODES['foot']], cost_factor)
                # 3: car-foot with geo_connection as Switch Point
                type_id = SWITCH_TYPES['geo_connection']
                car_foot_plan = RoutingPlan(
                    'By car first, then walking without parking',
                    source, target, [MODES['private_car'], MODES['foot']],
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
                # 4: public transportation
                public_plan = RoutingPlan(
                    'Walking and taking public transit', source, target,
                    [MODES['public_transportation']], cost_factor)
                public_plan.public_transit_set = [
                    MODES[m] for m in self.options['available_public_modes']]
                # 5: car-PT with geo_connection as Switch Point
                type_id = SWITCH_TYPES['geo_connection']
                car_public_plan1 = RoutingPlan(
                    'Driving and taking public transit',
                    source, target,
                    [MODES['private_car'], MODES['public_transportation']],
                    cost_factor, [type_id],
                    ["type_id=" + str(type_id) + " AND is_available=true"])
                car_public_plan1.public_transit_set = [
                    MODES[m] for m in self.options['available_public_modes']]
                if 'driving_distance_limit' in self.options:
                    car_public_plan1.switch_constraint_list = [
                        VERTEX_VALIDATION_CHECKER(
                            lambda v: 0 if v[0].distance <= float(
                                self.options['driving_distance_limit']) *
                            1000.0 else -1)]
                else:
                    car_public_plan1.switch_constraint_list = [None]
                # 6: car-PT with kiss+R as Switch Point
                type_id = SWITCH_TYPES['kiss_and_ride']
                car_public_plan2 = RoutingPlan(
                    'Driving and taking public transit via Kiss+R',
                    source, target,
                    [MODES['private_car'], MODES['public_transportation']],
                    cost_factor, [type_id],
                    ["type_id=" + str(type_id) + " AND is_available=true"])
                if 'driving_distance_limit' in self.options:
                    car_public_plan2.switch_constraint_list = [
                        VERTEX_VALIDATION_CHECKER(
                            lambda v: 0 if v[0].distance <= float(
                                self.options['driving_distance_limit']) *
                            1000.0 else -1)]
                else:
                    car_public_plan2.switch_constraint_list = [None]
                car_public_plan2.public_transit_set = [
                    MODES[m] for m in self.options['available_public_modes']]
                return [car_plan, foot_plan, public_plan, car_foot_plan,
                        car_public_plan1, car_public_plan2]

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
                foot_plan = RoutingPlan('Walking', source, target,
                                        [MODES['foot']], cost_factor)
                # 2: car-foot with parking lots as Switch Point
                type_id = SWITCH_TYPES['car_parking']
                car_foot_plan = RoutingPlan(
                    'Driving, parking and walking', source, target,
                    [MODES['private_car'], MODES['foot']], cost_factor, [type_id],
                    ["type_id=" + str(type_id) + " AND is_available=true"])
                if 'driving_distance_limit' in self.options:
                    car_foot_plan.switch_constraint_list = [
                        VERTEX_VALIDATION_CHECKER(
                            lambda v: 0 if v[0].distance <= float(
                                self.options['driving_distance_limit']) *
                            1000.0 / 2 else -1)]
                else:
                    car_foot_plan.switch_constraint_list = [None]
                # 3: public transportation
                public_plan = RoutingPlan(
                    'Walking and taking public transit', source, target,
                    [MODES['public_transportation']], cost_factor)
                public_plan.public_transit_set = [
                    MODES[m] for m in self.options['available_public_modes']]
                # 4: car-PT with parking as Switch Point
                type_id = SWITCH_TYPES['car_parking']
                car_public_plan1 = RoutingPlan(
                    'Driving, parking and taking public transit',
                    source, target,
                    [MODES['private_car'], MODES['public_transportation']],
                    cost_factor, [type_id],
                    ["type_id=" + str(type_id) + " AND is_available=true"])
                car_public_plan1.public_transit_set = [
                    MODES[m] for m in self.options['available_public_modes']]
                if 'driving_distance_limit' in self.options:
                    car_public_plan1.switch_constraint_list = [
                        VERTEX_VALIDATION_CHECKER(
                            lambda v: 0 if v[0].distance <= float(
                                self.options['driving_distance_limit']) *
                            1000.0 / 2 else -1)]
                else:
                    car_public_plan1.switch_constraint_list = [None]
                # 5: car-PT with P+R as Switch Point
                type_id = SWITCH_TYPES['park_and_ride']
                car_public_plan2 = RoutingPlan(
                    'Driving, parking and taking public transit',
                    source, target,
                    [MODES['private_car'], MODES['public_transportation']],
                    cost_factor, [type_id],
                    ["type_id=" + str(type_id) + " AND is_available=true"])
                car_public_plan2.public_transit_set = [
                    MODES[m] for m in self.options['available_public_modes']]
                if 'driving_distance_limit' in self.options:
                    car_public_plan2.switch_constraint_list = [
                        VERTEX_VALIDATION_CHECKER(
                            lambda v: 0 if v[0].distance <= float(
                                self.options['driving_distance_limit']) *
                            1000.0 / 2 else -1)]
                else:
                    car_public_plan2.switch_constraint_list = [None]
                return [foot_plan, car_foot_plan, public_plan,
                        car_public_plan1, car_public_plan2]

            elif self.options['objective'] == 'shortest':
                if not self.options['can_use_public']:
                    if not self.options['has_private_car']:
                        # no car, walk only
                        foot_plan = RoutingPlan(
                            'Walking', source, target, [MODES['foot']],
                            cost_factor)
                        return [foot_plan]
                    else:
                        # car
                        car_plan = RoutingPlan(
                            'Take a car', source, target, [MODES['private_car']],
                            cost_factor)
                        if 'driving_distance_limit' in self.options:
                            car_plan.target_constraint = \
                                VERTEX_VALIDATION_CHECKER(
                                    lambda v: 0 if v[0].distance <= float(
                                        self.options['driving_distance_limit']) *
                                    1000.0 else -1)
                        # foot
                        foot_plan = RoutingPlan('Walking', source, target,
                                                [MODES['foot']], cost_factor)
                        return [car_plan, foot_plan]
                else:
                    # TODO: finish this branch
                    return []
