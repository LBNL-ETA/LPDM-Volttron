TROPEC_BASE = "TROPEC"
TIME_UNTIL_NEXT_EVENT_TOPIC_GLOBAL = "{base}/time_until_next_event".format(base = TROPEC_BASE)
TIME_UNTIL_NEXT_EVENT_TOPIC_SPECIFIC_AGENT = TIME_UNTIL_NEXT_EVENT_TOPIC_GLOBAL + "/{id}" 

ENERGY_PRICE_TOPIC = "{base}/energy_price".format(base = TROPEC_BASE)
ENERGY_PRICE_TOPIC_SPECIFIC_AGENT = ENERGY_PRICE_TOPIC + "/{id}"
POWER_USE_TOPIC = "{base}/power_use".format(base = TROPEC_BASE)
POWER_USE_TOPIC_SPECIFIC_AGENT = POWER_USE_TOPIC + "/{id}"

SET_POWER_TOPIC = "{base}/set_power_use".format(base = TROPEC_BASE)
SET_POWER_TOPIC_SPECIFIC_AGENT = SET_POWER_TOPIC + "/{id}"

BASE_SUBSCRIPTION_TOPIC = "{base}/grid_controller/{{id}}".format(base = TROPEC_BASE)
BASE_ADD_CONTROLLED_DEVICE_TOPIC = BASE_SUBSCRIPTION_TOPIC + "/add" 
ADD_GENERATOR_TOPIC = BASE_ADD_CONTROLLED_DEVICE_TOPIC + "/generator" 
ADD_END_USE_DEVICE_TOPIC = BASE_ADD_CONTROLLED_DEVICE_TOPIC + "/end_use_device"
REMOVE_GENERATOR_TOPIC = ADD_GENERATOR_TOPIC.replace("/add", "/remove") 
REMOVE_END_USE_DEVICE_TOPIC = ADD_END_USE_DEVICE_TOPIC.replace("/add", "/remove")

SYSTEM_TIME_TOPIC = "{base}/system_time".format(base = TROPEC_BASE)
SYSTEM_TIME_TOPIC_SPECIFIC_AGENT = SYSTEM_TIME_TOPIC + "/{id}"

FINISHED_INITIALIZING_TOPIC_BASE = "{base}/init/finished".format(base = TROPEC_BASE)
FINISHED_INITIALIZING_TOPIC = FINISHED_INITIALIZING_TOPIC_BASE+ "/{id}" 

SCENARIO_ID_TOPIC = "{base}/scenario_id".format(base = TROPEC_BASE)

SUBSCRIPTION_TOPIC = "{base}/subscriptions".format(base = TROPEC_BASE)

FINISHED_PROCESSING_MESSSAGE = "{base}/finished_processinng".format(base = TROPEC_BASE)
FINISHED_PROCESSING_MESSSAGE_SPECIFIC_AGENT = FINISHED_PROCESSING_MESSSAGE + "/{id}"

FUEL_LEVEL_BASE = "{base}/FUEL_LEVEL".format(base = TROPEC_BASE)
FUEL_LEVEL_TOPIC = FUEL_LEVEL_BASE + "/{id}"