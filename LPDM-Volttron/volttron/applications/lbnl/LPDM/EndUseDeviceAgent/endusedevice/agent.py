# -*- coding: utf-8 -*- {{{
# vim: set fenc=utf-8 ft=python sw=4 ts=4 sts=4 et:


import sys


from volttron.platform.agent import utils
from volttron.platform.messaging import headers as headers_mod
from volttron.platform.vip.agent import Core
from volttron.applications.lbnl.LPDM.BaseAgent.base.topics import *
from volttron.applications.lbnl.LPDM.SimulationAgent.simulation.agent import SimulationAgent

from device.simulated.eud import Eud
from device.simulated.hue_light_eud import Light
#from tug_devices.light import Light as WemoLight
from device.simulated.refrigerator import Refrigerator
from device.simulated.air_conditioner import AirConditioner

def eud_factory(type_id):
    device_type_to_class_map = {}
    device_type_to_class_map["hue_light"] = Light
    device_type_to_class_map["refrigerator"] = Refrigerator
    device_type_to_class_map["air_conditioner"] = AirConditioner
    #device_type_to_class_map["wemo_light"] = WemoLight
    
    return device_type_to_class_map.get(type_id, Eud)
        

class EndUseDeviceAgent(SimulationAgent):
    """
    A base class for all power-consuming objects in the system.  Registers some of its functions with the 
    underlying device's config file.
    """
    def __init__(self, **kwargs):
        super(EndUseDeviceAgent, self).__init__(**kwargs)
        
        try:
            config = kwargs
            config["device_name"] = config["device_id"]
            self.grid_controller_id = config["grid_controller_id"]
        except:
            config = {}           
        config["broadcastNewPrice"] = self.send_new_price
        config["broadcastNewPower"] = self.send_new_power
        config["broadcastNewTTIE"] = self.send_new_time_until_next_event 
        self.config = self.configure_logger(config)     
        
    def send_new_price(self, source_device_id, target_device_id, timestamp, price):
        raise NotImplementedError("End use devices should not be sending price information.")
        
    @Core.receiver('onstart')
    def on_message_bus_start(self, sender, **kwargs):
        """
        Handles behavior for setting up subscriptions to the message bus for energy messages, configures the underlying device
        that this code wraps, broadcasts any connections to other devices in the system (E.G. the grid controller it is connected to),
        and sends a message indicating it has successfully initialized.
        """
        super(EndUseDeviceAgent, self).on_message_bus_start(sender, **kwargs)
        self.energy_price_subscribed_topic = ENERGY_PRICE_TOPIC_SPECIFIC_AGENT.format(id = self.agent_id)
        self.energy_subscription_id = self.vip.pubsub.subscribe("pubsub", self.energy_price_subscribed_topic, self.on_price_update)
        eud_class = eud_factory(self.config.get("device_type", None))
        self.end_use_device = eud_class(self.config)
        self.end_use_device._price = 0.343784378438
        self.broadcast_connection()
        self.send_subscriptions()
        self.send_finished_initialization()
        
    def get_device(self):
        """
        :return end_use_device: The underlying device this code wraps. 
        """
        return self.end_use_device
        
    def broadcast_connection(self):
        """
        Posts a message to the grid_controller this device is attached to telling the grid_controller
        to add it to the list of connected power consuming devices.
        """
        headers = self.default_headers(None)
        topic = ADD_END_USE_DEVICE_TOPIC.format(id = self.grid_controller_id)
        self.vip.pubsub.publish("pubsub", topic, headers, {"agent_id" : self.agent_id})
        
    def send_subscriptions(self):
        """
        Sends a message saying which energy_price_topic it has subscribed to.
        Needed for simulation but may also aid in diagnostics for real systems.
        """
        subscriptions = [self.energy_price_subscribed_topic]        
        message = {"subscriptions" : subscriptions}
        headers = {}
        headers[headers_mod.FROM] = self.agent_id
        self.vip.pubsub.publish("pubsub", SUBSCRIPTION_TOPIC, headers, message)
        
    def on_price_update(self, peer, sender, bus, topic, headers, message):
        """
        Handles reacting to a new energy price message.  Updates the local time,
        calls onPriceChange on the underlying device, and sends a finished processing message.
        """
        device_id = headers.get(headers_mod.FROM, None)
        message_id = headers.get("message_id", None)
        self.last_message_id = message_id
        price = message.get("price", None)
        timestamp = headers.get("timestamp", None)
        if timestamp > self.time:
            self.time = timestamp
        self.end_use_device.onPriceChange(device_id, self.end_use_device._device_id, int(self.time), price)
        self.send_finish_processing_message()


def main(argv=sys.argv):
    '''Main method called by the eggsecutable.'''
    utils.vip_main(EndUseDeviceAgent)


if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv))
    except KeyboardInterrupt:
        pass
