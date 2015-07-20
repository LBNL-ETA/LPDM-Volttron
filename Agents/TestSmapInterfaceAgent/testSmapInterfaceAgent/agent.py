import logging
import sys

from volttron.platform.agent import BaseAgent, PublishMixin, periodic
from volttron.platform.agent import utils, matching
from volttron.platform.messaging import headers as headers_mod, topics
# from Agents.SmapInterfaceAgent.smapinterface import settings
#from Agents.SmapInterfaceAgent.smapinterface import settings
# from smapinterface import settings
from Agents.SmapInterfaceAgent.smapinterface.topics import *

utils.setup_logging()
_log = logging.getLogger(__name__)



class TestSmapInterfaceAgent(PublishMixin, BaseAgent):

    def __init__(self, config_path, **kwargs):
        super(TestSmapInterfaceAgent, self).__init__(**kwargs)
        self.config = utils.load_config(config_path)
    def setup(self):
        self._agent_id = self.config['agentid']
        super(TestSmapInterfaceAgent, self).setup()
        self.post_test(3)        
            
    def post_test(self, val):
        import time
        headers = {'SourceName': "test",
                   'requesterID': self._agent_id,
                   headers_mod.FROM : self._agent_id,
                   "SmapRoot" : "http://elnhv.lbl.gov",
                   'Stream' : "/test_smap_interface_agent",
                   'ApiKey' : "3EYQy04hlPpA03SixKcRJaIreUrnpdYu9bNn",
                   'StreamUUID' : "01f235e4-65cd-44b3-9272-a614fef452ff"                      
                   }
        metadata = {"Instrument:" : {"Model" : "Model T"}, "UnitofMeasure" : "F", "Timezone" : "America/Los_Angeles"}
        
        msg = {"timeseries" : [[int(time.time()) * 1000, val]], "metadata" : metadata}                           
        
        self.publish_json(UPLOAD_REQUEST_TOPIC + "/test/test_smap_interface_agent", headers, msg)
        
    
    @matching.match_exact(UPLOAD_RESPONSE_TOPIC + "/test/test_smap_interface_agent")
    def on_test_response(self, topic, headers, message, match):        
        import time
        five_minutes = 60*5
        try:                    
            print "Received upload request respons:\n".format(s = message)
            #source = headers.get('SourceName', None)
            #smap_root = headers.get("ArchiverUrl", None)            
            #start_time = headers.get('StartTime', None)
            #end_time = headers.get('EndTime', None)      
            print "Trying to download timeseries"
            headers = {'SourceName': "test",
                   'requesterID': self._agent_id,
                   headers_mod.FROM : self._agent_id,
                   "SmapRoot" : "http://elnhv.lbl.gov",
                   "StartTime" : int(time.time()) - five_minutes,
                   "EndTime" : int(time.time())
                   }
            self.publish_json(DOWNLOAD_REQUEST_TOPIC + "/test_smap_interface_agent", headers, {})
        except:
            print "FAILURE due to exception: %s" % sys.exc_info()[0]
    
    @matching.match_exact(DOWNLOAD_RESPONSE_TOPIC + "/test/test_smap_interface_agent")        
    def on_download_response(self, topic, headers, message, match):
        try:
            print "Received download request response:\n{s}".format(s = message)
        except:
            print "FAILURE due to exception: %s" % sys.exc_info()[0]
        
    @periodic(60)
    def post_test_periodically(self):
        import random
        print "archiver agent test"
        self.post_test(random.random())
        
def main(argv=sys.argv):
    '''Main method called by the eggsecutable.'''
    utils.default_main(TestSmapInterfaceAgent,
                        description='Testing agent for Archiver Agent in VOLTTRON Lite',
                        argv=argv)

if __name__ == '__main__':
    # Entry point for script
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        pass
