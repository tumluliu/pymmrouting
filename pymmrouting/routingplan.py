""" RoutingPlan class is a part of pymmrouting module """


class RoutingPlan(object):

    """ Store the multimodal routing plan """

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
