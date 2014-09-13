"""
ORM definitions for mapping multimodal graph data stored in PostgreSQL database
"""

from sqlalchemy import create_engine, Column, \
    Integer, BigInteger, Float, Boolean, String
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.ext.declarative import declarative_base
from geoalchemy2 import Geometry
from geoalchemy2.functions import ST_AsGeoJSON as st_asgeojson
import json

engine = create_engine('postgresql://liulu:workhard@localhost/mmrp_munich')
Base = declarative_base(bind=engine)
Session = scoped_session(sessionmaker(engine))


class Edge(Base):
    """
    length double precision,
    speed_factor double precision,
    mode_id integer NOT NULL,
    from_id bigint NOT NULL,
    to_id bigint NOT NULL,
    edge_id bigint NOT NULL,
    osm_id bigint NOT NULL,
    CONSTRAINT edges_pkey PRIMARY KEY (edge_id)
    """
    __tablename__ = 'edges'
    length = Column(Float)
    speed_factor = Column(Float)
    mode_id = Column(Integer, nullable=False)
    from_id = Column(BigInteger, nullable=False)
    to_id = Column(BigInteger, nullable=False)
    edge_id = Column(BigInteger, primary_key=True)
    osm_id = Column(BigInteger, nullable=False)

    def __repr__(self):
        return '%s(%r, %r, %r, %r, %r, %r, %r)' % \
            (self.__class__.__name__,
             self.mode_id,
             self.edge_id,
             self.from_id,
             self.to_id,
             self.length,
             self.speed_factor,
             self.osm_id)


class Vertex(Base):
    """
    out_degree integer,
    vertex_id bigint NOT NULL,
    osm_id bigint NOT NULL,
    mode_id integer NOT NULL,
    lon double precision,
    lat double precision,
    CONSTRAINT vertices_pkey PRIMARY KEY (vertex_id)
    """
    __tablename__ = 'vertices'
    out_degree = Column(Integer)
    vertex_id = Column(BigInteger, primary_key=True)
    osm_id = Column(BigInteger, nullable=False)
    mode_id = Column(Integer, nullable=False)
    lon = Column(Float)
    lat = Column(Float)

    def __repr__(self):
        return '%s(%r, %r, %r, %r, %r, %r)' % \
            (self.__class__.__name__,
             self.mode_id,
             self.vertex_id,
             self.lon,
             self.lat,
             self.out_degree,
             self.osm_id)


class SwitchPoint(Base):
    """
    cost double precision,
    is_available boolean,
    from_mode_id integer NOT NULL,
    to_mode_id integer NOT NULL,
    type_id integer NOT NULL,
    from_vertex_id bigint NOT NULL,
    to_vertex_id bigint NOT NULL,
    switch_point_id bigint NOT NULL,
    ref_poi_id bigint,
    CONSTRAINT switch_points_pkey PRIMARY KEY (switch_point_id)
    """
    __tablename__ = 'switch_points'
    cost = Column(Float)
    is_available = Column(Boolean)
    from_mode_id = Column(Integer, nullable=False)
    to_mode_id = Column(Integer, nullable=False)
    type_id = Column(Integer, nullable=False)
    from_vertex_id = Column(BigInteger, nullable=False)
    to_vertex_id = Column(BigInteger, nullable=False)
    switch_point_id = Column(BigInteger, primary_key=True)
    ref_poi_id = Column(BigInteger)

    def __repr__(self):
        return '%s(%r, %r, %r, %r, %r, %r, %r, %r, %r)' % \
            (self.__class__.__name__,
             self.switch_point_id,
             self.from_mode_id,
             self.to_mode_id,
             self.from_vertex_id,
             self.to_vertex_id,
             self.type_id,
             self.is_available,
             self.cost,
             self.ref_poi_id)


class SwitchType(Base):
    """
    type_name character varying(255),
    type_id integer NOT NULL,
    CONSTRAINT switch_types_pkey PRIMARY KEY (type_id)
    """
    __tablename__ = 'switch_types'
    type_name = Column(String(255))
    type_id = Column(Integer, primary_key=True)

    def __repr__(self):
        return '%s(%r, %r)' % \
            (self.__class__.__name__, self.type_name, self.type_id)


class Mode(Base):
    """
    mode_name character varying(255),
    mode_id integer NOT NULL,
    CONSTRAINT modes_pkey PRIMARY KEY (mode_id)
    """
    __tablename__ = 'modes'
    mode_name = Column(String(255))
    mode_id = Column(Integer, primary_key=True)

    def __repr__(self):
        return '%s(%r, %r)' % \
            (self.__class__.__name__, self.mode_name, self.mode_id)


class OSMLine(Base):
    """
    mapping of munich_osm_line
    """
    __tablename__ = 'munich_osm_line'
    osm_id = Column(BigInteger, primary_key=True)
    amenity = Column(String)
    highway = Column(String)
    name = Column(String)
    oneway = Column(String)
    way = Column(Geometry(geometry_type='LINESTRING', srid=900913))

    def __repr__(self):
        return '%s(%r, %r, %r, %r, %r)' % \
            (self.__class__.__name__,
             self.osm_id,
             self.amenity,
             self.highway,
             self.name,
             self.oneway)


class OSMPoint(Base):
    """
    mapping of munich_osm_point
    """
    __tablename__ = 'munich_osm_point'
    osm_id = Column(BigInteger, primary_key=True)
    amenity = Column(String)
    name = Column(String)
    way = Column(Geometry(geometry_type='POINT', srid=900913))

    def __repr__(self):
        return '%s(%r, %r, %r)' % \
            (self.__class__.__name__,
             self.osm_id,
             self.amenity,
             self.name)

def get_waypoints(way_geom):
    geom_json = json.loads(Session.scalar(st_asgeojson(way_geom)))
    # print geom_json['coordinates']
    return geom_json['coordinates']

# session = Session()
# query = session.query(Edge)
# e = query.filter(Edge.from_id == 121706196500,
#                  Edge.to_id == 121955202).first()
# print e.osm_id
