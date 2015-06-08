""" RoutingResult class is a part of pymmrouting module """

from ctypes import POINTER, Structure, c_longlong, c_int
from itertools import tee, izip
from .orm_graphmodel import Mode, Session, Vertex, Edge, \
    StreetLine, get_waypoints
from os import path
import json
import logging

logger = logging.getLogger(__name__)

MODES         = {str(m_name): m_id
                 for m_name, m_id in
                 Session.query(Mode.mode_name, Mode.mode_id)}
TMP_DIR = "tmp/"

class RawPath(Structure):
    _fields_ = [("vertex_list", POINTER(c_longlong)),
                ("vertex_list_length", c_int)]

class RawMultimodalPath(Structure):
    _fields_ = [("path_segments", POINTER(RawPath))]

class ModePath(object):

    """ Path description of a single transportation mode
    """

    def __init__(self, mode, init_vertices=None):
        self.mode           = mode
        self.vertex_id_list = [] if init_vertices is None else init_vertices
        self._link_id_list  = []
        self._edge_id_list  = []
        self._point_list    = []
        self.sub_mode_paths = []
        # FIXME: The following attribute values can not be figured out so far
        #self.length         = 0.0
        #self.walking_length = 0.0
        #self.walking_time   = 0.0

    @property
    def is_multimodal(self):
        return True if self.mode == MODES['public_transportation'] else False

    @property
    def edge_id_list(self):
        for i, j in self._pairwise(self.vertex_id_list):
            self._edge_id_list.append(Session.query(Edge.edge_id).filter(
                Edge.from_id == i, Edge.to_id == j).first().edge_id)
        return self._edge_id_list

    @property
    def link_id_list(self):
        for i, j in self._pairwise(self.vertex_id_list):
            self._link_id_list.append(Session.query(Edge.link_id).filter(
                Edge.from_id == i, Edge.to_id == j).first().link_id)
        return self._link_id_list

    def _get_way_points_between_vertices(self, u, v):
        link_id = Session.query(Edge.link_id).filter(
        Edge.from_id == u, Edge.to_id == v).first()
        # FIXME: It is not reliable to find the line feature by
        # fnodeid/tnodeid pair or um_id because both of them are not
        # unique. There is actually no unique id field available in UM
        # dataset except the sequence id - gid generated when importing to
        # database. So perhaps I have to use gid as the reference id when
        # searching for the line feature although this is not good in
        # practice.
        coord_list = []
        if self.mode in [MODES['private_car'], MODES['foot']]:
            return get_waypoints(Session.query(StreetLine.geom).filter(
                StreetLine.link_id == link_id).first().geom)
        elif self.mode == MODES['underground']:
            raw_fnodeid = u % 10000000 - u % 1000000 + u % 100000
            raw_tnodeid = v % 10000000 - u % 1000000 + u % 100000
            sql = "SELECT ST_AsGeoJSON(underground_lines.geom, 4326) AS line_geom \
                FROM underground_lines WHERE (fnodeid = :fnode AND tnodeid = :tnode) \
                OR (fnodeid = :tnode AND tnodeid = :fnode) LIMIT 1;"
        elif self.mode == MODES['suburban']:
            raw_fnodeid = u % 100000000
            raw_tnodeid = v % 100000000
            sql = "SELECT ST_AsGeoJSON(suburban_lines.geom, 4326) AS line_geom \
                FROM suburban_lines WHERE (fnodeid = :fnode AND tnodeid = :tnode) \
                OR (fnodeid = :tnode AND tnodeid = :fnode) LIMIT 1;"
        elif self.mode == MODES['tram']:
            raw_fnodeid = u % 100000000
            raw_tnodeid = v % 100000000
            sql = "SELECT ST_AsGeoJSON(tram_lines.geom, 4326) AS line_geom \
                FROM tram_lines WHERE (fnodeid = :fnode AND tnodeid = :tnode) \
                OR (fnodeid = :tnode AND tnodeid = :fnode) LIMIT 1;"
        linestring = Session.execute(sql, {'fnode': raw_fnodeid,
                                           'tnode': raw_tnodeid}).fetchall()
        coords = json.loads(linestring[0][0])['coordinates']
        coord_list = [j for i in coords for j in i]
        logger.debug("Coordinate list between %s and %s: %s", u, v, coord_list)
        return coord_list

    def _geo_diff(self, p1, p2):
        x_diff = abs(p1[0] - p2[0])
        y_diff = abs(p1[1] - p2[1])
        return (x_diff + y_diff) * 0.5

    def _concat_seg_points(self, index, path_seg_points, threshold=1.0e-6):
        if index == 1:
            if (self._geo_diff(self._point_list[0], path_seg_points[0]) <= threshold) or \
                (self._geo_diff(self._point_list[0], path_seg_points[-1]) <= threshold):
                self._point_list.reverse()
        if index >= 1:
            if self._geo_diff(self._point_list[-1], path_seg_points[-1]) <= threshold:
                path_seg_points.reverse()
        self._point_list += path_seg_points

    @property
    def point_list(self):
        self._point_list = []
        for index, (i, j) in enumerate(self._pairwise(self.vertex_id_list)):
            way_points = self._get_way_points_between_vertices(i, j)
            self._concat_seg_points(index, way_points)
        return self._point_list

    def _pairwise(self, iterable):
        """ transform a list into a pairwise iterable container like this:
            [s0, s1, s2, s3, ...] -> [s0,s1], [s1,s2], [s2, s3], ...
        """
        a, b = tee(iterable)
        next(b, None)
        return izip(a, b)

    def to_geojson(self):
        return {"type": "LineString", "coordinates": self.point_list}

    # FIXME: I have some wierd feelings about this method, should be fixed
    def expand_mode_path(self):
        if self.is_multimodal:
            first_mode = Session.query(Vertex.mode_id).filter(
                Vertex.vertex_id == self.vertex_id_list[0]).first().mode_id
            mp = ModePath(first_mode, [self.vertex_id_list[0]])
            self.sub_mode_paths.append(mp)
            last_mode = first_mode
            for v in self.vertex_id_list[1:]:
                vm = Session.query(Vertex.mode_id).filter(
                    Vertex.vertex_id == v).first().mode_id
                if vm != last_mode:
                    mp = ModePath(vm, [v])
                    self.sub_mode_paths.append(mp)
                else:
                    mp.vertex_id_list.append(v)
                last_mode = vm


class RoutingResult(object):

    """ Store the multimodal routing results """

    def __init__(self):
        self.is_existent              = False
        self.planned_mode_list        = []
        self.unfolded_mode_list       = []
        self.mode_paths               = []
        self.switch_type_list         = []
        self.planned_switch_type_list = []
        self.switch_point_list        = []
        self.switch_point_name_list   = []
        self.description              = ''
        self.length                   = 0.0
        self.time                     = 0.0
        self.walking_time             = 0.0
        self.walking_length           = 0.0

    @property
    def path_by_vertices(self):
        #if not self.mode_paths: return []
        #return reduce(lambda x, y: x.vertex_id_list + y.vertex_id_list, self.mode_paths)
        vertices = []
        for mp in self.mode_paths:
            vertices += mp.vertex_id_list
        return vertices

    @property
    def path_by_edges(self):
        #if not self.mode_paths: return []
        #return reduce(lambda x, y: x.edge_id_list + y.edge_id_list, self.mode_paths)
        edges = []
        for mp in self.mode_paths:
            edges += mp.edge_id_list
        return edges

    @property
    def path_by_links(self):
        #if not self.mode_paths: return []
        #return reduce(lambda x, y: x.link_id_list + y.link_id_list, self.mode_paths)
        links = []
        for mp in self.mode_paths:
            links += mp.link_id_list
        return links

    @property
    def path_by_points(self):
        #if not self.mode_paths: return []
        #return reduce(lambda x, y: x.point_list + y.point_list, self.mode_paths)
        points = []
        for mp in self.mode_paths:
            points += mp.point_list
        return points

    # TODO: The following calculating can be done when those attributes in each
    # mode graph is able to given by mmspa lib
    #@property
    #def length(self):
        #return sum(map(lambda x: x.length, self.mode_paths))

    #@property
    #def time(self):
        #return sum(map(lambda x: x.time, self.mode_paths))

    #@property
    #def walking_time(self):
        #return sum(map(lambda x: x.walking_time, self.mode_paths))

    #@property
    #def walking_length(self):
        #return sum(map(lambda x: x.walking_length, self.mode_paths))

    def unfold_sub_paths(self):
        mode_paths = []
        for mp in self.mode_paths:
            if not mp.is_multimodal:
                mode_paths.append(mp)
            else:
                mp.expand_mode_path()
                mode_paths += mp.sub_mode_paths
                self.mode_paths = mode_paths

    def output_path_info(self, prefix=None):
        if prefix is None:
            prefix = '-'.join(self.description.split())
            logger.debug("paths expressed with vertex id list: %s",
                         self.path_by_vertices)
            logger.debug("paths expressed with raw link id list: %s",
                         self.path_by_links)
            logger.debug("paths expressed with point coordinate list: %s",
                         self.path_by_points)
            for i, mp in enumerate(self.mode_paths):
                path_seg_file = path.join(TMP_DIR, str(i) + "." + str(prefix) + \
                                        "_" + str(mp.mode) + '_path_seg.geojson')
                with open(path_seg_file, 'w') as mode_path_file:
                    mode_path_file.write(json.dumps(mp.to_geojson()))
