""" Read config.json file to construct the project-level settings object
"""

import json

# TODO: Identify the config.json file in a good way
CONFIG_FILE = "config.json"
with (open(CONFIG_FILE, 'r')) as conf_file:
    DATABASE = json.load(conf_file)["sqlalchemy"]["database"]
