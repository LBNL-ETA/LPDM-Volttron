import sys

from volttron.platform.agent import BaseAgent, PublishMixin
from volttron.platform.agent import utils
from volttron.platform.messaging import headers as headers_mod

from topics import *

class TROPEC_BaseAgent(PublishMixin, BaseAgent):
    def __init__(self, **kwargs):
            super(TROPEC_BaseAgent, self).__init__(**kwargs)
            self.time = None            
            self.agent_id = kwargs["device_id"]
            self.last_message_id = None
            self.message_processing_time = .001
    
    def default_headers(self, target_device):
        from uuid import uuid1
        headers = {}
        headers[headers_mod.FROM] = self.agent_id
        if target_device:
            headers[headers_mod.TO] = target_device
        headers["timestamp"] = self.time        
        headers["responding_to"] = self.last_message_id
        headers["message_id"] = str(uuid1())
        
        return headers
        
    def get_time(self):
        raise NotImplementedError("Implement in derived class.")
  
    def send_new_price(self, source_device_id, target_device_id, timestamp, price):
        headers = self.default_headers(target_device_id)        
        headers["timestamp"] = timestamp + .001
        message = {"price" : price}
        topic = ENERGY_PRICE_TOPIC_SPECIFIC_AGENT.format(id = self.agent_id)
        self.publish_json(topic, headers, message)
        try:
            fuel_topic = FUEL_LEVEL_TOPIC.format(id = self.agent_id)
            message = {"fuel_level" : self.get_device()._fuel_level}
            self.publish_json(fuel_topic, headers, message)
        except:
            pass

    def send_new_power(self, source_device_id, target_device_id, timestamp, power):
        headers = self.default_headers(target_device_id)     
        headers["timestamp"] = timestamp + .001
        message = {"power" : power}
        topic = POWER_USE_TOPIC_SPECIFIC_AGENT.format(id = self.agent_id)
        self.publish_json(topic, headers, message)
    
    def send_new_time_until_next_event(self, source_device_id, target_device_id, time_until_next_event):
        headers = self.default_headers(target_device_id)      
        message = {"time_until_next_event" : time_until_next_event}
        topic = TIME_UNTIL_NEXT_EVENT_TOPIC_SPECIFIC_AGENT.format(id = self.agent_id)
    
        self.publish_json(topic, headers, message)
        
    def send_finished_initialization(self):
        headers = self.default_headers(None)            
        message = {"initialization_finished" : True}
        topic = FINISHED_INITIALIZING_TOPIC.format(id = self.agent_id)
        self.publish_json(topic, headers, message)
        
    def send_finish_processing_message(self):
        topic = FINISHED_PROCESSING_MESSSAGE_SPECIFIC_AGENT.format(id = self.agent_id)
        headers = self.default_headers(None)
        message = {"finished" : True}
        self.publish_json(topic, headers, message)
        
    def get_device(self):
        raise NotImplementedError("Implement in derived class.")
            

def main(argv=sys.argv):
    '''Main method called by the eggsecutable.'''
    utils.default_main(TROPEC_BaseAgent,
                       description='TROPEC Simulation Agent',
                       argv=argv)


if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv))
    except KeyboardInterrupt:
        pass
