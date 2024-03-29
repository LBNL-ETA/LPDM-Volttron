# -*- coding: utf-8 -*- {{{
# vim: set fenc=utf-8 ft=python sw=4 ts=4 sts=4 et:


import sys
import cPickle
import logging

from volttron.platform.agent import utils
from volttron.platform.agent.utils import jsonapi
from volttron.platform.vip.agent import Core
from volttron.platform.agent.matching import match_exact
from volttron.platform.messaging import headers as headers_mod

from applications.lbnl.LPDM.SimulationAgent.simulation.agent import SimulationAgent
from applications.lbnl.LPDM.BaseAgent.base.topics import *

from device.simulated.grid_controller import GridController

from lpdm_event import LpdmPriceEvent, LpdmInitEvent, LpdmPowerEvent

utils.setup_logging()
_log = logging.getLogger(__name__)
__version__ = '0.1'


class GridControllerAgent(SimulationAgent):
    def __init__(self, config_path, **kwargs):

        self.generators = {}
        self.end_use_devices = {}

        config = utils.load_config(config_path)
        _log.debug(config)

        try:
            config["device_name"] = config["device_id"]
        except:
            raise RuntimeError("Invalid configuration")

        config["broadcast_new_power"] = self.send_new_power
        config["broadcast_new_price"] = self.send_new_price
        config["broadcast_new_ttie"] = self.send_new_time_until_next_event
        config["broadcast_new_capacity"] = self.send_new_capacity
        config["broadcast"] = self.LPDM_broadcast

        # This needs to come after adding the callbacks to config due to LPDM now
        # only having one callback instead of several.  The actual mappings of 
        # what gets returned by the LPDM code will be handled in the LPDM_BaseAgent
        super(GridControllerAgent, self).__init__(config, **kwargs)

        self.subscription_topics = {}

    @Core.receiver('onstart')
    def on_message_bus_start(self, sender, **kwargs):

        topic = ADD_POWER_SOURCE_TOPIC.format(id=self.agent_id)
        self.subscription_topics[topic] = self.vip.pubsub.subscribe("pubsub", topic, self.on_add_power_source_message)
        topic = ADD_END_USE_DEVICE_TOPIC.format(id=self.agent_id)
        self.subscription_topics[topic] = self.vip.pubsub.subscribe("pubsub", topic, self.on_add_end_use_device_message)
        with open("/tmp/grid_controller_bus_start", "a") as f:
            f.write("Agent id {id}\n".format(id=self.agent_id))
            f.write("Config: {c}\n\n".format(c=self.config))
            f.write("Subscriptions: {s}\n\n".format(s=self.subscription_topics))

        self.send_subscriptions()
        self.grid_controller = GridController(self.config)
        evt = LpdmInitEvent()
        self.get_device().process_supervisor_event(evt)
        self.send_finished_initialization()

    def get_device(self):
        return self.grid_controller

    def send_new_price(self, source_device_id, target_device_id, timestamp, price):
        _log.debug("Sending new price: {p} to: {t}".format(p=price, t=target_device_id))
        headers = self.default_headers(target_device_id)
        headers["timestamp"] = timestamp + self.message_processing_time

        message = LpdmPriceEvent(source_device_id, target_device_id, timestamp, price)
        message = cPickle.dumps(message)
        topic = ENERGY_PRICE_TOPIC_SPECIFIC_AGENT.format(id=target_device_id)
        self.vip.pubsub.publish("pubsub", topic, headers, message)

    def send_subscriptions(self):
        subscriptions = []
        for generator_id, values in self.generators.items():
            subscriptions.append(values["price_topic"])
            subscriptions.append(values["capacity_topic"])

        for eud_id, values in self.end_use_devices.items():
            subscriptions.append(values["power_use_topic"])
            subscriptions.append(values["capacity_topic"])

        message = {"subscriptions": subscriptions}
        headers = {headers_mod.FROM: self.agent_id}
        self.vip.pubsub.publish("pubsub", SUBSCRIPTION_TOPIC, headers, message)

    def on_add_power_source_message(self, peer, sender, bus, topic, headers, message):
        device_id = headers[headers_mod.FROM]
        _log.debug("Power source added {p}".format(p=device_id))
        price_topic = ENERGY_PRICE_FROM_ENERGY_PRODUCER_TOPIC_SPECIFIC_AGENT.format(id=device_id)
        price_subscribe_id = self.vip.pubsub.subscribe("pubsub", price_topic, self.on_power_source_price_message)
        capacity_topic = CAPACITY_TOPIC_SPECIFIC_AGENT.format(id=device_id)
        capacity_subscribe_id = self.vip.pubsub.subscribe("pubsub", capacity_topic,
                                                          self.on_power_source_capacity_message)
        self.generators[device_id] = {"price_topic": price_topic,
                                      "subscription_id": price_subscribe_id,
                                      "capacity_topic": capacity_topic,
                                      "capacity_subscription_id": capacity_subscribe_id}

        evt = cPickle.loads(message)
        self.grid_controller.process_supervisor_event(evt)
        self.send_subscriptions()

    def on_power_source_power_use_message(self, peer, sender, bus, topic, headers, message):
        device_id = headers.get(headers_mod.FROM, None)
        evt = cPickle.loads(message)
        _log.debug("On power source power use {id} {p}".format(id=device_id, p=evt.value))
        self.grid_controller.process_supervisor_event(evt)
        self.send_finish_processing_message()

    def on_power_source_capacity_message(self, peer, sender, bus, topic, headers, message):
        device_id = headers.get(headers_mod.FROM, None)
        evt = cPickle.loads(message)
        _log.debug("On power source capacity {id} {p}".format(id=device_id, p=evt.value))
        self.grid_controller.process_supervisor_event(evt)
        self.send_finish_processing_message()

    def on_add_end_use_device_message(self, peer, sender, bus, topic, headers, message):
        device_id = headers[headers_mod.FROM]
        _log.debug("On end use device add {id}".format(id=device_id))
        power_topic = POWER_USE_TOPIC_SPECIFIC_AGENT.format(id=device_id)
        power_subscribe_id = self.vip.pubsub.subscribe("pubsub", power_topic, self.on_end_use_device_power_use_message)
        capacity_topic = CAPACITY_TOPIC_SPECIFIC_AGENT.format(id=device_id)
        capacity_subscribe_id = self.vip.pubsub.subscribe("pubsub", capacity_topic,
                                                          self.on_end_use_device_capacity_message)
        self.end_use_devices[device_id] = {"power_use_topic": power_topic,
                                           "power_subscription_id": power_subscribe_id,
                                           "capacity_topic": capacity_topic,
                                           "capacity_subscription_id": capacity_subscribe_id}
        evt = cPickle.loads(message)
        self.grid_controller.process_supervisor_event(evt)
        self.send_subscriptions()

    def on_remove_power_source_message(self, peer, sender, bus, topic, headers, message):
        raise RuntimeError("Grid Controllers no longer have a remove device method")
        device_id = headers[headers_mod.FROM]
        self.unsubscribe(self.geneators[device_id]["subscription_id"])
        del self.generators[device_id]
        evt = cPickle.loads(message)
        self.grid_controller.process_supervisor_event(evt)
        self.send_subscriptions()

    def on_remove_end_use_device_message(self, peer, sender, bus, topic, headers, message):
        raise RuntimeError("Grid Controllers no longer have a remove device method")
        device_id = headers[headers_mod.FROM]
        del self.generators[device_id]
        evt = cPickle.loads(message)
        self.grid_controller.process_supervisor_event(evt)
        self.send_subscriptions()

    def on_end_use_device_power_use_message(self, peer, sender, bus, topic, headers, message):
        message = cPickle.loads(message)
        device_id = headers.get(headers_mod.FROM, None)
        _log.debug("On end use device power use {id} {p}".format(id=device_id, p=evt.value))
        message_id = headers.get("message_id", None)
        self.last_message_id = message_id
        power_use = message.value
        timestamp = headers.get("timestamp", None)
        if timestamp > self.time:
            self.time = timestamp

        self.grid_controller.process_supervisor_event(message)
        self.send_finish_processing_message()

    def on_end_use_device_capacity_message(self, peer, sender, bus, topic, headers, message):
        message = cPickle.loads(message)
        device_id = headers.get(headers_mod.FROM, None)
        message_id = headers.get("message_id", None)
        self.last_message_id = message_id
        capacity = message.value
        timestamp = headers.get("timestamp", None)
        if timestamp > self.time:
            self.time = timestamp

        self.grid_controller.process_supervisor_event(message)
        self.send_finish_processing_message()

    def on_power_source_price_message(self, peer, sender, bus, topic, headers, message):
        device_id = headers.get(headers_mod.FROM, None)
        if device_id == self.agent_id:
            return
        message_id = headers.get("message_id", None)
        self.last_message_id = message_id
        timestamp = headers.get("timestamp", None)
        if timestamp > self.time:
            self.time = timestamp

        evt = cPickle.loads(message)
        self.grid_controller.process_supervisor_event(evt)
        self.send_finish_processing_message()


def main(argv=sys.argv):
    '''Main method called by the eggsecutable.'''
    utils.vip_main(GridControllerAgent)


if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv))
    except KeyboardInterrupt:
        pass
