"""
Infer feasible routing plans according to user preferences
"""


import json
from ctypes import *
from pymmrouting.datamodel import Vertex, VERTEX_VALIDATION_CHECKER

class RoutingPlan(object):

    """
    A plan of routing including transportation tools to use
    during the trip
    """

    def __init__(self):
        self.is_multimodal = False
        self.mode_list = []
        self.switch_type_list = []
        self.switch_condition_list = []
        self.switch_constraint_list = []
        #self.target_constraint = VERTEX_VALIDATION_CHECKER(lambda v: 0)
        self.target_constraint = None
        self.public_transit_set = []
        self.has_public_transit = False
        self.cost_factor = ''
        self.description = ''
        self.source = 0
        self.target = 0

class RoutingPlanInferer(object):

    """
    Infer the feasible routing plans according to routing options
    """

    MODES = {
        'private_car':           1001,
        'foot':                  1002,
        'underground':           1003,
        'suburban':              1004,
        'tram':                  1005,
        'bus':                   1006,
        'public_transportation': 1900,
        'bicycle':               1007,
        'taxi':                  1008
    }

    SWITCH_TYPES = {
        'car_parking':         2001,
        'geo_connection':      2002,
        'park_and_ride':       2003,
        'underground_station': 2004,
        'suburban_station':    2005,
        'tram_station':        2006,
        'bus_station':         2007,
        'kiss_and_ride':       2008
    }


    def __init__(self):
        self.options = {}

    def load_routing_options(self, options_file_path):
        with open(options_file_path) as options_file:
            self.options = json.load(options_file)

    def generate_routing_plan(self):
        routing_plan_list = []
        if self.options == {}:
            raise Exception('Empty routing options!')

        if self.options['objective'] == 'shortest':
            cost_factor = 'length'
        elif self.options['objective'] == 'fastest':
            cost_factor = 'speed'
        if self.options['objective'] == 'fastest':
            if len(self.options['available_public_modes']) == 0:
                if not self.options['has_private_car']:
                    # only can walk, mono-modal routing
                    routing_plan = RoutingPlan()
                    routing_plan.mode_list.append(self.MODES['foot'])
                    routing_plan.is_multimodal = False
                    routing_plan.cost_factor = cost_factor
                    routing_plan.description = 'Walking'
                    routing_plan_list.append(routing_plan)
                    return routing_plan_list

                if self.options['has_private_car'] and (not self.options['need_parking']):
                    # somebody else will be the driver
                    # the car can be parked temporarily anywhere
                    # There are 3 possible mode combinations in this case:
                    # car; foot; car-foot with geo_connection as Switch Point
                    # 1st: car only
                    routing_plan = RoutingPlan()
                    routing_plan.mode_list.append(self.MODES['private_car'])
                    routing_plan.is_multimodal = False
                    routing_plan.cost_factor = cost_factor
                    routing_plan.description = 'Driving a car'
                    if 'driving_distance_limit' in self.options:
                        routing_plan.target_constraint = VERTEX_VALIDATION_CHECKER(
                            lambda v: 0 if v[0].distance <= float(
                                self.options['driving_distance_limit']) *
                            1000.0 else -1)
                    routing_plan_list.append(routing_plan)
                    # 2nd: foot only
                    routing_plan = RoutingPlan()
                    routing_plan.mode_list.append(self.MODES['foot'])
                    routing_plan.is_multimodal = False
                    routing_plan.cost_factor = cost_factor
                    routing_plan.description = 'Walking'
                    routing_plan_list.append(routing_plan)
                    # 3rd: car-foot with geo_connection as Switch Point
                    routing_plan = RoutingPlan()
                    routing_plan.mode_list.append(self.MODES['private_car'])
                    routing_plan.mode_list.append(self.MODES['foot'])
                    type_id = self.SWITCH_TYPES['geo_connection']
                    routing_plan.switch_type_list.append(type_id)
                    routing_plan.switch_condition_list.append(
                        "type_id=" +
                        str(type_id) +
                        " AND is_available=true")
                    if 'driving_distance_limit' in self.options:
                        routing_plan.switch_constraint_list.append(
                            VERTEX_VALIDATION_CHECKER(
                                lambda v: 0 if v[0].distance <= float(
                                    self.options['driving_distance_limit']) *
                                1000.0 else -1))
                    else:
                        routing_plan.switch_constraint_list.append(None)
                    routing_plan.is_multimodal = True
                    routing_plan.cost_factor = cost_factor
                    routing_plan.description = 'By car first, then walking without parking'
                    routing_plan_list.append(routing_plan)
                    return routing_plan_list

                if self.options['has_private_car'] and self.options['need_parking']:
                    # the user may be the driver
                    # and he/she surely need a parking lot for the car
                    # There are also 2 possible mode combinations in this case:
                    # foot; car-foot with parking as Switch Point
                    # 1st: foot only
                    routing_plan = RoutingPlan()
                    routing_plan.mode_list.append(self.MODES['foot'])
                    routing_plan.is_multimodal = False
                    routing_plan.cost_factor = cost_factor
                    routing_plan.description = 'Walking'
                    routing_plan_list.append(routing_plan)
                    # 2nd: car-foot with parking lots as Switch Point
                    routing_plan = RoutingPlan()
                    routing_plan.mode_list.append(self.MODES['private_car'])
                    routing_plan.mode_list.append(self.MODES['foot'])
                    type_id = self.SWITCH_TYPES['car_parking']
                    routing_plan.switch_type_list.append(type_id)
                    routing_plan.switch_condition_list.append(
                        "type_id=" +
                        str(type_id) +
                        " AND is_available=true")
                    if 'driving_distance_limit' in self.options:
                        routing_plan.switch_constraint_list.append(
                            VERTEX_VALIDATION_CHECKER(
                                lambda v: 0 if v[0].distance <= float(
                                    self.options['driving_distance_limit']) *
                                1000.0 / 2 else -1))
                    else:
                        routing_plan.switch_constraint_list.append(None)
                    routing_plan.is_multimodal = True
                    routing_plan.cost_factor = cost_factor
                    routing_plan.description = 'Driving, parking and walking'
                    routing_plan_list.append(routing_plan)
                    return routing_plan_list
            else:
                # can use public transportation system
                # 2010-02-01 important comments by Liu Lu
                # !!!IMPORTANT!!!: according to the latest idea in my head, in this
                #                  "can use public transportation" branch, the selected
                #                  PT modes networks should be combined together with
                #                  the pedestrian network. This process can avoid the
                #                  redundant inferred routing plans e.g. foot-PT-foot,
                #                  PT-foot, foot-PT etc.
                #                  As a result, the new PT(1900) mode here means the
                #                  network composed of pedestrian and selected PT modes
                #                  networks
                #
                if not self.options['has_private_car']:
                    # the user can walk or take public transportation
                    # 2 possible mode combinations:
                    # 1. foot;
                    # 2. PT
                    #
                    # 1: foot only
                    routing_plan = RoutingPlan()
                    routing_plan.mode_list.append(self.MODES['foot'])
                    routing_plan.is_multimodal = False
                    routing_plan.cost_factor = cost_factor
                    routing_plan.description = 'Walking'
                    routing_plan_list.append(routing_plan)
                    # 2: public transportation
                    routing_plan = RoutingPlan()
                    routing_plan.has_public_transit = True
                    routing_plan.mode_list.append(
                        self.MODES['public_transportation'])
                    for p_mode in self.options['available_public_modes']:
                        routing_plan.public_transit_set.append(
                            self.MODES[p_mode])
                    routing_plan.is_multimodal = True
                    routing_plan.cost_factor = cost_factor
                    routing_plan.description = 'Walking and taking public transit'
                    routing_plan_list.append(routing_plan)
                    return routing_plan_list

            if self.options['has_private_car'] and (not self.options['need_parking']):
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
                routing_plan = RoutingPlan()
                routing_plan.mode_list.append(self.MODES['private_car'])
                routing_plan.is_multimodal = False
                routing_plan.cost_factor = cost_factor
                routing_plan.description = 'Driving a car'
                if 'driving_distance_limit' in self.options:
                    routing_plan.target_constraint = VERTEX_VALIDATION_CHECKER(
                        lambda v: 0 if v[0].distance <= float(
                            self.options['driving_distance_limit']) *
                        1000.0 else -1)
                routing_plan_list.append(routing_plan)
                # 2: foot only
                routing_plan = RoutingPlan()
                routing_plan.mode_list.append(self.MODES['foot'])
                routing_plan.is_multimodal = False
                routing_plan.cost_factor = cost_factor
                routing_plan.description = 'Walking'
                routing_plan_list.append(routing_plan)
                # 3: car-foot with geo_connection as Switch Point
                routing_plan = RoutingPlan()
                routing_plan.mode_list.append(self.MODES['private_car'])
                routing_plan.mode_list.append(self.MODES['foot'])
                type_id = self.SWITCH_TYPES['geo_connection']
                routing_plan.switch_type_list.append(type_id)
                routing_plan.switch_condition_list.append(
                    "type_id=" +
                    str(type_id) +
                    " AND is_available=true")
                if 'driving_distance_limit' in self.options:
                    routing_plan.switch_constraint_list.append(
                        VERTEX_VALIDATION_CHECKER(
                            lambda v: 0 if v[0].distance <= float(
                                self.options['driving_distance_limit']) *
                            1000.0 else -1))
                else:
                    routing_plan.switch_constraint_list.append(None)
                routing_plan.is_multimodal = True
                routing_plan.cost_factor = cost_factor
                routing_plan.description = 'By car first, then walking without parking'
                routing_plan_list.append(routing_plan)
                # 4: public transportation
                routing_plan = RoutingPlan()
                routing_plan.has_public_transit = True
                routing_plan.mode_list.append(
                    self.MODES['public_transportation'])
                for p_mode in self.options['available_public_modes']:
                    routing_plan.public_transit_set.append(
                        self.MODES[p_mode])
                routing_plan.is_multimodal = True
                routing_plan.cost_factor = cost_factor
                routing_plan.description = 'Walking and taking public transit'
                routing_plan_list.append(routing_plan)
                # 5: car-PT with geo_connection as Switch Point
                routing_plan = RoutingPlan()
                routing_plan.has_public_transit = True
                routing_plan.mode_list.append(self.MODES['private_car'])
                routing_plan.mode_list.append(
                    self.MODES['public_transportation'])
                type_id = self.SWITCH_TYPES['geo_connection']
                routing_plan.switch_type_list.append(type_id)
                routing_plan.switch_condition_list.append(
                    "type_id=" +
                    str(type_id) +
                    " AND is_available=true")
                if 'driving_distance_limit' in self.options:
                    routing_plan.switch_constraint_list.append(
                        VERTEX_VALIDATION_CHECKER(
                            lambda v: 0 if v[0].distance <= float(
                                self.options['driving_distance_limit']) *
                            1000.0 else -1))
                else:
                    routing_plan.switch_constraint_list.append(None)
                for p_mode in self.options['available_public_modes']:
                    routing_plan.public_transit_set.append(
                        self.MODES[p_mode])
                routing_plan.is_multimodal = True
                routing_plan.cost_factor = cost_factor
                routing_plan.description = 'Driving and taking public transit'
                routing_plan_list.append(routing_plan)
                # 6: car-PT with kiss+R as Switch Point
                routing_plan = RoutingPlan()
                routing_plan.has_public_transit = True
                routing_plan.mode_list.append(self.MODES['private_car'])
                routing_plan.mode_list.append(
                    self.MODES['public_transportation'])
                type_id = self.SWITCH_TYPES['kiss_and_ride']
                routing_plan.switch_type_list.append(type_id)
                routing_plan.switch_condition_list.append(
                    "type_id=" +
                    str(type_id) +
                    " AND is_available=true")
                if 'driving_distance_limit' in self.options:
                    routing_plan.switch_constraint_list.append(
                        VERTEX_VALIDATION_CHECKER(
                            lambda v: 0 if v[0].distance <= float(
                                self.options['driving_distance_limit']) *
                            1000.0 else -1))
                else:
                    routing_plan.switch_constraint_list.append(None)
                for p_mode in self.options['available_public_modes']:
                    routing_plan.public_transit_set.append(
                        self.MODES[p_mode])
                routing_plan.is_multimodal = True
                routing_plan.cost_factor = cost_factor
                routing_plan.description = 'Driving and taking public transit via Kiss+R'
                routing_plan_list.append(routing_plan)
                return routing_plan_list

            if self.options['has_private_car'] and self.options['need_parking']:
                # the user may be the driver
                # and he/she surely need a parking lot for the car
                # There are 6 possible mode combinations in this case:
                # 1. foot;
                # 2. car-foot with parking as Switch Point;
                # 3. PT;
                # 4. car-PT with parking as Switch Points;
                # 5. car-PT with P+R as Switch Points;
                #
                # 1: foot only
                routing_plan = RoutingPlan()
                routing_plan.mode_list.append(self.MODES['foot'])
                routing_plan.is_multimodal = False
                routing_plan.cost_factor = cost_factor
                routing_plan.description = 'Walking'
                routing_plan_list.append(routing_plan)
                # 2: car-foot with parking lots as Switch Point
                routing_plan = RoutingPlan()
                routing_plan.mode_list.append(self.MODES['private_car'])
                routing_plan.mode_list.append(self.MODES['foot'])
                type_id = self.SWITCH_TYPES['car_parking']
                routing_plan.switch_type_list.append(type_id)
                routing_plan.switch_condition_list.append(
                    "type_id=" +
                    str(type_id) +
                    " AND is_available=true")
                if 'driving_distance_limit' in self.options:
                    routing_plan.switch_constraint_list.append(
                        VERTEX_VALIDATION_CHECKER(
                            lambda v: 0 if v[0].distance <= float(
                                self.options['driving_distance_limit']) *
                                1000.0 / 2 else -1))
                else:
                    routing_plan.switch_constraint_list.append(None)
                routing_plan.is_multimodal = True
                routing_plan.cost_factor = cost_factor
                routing_plan.description = 'Driving, parking and walking'
                routing_plan_list.append(routing_plan)
                # 3: public transportation
                routing_plan = RoutingPlan()
                routing_plan.has_public_transit = True
                routing_plan.mode_list.append(
                    self.MODES['public_transportation'])
                for p_mode in self.options['available_public_modes']:
                    routing_plan.public_transit_set.append(
                        self.MODES[p_mode])
                routing_plan.is_multimodal = True
                routing_plan.cost_factor = cost_factor
                routing_plan.description = 'Walking and taking public transit'
                routing_plan_list.append(routing_plan)
                # 4: car-PT with parking as Switch Point
                routing_plan = RoutingPlan()
                routing_plan.has_public_transit = True
                routing_plan.mode_list.append(self.MODES['private_car'])
                routing_plan.mode_list.append(
                    self.MODES['public_transportation'])
                type_id = self.SWITCH_TYPES['car_parking']
                routing_plan.switch_type_list.append(type_id)
                routing_plan.switch_condition_list.append(
                    "type_id=" +
                    str(type_id) +
                    " AND is_available=true")
                if 'driving_distance_limit' in self.options:
                    routing_plan.switch_constraint_list.append(
                        VERTEX_VALIDATION_CHECKER(
                            lambda v: 0 if v[0].distance <= float(
                                self.options['driving_distance_limit']) *
                            1000.0 / 2 else -1))
                else:
                    routing_plan.switch_constraint_list.append(None)
                for p_mode in self.options['available_public_modes']:
                    routing_plan.public_transit_set.append(
                        self.MODES[p_mode])
                routing_plan.is_multimodal = True
                routing_plan.cost_factor = cost_factor
                routing_plan.description = 'Driving, parking and taking public transit'
                routing_plan_list.append(routing_plan)
                # 5: car-PT with P+R as Switch Point
                routing_plan = RoutingPlan()
                routing_plan.has_public_transit = True
                routing_plan.mode_list.append(self.MODES['private_car'])
                routing_plan.mode_list.append(
                    self.MODES['public_transportation'])
                type_id = self.SWITCH_TYPES['park_and_ride']
                routing_plan.switch_type_list.append(type_id)
                routing_plan.switch_condition_list.append(
                    "type_id=" +
                    str(type_id) +
                    " AND is_available=true")
                if 'driving_distance_limit' in self.options:
                    routing_plan.switch_constraint_list.append(
                        VERTEX_VALIDATION_CHECKER(
                            lambda v: 0 if v[0].distance <= float(
                                self.options['driving_distance_limit']) *
                            1000.0 / 2 else -1))
                else:
                    routing_plan.switch_constraint_list.append(None)
                for p_mode in self.options['available_public_modes']:
                    routing_plan.public_transit_set.append(
                        self.MODES[p_mode])
                routing_plan.is_multimodal = True
                routing_plan.cost_factor = cost_factor
                routing_plan.description = 'Driving and taking public transit via P+R'
                routing_plan_list.append(routing_plan)
                return routing_plan_list

            elif self.options['objective'] == 'shortest':
                if not self.options['can_use_public']:
                    if not self.options['has_private_car']:
                        # no car, walk only
                        routing_plan = RoutingPlan()
                        routing_plan.mode_list.append(self.MODES['foot'])
                        routing_plan.is_multimodal = False
                        routing_plan.cost_factor = cost_factor
                        routing_plan.description = 'Walking'
                        routing_plan_list.append(routing_plan)
                        return routing_plan_list
                    else:
                        # car
                        routing_plan = RoutingPlan()
                        routing_plan.mode_list.append(
                            self.MODES['private_car'])
                        routing_plan.is_multimodal = False
                        routing_plan.cost_factor = cost_factor
                        routing_plan.description = 'Driving a car'
                        routing_plan_list.append(routing_plan)
                        if 'driving_distance_limit' in self.options:
                            routing_plan.target_constraint = VERTEX_VALIDATION_CHECKER(
                                lambda v: 0 if v[0].distance <= float(
                                    self.options['driving_distance_limit']) *
                                1000.0 else -1)
                        # foot
                        routing_plan = RoutingPlan()
                        routing_plan.mode_list.append(self.MODES['foot'])
                        routing_plan.is_multimodal = False
                        routing_plan.cost_factor = cost_factor
                        routing_plan.description = 'Walking'
                        routing_plan_list.append(routing_plan)
                        return routing_plan_list
                else:
                    # TODO: finish this branch
                    return []
