import sys
from volttron.platform.agent import utils
from volttron.platform.agent.utils import jsonapi
from volttron.platform.messaging import headers as headers_mod
from Agents.TROPEC_BaseAgent.base.topics import *
from Agents.TROPEC_SimulationAgent.simulation.agent import SimulationAgent
from tug_devices.eud import Eud

def log_entry_and_exit(f):
    def _f(*args):        
        print "Entering EndUseDeviceAgent {f}".format(f = f.__name__)
        res = f(*args)
        print "Exited EndUseDeviceAgent {f}".format(f = f.__name__)
        return res
    return _f

class EndUseDeviceAgent(SimulationAgent):
    
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
        self.energy_price_subscribed_topic = ENERGY_PRICE_TOPIC_SPECIFIC_AGENT.format(id = self.agent_id)
        self.energy_subscription_id = self.subscribe(self.energy_price_subscribed_topic, self.on_price_update)
        self.end_use_device = Eud(config)
        self.broadcast_connection()
        self.send_subscriptions()
        self.send_finished_initialization()
        
    def get_device(self):
        return self.end_use_device
        
    def broadcast_connection(self):
        headers = self.default_headers(None)
        self.publish_json(ADD_END_USE_DEVICE_TOPIC.format(id = self.grid_controller_id), headers, {"agent_id" : self.agent_id})
        
    def send_subscriptions(self):
        subscriptions = [self.energy_price_subscribed_topic]        
        message = {"subscriptions" : subscriptions}
        headers = {}
        headers[headers_mod.FROM] = self.agent_id
        self.publish_json(SUBSCRIPTION_TOPIC, headers, message)
        
    def on_price_update(self, topic, headers, message, matched):
        message = jsonapi.loads(message[0])
        device_id = headers.get(headers_mod.FROM, None)
        message_id = headers.get("message_id", None)
        self.last_message_id = message_id
        price = message.get("price", None)
        timestamp = headers.get("timestamp", None)
        if timestamp > self.time:
            self.time = timestamp
        self.end_use_device.onPriceChange(device_id, self.end_use_device._device_id, self.time, price)
        self.send_finish_processing_message()
        

def main(argv=sys.argv):
    '''Main method called by the eggsecutable.'''
    utils.default_main(EndUseDeviceAgent,
                       description='TROPEC EndUseDevice Agent',
                       argv=argv)


if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv))
    except KeyboardInterrupt:
        pass
