import sys
from volttron.platform.agent import utils
from volttron.platform.agent.utils import jsonapi
from Agents.TROPEC_BaseAgent.base.topics import *
from Agents.TROPEC_BaseAgent.base.agent import TROPEC_BaseAgent


class SimulationAgent(TROPEC_BaseAgent):
    def __init__(self, **kwargs):
            super(SimulationAgent, self).__init__(**kwargs)
            self.time = 0
            self.time_topic_registration_id = self.subscribe(SYSTEM_TIME_TOPIC_SPECIFIC_AGENT.format(id = self.agent_id), self.on_time_update)

    def on_time_update(self, topic, headers, message, matched):        
        message = jsonapi.loads(message[0])
        timestamp = message["timestamp"]
        self.last_message_id = headers.get("message_id", None)
        self.time = float(timestamp)
        print "Time:\t{s}".format(s = self.time)
        device = self.get_device()
        device.onTimeChange(self.time)
        
    def get_time(self):
        return self.time
            

def main(argv=sys.argv):
    '''Main method called by the eggsecutable.'''
    utils.default_main(SimulationAgent,
                       description='TROPEC Simulation Agent',
                       argv=argv)


if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv))
    except KeyboardInterrupt:
        pass
