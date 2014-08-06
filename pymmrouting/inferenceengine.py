"""
Infer feasible routing plans according to user preferences
"""


class RoutingOptions(object):

    """
    Routing options for describing user preferences
    """

    def __init__(self):
        self.can_use_public = False
        self.can_use_underground = False
        self.can_use_suburban = False
        self.can_use_tram = False
        self.can_use_bus = False
        self.can_use_taxi = False
        self.has_bicycle = False
        self.has_motorcycle = False
        self.has_private_car = False
        self.need_parking = False
        self.objective = ''
        self.available_public_modes = []

    def can_use_underground(self, can_use):
        self.can_use_underground = can_use
        self.available_public_modes.append("underground")

    def can_use_suburban(self, can_use):
        self.can_use_suburban = can_use
        self.available_public_modes.append("suburban")

    def can_use_tram(self, can_use):
        self.can_use_tram = can_use
        self.available_public_modes.append("tram")

    def can_use_bus(self, can_use):
        self.can_use_bus = can_use
        self.available_public_modes.append("bus")

    def generate_id(self):
        id = []
        if self.can_use_public: id[0] = "1"
        else: id[0] = "0"
        if self.can_use_underground: id[1] = "1"
        else: id[1] = "0"
        if self.can_use_suburban: id[2] = "1"
        else: id[2] = "0"
        if self.can_use_tram: id[3] = "1"
        else: id[3] = "0"
        if self.can_use_bus: id[4] = "1"
        else: id[4] = "0"
        if self.can_use_taxi: id[5] = "1"
        else: id[5] = "0"
        if self.has_bicycle: id[6] = "1"
        else: id[6] = "0"
        if self.has_motorcycle: id[7] = "1"
        else: id[7] = "0"
        if self.has_private_car: id[8] = "1"
        else: id[8] = "0"
        if self.need_parking: id[9] = "1"
        else: id[9] = "0"
        if self.objective == 'shortest':
            id[10] = "0"
        elif self.objective == 'fastest':
            id[10] = "1"
        else:
            id[10] = "2"

        return id.to_s


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
        self.target_constraint = None
        self.public_transit_set = []
        self.has_public_transit = False
        self.cost_factor = ''
        self.description = ''


class RoutingPlanInferer(object):

    """
    Infer the feasible routing plans according to routing options
    """

    def __init__(self):
        self.stub = ""

    def generate_routing_plan(self):
        return RoutingPlan()
