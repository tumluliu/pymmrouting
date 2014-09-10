#!/bin/bash

rm *.txt
rm vertices.csv
rm edges.csv
rm car_parkings.csv
python osm_parser.py
psql -c "TRUNCATE vertices,edges,car_parkings;" -d mmrp_munich_osm -U liulu
psql -c "\COPY vertices FROM './vertices.csv' WITH CSV HEADER;" -d mmrp_munich_osm -U liulu
psql -c "\COPY edges FROM './edges.csv' WITH CSV HEADER;" -d mmrp_munich_osm -U liulu
psql -c "\COPY switch_points FROM './switch_points.csv' WITH CSV HEADER;" -d mmrp_munich_osm -U liulu
psql -c "\COPY car_parkings FROM './car_parkings.csv' WITH CSV HEADER;" -d mmrp_munich_osm -U liulu
