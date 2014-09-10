""" RoutingResult class is a part of pymmrouting module """

from ctypes import POINTER, Structure, c_longlong, c_int


class Path(Structure):
    _fields_ = [("vertex_list", POINTER(c_longlong)),
                ("vertex_list_length", c_int)]


class MultimodalPath(Structure):
    _fields_ = [("path_segments", POINTER(Path))]


class RoutingResult(object):

    """ Store the multimodal routing results """

    def __init__(self):
        self.is_existent = False
        self.planned_mode_list = []
        self.rendering_mode_list = []
        self.paths_by_vertex_id = {}
        self.paths_by_edge_id = {}
        self.paths_by_link_id = {}
        self.paths_by_points = {}
        self.switch_type_list = []
        self.planned_switch_type_list = []
        self.switch_point_list = []
        self.switch_point_name_list = []
        self.description = ''
        self.length = 0.0
        self.time = 0.0
        self.walking_length = 0.0
        self.walking_time = 0.0

    def show_on_map(self, basemap):
        print "paths in vertex_id list:"
        print self.paths_by_vertex_id
        print "paths in osm_id list:"
        print self.paths_by_link_id
        print "I will be rendered on " + str(basemap)
