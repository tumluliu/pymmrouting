""" RoutingResult class is a part of pymmrouting module """

from ctypes import POINTER, Structure, c_longlong, c_int
from itertools import tee, izip
from geoalchemy2.functions import ST_AsGeoJSON as st_asgeojson
from .orm_graphmodel import Mode, Session, Vertex, Edge, StreetLine, \
    CarParking, StreetJunction, ParkAndRide, UndergroundPlatform, \
    SuburbanStation, TramStation, get_waypoints, SwitchPoint, SwitchType
from os import path
import json
import logging

logger = logging.getLogger(__name__)

MODES = {
    str(m_name): m_id
    for m_name, m_id in
    Session.query(Mode.mode_name, Mode.mode_id)
}

INV_MODES = {
    m_id: str(m_name)
    for m_name, m_id in
    Session.query(Mode.mode_name, Mode.mode_id)
}

PUBLIC_TRANSIT_MODES = {
    'underground': MODES['underground'],
    'suburban':    MODES['suburban'],
    'tram':        MODES['tram'],
    'bus':         MODES['bus']
}

SWITCH_TYPES = {
    t_name: t_id
    for t_name, t_id in
    Session.query(SwitchType.type_name, SwitchType.type_id)
}

DEFAULT_MODE_COLORS = {
    'private_car': '#26314c',
    'foot':        '#3bb2d0',
    'underground': '#006cb2',
    'suburban':    '#509552',
    'tram':        '#d03c41',
    'bus':         '#015869',
    'bicycle':     '#d07a3c'
}

SWITCH_SYMBOL = {
    'car_parking':         'parking',
    'geo_connection':      '',
    'park_and_ride':       'parking-garage',
    'underground_station': 'rail',
    'suburban_station':    'rail-light',
    'tram_station':        'rail-metro',
    'bus_station':         'bus',
    # FIXME There should be sub-types under kiss_and_ride, i.e. u-station,
    # s-station, tram-station or bus-station
    'kiss_and_ride':       ''
}
# TODO: This mapping should not be place here in the source code. It should be
# somewhere else in the persistant container like database
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
        self.properties     = {
            'type':        'path',
            'title':       '',
            'description': '',
            'mode':        INV_MODES[self.mode]
        }
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
        self.is_existent               = False
        self.planned_mode_list         = []
        self.unfolded_mode_list        = []
        self.mode_paths                = []
        self.planned_switch_type_list  = []
        self.description               = ''
        self.length                    = 0.0
        self.time                      = 0.0
        self.walking_time              = 0.0
        self.walking_length            = 0.0

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

    @property
    def switch_points(self):
        sp_list = []
        if len(self.mode_paths) < 2:
            return []
        from_vertex_id = self.mode_paths[0].vertex_id_list[-1]
        from_mode = self.mode_paths[0].mode
        for i, mp in enumerate(self.mode_paths[1:]):
            to_mode = mp.mode
            to_vertex_id = mp.vertex_id_list[0]
            if (set([from_mode, to_mode]).issubset(
                set(PUBLIC_TRANSIT_MODES.values() + [MODES['foot']]))):
                type_id = Session.query(SwitchPoint.type_id).filter(
                    SwitchPoint.from_vertex_id == from_vertex_id,
                    SwitchPoint.to_vertex_id == to_vertex_id,
                    SwitchPoint.from_mode_id == from_mode,
                    SwitchPoint.to_mode_id == to_mode).first().type_id
            else:
                type_id = self.planned_switch_type_list[i]
            ref_poi_id = Session.query(SwitchPoint.ref_poi_id).filter(
                SwitchPoint.from_vertex_id == from_vertex_id,
                SwitchPoint.to_vertex_id == to_vertex_id,
                SwitchPoint.from_mode_id == from_mode,
                SwitchPoint.to_mode_id == to_mode,
                SwitchPoint.type_id == type_id).first().ref_poi_id
            sp_list.append(self._get_switch_point_poi_info(from_mode, to_mode,
                                                           type_id, ref_poi_id))
            from_mode = to_mode
            from_vertex_id = mp.vertex_id_list[-1]
        return sp_list

    def _get_switch_point_poi_info(self, from_mode, to_mode,
                                   switch_type_id, ref_poi_id):
        logger.info("Find switch point between %s and %s, with type %s and poi id %s",
                    from_mode, to_mode, switch_type_id, ref_poi_id)
        sp_info = {
            'type': 'Feature',
            'properties': {},
            'geometry': {}
        }
        if switch_type_id == SWITCH_TYPES['car_parking']:
            logger.info("Find switch point around car parking lots")
            poi = Session.query(CarParking).filter(
                CarParking.osm_id == ref_poi_id).first()
            sp_info['properties'] = {
                "type": "switch_point",
                "switch_type": "car_parking",
                "name": poi.name
            }
        elif switch_type_id == SWITCH_TYPES['geo_connection']:
            logger.info("Find switch point around geo connections in street network")
            poi = Session.query(StreetJunction).filter(
                StreetJunction.osm_id == ref_poi_id).first()
            sp_info['properties'] = {
                "type": "switch_point",
                "switch_type": "geo_connection",
                "name": ""
            }
        elif switch_type_id == SWITCH_TYPES['park_and_ride']:
            logger.info("Find switch point around park and ride lots")
            poi = Session.query(ParkAndRide).filter(
                ParkAndRide.poi_id == ref_poi_id).first()
            sp_info['properties'] = {
                "type": "switch_point",
                "switch_type": "park_and_ride",
                "name": poi.um_name
            }
        elif (switch_type_id == SWITCH_TYPES['underground_station']) or \
            (switch_type_id == SWITCH_TYPES['kiss_and_ride'] and \
             to_mode == MODES['underground']):
            logger.info("Find switch point around underground platforms ")
            poi = Session.query(UndergroundPlatform).filter(
                UndergroundPlatform.platformid == ref_poi_id).first()
            sp_info['properties'] = {
                "type": "switch_point",
                "switch_type": "underground_station",
                "name": poi.station,
                "line": poi.line_name,
                "platform": poi.pf_name
            }
            logger.debug("Found poi: %s", poi)
        elif (switch_type_id == SWITCH_TYPES['suburban_station']) or \
            (switch_type_id == SWITCH_TYPES['kiss_and_ride'] and \
             to_mode == MODES['suburban']):
            logger.info("Find switch point around suburban stations ")
            poi = Session.query(SuburbanStation).filter(
                SuburbanStation.type_id == ref_poi_id).first()
            sp_info['properties'] = {
                "type": "switch_point",
                "switch_type": "suburban_station",
                "name": poi.um_name,
                "line": '',
                "platform": ''
            }
        elif (switch_type_id == SWITCH_TYPES['tram_station']) or \
            (switch_type_id == SWITCH_TYPES['kiss_and_ride'] and \
             to_mode == MODES['tram']):
            logger.info("Find switch point around tram stations ")
            poi = Session.query(TramStation).filter(
                TramStation.type_id == ref_poi_id).first()
            sp_info['properties'] = {
                "type": "switch_point",
                "switch_type": "tram_station",
                "name": poi.um_name,
                "line": '',
                "platform": ''
            }
            logger.debug("Found poi: %s", poi)
        else:
            logger.info("No matching switch point poi condition!")
            poi = None
            sp_info = {}
        if (not poi is None):
            geojson = json.loads(Session.scalar(st_asgeojson(poi.geom)))
            sp_info['geometry'] = geojson
        return sp_info

    def unfold_sub_paths(self):
        mode_paths = []
        for mp in self.mode_paths:
            if not mp.is_multimodal:
                mode_paths.append(mp)
            else:
                mp.expand_mode_path()
                mode_paths += mp.sub_mode_paths
                self.mode_paths = mode_paths
        self.unfolded_mode_list = [mp.mode for mp in self.mode_paths]

    def to_json(self):
        return json.dumps(self.to_dict())


    def to_dict(self):
        """
        A sample complicated GeoJSON:
        {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "properties": {
                    "stroke": "#eeffee",
                    "stroke-opacity": 0.7,
                    "stroke-width": 5
                },
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [119.2895599, 21.718679],
                        [119.2895599, 25.373809],
                        [122.61840, 25.37380917],
                        [122.61840, 21.71867980]
                    ]
                }
            }, {
                "type": "Feature",
                "properties": {
                    "title": "Hauptbahnhof",
                    "description": "Underground station, Platform 2",
                    "marker-color": "#0000ff",
                    "marker-symbol": "subway"
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [120.89355, 23.68477]
                }
            }]
        }
        """
        rd                     = {}
        rd["existence"]        = self.is_existent
        rd["summary"]          = self.description
        rd["distance"]         = self.length
        rd["duration"]         = self.time
        rd["walking_duration"] = self.walking_time
        rd["walking_distance"] = self.walking_length
        rd["switch_points"]    = self.switch_points
        rd["geojson"]          = {"type": "FeatureCollection", "features": []}
        for i, mp in enumerate(self.mode_paths):
            line_style = {
                "stroke": DEFAULT_MODE_COLORS[INV_MODES[mp.mode]],
                "stroke-opacity": 0.7,
                "stroke-width": 4
            }
            line_feature = {
                "type": "Feature",
                "properties": self._merge_dicts(mp.properties, line_style),
                "geometry": mp.to_geojson()
            }
            # Set the name of public transit lines according to the start
            # station switch point information
            if line_feature['properties']['mode'] in PUBLIC_TRANSIT_MODES.keys():
                if i > 0:
                    if 'line' in rd['geojson']['features'][-1]['properties']:
                        stationInfo = rd['geojson']['features'][-1]['properties']
                        if stationInfo['line'] != '':
                            line_feature['properties']['title'] = \
                                stationInfo['line']
                        else:
                            line_feature['properties']['title'] = \
                                line_feature['properties']['mode'] + ' line'
                    else:
                        # The previous switch_point is not a station, it might
                        # be P+R or K+R. So let's check the next switch_point
                        if 'line' in self.switch_points[i]['properties']:
                            stationInfo = self.switch_points[i]['properties']
                            if stationInfo['line'] != '':
                                line_feature['properties']['title'] = \
                                    stationInfo['line']
                            else:
                                line_feature['properties']['title'] = \
                                    line_feature['properties']['mode'] + ' line'
            rd["geojson"]["features"].append(line_feature)
            if (i < len(self.mode_paths) - 1):
                switch_point_style = {
                    "marker-size": "medium",
                    "marker-symbol": SWITCH_SYMBOL[self.switch_points[i]["properties"]["switch_type"]],
                    "title": self.switch_points[i]["properties"]["name"]
                }
                self.switch_points[i]["properties"] = self._merge_dicts(
                    switch_point_style, self.switch_points[i]["properties"])
                rd["geojson"]["features"].append(self.switch_points[i])
        return rd

    def _merge_dicts(self, x, y):
        z = x.copy()
        z.update(y)
        return z

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
