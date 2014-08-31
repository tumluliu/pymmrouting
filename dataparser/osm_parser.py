from imposm.parser import OSMParser
from math import radians, cos, sin, asin, sqrt
from termcolor import colored
import sys


class Vertex(object):

    """
    An ORM-like class mapping vertices table in database
    """

    def __init__(self):
        self.vertex_id = 0
        self.mode_id = 0
        self.lon = 0.0
        self.lat = 0.0
        self.osm_id = 0
        self.outdegree = 0
        self.first_edge = 0
        self.outgoings = []


class Edge(object):

    """
    An ORM-like class mapping edges table in database
    """

    def __init__(self):
        self.edge_id = 0
        self.from_id = 0
        self.to_id = 0
        self.osm_id = 0
        self.length = 0.0
        self.speed_factor = 0.0
        self.mode_id = 0


class ParkingLot(object):

    def __init__(self):
        self.osm_id = 0
        self.name = ''
        self.lon = 0.0
        self.lat = 0.0


class SwitchPoint(object):

    """
    An ORM-like class mapping switch_points table in database
    """
    def __init__(self):
        self.cost = 0.0
        self.is_available = True
        self.from_mode_id = 0
        self.to_mode_id = 0
        self.type_id = 0
        self.from_vertex_id = 0
        self.to_vertex_id = 0
        self.switch_point_id = 0
        self.ref_poi_id = 0


MODES = {'private_car':           11,
         'foot':                  12,
         'underground':           13,
         'suburban':              14,
         'tram':                  15,
         'bus':                   16,
         'bicycle':               17,
         'taxi':                  18,
         'public_transportation': 19}

SWITCH_TYPES = {'car_parking':         91,
                'geo_connection':      92,
                'park_and_ride':       93,
                'underground_station': 94,
                'suburban_station':    95,
                'tram_station':        96,
                'bus_station':         97,
                'kiss_and_ride':       98}


class MultimodalGraphBuilder(object):

    def __init__(self):
        self.car_road_file = open('car_roads.txt', 'w')
        self.foot_path_file = open('foot_paths.txt', 'w')
        self.bicycle_way_file = open('bicycle_ways.txt', 'w')
        self.bus_line_file = open('bus_lines.txt', 'w')
        self.tram_line_file = open('tram_lines.txt', 'w')
        self.underground_line_file = open('underground_lines.txt', 'w')
        self.suburban_line_file = open('suburban_lines.txt', 'w')
        self.nodes_file = open('nodes.txt', 'w')
        self.coords_file = open('coords.csv', 'w')
        self.vertices_file = open('vertices.csv', 'w')
        self.edges_file = open('edges.csv', 'w')
        self.switch_points_file = open('switch_points.csv', 'w')
        self.parking_lot_file = open('car_parkings.csv', 'w')
        self.parking_lot_file.write('osm_id,name,lon,lat\n')
        self.invalid_way_count = 0
        self.node_count = 0
        self.way_count = 0
        self.coords_count = 0
        self.relation_count = 0
        self.parking_lot_nodes_count = 0
        self.parking_lot_ways_count = 0
        self.car_ways_count = 0
        self.foot_ways_count = 0
        self.bicycle_ways_count = 0
        self.underground_route_count = 0
        self.tram_route_count = 0
        self.suburban_route_count = 0
        self.bus_route_count = 0
        self.bus_stop_count = 0
        self.tram_stop_count = 0
        self.subway_stop_count = 0
        self.suburban_stop_count = 0
        self.total_way_count = 0
        self.node_dict = {}
        self.coords_dict = {}
        self.vertex_dict = {}
        self.edge_dict = {}
        self.switch_point_dict = {}
        self.parking_dict = {}
        self.multimodal_ways = {}
        self.multimodal_ways['private_car'] = []
        self.multimodal_ways['foot'] = []
        self.multimodal_ways['bicycle'] = []

    def close_files(self):
        self.nodes_file.close()
        self.car_road_file.close()
        self.foot_path_file.close()
        self.bicycle_way_file.close()
        self.bus_line_file.close()
        self.tram_line_file.close()
        self.underground_line_file.close()
        self.suburban_line_file.close()
        self.nodes_file.close()
        self.coords_file.close()
        self.vertices_file.close()
        self.edges_file.close()
        self.switch_points_file.close()
        self.parking_lot_file.close()

    def coords(self, coords):
        for osmid, lon, lat in coords:
            self.coords_count += 1
            self.coords_dict[osmid] = (lon, lat)
            self.coords_file.write(str(osmid) + ',' + \
                                   str(lon) + ',' + \
                                   str(lat) + '\n')

    def nodes(self, nodes):
        for osmid, tags, pos in nodes:
            self.node_count += 1
            self.node_dict[osmid] = pos
            self.nodes_file.write(str(osmid) + '\n')
            if ('amenity' in tags) and (tags['amenity'] == 'parking'):
                parking_name = '' if 'name' not in tags else tags['name']
                parking = ParkingLot()
                parking.osm_id = osmid
                parking.name = parking_name.replace(',', ';')
                parking.lon = pos[0]
                parking.lat = pos[1]
                self.parking_dict[osmid] = parking
                self.parking_lot_file.write(str(osmid) + ',' + \
                                            parking.name.encode('utf-8') + ',' +\
                                            str(pos[0]) + ',' + \
                                            str(pos[1]) + '\n')

                self.parking_lot_nodes_count += 1

    def ways(self, ways):
        for osmid, tags, refs in ways:
            if 'highway' in tags:
                self.way_count += 1
                highway = tags['highway']
                access = {}
                access['bicycle'] = highway in BICYCLE_WAY_TAGS
                access['car'] = highway in CAR_WAY_TAGS
                access['foot'] = access['bicycle'] or highway in FOOT_WAY_TAGS
                if access['bicycle']:
                    self.multimodal_ways['bicycle'].append((osmid, tags, refs))
                if access['car']:
                    self.multimodal_ways['private_car'].append((osmid, tags, refs))
                if access['foot']:
                    self.multimodal_ways['foot'].append((osmid, tags, refs))
                            # if 'amenity' in tags:
                # if tags['amenity'] == 'parking':
                    # print 'osmid: ' + str(osmid)
                    # print tags
                    # self.parking_lot_ways_count += 1

    def build_mode_graph(self, mode):
        total = len(self.multimodal_ways[mode])
        progress = 0
        for osmid, tags, refs in self.multimodal_ways[mode]:
            progress += 1
            sys.stdout.write("\r%4.1f%%" % (float(progress) / float(total) * 100.0))
            sys.stdout.flush()
            if self.validate_way(osmid, tags, refs):
                self.invalid_way_count += 1
                print 'invalid way: ' + str(osmid)
            else:
                way_length = self.calc_way_length(refs)
                oneway = False
                if ('oneway' in tags) and (tags['oneway'] == 'yes'):
                    oneway = True
                avg_speed_factor = 0.005
                if mode == 'bicycle':
                    # the average speed of bicycle is assumed to 15 km/h
                    avg_speed_factor = 1 / (15 * 1000.0 / 60)
                if mode == 'private_car':
                    maxspeed = 30
                    if ('maxspeed' in tags) and is_number(tags['maxspeed']):
                        maxspeed = int(tags['maxspeed'])
                    # this is a magic number indicating the average speed
                    # compared with the maxspeed
                    exp_ratio = 0.618
                    avg_speed_factor = 1 / \
                        (maxspeed * exp_ratio * 1000 / 60)
                if mode == 'foot':
                    # the average speed of pedestrian is assumed to 4.5
                    # km/h
                    avg_speed_factor = 1 / (4.5 * 1000.0 / 60)
                self.add_edge(osmid, MODES[mode], refs, way_length,
                              avg_speed_factor, oneway)

    def build_switch_points(self, from_mode, to_mode, switch_type):
        if (from_mode == 'private_car') and (to_mode == 'foot') and \
                (switch_type == 'car_parking'):
            for p in self.parking_dict:
                print "Searching for the nearest vertex pair for parking lot " + str(p)
                from_vertex = self.find_nearest_vertex(self.parking_dict[p], 'private_car')
                print "Found vertex in car driving network: " + str(from_vertex.vertex_id)
                to_vertex = self.find_nearest_vertex(self.parking_dict[p], 'foot')
                print "Found vertex in pedestrian network: " + str(to_vertex.vertex_id)
                sp = SwitchPoint()
                sp.cost = 3.0
                sp.from_mode_id = MODES['private_car']
                sp.to_mode_id = MODES['foot']
                sp.from_vertex_id = from_vertex.vertex_id
                sp.to_vertex_id = to_vertex.vertex_id
                sp.ref_poi_id = self.parking_dict[p].osm_id
                sp.type_id = SWITCH_TYPES['car_parking']
                sp.switch_point_id = int(str(sp.type_id) + str(sp.ref_poi_id))
                sp.is_available = 't'
                self.switch_point_dict[sp.switch_point_id] = sp
                print "Switch point numbers: " + str(len(self.switch_point_dict))

    def find_nearest_vertex(self, poi, mode):
        min_distance = float('inf')
        nearest_vertex = None
        vertex_counter = 0

        for v in self.vertex_dict:
            vertex_counter += 1
            #print "vertex dict traversing progress: %d / %d" % \
                  #(vertex_counter, len(self.vertex_dict))
            if self.vertex_dict[v].mode_id == MODES[mode]:
                distance = calc_distance(poi.lon, poi.lat,
                                         self.vertex_dict[v].lon,
                                         self.vertex_dict[v].lat)
                #print "distance between poi " + str(poi.osm_id) + \
                    #" and vertex " + str(self.vertex_dict[v].vertex_id) + \
                    #" is " + str(distance)
                #print "min distance is " + str(min_distance)
                if distance < min_distance:
                    min_distance = distance
                    nearest_vertex = self.vertex_dict[v]
        return nearest_vertex

    def refine_graph(self):
        for v in self.vertex_dict:
            if self.vertex_dict[v].outdegree > 1:
                edges_to_remove = []
                # push the first edge digest in the dict
                outgoings_digest_dict = {self.vertex_dict[v].outgoings[0].to_id:
                                         self.vertex_dict[v].outgoings[0]}
                for e in self.vertex_dict[v].outgoings[1:]:
                    if e.to_id in outgoings_digest_dict:
                        # found hyper edge
                        self.vertex_dict[v].outdegree -= 1
                        if outgoings_digest_dict[e.to_id].length > e.length:
                            edges_to_remove.append(outgoings_digest_dict[e.to_id])
                        else:
                            edges_to_remove.append(e)
            for e in edges_to_remove:
                # remove the duplicated longer edge
                self.vertex_dict[v].outgoings.remove(e)
                del self.edge_dict[e.edge_id]

    def validate_graph(self):
        invalid_vertex_count = 0
        for v in self.vertex_dict:
            if self.vertex_dict[v].outdegree != \
               len(self.vertex_dict[v].outgoings):
                print 'invalid vertex found! vertex_id is ' + str(v)
                print 'claimed outdegree is ' + str(self.vertex_dict[v].outdegree)
                print 'real outdegree is ' + str(len(self.vertex_dict[v].outgoings))
                invalid_vertex_count += 1
            to_vertex_list = []
            for e in self.vertex_dict[v].outgoings:
                to_vertex_list.append(e.to_id)
            if len(to_vertex_list) != len(set(to_vertex_list)):
                print 'invalid vertex with hyper-edge found! vertex_id is ' + str(v)
                invalid_vertex_count += 1
        if invalid_vertex_count > 0:
            print 'found ' + str(invalid_vertex_count) + ' invalid vertices!'
            return False
        return True

    def write_graph(self):
        self.vertices_file.write('outdegree,vertex_id,osm_id,mode_id,lon,lat\n')
        for v in self.vertex_dict:
            self.vertices_file.write(str(self.vertex_dict[v].outdegree) + ',' +\
                                     str(self.vertex_dict[v].vertex_id) + ',' +\
                                     str(self.vertex_dict[v].osm_id) + ',' +\
                                     str(self.vertex_dict[v].mode_id) + ',' +\
                                     str(self.vertex_dict[v].lon) + ',' +\
                                     str(self.vertex_dict[v].lat) + '\n')

        self.edges_file.write(
            'length,speed_factor,mode_id,from_id,to_id,edge_id,osm_id\n')
        for e in self.edge_dict:
            self.edges_file.write(str(self.edge_dict[e].length) + ',' +\
                                  str(self.edge_dict[e].speed_factor) + ',' +\
                                  str(self.edge_dict[e].mode_id) + ',' +\
                                  str(self.edge_dict[e].from_id) + ',' +\
                                  str(self.edge_dict[e].to_id) + ',' +\
                                  str(self.edge_dict[e].edge_id) + ',' +\
                                  str(self.edge_dict[e].osm_id) + '\n')

# cost | is_available | from_mode_id | to_mode_id | type_id | from_vertex_id | to_vertex_id | switch_point_id | ref_poi_id
        self.switch_points_file.write(
            'cost,is_available,from_mode_id,to_mode_id,type_id,from_vertex_id,to_vertex_id,switch_point_id,ref_poi_id\n')
        for sp in self.switch_point_dict:
            self.switch_points_file.write(str(self.switch_point_dict[sp].cost) + ',' +\
                                          str(self.switch_point_dict[sp].is_available) + ',' +\
                                          str(self.switch_point_dict[sp].from_mode_id) + ',' +\
                                          str(self.switch_point_dict[sp].to_mode_id) + ',' +\
                                          str(self.switch_point_dict[sp].type_id) + ',' +\
                                          str(self.switch_point_dict[sp].from_vertex_id) + ',' +\
                                          str(self.switch_point_dict[sp].to_vertex_id) + ',' +\
                                          str(self.switch_point_dict[sp].switch_point_id) + ',' +\
                                          str(self.switch_point_dict[sp].ref_poi_id) + '\n')


    def add_edge(self, osm_id, mode_id, way_node_list, way_length,
                 avg_speed_factor, oneway):
        forward_edge = Edge()
        forward_edge.osm_id = osm_id
        forward_edge.edge_id = int(str(mode_id) + str(osm_id) + '00')
        from_vertex_id = int(str(mode_id) + str(way_node_list[0]))
        forward_edge.from_id = from_vertex_id
        to_vertex_id = int(str(mode_id) + str(way_node_list[-1]))
        forward_edge.to_id = to_vertex_id
        forward_edge.length = way_length
        forward_edge.mode_id = mode_id
        forward_edge.speed_factor = avg_speed_factor
        self.edge_dict[forward_edge.edge_id] = forward_edge
        if from_vertex_id in self.vertex_dict:
            self.vertex_dict[from_vertex_id].outdegree += 1
            self.vertex_dict[from_vertex_id].outgoings.append(forward_edge)
        else:
            from_vertex = Vertex()
            from_vertex.vertex_id = from_vertex_id
            from_vertex.osm_id = way_node_list[0]
            from_vertex.mode_id = mode_id
            from_vertex.outdegree = 1
            from_vertex.outgoings.append(forward_edge)
            from_vertex.lon = self.coords_dict[way_node_list[0]][0]
            from_vertex.lat = self.coords_dict[way_node_list[0]][1]
            self.vertex_dict[from_vertex_id] = from_vertex
        if to_vertex_id not in self.vertex_dict:
            to_vertex = Vertex()
            to_vertex.vertex_id = to_vertex_id
            to_vertex.osm_id = way_node_list[-1]
            to_vertex.mode_id = mode_id
            to_vertex.lon = self.coords_dict[way_node_list[-1]][0]
            to_vertex.lat = self.coords_dict[way_node_list[-1]][1]
            self.vertex_dict[to_vertex_id] = to_vertex
        if not oneway:
            backward_edge = Edge()
            backward_edge.edge_id = forward_edge.edge_id + 1
            backward_edge.osm_id = osm_id
            backward_edge.from_id = to_vertex_id
            backward_edge.to_id = from_vertex_id
            backward_edge.mode_id = mode_id
            backward_edge.length = way_length
            backward_edge.speed_factor = avg_speed_factor
            self.edge_dict[backward_edge.edge_id] = backward_edge
            self.vertex_dict[to_vertex_id].outdegree += 1
            self.vertex_dict[to_vertex_id].outgoings.append(backward_edge)

    def validate_way(self, osm_id, tags, refs):
        if refs[0] == refs[-1]:
            # print 'this is a cyclic way'
            return False
        for n in refs:
            if n not in self.coords_dict:
                # print str(n) + ' not exist in nodes'
                return False

        # THIS IS DAMM SLOW!!
        #for e in self.edge_dict:
            #if (self.edge_dict[e].from_id == refs[0]) and \
                    #(self.edge_dict[e].to_id == refs[-1]):
                ## an edge is already there between the same vertex pair
                ## print 'hypergraph is not supported, i.e. one directed vertex
                ## pair identifies only one directed edge'
                #return False

    def calc_way_length(self, refs):
        prev_node = self.coords_dict[int(refs[0])]
        way_length = 0.0
        for nd in refs[1:]:
            int_nd = int(nd)
            way_length += calc_distance(prev_node[0], prev_node[1],
                                        self.coords_dict[int_nd][0],
                                        self.coords_dict[int_nd][1])
            prev_node = self.coords_dict[int_nd]
        return way_length

    def relations(self, relations):
        for osmid, tags, members in relations:
            self.relation_count += 1
            # if ('type' in tags) and (tags['type'] == 'route'):
                # if ('route' in tags) and (tags['route'] == 'tram'):
                    # self.tram_route_count += 1
                    # self.tram_line_file.write(str(osmid) + '\n')
                    # self.tram_line_file.write(str(tags) + '\n')
                    # self.tram_line_file.write(str(members) + '\n')
                    # for m in members:
                        # if m[2] == 'stop':
                            # self.tram_stop_count += 1
                # if ('route' in tags) and (tags['route'] == 'bus'):
                    # self.bus_route_count += 1
                    # self.bus_line_file.write(str(osmid) + '\n')
                    # self.bus_line_file.write(str(tags) + '\n')
                    # self.bus_line_file.write(str(members) + '\n')
                    # for m in members:
                        # if m[2] == 'stop':
                            # self.bus_stop_count += 1
                # if ('route' in tags) and (tags['route'] == 'subway'):
                    # self.underground_route_count += 1
                    # self.underground_line_file.write(str(osmid) + '\n')
                    # self.underground_line_file.write(str(tags) + '\n')
                    # self.underground_line_file.write(str(members) + '\n')
                    # for m in members:
                        # if m[2] == 'stop':
                            # self.subway_stop_count += 1
                # if ('route' in tags) and (tags['route'] == 'light_rail'):
                    # self.suburban_route_count += 1
                    # self.suburban_line_file.write(str(osmid) + '\n')
                    # self.suburban_line_file.write(str(tags) + '\n')
                    # self.suburban_line_file.write(str(members) + '\n')
                    # for m in members:
                        # if m[2] == 'stop':
                            # self.suburban_stop_count += 1
BICYCLE_WAY_TAGS = (
    'primary',
    'secondary',
    'tertiary',
    'unclassified',
    'minor',
    'cycleway',
    'residential',
    'track',
    'service')

CAR_WAY_TAGS = (
    'motorway',
    'trunk',
    'primary',
    'secondary',
    'tertiary',
    'unclassified',
    'minor',
    'residential',
    'service')

FOOT_WAY_TAGS = (
    'footway',
    'steps')


def calc_distance(x1, y1, x2, y2):
    # Code coppied form:
    # http://stackoverflow.com/questions/4913349/haversine-formula-in-python-bearing-and-distance-between-two-gps-points
    """
      Calculate the great circle distance between two points
      on the earth (specified in decimal degrees)
    """
    # convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(radians, [x1, y1, x2, y2])

    # haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))

    # 6367 km is the radius of the Earth
    km = 6367 * c
    return km * 1000.0

def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False

builder = MultimodalGraphBuilder()
p = OSMParser(concurrency=2, coords_callback=builder.coords,
              nodes_callback=builder.nodes, ways_callback=builder.ways,
              relations_callback=builder.relations)
p.parse('/Users/user/Research/data/OSM/munich.osm.pbf')
print 'Start building foot network... ',
builder.build_mode_graph('foot')
print ' done!',
print 'Start building car network... ',
builder.build_mode_graph('private_car')
print ' done!',
print 'Start building bicycle network... ',
builder.build_mode_graph('bicycle')
print ' done!',
if builder.validate_graph():
    #builder.build_switch_points('private_car', 'foot', 'car_parking')
    builder.write_graph()

    print 'node count: ' + str(builder.node_count)
    print 'coords count: ' + str(builder.coords_count)
    print 'way count: ' + str(builder.way_count)
    print 'relation count: ' + str(builder.relation_count)
    print 'vertex count: ' + str(len(builder.vertex_dict))
    print 'edge count: ' + str(len(builder.edge_dict))
    print 'parking lot in nodes: ' + str(builder.parking_lot_nodes_count)
    # print 'parking lot in ways: ' + str(builder.parking_lot_ways_count)
    # print 'bus stops in nodes: ' + str(builder.bus_stop_count)
    # print 'tram stops in nodes: ' + str(builder.tram_stop_count)
    # print 'subway stops in nodes: ' + str(builder.subway_stop_count)
    # print 'suburban stops in nodes: ' + str(builder.suburban_stop_count)
    # print 'total non-area ways in ways: ' + str(builder.total_way_count)
    print 'car road segments in ways: ' + str(builder.car_ways_count)
    print 'foot path segments in ways: ' + str(builder.foot_ways_count)
    print 'bicycle way segments in ways: ' + str(builder.bicycle_ways_count)
    print 'invalid ways: ' + str(builder.invalid_way_count)
    # print 'suburban routes in relations: ' + str(builder.suburban_route_count)
    # print 'underground routes in relations: ' + str(builder.underground_route_count)
    # print 'bus routes in relations: ' + str(builder.bus_route_count)
    # print 'tram routes in relations: ' + str(builder.tram_route_count)
else:
    print colored('[FATAL] built graph has invalid members', 'red')

builder.close_files()

