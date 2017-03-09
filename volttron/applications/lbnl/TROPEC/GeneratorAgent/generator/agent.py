# -*- coding: utf-8 -*- {{{
# vim: set fenc=utf-8 ft=python sw=4 ts=4 sts=4 et:


import sys
from volttron.platform.agent import utils
from volttron.platform.vip.agent import Core
from volttron.platform.messaging import headers as headers_mod
from applications.lbnl.TROPEC.BaseAgent.base.topics import *
from applications.lbnl.TROPEC.SimulationAgent.simulation.agent import SimulationAgent
from tug_devices.diesel_generator import DieselGenerator 

class DieselGeneratorAgent(SimulationAgent):
    """
    Wraps a DieselGenerator
    """
    def __init__(self, **kwargs):
        """
        Initializes the agent and registers some of its functions with the 
        device's config file.
        """
        super(DieselGeneratorAgent, self).__init__(**kwargs)
        
        try:
            config = kwargs
            config["device_name"] = config["device_id"]
            self.grid_controller_id = config["grid_controller_id"]
        except:
            config = {}           
        config["broadcastNewPrice"] = self.send_new_price
        config["broadcastNewPower"] = self.send_new_power
        config["broadcastNewTTIE"] = self.send_new_time_until_next_event
        config = self.configure_logger(config)
        self.config = config
        
    def send_new_price(self, source_device_id, target_device_id, timestamp, price):
        """
        Posts a message to the generator's set_price topic with the generator's new price
        """
        headers = self.default_headers(target_device_id)        
        headers["timestamp"] = timestamp + self.message_processing_time
        message = {"price" : price}
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
        super(DieselGeneratorAgent, self).on_message_bus_start(sender, **kwargs)
        #self.subscribed_power_topic = SET_POWER_TOPIC_SPECIFIC_AGENT.format(id = self.agent_id)
        self.subscribed_power_topic = POWER_USE_TOPIC_SPECIFIC_AGENT.format(id = self.config["grid_controller_id"])
        self.power_subscription_id = self.vip.pubsub.subscribe("pubsub", self.subscribed_power_topic, self.on_power_update)
        self.subscribed_price_topic = ENERGY_PRICE_TOPIC_SPECIFIC_AGENT.format(id = self.agent_id)
        self.price_subscription_id = self.vip.pubsub.subscribe("pubsub", self.subscribed_price_topic, self.on_price_update)
        self.broadcast_connection()
        self.send_subscriptions()
        self.diesel_generator = DieselGenerator(self.config)
        self.send_finished_initialization()

    def broadcast_connection(self):
        """
        Posts a message to the grid_controller this device is attached to telling the grid_controller
        to add it to the list of connected power producing devices.
        """
        headers = self.default_headers(None)
        self.vip.pubsub.publish("pubsub", ADD_GENERATOR_TOPIC.format(id = self.grid_controller_id), headers, {"agent_id" : self.agent_id})
    
    def get_device(self):
        """
        :return: The diesel generator this code wraps.
        """        
        return self.diesel_generator
    
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
        self.diesel_generator.onTimeChange(self.time)
        self.diesel_generator.onPowerChange(device_id, self.diesel_generator._device_id, int(self.time), power)        
        self.send_finish_processing_message()              
        
    def on_price_update(self, peer, sender, bus, topic, headers, message):        
        print "On price update"
        if headers.get("timestamp", None) == 3600.006:
            pass 
        if self.last_message_id == headers["responding_to"]:
            return
        message_id = headers.get("message_id", None)
        self.last_message_id = message_id                
        self.send_finish_processing_message()
        

def main(argv=sys.argv):
    '''Main method called by the eggsecutable.'''
    utils.vip_main(DieselGeneratorAgent)


if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv))
    except KeyboardInterrupt:
        pass
