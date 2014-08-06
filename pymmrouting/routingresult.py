""" RoutingResult class is a part of pymmrouting module """


class RoutingResult(object):

    """ Store the multimodal routing results """

    def __init__(self):
        self.is_existent = False
        self.planned_mode_list = []
        self.rendering_mode_list = []
        self.paths_by_vertex_id = []
        self.paths_by_edge_id = []
        self.paths_by_link_id = []
        self.paths_by_points = []
        self.switch_type_list = []
        self.planned_switch_type_list = []
        self.switch_point_list = []
        self.switch_point_name_list = []
        self.description = ''
        self.length = 0.0
        self.time = 0.0
        self.walking_length = 0.0
        self.walking_time = 0.0
