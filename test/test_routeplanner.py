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
        rd = planner.find_path(plan)["result list"][0]
        self.assertTrue(rd["is existent"])
        self.assertTrue("Walking", rd["description"])
        self.assertAlmostEqual(5567.744, rd["length"], places=3)
        self.assertAlmostEqual(74.237, rd["time"], places=3)
        self.assertEqual(rd["length"], rd["walking length"])
        self.assertEqual(rd["time"], rd["walking time"])
        self.assertTrue(not rd["switch points"])
        self.assertEqual(1, len(rd["paths"]))
        self.assertEqual("foot", rd["paths"][0]["mode"])
        self.assertEqual("LineString", rd["paths"][0]["geojson"]["type"])
        self.assertGreaterEqual(len(rd["paths"][0]["geojson"]["coordinates"]), 2)
        self.assertListEqual([11.5682317, 48.1500053],
                             rd["paths"][0]["geojson"]["coordinates"][0])
        self.assertListEqual([11.5036395, 48.1583208],
                             rd["paths"][0]["geojson"]["coordinates"][-1])
        planner.cleanup()

    def test_find_path_for_driving_and_walking_plan(self):
        self.assertIn([self.modes["private_car"], self.modes["foot"]],
                      [i.mode_list for i in self.plans])
        for p in self.plans:
            if p.mode_list == [self.modes["private_car"], self.modes["foot"]]:
                plan = p
        with MultimodalRoutePlanner() as planner:
            rd = planner.find_path(plan)["result list"][0]
            self.assertTrue(rd["is existent"])
            self.assertFalse(not rd["switch points"])
            self.assertEqual("car_parking", rd["switch points"][0]["type"])
            self.assertEqual("Point", rd["switch points"][0]["geojson"]["type"])
            self.assertTrue("Driving, parking and walking", rd["description"])
            self.assertEqual(2, len(rd["paths"]))
            self.assertEqual("private_car", rd["paths"][0]["mode"])
            self.assertEqual("foot", rd["paths"][1]["mode"])
            self.assertAlmostEqual(6700.675, rd["length"], places=3)
            self.assertAlmostEqual(20.2001, rd["time"], places=3)
            self.assertAlmostEqual(522.534, rd["walking length"], places=3)
            self.assertAlmostEqual(6.967, rd["walking time"], places=3)
            self.assertEqual("LineString", rd["paths"][0]["geojson"]["type"])
            self.assertListEqual([11.5682317, 48.1500053],
                                 rd["paths"][0]["geojson"]["coordinates"][0])
            self.assertListEqual([11.5008518, 48.1611429],
                                 rd["paths"][0]["geojson"]["coordinates"][-1])
            self.assertGreaterEqual(len(rd["paths"][0]["geojson"]["coordinates"]), 2)
            self.assertEqual("LineString", rd["paths"][1]["geojson"]["type"])
            self.assertListEqual([11.5008518, 48.1611429],
                                 rd["paths"][1]["geojson"]["coordinates"][0])
            self.assertListEqual([11.5036395, 48.1583208],
                                 rd["paths"][1]["geojson"]["coordinates"][-1])
            self.assertGreaterEqual(len(rd["paths"][1]["geojson"]["coordinates"]), 2)

    def test_batch_find_paths(self):
        pass

if __name__ == "__main__":
    unittest.main()
