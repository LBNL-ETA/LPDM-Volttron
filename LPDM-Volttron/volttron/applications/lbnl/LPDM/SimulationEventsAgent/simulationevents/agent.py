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
        raise RuntimeError("This class probably does not work with latest changes.  It is not used by the CBERD experiment (currently) so is being left broken due to time constraints.")
        config = utils.load_config(config_path)
        try:
            config["device_name"] = config["device_id"]
            self.events = config["events"]        
        except:
            raise RuntimeError("Invalid configuration")
        
        # This needs to come after adding the callbacks to config due to LPDM now
        # only having one callback instead of several.  The actual mappings of 
        # what gets returned by the LPDM code will be handled in the LPDM_BaseAgent
        super(SimulationEventsAgent, self).__init__(config, **kwargs)           
                
                
    @Core.receiver("onsetup")
    def on_message_bus_setup(self, sender, **kwargs):
        pass
        
    @Core.receiver('onstart')
    def on_message_bus_start(self, sender, **kwargs):
        super(SimulationEventsAgent, self).on_message_bus_start(sender, **kwargs)
        self.send_new_time_until_next_event(self.agent_id, self.events[0]["time"])
        self.send_finished_initialization()
        
    def get_device(self):
        return self
    
    def send_events(self, events_to_send):
        for event in events_to_send:
            headers = self.default_headers(event["device_id"])
            message = {"parameter" : event["parameter"], "value" : event["value"]}
            self.vip.pubsub.publish("pubsub", CHANGE_DEVICE_PARAMETER_TOPIC_SPECIFIC_AGENT.format(id = event["device_id"]), headers, message)
    
    def onTimeChange(self, new_time):
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
        self.send_new_time_until_next_event(self.agent_id, ttie)
        self.send_finish_processing_message()
        

def main(argv=sys.argv):
    '''Main method called by the eggsecutable.'''
    utils.vip_main(SimulationEventsAgent)


if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv))
    except KeyboardInterrupt:
        pass
