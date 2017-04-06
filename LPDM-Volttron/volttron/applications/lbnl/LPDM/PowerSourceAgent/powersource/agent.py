# -*- coding: utf-8 -*- {{{
# vim: set fenc=utf-8 ft=python sw=4 ts=4 sts=4 et:


import sys
from volttron.platform.agent import utils
from volttron.platform.vip.agent import Core
from volttron.platform.messaging import headers as headers_mod
from applications.lbnl.LPDM.BaseAgent.base.topics import *
from applications.lbnl.LPDM.SimulationAgent.simulation.agent import SimulationAgent
from device.simulated.diesel_generator import DieselGenerator
from device.simulated.pv import Pv
from device.simulated.utility_meter import UtilityMeter

from lpdm_event import LpdmConnectDeviceEvent, LpdmPriceEvent
import cPickle

def power_source_factory(type_id):
    device_type_to_class_map = {}
    device_type_to_class_map["diesel_generator"] = DieselGenerator
    device_type_to_class_map["pw"] = Pv
    device_type_to_class_map["utility_meter"] = UtilityMeter
    
    #if it isn't a specialized type just use the basic EUD
    return device_type_to_class_map.get(type_id, DieselGenerator)

class PowerSourceAgent(SimulationAgent):
    """
    Wraps a Power Source
    """
    def __init__(self, config_path, **kwargs):
        """
        Initializes the agent and registers some of its functions with the 
        device's config file.
        """
        super(PowerSourceAgent, self).__init__(config_path, **kwargs)
        
        try:
            config = kwargs
            config["device_name"] = config["device_id"]
            self.grid_controller_id = config["grid_controller_id"]
        except:
            config = {}
                 
        config["broadcast_new_power"] = self.send_new_power
        config["broadcast_new_price"] = self.send_new_price
        config["broadcast_new_ttie"] = self.send_new_time_until_next_event
        config["broadcast_new_capacity"] = self.send_new_capacity   
        self.config = config
        
    def send_new_price(self, source_device_id, target_device_id, timestamp, price):
        """
        Posts a message to the generator's set_price topic with the generator's new price
        """
        headers = self.default_headers(target_device_id)        
        headers["timestamp"] = timestamp + self.message_processing_time
        message = LpdmPriceEvent(source_device_id, target_device_id, timestamp, price)
        message = cPickle.dumps(message)
        #message = {"price" : price}
        topic = ENERGY_PRICE_FROM_ENERGY_PRODUCER_TOPIC_SPECIFIC_AGENT.format(id = self.agent_id)
        self.vip.pubsub.publish("pubsub", topic, headers, message)
        try:
            fuel_topic = FUEL_LEVEL_TOPIC.format(id = self.agent_id)
            message = {"fuel_level" : self.get_device()._fuel_level}
            self.vip.pubsub.publish("pubsub", fuel_topic, headers, message)
        except:
            pass
        
        
    @Core.receiver('onstart')
    def on_message_bus_start(self, sender, **kwargs):
        """
        Handles behavior for setting up subscriptions to the message bus for power and price messages, configures the underlying device
        that this code wraps, broadcasts any connections to other devices in the system (E.G. the grid controller it is connected to),
        and sends a message indicating it has successfully initialized.
        """
        super(PowerSourceAgent, self).on_message_bus_start(sender, **kwargs)
        #self.subscribed_power_topic = SET_POWER_TOPIC_SPECIFIC_AGENT.format(id = self.agent_id)
        self.subscribed_power_topic = POWER_USE_TOPIC_SPECIFIC_AGENT.format(id = self.config["grid_controller_id"])
        self.power_subscription_id = self.vip.pubsub.subscribe("pubsub", self.subscribed_power_topic, self.on_power_update)
        self.subscribed_price_topic = ENERGY_PRICE_TOPIC_SPECIFIC_AGENT.format(id = self.agent_id)
        self.price_subscription_id = self.vip.pubsub.subscribe("pubsub", self.subscribed_price_topic, self.on_price_update)        
        self.device_type = self.config.get("device_type", None)
        self.device_class = power_source_factory(self.device_type)
        self.power_source = self.device_class(self.config)
        self.send_subscriptions()
        self.broadcast_connection()        
        self.send_finished_initialization()

    def broadcast_connection(self):
        """
        Posts a message to the grid_controller this device is attached to telling the grid_controller
        to add it to the list of connected power producing devices.
        """
        headers = self.default_headers(None)
        message = LpdmConnectDeviceEvent(self.power_source._device_id, self.device_type, self.device_class)
        message = cPickle.dumps(message)
        self.vip.pubsub.publish("pubsub", ADD_POWER_SOURCE_TOPIC.format(id = self.grid_controller_id), headers, message)
    
    def get_device(self):
        """
        :return: The diesel generator this code wraps.
        """        
        return self.power_source
    
    def send_subscriptions(self):
        """
        Sends a message saying which power_use_topic it has subscribed to.
        Needed for simulation but may also aid in diagnostics for real systems.
        """
        subscriptions = [self.subscribed_power_topic] #, self.subscribed_price_topic]        
        message = {"subscriptions" : subscriptions}
        headers = {}
        headers[headers_mod.FROM] = self.agent_id
        self.vip.pubsub.publish("pubsub", SUBSCRIPTION_TOPIC, headers, message)  
    
    def on_power_update(self, peer, sender, bus, topic, headers, message):
        """
        Handles reacting to a new power use message.  Updates the local time,
        calls onPriceChange on the underlying device, and sends a finished processing message.
        """  
        device_id = headers.get(headers_mod.FROM, None)
        message_id = headers.get("message_id", None)
        self.last_message_id = message_id
        power = message.get("power", None)
        timestamp = headers.get("timestamp", None)
        if timestamp > self.time:
            self.time = timestamp
        evt = cPickle.loads(message)
        self.power_source.process_supervisor_event(evt)
        #self.power_source.on_time_change(self.time)
        #self.power_source.on_power_change(device_id, self.diesel_generator._device_id, int(self.time), power)        
        self.send_finish_processing_message()              
        
    def on_price_update(self, peer, sender, bus, topic, headers, message):        
        print "On price update"
        if headers.get("timestamp", None) == 3600.006:
            pass 
        if self.last_message_id == headers["responding_to"]:
            return
        message_id = headers.get("message_id", None)
        self.last_message_id = message_id           
        evt = cPickle.loads(message)
        self.power_source.process_supervisor_event(evt)     
        self.send_finish_processing_message()
        

def main(argv=sys.argv):
    '''Main method called by the eggsecutable.'''
    utils.vip_main(PowerSourceAgent)


if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv))
    except KeyboardInterrupt:
        pass
