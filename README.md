# pymmrouting

CAUTION: the package is not finished yet.

python package of multimodal route planning based on [multimodal shortest path algorithms (mmspa)] (http://github.com/tumluliu/mmspa). The underlying path finding algorithms are described in detail in my doctor thesis [Data model and algorithms for multimodal route planning in transportation networks] (http://mediatum.ub.tum.de/node?id=1004678)

## Usage

A sample code snippet of calculating multimodal paths:

```python
from pymmrouting import routeplanner
from pymmrouting import datamodel
from pymmrouting import inferenceengine

inferer = inferenceengine.RoutingPlanInferer()
inferer.load_routing_options('./multimodal_routing_options.json')
routing_plans = inferer.generate_routing_plan()
mm_dataset = datamodel.MultimodalNetwork()
mm_dataset.connect_db("dbname = 'sample_multimodal_db' user = 'user' password = 'password'")
mm_dataset.assemble_networks(routing_plans)
# FIXME: should be coordinates
source = 100201021234
target = 100201034567
route_planner = routeplanner.RoutePlanner(mm_dataset)
results = RoutingResult()
results = route_planner.find_paths_between(source, target)
results.show_on_map('MAPBOX')
```

## Dependencies

* pymmspa4pg
* libmmspa4pg
* libpq

## Contact

Lu LIU

nudtlliu#gmail.com
