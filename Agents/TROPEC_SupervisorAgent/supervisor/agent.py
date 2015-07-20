import sys
from volttron.platform.agent import BaseAgent, PublishMixin
from volttron.platform.agent import utils
from volttron.platform.agent.utils import jsonapi
from volttron.platform.agent.matching import match_start
from volttron.platform.messaging import headers as headers_mod

import threading

from Agents.TROPEC_EndUseDeviceAgent.endusedevice.agent import EndUseDeviceAgent
from Agents.TROPEC_GridControllerAgent.gridcontroller.agent import GridControllerAgent
from Agents.TROPEC_GeneratorAgent.generator.agent import GeneratorAgent
from Agents.TROPEC_BaseAgent.base.topics import *
from Agents.SmapInterfaceAgent.smapinterface.settings import *
from Agents.SmapInterfaceAgent.smapinterface.topics import QUERY_REQUEST_TOPIC


class SupervisorAgent(PublishMixin, BaseAgent):
    def __init__(self, **kwargs):
        import os
        
        super(SupervisorAgent, self).__init__(**kwargs)
        self.available_agent_types = {"End_Use_Device" : EndUseDeviceAgent, "Grid_Controller" : GridControllerAgent, "Generator" : GeneratorAgent}
        self.messages_waiting_on = {"any" : []}
        try:
            os.remove("/tmp/TROPEC.log")
        except:
            pass                
        self.time = 0
        self.agent_id = "supervisor"
        self.agents_and_subscriptions = {}

        self.times_until_next_event = {}        
        self.agent_threads = self.process_scenario_file("./Agents/TROPEC_SupervisorAgent/supervisor/scenarios/test_scenario.json")
        self.publish_scenario_id()
        self.clear_smap_streams()        
        self.start_agents(self.agent_threads)
        self.grid_controllers = []
        
        
    def clear_smap_streams(self):
        query = "delete where Metadata/SourceName = 'TROPEC' and Path like '/{scenario_id}/%';".format(scenario_id = self.scenario_id)
        message = {"query" : query}
        headers = {}
        headers[headers_mod.FROM] = self.agent_id
        headers["SmapRoot"] = "http://elnhv.lbl.gov"
        headers["ApiKey"] = "3EYQy04hlPpA03SixKcRJaIreUrnpdYu9bNn"
        self.publish_json(QUERY_REQUEST_TOPIC, headers, message)
        
    def publish_scenario_id(self):
        message = {"scenario_id" : self.scenario_id}
        headers = {}
        headers[headers_mod.FROM] = self.agent_id
        self.publish_json(SCENARIO_ID_TOPIC, headers, message)
        

    def on_finsihed_initializing_an_agent(self, topic, headers, message, matched):
        from time import sleep
        self.start_agents(self.agent_threads)
        sleep(2)
        
    def start_agents(self, agent_threads):
        """
            Since we are starting these in threads we want to make sure everything is finished initializing before moving on to the next
            Each agent now posts to a finished initializing topic when the constructor is done.
        """
        #first start grid_controlelrs.  These are the real managers of the system and so should start first
        for t in agent_threads["Grid_Controller"]:
            if not t.isAlive():
                t.start()
                return
        
        #next start generators.  They are the things that actually provide power so no point having anything
        #using power without something to provide the power
        for t in agent_threads["Generator"]:
            if not t.isAlive():
                t.start()
                return
            
        #finally start end_use_devices
        for t in agent_threads["End_Use_Device"]:
            if not t.isAlive():
                t.start()
                return
        
    def process_scenario_file(self, fname):
        import json
        
        with open(fname, "r") as f:
            scenario = json.load(f)
                    
        agent_threads = {"Grid_Controller" : [], "End_Use_Device" : [], "Generator" : []}
            
        #for agent_type, agent_params in scenario.items():
        for scenario_param, values in scenario.items():
            if scenario_param not in self.available_agent_types:
                if scenario_param.lower() == "scenario_id":
                    self.scenario_id = values
                    continue
                else:
                    raise RuntimeError("Unknown scenario parameter:\t{s}".format(s = scenario_param))
            
            agent_type = scenario_param
            agent_params = values
            self.agents_and_subscriptions[agent_params["device_id"]] = []
            t = threading.Thread(target = utils.default_main, 
                                 args = (self.available_agent_types[agent_type], "{s} Agent started by supervisor".format(s = agent_type)), 
                                 kwargs = agent_params)
                                 
            agent_threads[agent_type].append(t)
            device_id = agent_params["device_id"]
            self.messages_waiting_on["any"].append({"topic" : TIME_UNTIL_NEXT_EVENT_TOPIC_SPECIFIC_AGENT.format(id = device_id)})
            self.times_until_next_event[device_id] = {"responding_to_message_id" : None, "timestamp" : None, "time_until_next_event" : None}
            
        return agent_threads
    
    @match_start(SUBSCRIPTION_TOPIC)
    def on_subscription_announcement(self, topic, headers, message, matched):
        device_id = headers.get(headers_mod.FROM, None)
        message = jsonapi.loads(message[0])
        subscriptions = message["subscriptions"]
        self.agents_and_subscriptions[device_id] = subscriptions
    
    def reset_times_until_next_event(self):
        for agent_id, values in self.times_until_next_event.items():
            self.times_until_next_event[agent_id] = {"responding_to_message_id" : None, "timestamp" : None, "time_until_next_event" : None}


    def get_agents_to_watch_for_response(self, topic):
        agents_to_watch_for_response = []
        for agent_id, subscriptions in self.agents_and_subscriptions.items():
            if topic in subscriptions:
                agents_to_watch_for_response.append(agent_id)
        return agents_to_watch_for_response
                    
    def on_device_change_announcement(self, topic, headers, message, matched):
        timestamp = headers.get("timestamp")
        if timestamp - 7200.006 >= 0:
            qq = 3
            qq
        agents_to_watch = self.get_agents_to_watch_for_response(topic)
        message_id = headers.get("message_id", None)
        device_id = headers.get(headers_mod.FROM, None)
        responding_to = headers.get("responding_to", None)
        
        if agents_to_watch:
            self.messages_waiting_on[message_id] = {"agent_ids" : agents_to_watch}
        
        if responding_to and responding_to in self.messages_waiting_on:
            try:
                del self.messages_waiting_on[responding_to]["agent_ids"][self.messages_waiting_on[responding_to]["agent_ids"].index(device_id)]
            except:
                pass
            if len(self.messages_waiting_on[responding_to]["agent_ids"]) == 0:
                del self.messages_waiting_on[responding_to]
                
    @match_start(FINISHED_PROCESSING_MESSSAGE)
    def on_finished_processing_announcement(self, topic, headers, message, matched):
        self.on_device_change_announcement(topic, headers, message, matched)
        self.check_all_agents_ready_for_next_time()
        
    @match_start(ENERGY_PRICE_TOPIC)
    def on_energy_price_announcement(self, topic, headers, message, matched):
        self.on_device_change_announcement(topic, headers, message, matched)
        
    @match_start(POWER_USE_TOPIC)
    def on_power_consumption_announcement(self, topic, headers, message, matched):
        self.on_device_change_announcement(topic, headers, message, matched)
        
    @match_start(SET_POWER_TOPIC)
    def on_set_power_announcement(self, topic, headers, message, matched):
        self.on_device_change_announcement(topic, headers, message, matched)
    
    
    @match_start(TIME_UNTIL_NEXT_EVENT_TOPIC_GLOBAL)
    def on_time_until_next_event(self, topic, headers, message, matched):
        message = jsonapi.loads(message[0])
        agent = headers[headers_mod.FROM]
        message_id = headers.get("message_id", None)
        timestamp = headers.get("timestamp", None)
        timestamp = float(timestamp)
        time_until_next_event = float(message["time_until_next_event"])
        responding_to = headers.get("responding_to", None)
        
        for id, vals in self.messages_waiting_on.items():
            if id.lower() =="any":
                for i in range(len(vals)):
                    if topic == vals[i]["topic"]:
                        del self.messages_waiting_on[id][i]
                        break
                if len(self.messages_waiting_on[id]) == 0:
                    del self.messages_waiting_on[id]
            else:
                if id == responding_to and agent in vals["agent_ids"]:
                    del self.messages_waiting_on[id]["agent_ids"][self.messages_waiting_on[id]["agent_ids"].index(agent)]
                if len(self.messages_waiting_on[id]["agent_ids"]) == 0:
                    del self.messages_waiting_on[id]
                    
                
        self.times_until_next_event[agent] = {"message_id" : message_id, "responding_to_message_id" : responding_to, "timestamp" : timestamp, "time_until_next_event" : time_until_next_event}
    def check_all_agents_ready_for_next_time(self):
        if len(self.messages_waiting_on):
            return
        earliest_next_event = 1e100
        last_message_timestamp = self.times_until_next_event.values()[0]["timestamp"]
        for agent_id, values in self.times_until_next_event.items():
            ttie = values["time_until_next_event"]
            message_timestamp = values["timestamp"]
            self.time = max(self.time, message_timestamp)
            if not ttie:
                return
            if ttie < earliest_next_event:
                earliest_agent = agent_id
                earliest_next_event = ttie
                
        self.send_new_time(earliest_agent, earliest_next_event)
               
    def update_times_until_next_event(self, time_skip):
        for agent_id, vals in self.times_until_next_event.items():
            if vals["time_until_next_event"]:
                self.times_until_next_event[agent_id]["time_until_next_event"] = vals["time_until_next_event"] - time_skip
        
    def send_new_time(self, agent_id, timestamp):
        from uuid import uuid1

        headers = {"message_id" : str(uuid1()) }
        self.time += timestamp
        headers[headers_mod.FROM] = self.agent_id
        headers["timestamp"] = self.time
        message = {"timestamp" : self.time}
        self.times_until_next_event[agent_id] = {"responding_to_message_id" : None, "timestamp" : None, "time_until_next_event" : None}
        self.update_times_until_next_event(timestamp)
        self.messages_waiting_on[headers["message_id"]] = {"agent_ids" : [agent_id]}
        self.publish_json(SYSTEM_TIME_TOPIC_SPECIFIC_AGENT.format(id = agent_id), headers, message)
        

def main(argv=sys.argv):
    '''Main method called by the eggsecutable.'''
    utils.default_main(SupervisorAgent,
                       description='TROPEC Supervisor Agent',
                       argv=argv)


if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv))
    except KeyboardInterrupt:
        pass
