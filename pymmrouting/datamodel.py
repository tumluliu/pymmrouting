"""
Data adapter for reading and parsing multimodal transportation networks and
related abstraction of facilities
"""

"""
from pymmspa4pg import connect_db, create_routing_plan, set_mode, \
    set_public_transit_mode, set_cost_factor, parse, dispose, \
    set_switch_condition, set_switching_constraint, set_target_constraint


class MultimodalNetwork(object):

#    Represent multimodal transportation networks in memory

    def __init__(self):
        self.stub = ""

    def connect_db(self, conn_info):
        if connect_db(conn_info) != 0:
            raise Exception("Connect to database error!")

    def assemble_networks(self, plan):
        create_routing_plan(len(plan.mode_list), len(plan.public_transit_set))
        # set mode list
        i = 0
        for mode in plan.mode_list:
            set_mode(i, mode)
            i += 1

        # set switch conditions and constraints if the plan is multimodal
        if len(plan.mode_list) > 1:
            for i in range(len(plan.mode_list) - 1):
                set_switch_condition(i, plan.switch_condition_list[i])
                set_switching_constraint(i, plan.switch_constraint_list[i])

        # set public transit modes if there are
        if plan.has_public_transit:
            i = 0
            for mode in plan.public_transit_set:
                set_public_transit_mode(i, mode)
                i += 1

        set_target_constraint(plan.target_constraint)
        set_cost_factor(plan.cost_factor)

        if parse() != 0:
            raise Exception("Assembling multimodal networks failed!")

    def disassemble_networks(self):
        dispose()

"""
