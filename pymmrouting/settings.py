""" Read config.json file to construct the project-level settings object
"""

import json
import logging

logger = logging.getLogger(__name__)

# TODO: Identify the config.json file in a good way
CONFIG_FILE = "config.json"
with (open(CONFIG_FILE, 'r')) as conf_file:
    conf = json.load(conf_file)
    logger.debug("Get config from %s: %s", CONFIG_FILE, conf)
    PG_DB_CONF = conf["pg_datasource"]["connection"]
    logger.debug("Content of ['pg_datasource']['connection'] section: %s", PG_DB_CONF)
    PGBOUNCER_CONF = conf["pg_datasource"]["pgbouncer"]
    logger.debug("Content of ['pg_datasource']['pgbouncer'] section: %s", PGBOUNCER_CONF)
