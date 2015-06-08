"""
ORM definitions for mapping multimodal graph data stored in PostgreSQL database

"""

from sqlalchemy import create_engine, Column, BigInteger, String
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.engine.url import URL
from geoalchemy2 import Geometry
from geoalchemy2.functions import ST_AsGeoJSON as st_asgeojson
from .settings import PG_DB_CONF
import json
import logging

logger = logging.getLogger(__name__)

engine = create_engine(URL(**PG_DB_CONF))
Base = declarative_base(bind=engine)
Session = scoped_session(sessionmaker(engine))


class CarParking(Base):
    """ mapping of existing table car_parkings
    Columns:
        id         integer NOT NULL,
        link_id    integer,
        poi_id     integer,
        fac_type   integer,
        poi_name   character varying(255),
        poi_langcd character varying(255),
        poi_nmtype character varying(255),
        poi_st_num character varying(255),
        st_name    character varying(255),
        st_langcd  character varying(255),
        poi_st_sd  character varying(255),
        acc_type   character varying(255),
        ph_number  character varying(255),
        chain_id   integer,
        nat_import character varying(255),
        private    character varying(255),
        in_vicin   character varying(255),
        num_parent integer,
        num_child  integer,
        percfrref  integer,
        van_city   character varying(255),
        act_addr   character varying(255),
        act_st_nam character varying(255),
        act_st_num character varying(255),
        act_admin  character varying(255),
        act_postal character varying(255),
        um_id      double precision,
        geom   geometry,
    """
    __tablename__ = 'car_parkings'
    osm_id = Column(BigInteger, primary_key=True)
    name = Column(String)
    geom = Column(Geometry(geometry_type='POINT', srid=4326))


class ParkAndRide(Base):
    """ mapping of existing table park_and_rides
    Columns:
        id         integer NOT NULL,
        link_id    integer,
        poi_id     integer,
        fac_type   integer,
        poi_name   character varying(255),
        poi_langcd character varying(255),
        poi_nmtype character varying(255),
        poi_st_num character varying(255),
        st_name    character varying(255),
        st_langcd  character varying(255),
        poi_st_sd  character varying(255),
        acc_type   character varying(255),
        ph_number  character varying(255),
        chain_id   integer,
        nat_import character varying(255),
        private    character varying(255),
        in_vicin   character varying(255),
        num_parent integer,
        num_child  integer,
        percfrref  integer,
        van_city   character varying(255),
        act_addr   character varying(255),
        act_st_nam character varying(255),
        act_st_num character varying(255),
        act_admin  character varying(255),
        act_postal character varying(255),
        um_id      double precision,
        um_name    character varying(255),
        um_cat     character varying(255),
        um_type    integer,
        nvt_region character varying(255),
        geom   geometry,
    """
    __tablename__ = 'park_and_rides'
    __table_args__ = {'autoload': True}


class SuburbanJunction(Base):
    """ mapping of existing table suburban_junctions
    Columns:
        id       integer NOT NULL,
        x        double precision,
        y        double precision,
        nodeid   integer,
        valence  integer,
        geom geometry,
    """
    __tablename__ = 'suburban_junctions'
    __table_args__ = {'autoload': True}


class SuburbanLine(Base):
    """ mapping of existing table suburban_lines
    Columns:
        id         integer NOT NULL,
        um_id      double precision,
        um_name    character varying(255),
        um_type    integer,
        timespan   integer,
        label      character varying(255),
        ob         character varying(255),
        oba        integer,
        bkt        integer,
        tr_type    character varying(255),
        et_fnode   double precision,
        et_tnode   double precision,
        shape_leng double precision,
        enabled    integer,
        fnodeid    integer,
        tnodeid    integer,
        overlapobj integer,
        snodesobj  integer,
        zerofeat   integer,
        geom   geometry,
    """
    __tablename__ = 'suburban_lines'
    __table_args__ = {'autoload': True}


class SuburbanStation(Base):
    """ mapping of existing table suburban_stations
    Columns:
        id       integer NOT NULL DEFAULT,
        um_id    double precision,
        um_name  character varying(255),
        um_type  integer,
        tr_type  character varying(255),
        link_id  integer,
        fac_type integer,
        ob       character varying(255),
        oba      integer,
        bfk      integer,
        type_id  integer,
        geom geometry,
    """
    __tablename__ = 'suburban_stations'
    __table_args__ = {'autoload': True}


class TramJuction(Base):
    """ mapping of existing table tram_junctions
    Columns:
        id       integer NOT NULL,
        x        double precision,
        y        double precision,
        nodeid   integer,
        valence  integer,
        geom geometry,
    """
    __tablename__ = 'tram_junctions'
    __table_args__ = {'autoload': True}


class TramLine(Base):
    """ mapping of existing table tram_lines
    Columns:
        id         integer NOT NULL,
        um_id      double precision,
        um_name    character varying(255),
        um_type    integer,
        timespan   integer,
        label      character varying(255),
        ob         character varying(255),
        oba        integer,
        bkt        integer,
        tr_type    character varying(255),
        et_fnode   double precision,
        et_tnode   double precision,
        shape_leng double precision,
        enabled    integer,
        fnodeid    integer,
        tnodeid    integer,
        overlapobj integer,
        snodesobj  integer,
        zerofeat   integer,
        geom   geometry,
    """
    __tablename__ = 'tram_lines'
    __table_args__ = {'autoload': True}


class TramStation(Base):
    """ mapping of existing table tram_stations
    Columns:
        id       integer NOT NULL,
        um_id    double precision,
        um_name  character varying(255),
        um_type  integer,
        tr_type  character varying(255),
        link_id  integer,
        fac_type integer,
        ob       character varying(255),
        oba      integer,
        bfk      integer,
        type_id  integer,
        geom geometry,
    """
    __tablename__ = 'tram_stations'
    __table_args__ = {'autoload': True}


class UndergroundPlatform(Base):
    __tablename__ = 'underground_platforms'
    __table_args__ = {'autoload': True}


class UndergroundJunction(Base):
    """ mapping of existing table underground_junctions
    Columns:
        id       integer NOT NULL,
        x        double precision,
        y        double precision,
        nodeid   integer,
        valence  integer,
        geom geometry,
    """
    __tablename__ = 'underground_junctions'
    __table_args__ = {'autoload': True}


class UndergroundLine(Base):
    """ mapping of existing table underground_lines
    Columns:
        id         integer NOT NULL,
        um_id      double precision,
        um_name    character varying(255),
        um_type    integer,
        timespan   integer,
        label      character varying(255),
        ob         character varying(255),
        oba        integer,
        bkt        integer,
        tr_type    character varying(255),
        et_fnode   double precision,
        et_tnode   double precision,
        shape_leng double precision,
        enabled    integer,
        fnodeid    integer,
        tnodeid    integer,
        overlapobj integer,
        snodesobj  integer,
        zerofeat   integer,
        geom   geometry,
    """
    __tablename__ = 'underground_lines'
    __table_args__ = {'autoload': True}


class UndergroundStation(Base):
    """ mapping of existing table underground_stations
    Columns:
        id       integer NOT NULL,
        um_id    double precision,
        um_name  character varying(255),
        um_type  integer,
        tr_type  character varying(255),
        link_id  integer,
        fac_type integer,
        ob       character varying(255),
        oba      integer,
        bfk      integer,
        type_id  integer,
        geom geometry,
    """
    __tablename__ = 'underground_stations'
    __table_args__ = {'autoload': True}


class Edge(Base):
    """ mapping of existing table edges
    Columns:
        id           integer NOT NULL,
        length       double precision,
        speed_factor double precision,
        created_at   timestamp without time zone,
        updated_at   timestamp without time zone,
        mode_id      integer NOT NULL,
        from_id      bigint NOT NULL,
        to_id        bigint NOT NULL,
        edge_id      bigint NOT NULL,
    """
    __tablename__ = 'edges'
    __table_args__ = {'autoload': True}


class Vertex(Base):
    """ mapping of table vertices
        id         integer NOT NULL,
        out_degree integer,
        created_at timestamp without time zone,
        updated_at timestamp without time zone,
        first_edge double precision,
        vertex_id  bigint NOT NULL,
        mode_id    integer NOT NULL,
        x          double precision,
        y          double precision,
    """
    __tablename__ = 'vertices'
    __table_args__ = {'autoload': True}


class SwitchPoint(Base):
    """ mapping of existing table switch_points
    Columns:
        id              integer NOT NULL,
        cost            double precision,
        is_available    boolean,
        created_at      timestamp without time zone,
        updated_at      timestamp without time zone,
        from_mode_id    integer NOT NULL,
        to_mode_id      integer NOT NULL,
        type_id         integer NOT NULL,
        from_vertex_id  bigint NOT NULL,
        to_vertex_id    bigint NOT NULL,
        switch_point_id bigint,
        ref_poi_id      bigint,
    """
    __tablename__ = 'switch_points'
    __table_args__ = {'autoload': True}


class SwitchType(Base):
    """ mapping of existing table switch_types
    Columns:
        id         integer NOT NULL,
        type_name  character varying(255),
        created_at timestamp without time zone,
        updated_at timestamp without time zone,
        type_id    integer NOT NULL,
    """
    __tablename__ = 'switch_types'
    __table_args__ = {'autoload': True}


class Mode(Base):
    """ mapping of existing table modes
    Columns:
        id         integer NOT NULL,
        mode_name  character varying(255),
        created_at timestamp without time zone,
        updated_at timestamp without time zone,
        mode_id    integer NOT NULL,
    """
    __tablename__ = 'modes'
    __table_args__ = {'autoload': True}


class OSMLine(Base):
    """ mapping of existing table osm_line
    Columns:
        gid                  integer,serial,primary key,
        osm_id               bigint,
        access               text,
        "addr:housename"     text,
        "addr:housenumber"   text,
        "addr:interpolation" text,
        admin_level          text,
        aerialway            text,
        aeroway              text,
        amenity              text,
        area                 text,
        barrier              text,
        bicycle              text,
        brand                text,
        bridge               text,
        boundary             text,
        building             text,
        construction         text,
        covered              text,
        culvert              text,
        cutting              text,
        denomination         text,
        disused              text,
        embankment           text,
        foot                 text,
        "generator:source"   text,
        harbour              text,
        highway              text,
        historic             text,
        horse                text,
        intermittent         text,
        junction             text,
        landuse              text,
        layer                text,
        leisure              text,
        lock                 text,
        man_made             text,
        military             text,
        motorcar             text,
        name                 text,
        "natural"            text,
        office               text,
        oneway               text,
        operator             text,
        place                text,
        population           text,
        power                text,
        power_source         text,
        public_transport     text,
        railway              text,
        ref                  text,
        religion             text,
        route                text,
        service              text,
        shop                 text,
        sport                text,
        surface              text,
        toll                 text,
        tourism              text,
        "tower:type"         text,
        tracktype            text,
        tunnel               text,
        water                text,
        waterway             text,
        wetland              text,
        width                text,
        wood                 text,
        z_order              integer,
        way_area             real,
        way                  geometry(LineString,4326)
        """
    __tablename__ = 'osm_line'
    osm_id = Column(BigInteger, primary_key=True)
    amenity = Column(String)
    highway = Column(String)
    name = Column(String)
    #oneway = Column(String)
    way = Column(Geometry(geometry_type='LINESTRING', srid=4326))
    #__table_args__ = (PrimaryKeyConstraint('gid', 'osm_id'), {'autoload':True})
    #__mapper_args__ = {
        #'include_properties' :['osm_id', 'amenity', 'highway', 'name', 'oneway',
                               #'way']
    #}

class OSMPoint(Base):
    """ mapping of osm_point
    Columns:
        gid                  integer,serial,primary key,
        osm_id               bigint,
        access               text,
        "addr:housename"     text,
        "addr:housenumber"   text,
        "addr:interpolation" text,
        admin_level          text,
        aerialway            text,
        aeroway              text,
        amenity              text,
        area                 text,
        barrier              text,
        bicycle              text,
        brand                text,
        bridge               text,
        boundary             text,
        building             text,
        capital              text,
        construction         text,
        covered              text,
        culvert              text,
        cutting              text,
        denomination         text,
        disused              text,
        ele                  text,
        embankment           text,
        foot                 text,
        "generator:source"   text,
        harbour              text,
        highway              text,
        historic             text,
        horse                text,
        intermittent         text,
        junction             text,
        landuse              text,
        layer                text,
        leisure              text,
        lock                 text,
        man_made             text,
        military             text,
        motorcar             text,
        name                 text,
        "natural"            text,
        office               text,
        oneway               text,
        operator             text,
        place                text,
        poi                  text,
        population           text,
        power                text,
        power_source         text,
        public_transport     text,
        railway              text,
        ref                  text,
        religion             text,
        route                text,
        service              text,
        shop                 text,
        sport                text,
        surface              text,
        toll                 text,
        tourism              text,
        "tower:type"         text,
        tunnel               text,
        water                text,
        waterway             text,
        wetland              text,
        width                text,
        wood                 text,
        z_order              integer,
        way                  geometry(Point,4326)
    NOTE:
        to find the nearest neighbor with this class, the right way should
        be like this:
        Session.query(StreetJunction).
        order_by(StreetJunction.way.distance_box('POINT(0 0)')).limit(10)
    """
    __tablename__ = 'osm_point'
    osm_id = Column(BigInteger, primary_key=True)
    amenity = Column(String)
    name = Column(String)
    way = Column(Geometry(geometry_type='POINT', srid=4326))
    #__table_args__ = (PrimaryKeyConstraint('gid'), {'autoload':True})
    #__mapper_args__ = {'include_properties' :['osm_id', 'way']}

class StreetLine(Base):
    __tablename__ = 'street_lines'
    link_id = Column(BigInteger, primary_key=True)
    osm_id = Column(BigInteger)
    from_node = Column(BigInteger)
    to_node = Column(BigInteger)
    geom = Column(Geometry(geometry_type='LINESTRING', srid=4326))

class StreetJunction(Base):
    __tablename__ = 'street_junctions'
    osm_id = Column(BigInteger, primary_key=True)
    geom = Column(Geometry(geometry_type='POINT', srid=4326))

def get_waypoints(way_geom):
    geom_json = json.loads(Session.scalar(st_asgeojson(way_geom)))
    coord_list = []
    if geom_json['type'].upper() == 'LINESTRING':
        coord_list = geom_json['coordinates']
    elif geom_json['type'].upper() == 'MULTILINESTRING':
        coord_list = [j for i in geom_json['coordinates'] for j in i]
        logger.debug("Get way points in GeoJSON: %s", geom_json)
    return coord_list
