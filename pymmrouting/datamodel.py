"""
Data adapter for reading and parsing multimodal transportation networks and
related abstraction of facilities
"""


from pymmspa4pg import connect_db, create_routing_plan, set_mode, set_public_transit_mode, set_cost_factor, parse

class MultimodalNetwork(object):

    """
    Represent multimodal transportation networks in memory
    """

    def __init__(self):
        self.stub = ""

    def connect_db(self, conn_info):
        if connect_db(conn_info) != 0:
            raise Exception("Connect to database error!")

    def assemble_networks(self, plan):
        create_routing_plan(len(plan.mode_list), len(plan.public_transit_set))
        i = 0
        for m in plan.mode_list:
            set_mode(i, m)
            i += 1
        i = 0
        for m in plan.public_transit_set:
            set_public_transit_mode(i, m)
            i += 1
        set_cost_factor(plan.cost_factor)
        if parse() != 0:
            raise Exception("Assembling multimodal networks failed!")
