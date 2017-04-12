# -*- coding: utf-8 -*- {{{
# vim: set fenc=utf-8 ft=python sw=4 ts=4 sts=4 et:


import sys
import cPickle

from volttron.platform.agent import utils
from volttron.platform.messaging import headers as headers_mod
from volttron.platform.vip.agent import Core
from applications.lbnl.LPDM.BaseAgent.base.topics import *
from applications.lbnl.LPDM.SimulationAgent.simulation.agent import SimulationAgent

from device.simulated.eud import Eud
from device.simulated.air_conditioner import AirConditioner
from device.simulated.fixed_consumption import FixedConsumption

from lpdm_event import LpdmConnectDeviceEvent, LpdmInitEvent

def eud_factory(type_id):
    device_type_to_class_map = {}
    device_type_to_class_map["fixed_consumption"] = FixedConsumption
    device_type_to_class_map["air_conditioner"] = AirConditioner
    
    #if it isn't a specialized type just use the basic EUD
    return device_type_to_class_map.get(type_id, Eud)
        

class EndUseDeviceAgent(SimulationAgent):
    """
    A base class for all power-consuming objects in the system.  Registers some of its functions with the 
    underlying device's config file.
    """
    def __init__(self, config_path, **kwargs):
        super(EndUseDeviceAgent, self).__init__(config_path, **kwargs)
        
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
        self.device_type = self.config.get("device_type", None)
        self.device_class = eud_factory(self.device_type)
        self.end_use_device = self.device_class(self.config)        
        #self.end_use_device._price = 0.343784378438
        self.broadcast_connection()
        self.send_subscriptions()
        evt = LpdmInitEvent()
        self.get_device().process_supervisor_event(evt)
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
        message = LpdmConnectDeviceEvent(self.end_use_device._device_id, self.device_type, self.device_class)
        message = cPickle.dumps(message)
        self.vip.pubsub.publish("pubsub", topic, headers, message)
        
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
        message = cPickle.loads(message)
        device_id = headers.get(headers_mod.FROM, None)
        message_id = headers.get("message_id", None)
        self.last_message_id = message_id
        price = message.value
        timestamp = headers.get("timestamp", None)
        if timestamp > self.time:
            self.time = timestamp
        self.end_use_device.process_supervisor_event(message)
        self.send_finish_processing_message()


def main(argv=sys.argv):
    '''Main method called by the eggsecutable.'''
    utils.vip_main(EndUseDeviceAgent)


if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv))
    except KeyboardInterrupt:
        pass
