import sys
from volttron.platform.agent import utils
from Agents.TROPEC_BaseAgent.base.topics import *
from Agents.TROPEC_BaseAgent.base.agent import TROPEC_BaseAgent

class RealAgent(TROPEC_BaseAgent):
    def __init__(self, **kwargs):
        super(RealAgent, self).__init__(**kwargs)
        self.time = None

    def get_time(self):
        from time import time
        return time()

def main(argv=sys.argv):
    '''Main method called by the eggsecutable.'''
    utils.default_main(RealAgent,
                       description='TROPEC Real (non-simulation) Agent',
                       argv=argv)


if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv))
    except KeyboardInterrupt:
        pass
