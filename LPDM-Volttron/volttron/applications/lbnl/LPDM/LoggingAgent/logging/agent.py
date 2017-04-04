# -*- coding: utf-8 -*- {{{
# vim: set fenc=utf-8 ft=python sw=4 ts=4 sts=4 et:


import sys
import requests
from requests import ConnectionError

from volttron.platform.agent import BaseAgent, PublishMixin
from volttron.platform.agent import utils
from volttron.platform.agent.utils import jsonapi
from volttron.platform.agent.matching import match_all, match_start, match_exact
from volttron.platform.messaging import headers as headers_mod
#from volttron.platform.messaging import headers as headers_mod
#from volttron.platform.messaging import topics
from volttron.applications.lbnl.LPDM.BaseAgent.base.topics import *
from volttron.applications.lbnl.LPDM.SmapInterfaceAgent.smapinterface.topics import *

import json
from collections import defaultdict

def log_entry_and_exit(f):
    def _f(*args):
        print "Entering %s" % f.__name__
        f(*args)
        print "Exited %s" % f.__name__
    return _f

jan_1_2015 = 1420099200000

class LoggingAgent(PublishMixin, BaseAgent):
    def __init__(self, **kwargs):
        super(LoggingAgent, self).__init__(**kwargs)      
        self.scenario_id = "simulation"   
        self.last_posted_timestamp = 0
        self.power_values = defaultdict(list)
        self.energy_price_values = defaultdict(list)
        self.fuel_level_values = defaultdict(list)
        
    def reset_cached_values(self):
        new_power_values = defaultdict(list)
        new_energy_price_values = defaultdict(list)
        new_fuel_level_values = defaultdict(list)
        
        for agent_id, values in self.power_values.items():
            new_power_values[agent_id].append(values[-1])        
        for agent_id, values in self.energy_price_values.items():
            new_energy_price_values[agent_id].append(values[-1])
        for agent_id, values in self.fuel_level_values.items():
            new_fuel_level_values[agent_id].append(values[-1])    
            
        self.power_values = new_power_values
        self.energy_price_values = new_energy_price_values
        self.fuel_level_values = new_fuel_level_values
        
        
    def make_square_for_smap(self, timeseries):
        res = [timeseries[0]]
        for i in range(1, len(timeseries)):
            cur_point = timeseries[i]
            if res[-1][0] < cur_point[0] - 1000:
                res.append([cur_point[0] - 1000, res[-1][1]])
            res.append(cur_point)
            
        return res
            
        
    def upload_everything(self):
        def get_headers(device_id, reading_type):
            headers = {'SourceName': "LPDM",                   
                       headers_mod.FROM : "LPDM logger",
                       "SmapRoot" : "http://elnhv.lbl.gov/",
                       #'Stream' : "/simulation/{id}".format(id = from_id),
                       'Stream' : "{scenario_id}/{id}/{reading_type}".format(scenario_id = self.scenario_id, id = device_id, reading_type = reading_type),
                       'ApiKey' : "3EYQy04hlPpA03SixKcRJaIreUrnpdYu9bNn",
                       'StreamUUID' : "USE EXISTING"                      
                       }
            return headers
        
        for device_id, values in self.power_values.items():
            headers = get_headers(device_id, "power")
            metadata = {"UnitofMeasure" : "W", "Timezone" : "America/Los_Angeles"}
            
            self.last_posted_timestamp = max(self.last_posted_timestamp, values[-1][0])
            converted_values = [[jan_1_2015 + int(x[0] * 1000), x[1]] for x in values]     
            converted_values = self.make_square_for_smap(converted_values)       
            msg = {"timeseries" : converted_values, "metadata" : metadata}                           
            
            self.vip.pubsub.publish("pubsub", UPLOAD_REQUEST_TOPIC + "/Logging", headers, msg)
            
        for device_id, values in self.energy_price_values.items():
            headers = get_headers(device_id, "price")
            metadata = {"UnitofMeasure" : "$/kWh", "Timezone" : "America/Los_Angeles"}
            
            self.last_posted_timestamp = max(self.last_posted_timestamp, values[-1][0])
            converted_values = [[jan_1_2015 + int(x[0] * 1000), x[1]] for x in values]   
            converted_values = self.make_square_for_smap(converted_values)         
            msg = {"timeseries" : converted_values, "metadata" : metadata}                           
            
            self.vip.pubsub.publish("pubsub", UPLOAD_REQUEST_TOPIC + "/Logging", headers, msg)
            
        for device_id, values in self.fuel_level_values.items():
            headers = get_headers(device_id, "fuel_level")
            metadata = {"UnitofMeasure" : "%", "Timezone" : "America/Los_Angeles"}
            
            self.last_posted_timestamp = max(self.last_posted_timestamp, values[-1][0])
            converted_values = [[jan_1_2015 + int(x[0] * 1000), x[1]] for x in values]       
            converted_values = self.make_square_for_smap(converted_values)     
            msg = {"timeseries" : converted_values, "metadata" : metadata}                           
            
            self.vip.pubsub.publish("pubsub", UPLOAD_REQUEST_TOPIC + "/Logging", headers, msg)
            
    def check_and_upload_previous_day(self, timestamp):
        """
            If timestamp is greater than one day later than the last uploaded timestamp then upload all data
            and clear out cache
        """
        
        one_day_seconds = 60*60*24
        if timestamp > self.last_posted_timestamp + one_day_seconds:
            self.upload_everything()
            self.reset_cached_values()
            
    @match_start(POWER_USE_TOPIC)
    def on_power_message(self, topic, headers, message, matched):
        message = jsonapi.loads(message[0])
        from_id = headers[headers_mod.FROM]
        timestamp = float(headers["timestamp"])
        power = message["power"]        
        self.check_and_upload_previous_day(timestamp)
        self.power_values[from_id].append([timestamp, power])
    
        
    @match_start(ENERGY_PRICE_TOPIC)
    def on_energy_price_message(self, topic, headers, message, matched):
        message = jsonapi.loads(message[0])
        from_id = headers[headers_mod.FROM]
        timestamp = float(headers["timestamp"])
        energy_price = message["price"]
        self.check_and_upload_previous_day(timestamp)
        self.energy_price_values[from_id].append([timestamp, energy_price])
        
        
    @match_start(FUEL_LEVEL_BASE)
    def on_fuel_level_message(self, topic, headers, message, matched):
        message = jsonapi.loads(message[0])
        from_id = headers[headers_mod.FROM]
        timestamp = float(headers["timestamp"])
        fuel_level = message["fuel_level"]
        self.check_and_upload_previous_day(timestamp)
        self.fuel_level_values[from_id].append([timestamp, fuel_level])
        
    
    #@match_all
    @match_start(PROJECT_BASE)
    def on_project_message(self, topic, headers, message, matched):
        with open("/tmp/LPDM.log", "a") as f:
            f.write("{topic}\t{headers}\t{message}\n\n".format(topic = topic, headers = headers, message = message))
            
    @match_exact(SCENARIO_ID_TOPIC)
    def on_scenario_id_message(self, topic, headers, message, matched):
        message = json.loads(message[0])
        self.scenario_id = message.get("scenario_id", None)
        if self.scenario_id[0] != "/":
            self.scenario_id = "/" + self.scenario_id
        self.last_posted_timestamp = 0
        self.power_values = defaultdict(list)
        self.energy_price_values = defaultdict(list)
        self.fuel_level_values = defaultdict(list)

def main(argv=sys.argv):
    '''Main method called by the eggsecutable.'''
    utils.vip_main(LoggingAgent)


if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv))
    except KeyboardInterrupt:
        pass
