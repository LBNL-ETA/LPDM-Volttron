# -*- coding: utf-8 -*- {{{
# vim: set fenc=utf-8 ft=python sw=4 ts=4 sts=4 et:


import sys
from volttron.platform.agent import utils
from volttron.platform.agent.utils import jsonapi
from volttron.platform.vip.agent import Core
from volttron.applications.lbnl.LPDM.BaseAgent.base.topics import *
from volttron.applications.lbnl.LPDM.BaseAgent.base.agent import BaseAgent
#from tug_logger import TugLogger
from simulation_logger import SimulationLogger


class SimulationAgent(BaseAgent):
    def __init__(self, **kwargs):
            super(SimulationAgent, self).__init__(**kwargs)
            self.time = 0
            self.message_processing_time = .001
            
    @Core.receiver('onstart')
    def on_message_bus_start(self, sender, **kwargs):
        topic = SYSTEM_TIME_TOPIC_SPECIFIC_AGENT.format(id = self.agent_id)
        self.time_topic_registration_id = self.vip.pubsub.subscribe("pubsub", topic, self.on_time_update)

    def on_time_update(self, peer, sender, bus, topic, headers, message):        
        timestamp = message["timestamp"]
        self.last_message_id = headers.get("message_id", None)
        self.time = float(timestamp)
        print "Time:\t{s}".format(s = self.time)
        device = self.get_device()
        device.onTimeChange(int(self.time))       
        self.send_finish_processing_message()
        
    def configure_logger(self, config):
        self.simulation_log_manager = SimulationLogger()
        config["app_log_manager"] = self.simulation_log_manager             
        config["logger"] = self.simulation_log_manager.logger
        config["tug_logger"] = TugLogger()      
        return config
        
    def get_time(self):
        return self.time
            

def main(argv=sys.argv):
    '''Main method called by the eggsecutable.'''
    utils.vip_main(SimulationAgent)


if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv))
    except KeyboardInterrupt:
        pass
