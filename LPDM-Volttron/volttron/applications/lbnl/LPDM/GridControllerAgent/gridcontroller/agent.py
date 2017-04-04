# -*- coding: utf-8 -*- {{{
# vim: set fenc=utf-8 ft=python sw=4 ts=4 sts=4 et:


import sys

from volttron.platform.agent import utils
from volttron.platform.agent.utils import jsonapi
from volttron.platform.vip.agent import Core
from volttron.platform.agent.matching import match_exact
from volttron.platform.messaging import headers as headers_mod

from volttron.applications.lbnl.LPDM.SimulationAgent.simulation.agent import SimulationAgent
from volttron.applications.lbnl.LPDM.BaseAgent.base.topics import *

from device.simulated.grid_controller import GridController 


def log_entry_and_exit(f):
    def _f(*args):        
        print "Entering GridControllerAgent {f}".format(f = f.__name__)
        res = f(*args)
        print "Exited GridControllerAgent {f}".format(f = f.__name__)
        return res
    return _f


class GridControllerAgent(SimulationAgent):
    def __init__(self, **kwargs):
        super(GridControllerAgent, self).__init__(**kwargs)
        self.generators = {}
        self.end_use_devices = {}
        
        try:
            config = kwargs
            config["device_name"] = config["device_id"]
        except:
            config = {}           
        config["broadcastNewPrice"] = self.send_new_price
        config["broadcastNewPower"] = self.send_new_power
        config["broadcastNewTTIE"] = self.send_new_time_until_next_event      
        
        config = self.configure_logger(config)
        self.config = config
            
        self.subscription_topics = {}
        
    
        
    @Core.receiver('onstart')
    def on_message_bus_start(self, sender, **kwargs):
            
        topic = ADD_GENERATOR_TOPIC.format(id = self.agent_id)
        self.subscription_topics[topic] = self.vip.pubsub.subscribe("pubsub", topic, self.on_add_generator_message)
        topic = ADD_END_USE_DEVICE_TOPIC.format(id = self.agent_id)
        self.subscription_topics[topic] = self.vip.pubsub.subscribe("pubsub", topic, self.on_add_end_use_device_message)        
        self.send_subscriptions()
        if "battery_config" in self.config:
            self.config["battery_config"]["tug_logger"] = self.config["tug_logger"]
            self.config["battery_config"]["logger"] = self.config["logger"]
            self.config["battery_config"]["app_log_manager"] = self.config["app_log_manager"]
            
        self.grid_controller = GridController(self.config)
        self.send_finished_initialization()
            
    def get_device(self):
        return self.grid_controller
     
    def send_new_price(self, source_device_id, target_device_id, timestamp, price):        
        headers = self.default_headers(target_device_id)        
        headers["timestamp"] = timestamp + self.message_processing_time
        message = {"price" : price}
        topic = ENERGY_PRICE_TOPIC_SPECIFIC_AGENT.format(id = target_device_id)
        self.vip.pubsub.publish("pubsub", topic, headers, message)
         
#     def send_new_power(self, source_device_id, target_device_id, timestamp, power):
#         headers = self.default_headers(target_device_id)     
#         headers["timestamp"] = timestamp + .001
#         message = {"power" : power}
#         topic = SET_POWER_TOPIC_SPECIFIC_AGENT.format(id = target_device_id)
#         self.vip.pubsub.publish("pubsub", topic, headers, message)
    
    def send_subscriptions(self):
        subscriptions = []
        for generator_id, values in self.generators.items():
            subscriptions.append(values["price_topic"])
            
        for eud_id, values in self.end_use_devices.items():
            subscriptions.append(values["power_use_topic"])
        
        message = {"subscriptions" : subscriptions}
        headers = {}
        headers[headers_mod.FROM] = self.agent_id
        self.vip.pubsub.publish("pubsub", SUBSCRIPTION_TOPIC, headers, message)        
    
    def on_add_generator_message(self, peer, sender, bus, topic, headers, message):
        device_id = headers[headers_mod.FROM]        
        price_topic = ENERGY_PRICE_FROM_ENERGY_PRODUCER_TOPIC_SPECIFIC_AGENT.format(id = device_id)
        price_subscribe_id = self.vip.pubsub.subscribe("pubsub", price_topic, self.on_generator_price_message)
        power_topic = POWER_USE_TOPIC_SPECIFIC_AGENT.format(id = device_id)
        power_subscribe_id = self.vip.pubsub.subscribe("pubsub", power_topic, self.on_generator_power_use_message)
        self.generators[device_id] = {"price_topic" : price_topic, "subscription_id" : price_subscribe_id, "power_topic" : power_topic, "power_susbscription_id" : power_subscribe_id}
        self.grid_controller.addDevice(device_id, "diesel_generator")        
        self.send_subscriptions()
        
    def on_generator_power_use_message(self, peer, sender, bus, topic, headers, message):
        device_id = headers.get(headers_mod.FROM, None)
        if message["power"] == 0:
            self.grid_controller.onPriceChange(device_id, None, int(self.time), 3)
        
    def on_add_end_use_device_message(self, peer, sender, bus, topic, headers, message):
        device_id = headers[headers_mod.FROM]
        power_topic = POWER_USE_TOPIC_SPECIFIC_AGENT.format(id = device_id)
        subscribe_id = self.vip.pubsub.subscribe("pubsub", power_topic, self.on_end_use_device_power_use_message)
        self.end_use_devices[device_id] = {"power_use_topic" : power_topic, "subscription_id" : subscribe_id}
        self.grid_controller.addDevice(device_id, "end_use_device")
        self.send_subscriptions()
        
    def on_remove_generator_message(self, peer, sender, bus, topic, headers, message):
        device_id = headers[headers_mod.FROM]
        self.unsubscribe(self.geneators[device_id]["subscription_id"])
        del self.generators[device_id]
        self.grid_controller.removeDevice(device_id, "diesel_generator")
        self.send_subscriptions()
        
        
    def on_remove_end_use_device_message(self, peer, sender, bus, topic, headers, message):
        device_id = headers[headers_mod.FROM]
        del self.generators[device_id]
        self.grid_controller.removeDevice(device_id, "end_use_device")
        self.send_subscriptions()
    
    def on_end_use_device_power_use_message(self, peer, sender, bus, topic, headers, message):
        device_id = headers.get(headers_mod.FROM, None)
        message_id = headers.get("message_id", None)
        self.last_message_id = message_id
        power_use = message.get("power", None)
        timestamp = headers.get("timestamp", None)
        if timestamp > self.time:
            self.time = timestamp

        self.grid_controller.onPowerChange(device_id, None, int(self.time), power_use)
        self.send_finish_processing_message()
        
            
    def on_generator_price_message(self, peer, sender, bus, topic, headers, message):
        device_id = headers.get(headers_mod.FROM, None)
        if device_id == self.agent_id:
            return
        message_id = headers.get("message_id", None)
        self.last_message_id = message_id
        price = message.get("price")        
        timestamp = headers.get("timestamp", None)
        if timestamp > self.time:
            self.time = timestamp
        self.grid_controller.onPriceChange(device_id, None, int(self.time), price)
        self.send_finish_processing_message()
        
        

def main(argv=sys.argv):
    '''Main method called by the eggsecutable.'''
    utils.vip_main(GridControllerAgent)


if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv))
    except KeyboardInterrupt:
        pass
