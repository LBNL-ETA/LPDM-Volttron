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

start_time_offset = 0

class DashboardLoggingAgent(PublishMixin, BaseAgent):
    def __init__(self, **kwargs):
        super(DashboardLoggingAgent, self).__init__(**kwargs)      
        self.scenario_id = "simulation"
        self.socket_id = kwargs["socket_id"]
        self.server_ip = kwargs["server_ip"]
        self.server_port = kwargs["server_port"]
        self.client_id = kwargs["client_id"]
           
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
        
    def _create_action_payload(self, device_name, values, action, is_initial_event, description, device_uuid):
        action = {}
        action["is_initial_event"] = is_initial_event
        action["description"] = description
        action["device_name"] = device_name
        action["values"] = values
        action["action"] = action
        action["uuid"] = device_uuid
        
        return action
    
    def is_initial_event(self, timestamp):
        return timestamp == int(timestamp)
    
    def post_action(self, timestamp, action):
        import requests
        
        payload = {}
        payload["socket_id"] = self.socket_id
        payload["client_id"] = self.client_id
        payload["actions"] = [action]
        payload["time"] = timestamp
        
    def upload_everything(self):                
        actions = []
        for device_id, values in self.power_values.items():
            for value in values:
                ts = value[0]
                val = value[1]                
                action = self._create_action_payload(device_id, val, "set_power_level", self.is_initial_event(ts), "W", device_id)
                actions.append({"timestamp" : ts, "action" : action})
                        
            
        for device_id, values in self.energy_price_values.items():
            for value in values:
                ts = value[0]
                val = value[1]
                action = self._create_action_payload(device_id, val, "new_electricity_price", self.is_initial_event(ts), "$/kWh", device_id)
                actions.append({"timestamp" : ts, "action" : action})
                
            
        for device_id, values in self.fuel_level_values.items():
            for value in values:
                ts = value[0]
                val = value[1]
                action = self._create_action_payload(device_id, val, "fuel_level", self.is_initial_event(ts), "%", device_id)
                actions.append({"timestamp" : ts, "action" : action})
                
        actions.sort(key = lambda x : x["timestamp"])
        
        for action in actions:
            self.post_action(action["timestamp"], action["action"])
            
    def check_and_upload_previous_day(self, timestamp):
        """
            If timestamp is greater than one day later than the last uploaded timestamp then upload all data
            and clear out cache
        """
        
        one_day_seconds = 60*60*24
        if timestamp > self.last_posted_timestamp + one_day_seconds:
            self.upload_everything()
            self.reset_cached_values()
            
    #@match_start(POWER_USE_TOPIC)
    @PubSub.subscribe("pubsub", POWER_USE_TOPIC)
    def on_power_message(self, peer, sender, bus, topic, headers, message):
        from_id = headers[headers_mod.FROM]
        timestamp = float(headers["timestamp"])
        power = message["power"]        
        self.check_and_upload_previous_day(timestamp)
        self.power_values[from_id].append([timestamp, power])

        
    @PubSub.subscribe("pubsub", ENERGY_PRICE_TOPIC)
    def on_energy_price_message(self, peer, sender, bus, topic, headers, message):
        from_id = headers[headers_mod.FROM]
        timestamp = float(headers["timestamp"])
        energy_price = message["price"]
        self.check_and_upload_previous_day(timestamp)
        self.energy_price_values[from_id].append([timestamp, energy_price])

    @PubSub.subscribe("pubsub", FUEL_LEVEL_BASE)
    def on_fuel_level_message(self, peer, sender, bus, topic, headers, message):
        from_id = headers[headers_mod.FROM]
        timestamp = float(headers["timestamp"])
        fuel_level = message["fuel_level"]
        self.check_and_upload_previous_day(timestamp)
        self.fuel_level_values[from_id].append([timestamp, fuel_level])

    #@match_all
    @PubSub.subscribe("pubsub", BASE)
    def on_message(self, topic, headers, message, matched):
        with open("/tmp/LPDM.log", "a") as f:
            f.write("{topic}\t{headers}\t{message}\n\n".format(topic = topic, headers = headers, message = message))
            
    @PubSub.subscribe("pubsub", SCENARIO_ID_TOPIC)
    def on_scenario_id_message(self, topic, headers, message, matched):
        message = json.loads(message[0])
        self.scenario_id = message.get("scenario_id", None)
        if self.scenario_id[0] != "/":
            self.scenario_id = "/" + self.scenario_id
        self.last_posted_timestamp = 0
        self.power_values = defaultdict(list)
        self.energy_price_values = defaultdict(list)
        self.fuel_level_values = defaultdict(list)
        
    @PubSub.subscribe("pubsub", TERMINATE_TOPIC)
    def on_terminate(self, topic, headers, message, matched):
        self.upload_everything()
        self.reset_cached_values()

def main(argv=sys.argv):
    '''Main method called by the eggsecutable.'''
    utils.vip_main(DashboardLoggingAgent)


if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv))
    except KeyboardInterrupt:
        pass
