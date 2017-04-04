# -*- coding: utf-8 -*- {{{
# vim: set fenc=utf-8 ft=python sw=4 ts=4 sts=4 et:


import sys
from volttron.platform.agent import utils
from volttron.applications.lbnl.LPDM.BaseAgent.base.topics import *
from volttron.applications.lbnl.LPDM.BaseAgent.base.agent import BaseAgent

def log_entry_and_exit(f):
    def _f(*args):
        print "Entering %s" % f.__name__
        f(*args)
        print "Exited %s" % f.__name__
    return _f



class RealAgent(BaseAgent):
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
