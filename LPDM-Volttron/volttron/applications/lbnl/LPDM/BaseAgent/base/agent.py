# -*- coding: utf-8 -*- {{{
# vim: set fenc=utf-8 ft=python sw=4 ts=4 sts=4 et:


import sys
import cPickle

from volttron.platform.vip.agent import Agent, Core, PubSub
from volttron.platform.agent import utils
from volttron.platform.messaging import headers as headers_mod
from topics import *

from lpdm_event import LpdmPowerEvent, LpdmTtieEvent, LpdmCapacityEvent

class LPDM_BaseAgent(Agent):
    """
    Base class for LPDM agents.  Responsible for most of the general things need to run in volttron
    like handling messages or setting the interface for subclasses to handle messages where necessary
    and the basic headers of the message.  Also handles messages for changing device settings.        
    """
    def __init__(self, config_path, **kwargs):
        """
        :param device_id:  string, the id of the device in the system.  Should be unique within the run.
        """
        super(LPDM_BaseAgent, self).__init__(**kwargs)
        self.time = None            
        self.agent_id = kwargs["device_id"]
        self.last_message_id = None            
             
    @Core.receiver('onstart')
    def on_message_bus_start(self, sender, **kwargs):
        """
        Subscribes to the specific devic's parameter change topic.  If any message calling for a parameter change in this device
        E.G. if the subclass of this is Generator and there is a message to change the refuel date it should target the
        on_device_parameter_change_message function
        """
        self.vip.pubsub.subscribe("pubsub", CHANGE_DEVICE_PARAMETER_TOPIC_SPECIFIC_AGENT.format(id = self.agent_id), self.on_device_parameter_change_message)
            
    def default_headers(self, target_device):
        """
        The default headers in a LPDM message.  
        
        :param target_device:  The id of the intended target, if there is one.
        
        :returns  A dict of header information.  Currently consists of:
            From:  The sending agent (ie this agent)
            To:  The intended target, if there is one
            timestamp:  the time the message is being sent
            responding_to:  The id of the message that triggered this message, if any
            message_id:  A uuid to identify a message in a run.
        """
        from uuid import uuid4
        headers = {}
        headers[headers_mod.FROM] = self.agent_id
        if target_device:
            headers[headers_mod.TO] = target_device
        headers["timestamp"] = self.time        
        headers["responding_to"] = self.last_message_id
        headers["message_id"] = str(uuid4())
        
        return headers
        
    def get_time(self):
        """
        The base class does not handle time because it does not know if it is in reality or a simulation.
        Leaving time to the derived classes allows for a mix of real and simulated devices.
        """
        raise NotImplementedError("Implement in derived class.")
  
    def send_new_price(self, source_device_id, target_device_id, timestamp, price):
        """
        The base class does not handle sending prices because different devices have different behavior for sending
        a price.  E.G. grid controllers send a price message, generators send a price message and a fuel level message,
        end use devices to not send prices.
        """
        raise NotImplementedError("send_new_price should be implemented in appropriate subclasses")
        
    @PubSub.subscribe("pubsub", TERMINATE_TOPIC)
    def on_terminate(self, peer, sender, bus, topic, headers, message):
        """
        Handles what happens when an agent is terminated (E.G. at the end of a scenario run)
        Updates the device's time, calls finish() on the device, calls generatePlots() on the device,
        sends a message saying it is finished then terminates.
        """
        message_id = headers.get("message_id", None)
        self.last_message_id = message_id
        timestamp = message["timestamp"]
        self.last_message_id = headers.get("message_id", None)
        timestamp = float(timestamp)
        
        device = self.get_device()
        device.onTimeChange(timestamp)
        device.finish()
        device.generatePlots()
        self.send_finish_processing_message()
        self.core.stop()

    def send_new_power(self, source_device_id, target_device_id, timestamp, power):
        """
        Posts a new power message.
        """
        headers = self.default_headers(target_device_id)             
        headers["timestamp"] = timestamp + getattr(self, "message_processing_time", 0)
        #message = {"power" : power}
        message = LpdmPowerEvent(source_device_id, target_device_id, timestamp, power)
        message = cPickle.dumps(message)
        topic = POWER_USE_TOPIC_SPECIFIC_AGENT.format(id = self.agent_id)
        self.vip.pubsub.publish("pubsub", topic, headers, message)
    
    def send_new_time_until_next_event(self, source_device_id, time_until_next_event, target_device_id = "all"):
        """
        Posts a new time until next event message.
        """
        headers = self.default_headers(target_device_id)      
        #message = {"time_until_next_event" : time_until_next_event}
        
        message = LpdmTtieEvent(target_device_id, time_until_next_event)
        message = cPickle.dumps(message)
        
        topic = TIME_UNTIL_NEXT_EVENT_TOPIC_SPECIFIC_AGENT.format(id = self.agent_id)
    
        self.vip.pubsub.publish("pubsub", topic, headers, message)
        
    def send_new_capacity(self, source_device_id, target_device_id, timestamp, capacity):
        """
        Posts a new capacity message.
        """
        headers = self.default_headers(target_device_id)             
        headers["timestamp"] = timestamp + getattr(self, "message_processing_time", 0)
        #message = {"capacity" : capacity}
        message = LpdmCapacityEvent(source_device_id, target_device_id, timestamp, capacity)
        message = cPickle.dumps(message)
        topic = POWER_USE_TOPIC_SPECIFIC_AGENT.format(id = self.agent_id)
        self.vip.pubsub.publish("pubsub", topic, headers, message)
        
    def send_finished_initialization(self):
        """
        Posts a message indicating the agent has successfully initialized
        """
        headers = self.default_headers(None)            
        message = {"initialization_finished" : True}
        topic = FINISHED_INITIALIZING_TOPIC.format(id = self.agent_id)
        self.vip.pubsub.publish("pubsub", topic, headers, message)
        
    def send_finish_processing_message(self):
        """
        Posts a message indicating that the device has finished responding to another message
        Needed for simulations.  Not strictly necessary for realtime but may be useful in
        diagnosing system problems and may afford more control in timing events.
        """        
        topic = FINISHED_PROCESSING_MESSSAGE_SPECIFIC_AGENT.format(id = self.agent_id)
        headers = self.default_headers(None)
        message = {"finished" : True}
        self.vip.pubsub.publish("pubsub", topic, headers, message)
        
    def get_device(self):
        """
        Subclasses should return the actual device the VOLTTRON agent is wrapping.
        """
        raise NotImplementedError("Implement in derived class.")
    
    def on_device_parameter_change_message(self, topic, headers, message, matched):
        """
        Responds to a message telling a device to change a paramater.  E.G. a message telling the
        generator that the next refuel date has changed.
        
        :param message:  VOLTTRON message dict.  Should have a "parameter" field and a "value" field
                            where parameter is the param to be changed and value is the new value. 
        
        """
        param = message["parameter"]
        new_val = message["value"]
        device = self.get_device()
        device.__dict__["_" + param] = new_val        
        device.refresh()
        self.send_finish_processing_message()

def main(argv=sys.argv):
    '''Main method called by the eggsecutable.'''
    utils.vip_main(LPDM_BaseAgent)


if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv))
    except KeyboardInterrupt:
        pass
