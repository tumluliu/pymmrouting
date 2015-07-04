import unittest
from pymmrouting.routeplanner import MultimodalRoutePlanner
from pymmrouting.inferenceengine import RoutingPlanInferer
from pymmrouting.orm_graphmodel import SwitchType, Mode, Session

class RoutePlannerTestCase(unittest.TestCase):

    def setUp(self):
        routing_options_file = \
            "test/routing_options_driving_parking_and_go.json"
        self.inferer = RoutingPlanInferer()
        self.inferer.load_routing_options_from_file(routing_options_file)
        self.plans = self.inferer.generate_routing_plan()
        self.modes = {
            str(m_name): m_id
            for m_name, m_id in
            Session.query(Mode.mode_name, Mode.mode_id)
        }
        self.switch_types = {
            str(t_name): t_id
            for t_name, t_id in
            Session.query(SwitchType.type_name, SwitchType.type_id)
        }

    def test_find_path_for_walking_plan(self):
        self.assertIn([self.modes["foot"]], [i.mode_list for i in self.plans])
        for p in self.plans:
            if p.mode_list == [self.modes["foot"]]:
                plan = p
        planner = MultimodalRoutePlanner()
        result = planner.find_path(plan)
        rd = result["routes"][0]
        self.assertTrue(rd["existence"])
        self.assertTrue("Walking", rd["summary"])
        self.assertAlmostEqual(5567.744, rd["distance"], places=3)
        self.assertAlmostEqual(74.237, rd["duration"], places=3)
        self.assertEqual(rd["distance"], rd["walking_distance"])
        self.assertEqual(rd["duration"], rd["walking_duration"])
        self.assertTrue(not rd["switch_points"])
        self.assertEqual(1, len(rd["geojson"]["features"]))
        self.assertEqual("foot", rd["geojson"]["features"][0]["properties"]["mode"])
        self.assertEqual("LineString", rd["geojson"]["features"][0]['geometry']["type"])
        self.assertGreaterEqual(len(rd["geojson"]["features"][0]["geometry"]["coordinates"]), 2)
        self.assertListEqual([11.5682317, 48.1500053],
                             rd["geojson"]["features"][0]["geometry"]["coordinates"][0])
        self.assertListEqual([11.5036395, 48.1583208],
                             rd["geojson"]["features"][0]["geometry"]["coordinates"][-1])
        self.assertListEqual([11.5682317, 48.1500053],
                             result["source"]["geometry"]["coordinates"])
        self.assertListEqual([11.5036395, 48.1583208],
                             result["target"]["geometry"]["coordinates"])
        planner.cleanup()

    def test_find_path_for_driving_and_walking_plan(self):
        self.assertIn([self.modes["private_car"], self.modes["foot"]],
                      [i.mode_list for i in self.plans])
        for p in self.plans:
            if p.mode_list == [self.modes["private_car"], self.modes["foot"]]:
                plan = p
        with MultimodalRoutePlanner() as planner:
            result = planner.find_path(plan)
            rd = result["routes"][0]
            self.assertListEqual([11.5682317, 48.1500053],
                                result["source"]["geometry"]["coordinates"])
            self.assertListEqual([11.5036395, 48.1583208],
                                result["target"]["geometry"]["coordinates"])
            self.assertTrue(rd["existence"])
            self.assertFalse(not rd["switch_points"])
            self.assertEqual("car_parking",
                             rd["switch_points"][0]['properties']["switch_type"])
            self.assertEqual("Point", rd["switch_points"][0]["geometry"]["type"])
            self.assertTrue("Driving, parking and walking", rd["summary"])
            self.assertEqual(3, len(rd["geojson"]["features"]))
            self.assertEqual("private_car", rd["geojson"]["features"][0]["properties"]["mode"])
            self.assertEqual("car_parking", rd["geojson"]["features"][1]["properties"]["switch_type"])
            self.assertEqual("foot", rd["geojson"]["features"][2]["properties"]["mode"])
            self.assertAlmostEqual(6700.675, rd["distance"], places=3)
            self.assertAlmostEqual(20.2001, rd["duration"], places=3)
            self.assertAlmostEqual(522.534, rd["walking_distance"], places=3)
            self.assertAlmostEqual(6.967, rd["walking_duration"], places=3)
            self.assertEqual("LineString", rd["geojson"]["features"][0]["geometry"]["type"])
            self.assertListEqual([11.5682317, 48.1500053],
                                 rd["geojson"]["features"][0]["geometry"]["coordinates"][0])
            self.assertListEqual([11.5008518, 48.1611429],
                                 rd["geojson"]["features"][0]["geometry"]["coordinates"][-1])
            self.assertIn("stroke", rd['geojson']['features'][0]['properties'])
            self.assertGreaterEqual(len(rd["geojson"]["features"][0]["geometry"]["coordinates"]), 2)
            self.assertEqual("switch_point", rd['geojson']['features'][1]['properties']['type'])
            self.assertEqual("car_parking", rd['geojson']['features'][1]['properties']['switch_type'])
            self.assertIn("marker-size", rd['geojson']['features'][1]['properties'])
            self.assertEqual("LineString", rd["geojson"]["features"][2]["geometry"]["type"])
            self.assertListEqual([11.5008518, 48.1611429],
                                 rd["geojson"]["features"][2]["geometry"]["coordinates"][0])
            self.assertListEqual([11.5036395, 48.1583208],
                                 rd["geojson"]["features"][2]["geometry"]["coordinates"][-1])
            self.assertGreaterEqual(len(rd["geojson"]["features"][2]["geometry"]["coordinates"]), 2)

    def test_batch_find_paths(self):
        pass

if __name__ == "__main__":
    unittest.main()
