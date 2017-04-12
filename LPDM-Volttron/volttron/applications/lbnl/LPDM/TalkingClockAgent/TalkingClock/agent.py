# -*- coding: utf-8 -*- {{{
# vim: set fenc=utf-8 ft=python sw=4 ts=4 sts=4 et:

import logging
logging.basicConfig()

import sys
import cPickle
from time import time

from volttron.platform.vip.agent import Agent, Core, PubSub
from volttron.platform.agent import utils
from volttron.platform.messaging import headers as headers_mod
from applications.lbnl.LPDM.BaseAgent.base.topics import SYSTEM_TIME_TOPIC

from lpdm_event import LpdmTtieEvent

class LPDM_TalkingClock(Agent):
    """
    Base class for LPDM agents.  Responsible for most of the general things need to run in volttron
    like handling messages or setting the interface for subclasses to handle messages where necessary
    and the basic headers of the message.  Also handles messages for changing device settings.        
    """
    def __init__(self, config_path, **kwargs):
        """
        :param device_id:  string, the id of the device in the system.  Should be unique within the run.
        """
        super(LPDM_TalkingClock, self).__init__(**kwargs)
                 
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
        headers[headers_mod.FROM] = "clock"
        if target_device:
            headers[headers_mod.TO] = target_device
        headers["timestamp"] = self.get_time()
        headers["message_id"] = str(uuid4())
        
        return headers
        
    def get_time(self):
        """
        The base class does not handle time because it does not know if it is in reality or a simulation.
        Leaving time to the derived classes allows for a mix of real and simulated devices.
        """
        return time()
  

    @Core.periodic(5)
    def send_new_time(self):
        """
        Posts a new time message.
        """
        headers = self.default_headers("all")                             
        message = LpdmTtieEvent("all", headers["timestamp"]) 
        message = cPickle.dumps(message)
        topic = SYSTEM_TIME_TOPIC
        self.vip.pubsub.publish("pubsub", topic, headers, message)
    
def main(argv=sys.argv):
    '''Main method called by the eggsecutable.'''
    utils.vip_main(LPDM_TalkingClock)


if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv))
    except KeyboardInterrupt:
        pass
