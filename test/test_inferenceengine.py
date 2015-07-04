import unittest
from pymmrouting.inferenceengine import RoutingPlan, RoutingPlanInferer
from pymmrouting.datamodel import VERTEX_VALIDATION_CHECKER
from pymmrouting.orm_graphmodel import SwitchType, Mode, Session
from os import path


class RoutingPlanTestCase(unittest.TestCase):

    def setUp(self):
        foot_source = {
            'type': 'Feature',
            'geometry': {
                'type': 'Point',
                'coordinates': [11.5675, 48.1495]
            },
            'properties': {'id': 12618163561}
        }
        car_source = {
            'type': 'Feature',
            'geometry': {
                'type': 'Point',
                'coordinates': [11.5675, 48.1495]
            },
            'properties': {'id': 11618163561}
        }
        target = {
            'type': 'Feature',
            'geometry': {
                'type': 'Point',
                'coordinates': [11.5038, 48.1583]
            },
            'properties': {'id': 12672741190}
        }
        cost = 'speed'
        modes = {str(m_name): m_id
                 for m_name, m_id in
                 Session.query(Mode.mode_name, Mode.mode_id)}
        switch_types = {str(t_name): t_id
                        for t_name, t_id in
                        Session.query(SwitchType.type_name, SwitchType.type_id)}
        # 1: Walking
        self.foot_plan = RoutingPlan(
            'Walking', foot_source, target, [modes['foot']], cost)
        self.car_plan = RoutingPlan(
            'Take a car', car_source, target, [modes['private_car']], cost)
        # 2: Driving
        driving_distance_limit = 200
        self.car_plan.target_constraint = VERTEX_VALIDATION_CHECKER(
            lambda v: 0 if v[0].distance <= float(driving_distance_limit) *
            1000.0 else -1)
        # 3: Take public transportation
        self.public_plan = RoutingPlan(
            'Walking and taking public transit', foot_source, target,
            [modes['public_transportation']], cost)
        self.public_plan.public_transit_set = [
            modes['underground'], modes['tram']]
        # 4: car-PT with geo_connection as Switch Point
        type_id = switch_types['geo_connection']
        self.car_public_plan = RoutingPlan(
            'Driving and taking public transit',
            car_source, target,
            [modes['private_car'], modes['public_transportation']],
            cost, [type_id],
            ["type_id=" + str(type_id) + " AND is_available=true"])
        self.car_public_plan.public_transit_set = [
            modes['suburban'], modes['tram'], modes['underground']]
        self.car_public_plan.switch_constraint_list = [
            VERTEX_VALIDATION_CHECKER(
                lambda v: 0 if v[0].distance <= float(driving_distance_limit) *
                1000.0 else -1)]

    def test_is_multimodal(self):
        self.assertFalse(self.foot_plan.is_multimodal)
        self.assertFalse(self.car_plan.is_multimodal)
        self.assertTrue(self.public_plan.is_multimodal)
        self.assertTrue(self.car_public_plan.is_multimodal)

    def test_has_public_transit(self):
        self.assertFalse(self.foot_plan.has_public_transit)
        self.assertFalse(self.car_plan.has_public_transit)
        self.assertTrue(self.public_plan.has_public_transit)
        self.assertTrue(self.car_public_plan.has_public_transit)

class RoutingPlanInfererTestCase(unittest.TestCase):


    def setUp(self):
        self.routing_options_file1 = "test/routing_options_driving_parking_and_go.json"
        self.routing_options_file2 = "test/routing_options_driving_and_taking_public_transit.json"
        self.routing_options_file3 = "test/routing_options_take_a_car_and_public_transit.json"
        self.inferer = RoutingPlanInferer()
        self.modes = {str(m_name): m_id
                      for m_name, m_id in
                      Session.query(Mode.mode_name, Mode.mode_id)}
        self.switch_types = {str(t_name): t_id
                             for t_name, t_id in
                             Session.query(SwitchType.type_name, SwitchType.type_id)}

    def test_load_routing_options_from_file(self):
        # test for routing options 1
        self.inferer.load_routing_options_from_file(self.routing_options_file1)
        self.assertIn("has_private_car", self.inferer.options)
        self.assertIn("need_parking", self.inferer.options)
        self.assertIn("source", self.inferer.options)
        self.assertIn("target", self.inferer.options)
        self.assertTrue(self.inferer.options["has_private_car"])
        self.assertTrue(self.inferer.options["need_parking"])
        self.assertEqual(len(self.inferer.options["available_public_modes"]), 0)
        self.assertEqual("coordinate", self.inferer.options["source"]["type"])
        self.assertEqual("coordinate", self.inferer.options["target"]["type"])
        # test for routing options 2
        self.inferer.load_routing_options_from_file(self.routing_options_file2)
        self.assertIn("has_private_car", self.inferer.options)
        self.assertIn("need_parking", self.inferer.options)
        self.assertIn("source", self.inferer.options)
        self.assertIn("target", self.inferer.options)
        self.assertTrue(self.inferer.options["has_private_car"])
        self.assertTrue(self.inferer.options["need_parking"])
        self.assertEqual(len(self.inferer.options["available_public_modes"]), 2)
        self.assertEqual("coordinate", self.inferer.options["source"]["type"])
        self.assertEqual("coordinate", self.inferer.options["target"]["type"])
        # test for routing options 3
        self.inferer.load_routing_options_from_file(self.routing_options_file3)
        self.assertIn("has_private_car", self.inferer.options)
        self.assertIn("need_parking", self.inferer.options)
        self.assertIn("source", self.inferer.options)
        self.assertIn("target", self.inferer.options)
        self.assertTrue(self.inferer.options["has_private_car"])
        self.assertFalse(self.inferer.options["need_parking"])
        self.assertEqual(len(self.inferer.options["available_public_modes"]), 3)
        self.assertEqual("coordinate", self.inferer.options["source"]["type"])
        self.assertEqual("coordinate", self.inferer.options["target"]["type"])

    def test_generate_routing_plan(self):
        # test for routing options 1
        self.inferer.load_routing_options_from_file(self.routing_options_file1)
        test_plans1 = self.inferer.generate_routing_plan()
        self.assertEqual(2, len(test_plans1))
        self.assertIn([self.modes["foot"]], [i.mode_list for i in test_plans1])
        self.assertIn([self.modes["private_car"], self.modes["foot"]],
                      [i.mode_list for i in test_plans1])
        # test for routing options 2
        self.inferer.load_routing_options_from_file(self.routing_options_file2)
        test_plans2 = self.inferer.generate_routing_plan()
        self.assertEqual(5, len(test_plans2))
        self.assertIn([self.modes["public_transportation"]],
                      [i.mode_list for i in test_plans2])
        self.assertIn([self.modes["private_car"], self.modes["public_transportation"]],
                      [i.mode_list for i in test_plans2])
        # test for routing options 3
        self.inferer.load_routing_options_from_file(self.routing_options_file3)
        test_plans3 = self.inferer.generate_routing_plan()
        self.assertEqual(5, len(test_plans3))
        self.assertIn(3, [len(p.public_transit_set) for p in test_plans3])
        self.assertIn([self.modes["public_transportation"]],
                      [i.mode_list for i in test_plans2])
        self.assertNotIn([self.modes["private_car"]],
                         [i.mode_list for i in test_plans3])


if __name__ == "__main__":
    unittest.main()
