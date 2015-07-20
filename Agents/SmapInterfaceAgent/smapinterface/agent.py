import sys

from volttron.platform.agent import BaseAgent, PublishMixin
from volttron.platform.agent import utils
from volttron.platform.agent.utils import jsonapi
from volttron.platform.agent.matching import match_start, match_exact
from volttron.platform.messaging import headers as headers_mod

import logging

from topics import *

logging.basicConfig()

def SmapInterfaceAgent(config_path, **kwargs):
    config = utils.load_config(config_path)

    def get_config(name):
        try:
            value = kwargs.pop(name)
        except KeyError:
            return config[name]

    class Agent(PublishMixin, BaseAgent):
        def __init__(self, **kwargs):
                super(Agent, self).__init__(**kwargs)
                self.cached_uuids = {}
    #         self.subscribe(REQUEST_TOPIC, self.handle_request)
    
        
        @match_exact(QUERY_REQUEST_TOPIC)
        def execute_query(self, topic, headers, message, matched):
            from smap_execute_query import execute_query
            message = jsonapi.loads(message[0])
            smap_root = headers.get("SmapRoot", None)
            api_key = headers.get('ApiKey', None)
            query = message["query"]
            res = execute_query(smap_root, api_key, query)
            qq = 5
        
        @match_start(UPLOAD_REQUEST_TOPIC)
        def upload_timeseries_to_smap(self, topic, headers, message, matched):
            import uuid
            import smap_upload_data
            from smap_download_data import get_stream_UUIDs_and_metadata           
            from dateutil.parser import parse
            message = jsonapi.loads(message[0])
            path = topic[len(UPLOAD_REQUEST_TOPIC):]
            source = headers.get('SourceName', None)
            smap_root = headers.get("SmapRoot", None)
            stream = headers.get('Stream', None)
            api_key = headers.get('ApiKey', None)            
            stream_uuid = headers.get('StreamUUID', str(uuid.uuid4()))
            if stream_uuid and stream_uuid.upper() == "USE EXISTING":
                if (smap_root, source, stream) in self.cached_uuids:
                    stream_uuid = self.cached_uuids[(smap_root, source, stream)]
                else:
                    uuid_to_metadata = get_stream_UUIDs_and_metadata(smap_root, stream, source)
                    if uuid_to_metadata:
                        stream_uuid = uuid_to_metadata.keys()[0]
                    else:
                        stream_uuid = str(uuid.uuid4())
                    self.cached_uuids[(smap_root, source, stream)] = stream_uuid
                    
            
            timeseries = message['timeseries']
            pub_headers = {headers_mod.FROM: 'SmapInterfaceAgent',
                           headers_mod.TO: headers[headers_mod.FROM] if headers_mod.FROM in headers else 'Unknown'}
                        
            metadata = message['metadata']
            units = metadata['UnitofMeasure'] if 'UnitofMeasure' in metadata else None     
            
            try:
                res = smap_upload_data.upload(timeseries, smap_root, api_key, source, stream, stream_uuid, units, additional_metadata = metadata)
            except Exception as e:
                self.publish(UPLOAD_RESPONSE_TOPIC + path,
                             pub_headers, "Trying to upload the timeseries threw: %s" % e)
                return
            
            if res == False:
                self.publish(UPLOAD_RESPONSE_TOPIC + path,
                             pub_headers, "Trying to upload to smap failed.")
            else:
                self.publish(UPLOAD_RESPONSE_TOPIC + path,
                             pub_headers, "Success")

                                
        @match_start(DOWNLOAD_REQUEST_TOPIC)        
        def download_timeseries_from_smap(self, topic, headers, message, matched):
            from smap_download_data import download_data
            path = topic[len(DOWNLOAD_REQUEST_TOPIC):]
            
            stream = topic[len(DOWNLOAD_REQUEST_TOPIC):]
            source = headers.get('SourceName', None)
            smap_root = headers.get("SmapRoot", None)            
            start_time = headers.get('StartTime', None)
            end_time = headers.get('EndTime', None)                        
            
            data, timezone = download_data(smap_root, stream, source_name = source, start_time = start_time, end_time = end_time)
            message = {"timeseries" : data, "timezone" : timezone}
            
            pub_headers = {headers_mod.FROM: 'SmapInterfaceAgent',
                           headers_mod.TO: headers[headers_mod.FROM] if headers_mod.FROM in headers else 'Unknown'}
            self.publish_json(DOWNLOAD_RESPONSE_TOPIC + path, pub_headers, message)
        
    Agent.__name__ = 'SmapInterfaceAgent'
    return Agent(**kwargs)

def main(argv=sys.argv):
    '''Main method called by the eggsecutable.'''
    utils.default_main(SmapInterfaceAgent,
                       description='VOLTTRON sMAP interface agent',
                       argv=argv)


if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv))
    except KeyboardInterrupt:
        pass
