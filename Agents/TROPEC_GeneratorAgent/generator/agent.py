import sys
from volttron.platform.agent import utils
from volttron.platform.agent.utils import jsonapi
from volttron.platform.messaging import headers as headers_mod
from Agents.TROPEC_BaseAgent.base.topics import *
from Agents.TROPEC_SimulationAgent.simulation.agent import SimulationAgent
from tug_devices.diesel_generator import DieselGenerator

class GeneratorAgent(SimulationAgent):
    def __init__(self, **kwargs):
        super(GeneratorAgent, self).__init__(**kwargs)
        
        try:
            config = kwargs
            config["device_name"] = config["device_id"]
            self.grid_controller_id = config["grid_controller_id"]
        except:
            config = {}           
        config["broadcastNewPrice"] = self.send_new_price
        config["broadcastNewPower"] = self.send_new_power
        config["broadcastNewTTIE"] = self.send_new_time_until_next_event
        self.diesel_generator = DieselGenerator(config)
        self.subscribed_power_topic = SET_POWER_TOPIC_SPECIFIC_AGENT.format(id = self.agent_id)
        self.power_subscription_id = self.subscribe(self.subscribed_power_topic, self.on_power_update)
        self.broadcast_connection()
        self.send_subscriptions()
        self.send_finished_initialization()

    def broadcast_connection(self):
        headers = self.default_headers(None)
        self.publish_json(ADD_GENERATOR_TOPIC.format(id = self.grid_controller_id), headers, {"agent_id" : self.agent_id})
    
    def get_device(self):
        return self.diesel_generator
    
    def send_subscriptions(self):
        subscriptions = [self.subscribed_power_topic]        
        message = {"subscriptions" : subscriptions}
        headers = {}
        headers[headers_mod.FROM] = self.agent_id
        self.publish_json(SUBSCRIPTION_TOPIC, headers, message)  
    
    def on_power_update(self, topic, headers, message, matched):        
        message = jsonapi.loads(message[0])
        device_id = headers.get(headers_mod.FROM, None)
        message_id = headers.get("message_id", None)
        self.last_message_id = message_id
        power = message.get("power", None)
        timestamp = headers.get("timestamp", None)
        if timestamp > self.time:
            self.time = timestamp
        self.diesel_generator.onPowerChange(device_id, self.diesel_generator._device_id, self.time, power)
        self.diesel_generator.onTimeChange(self.time)
        self.send_finish_processing_message()
        
def main(argv=sys.argv):
    '''Main method called by the eggsecutable.'''
    utils.default_main(GeneratorAgent,
                       description='TROPEC Generator Agent',
                       argv=argv)


if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv))
    except KeyboardInterrupt:
        pass
