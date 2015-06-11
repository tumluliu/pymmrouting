# pymmrouting

## Introduction

Python package of multimodal route planning based on [multimodal shortest path algorithms (mmspa)] (https://github.com/tumluliu/mmspa). The underlying path finding algorithms are described in detail in my doctor thesis [Data model and algorithms for multimodal route planning in transportation networks] (http://mediatum.ub.tum.de/node?id=1004678). So far, the multimodal transportation network it uses is stored in PostGIS. The database structure as well as the data can be prepared with [mmgraphdb-builder] (https://github.com/tumluliu/mmgraphdb-builder). The testbed data source is from OpenStreetMap and UnitedMaps. 

It should be noted that the path-finding process is not lightning-fast since the hierarchical multimodal networks is not built yet. The timetable of public transits as well as traffic rules in motorized roads are not modeled either for the moment.

The detailed platform information of all the U-bahn stations in Munich is collected by myself in late 2010. So you may find the routing result is more reasonable in underground network than that in suburban and tram networks because I had no time to collect the platform info for suburban and tram stations at that time. The bus lines are not included for the moment.

## Usage

Rename the `sample-config.json` to `config.json` and modify its content according to your environment.

A sample code snippet of calculating multimodal paths:

```python
from pymmrouting.inferenceengine import RoutingPlanInferer
from pymmrouting.routeplanner import MultimodalRoutePlanner

inferer = RoutingPlanInferer()
inferer.load_routing_options('./sample-options/routing_options_driving_and_taking_public_transit.json')
plans = inferer.generate_routing_plan()
planner = MultimodalRoutePlanner()
results = planner.batch_find_path(plans)
planner.cleanup()
```

And all the possible multimodal routing results including multimodal paths and switch points are stored in `results` which is a dict variable and can be serialized into a JSON format file.

## Dependencies

- sqlalchemy
- geoalchemy2
- [mmspa] (https://github.com/tumluliu/mmspa)

## Contact

- Lu LIU
- nudtlliu#gmail.com

