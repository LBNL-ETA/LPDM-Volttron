import sys
from volttron.platform.agent import utils
from volttron.platform.agent.utils import jsonapi
from volttron.platform.vip.agent import Core
from volttron.platform.messaging import headers as headers_mod
from volttron.applications.lbnl.LPDM.BaseAgent.base.topics import *
from volttron.applications.lbnl.LPDM.SimulationAgent.simulation.agent import SimulationAgent
from device.simulated.eud import Eud


class SimulationEventsAgent(SimulationAgent):
    
    def __init__(self, config_path, **kwargs):
        super(SimulationEventsAgent, self).__init__(config_path, **kwargs)
        
        try:
            config = kwargs
            config["device_name"] = config["device_id"]
            self.events = config["events"]        
        except:
            config = {}           
                
                
    @Core.receiver("onsetup")
    def on_message_bus_setup(self, sender, **kwargs):
        pass
        
    @Core.receiver('onstart')
    def on_message_bus_start(self, sender, **kwargs):
        super(SimulationEventsAgent, self).on_message_bus_start(sender, **kwargs)
        self.send_new_time_until_next_event(self.agent_id, "all", self.events[0]["time"])
        self.send_finished_initialization()
        
    def get_device(self):
        return self
    
    def send_events(self, events_to_send):
        for event in events_to_send:
            headers = self.default_headers(event["device_id"])
            message = {"parameter" : event["parameter"], "value" : event["value"]}
            self.vip.pubsub.publish("pubsub", CHANGE_DEVICE_PARAMETER_TOPIC_SPECIFIC_AGENT.format(id = event["device_id"]), headers, message)
    
    def onTimeChange(self, new_time):
        #def send_new_time_until_next_event(self, source_device_id, target_device_id, time_until_next_event):
        next_event = None
        events_to_send = []
        events_yet_to_send = []
        for event in self.events:
            if event["time"] > new_time:
                if (not next_event) or (next_event["time"] > event["time"]):
                    next_event = event
                events_yet_to_send.append(event)
            else:
                events_to_send.append(event)
        self.send_events(events_to_send)
        self.events = events_yet_to_send
        ttie = 1e100
        if next_event:
            ttie = next_event["time"] - new_time
        self.send_new_time_until_next_event(self.agent_id, "all", ttie)
        self.send_finish_processing_message()
        

def main(argv=sys.argv):
    '''Main method called by the eggsecutable.'''
    utils.vip_main(SimulationEventsAgent)


if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv))
    except KeyboardInterrupt:
        pass
