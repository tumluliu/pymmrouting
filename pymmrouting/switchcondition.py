""" SwitchCondition class is a part of pymmrouting module """


class SwitchCondition(object):

    """ Store the conditions of a switching action between two
        transportation modes
    """

    def __init__(self):
        self.type = ''
        self.cost = 0.0
        self.is_available = True
