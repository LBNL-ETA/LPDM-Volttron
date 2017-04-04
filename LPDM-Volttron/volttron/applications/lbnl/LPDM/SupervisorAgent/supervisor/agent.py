# -*- coding: utf-8 -*- {{{
# vim: set fenc=utf-8 ft=python sw=4 ts=4 sts=4 et:


import sys
from volttron.platform.vip.agent import Agent, Core, PubSub, compat
from volttron.platform.agent import utils
from volttron.platform.agent.utils import jsonapi
from volttron.platform.agent.matching import match_start
from volttron.platform.messaging import headers as headers_mod

import threading

from volttron.applications.lbnl.LPDM.EndUseDeviceAgent.endusedevice.agent import EndUseDeviceAgent 
from volttron.applications.lbnl.LPDM.GridControllerAgent.gridcontroller.agent import GridControllerAgent
from volttron.applications.lbnl.LPDM.GeneratorAgent.generator.agent import DieselGeneratorAgent
from volttron.applications.lbnl.LPDM.SimulationEventsAgent.simulationevents.agent import SimulationEventsAgent
from volttron.applications.lbnl.LPDM.BaseAgent.base.topics import *
#from volttron.applications.lbnl.LPDM.SmapInterfaceAgent.smapinterface.agent import SmapInterfaceAgent
from volttron.applications.lbnl.LPDM.SmapInterfaceAgent.smapinterface.settings import *
#from volttron.applications.lbnl.LPDM.SmapInterfaceAgent.smapinterface.topics import QUERY_REQUEST_TOPIC
from volttron.applications.lbnl.LPDM.LoggingAgent.logging.agent import LoggingAgent

from time import sleep
from uuid import uuid4

from supervisor_logic import SupervisorLogic

def log_entry_and_exit(f):
    def _f(*args):        
        print "Entering Supervisor {f}".format(f = f.__name__)
        res = f(*args)
        print "Exited Supervisor {f}".format(f = f.__name__)
        return res
    return _f

class SupervisorAgent(Agent):
    def __init__(self, **kwargs):
        import os
        import json
        
        super(SupervisorAgent, self).__init__(**kwargs)
        self.available_agent_types = {"End_Use_Device" : EndUseDeviceAgent, "Grid_Controller" : GridControllerAgent, "Generator" : DieselGeneratorAgent}
        self.messages_waiting_on = {"any" : []}
        try:
            os.remove("/tmp/LPDM.log")
        except:
            pass                
        self.time = 0
        self.agent_id = "supervisor"
        self.agents_and_subscriptions = {}
        self.terminating_scenatio = False
        
        self.scenario_end_timestamp = None
        self.end_scenario_run_msg_id = None
        self.finished_callback = kwargs.get("finished_callback", None)
        self.logic = SupervisorLogic(finished_callback = self.end_scenario_run)
        
        self.scenario = kwargs.get("scenario", None)
        
        if not self.scenario:
            raise RuntimeError("Missing Scenario")
            

        self.times_until_next_event = {}        
        self.agent_threads = self.process_scenario(self.scenario)
        
        
        
#        self.agent_threads["smap_interface"] = [ threading.Thread(target = utils.vip_main, 
#                                                          args = (SmapInterfaceAgent, ))]  
        
#        self.agent_threads["logging"] = [ threading.Thread(target = utils.vip_main, 
#                                                           args = (LoggingAgent, ))]
        
    @Core.receiver('onstart')
    def on_message_bus_start(self, sender, **kwargs):
        import sys
        if self.events:
            self.agent_threads["events"] = [(-1,  threading.Thread(target = utils.vip_main, 
                                                          args = (SimulationEventsAgent, ),
                                                          kwargs = {"device_id" : "simulation_events_agent", "events" : self.events}))]            
        
        
        
        sleep(2)            
        self.start_agents(self.agent_threads)
        self.grid_controllers = []
        
        
    def clear_smap_streams(self):
        query = "delete where Metadata/SourceName = 'LPDM' and Path like '/{scenario_id}/%';".format(scenario_id = self.scenario_id)
        message = {"query" : query}
        headers = {}
        headers[headers_mod.FROM] = self.agent_id
        headers["SmapRoot"] = "http://elnhv.lbl.gov"
        headers["ApiKey"] = "3EYQy04hlPpA03SixKcRJaIreUrnpdYu9bNn"
        self.vip.pubsub.publish("pubsub", QUERY_REQUEST_TOPIC, headers, message)
        
    def publish_scenario_id(self):
        message = {"scenario_id" : self.scenario_id}
        headers = {}
        headers[headers_mod.FROM] = self.agent_id
        self.vip.pubsub.publish("pubsub", SCENARIO_ID_TOPIC, headers, message)
        
        
    @PubSub.subscribe("pubsub", FINISHED_INITIALIZING_TOPIC_BASE)
    def on_finished_initializing_an_agent(self, peer, sender, bus, topic, headers, message):        
        self.start_agents(self.agent_threads)
        sleep(2)
        
    def start_agents(self, agent_threads):
        """
            Since we are starting these in threads we want to make sure everything is finished initializing before moving on to the next
            Each agent now posts to a finished initializing topic when the constructor is done.
        """                    
        if "smap_interface" in agent_threads:
            for id, t in agent_threads["smap_interface"]:
                if not t.isAlive():
                    t.start()                
                
        if "logging" in agent_threads:        
            for id, t in agent_threads["logging"]:
                if not t.isAlive():
                    t.start()                                                
                
        if "events" in agent_threads:
            for id, t in agent_threads["events"]:
                if not t.isAlive():
                    self.logic.add_agent(id, lambda message_id, ts : self.send_new_time(id, message_id, ts))
                    t.start()
                    return
                    
        self.publish_scenario_id()
        self.clear_smap_streams()
                
        #first start grid_controlelrs.  These are the real managers of the system and so should start first
        if "Grid_Controller" in agent_threads:
            for id, t in agent_threads["Grid_Controller"]:
                if not t.isAlive():
                    self.logic.add_agent(id, lambda message_id, ts : self.send_new_time(id, message_id, ts))
                    t.start()
                    return            
        
        #next start generators.  They are the things that actually provide power so no point having anything
        #using power without something to provide the power
        if "Generator" in agent_threads:
            for id, t in agent_threads["Generator"]:
                if not t.isAlive():
                    self.logic.add_agent(id, lambda message_id, ts : self.send_new_time(id, message_id, ts))
                    t.start()
                    return
            
        #finally start end_use_devices
        if "End_Use_Device" in agent_threads:
            for id, t in agent_threads["End_Use_Device"]:
                if not t.isAlive():
                    self.logic.add_agent(id, lambda message_id, ts : self.send_new_time(id, message_id, ts))
                    t.start()
                    return
                
        #all one starting things up, start the supervisor
#        self.logic.check_all_agents_ready_for_next_time()
                
    def get_dashboard_info(self, scenario):
        res = {}
        res["host"] = scenario.get("server_ip")
        res["port"] = scenario.get("server_port")
        res["socket_id"] = scenario.get("socket_id")                           
        res["client_id"] = scenario.get("client_id")
        
        if res["host"] is None:
            res = None
        
        return res 
        
    def process_scenario(self, scenario):
        import json
        
        if isinstance(scenario, basestring):
            with open(scenario, "r") as f:
                scenario = json.load(f)                    
                    
        agent_threads = {"Grid_Controller" : [], "End_Use_Device" : [], "Generator" : []}
        scenario_id = scenario.get("client_id", None)#["scenario_id"]
        self.scenario_id = scenario_id
        if isinstance(scenario["devices"], basestring):
            components = json.loads(scenario["devices"])#["components"]
        else:
            components = scenario["devices"]
        
        dashboard_info = self.get_dashboard_info(scenario)
            
        #for agent_type, agent_params in scenario.items():
        for component in components:
            component_type = component["type"]
            component_params = component
            component_params["dashboard"] = dashboard_info
            component_params["device_id"] = component_params["device_id"] if component_params["device_id"] else component_params["device_name"]
            if component_type not in self.available_agent_types:
                raise RuntimeError("Unknown scenario parameter:\t{s}".format(s = component_type))
            
            self.agents_and_subscriptions[component_params["device_id"]] = []
            t = threading.Thread(target = utils.vip_main, 
                                 args = (self.available_agent_types[component_type],), 
                                 kwargs = component_params)
                                 
            device_id = component_params["device_id"]
            agent_threads[component_type].append((device_id, t))
            
            
        self.events = []
        if "events" in scenario:
            events = scenario["events"]
            self.events = events
            
        
            
        run_time_days = scenario.get("run_time_days")        
        end_scenario_time = float(run_time_days) * 60 * 60 * 24 if run_time_days else None
                
        if end_scenario_time:
            self.scenario_end_timestamp = end_scenario_time
            
        return agent_threads
    
    @PubSub.subscribe("pubsub", SUBSCRIPTION_TOPIC)
    def on_subscription_announcement(self, peer, sender, bus, topic, headers, message):
        device_id = headers.get(headers_mod.FROM, None)
        subscriptions = message["subscriptions"]
        self.logic.on_subscription_announcement(device_id, subscriptions)
    
    
    def post_fininished_message_to_dashboard(self):
        pass
    
    @PubSub.subscribe("pubsub", FINISHED_PROCESSING_MESSSAGE)
    def on_finished_processing_announcement(self, peer, sender, bus, topic, headers, message):
        #self.on_device_change_announcement(topic, headers, message, matched)
        responding_to = headers.get("responding_to", None)
        device_id = headers.get(headers_mod.FROM, None)
        print "finished_processing topic:\t{t}\theaders:\t{h}".format(t=topic, h=headers)
        print
        print "waiting on:\t{w}".format(w = self.messages_waiting_on)
        print
        
        self.logic.on_finished_processing_announcement(device_id, responding_to, topic)    
        
    @PubSub.subscribe("pubsub", ENERGY_PRICE_TOPIC)
    def on_energy_price_announcement(self, peer, sender, bus, topic, headers, message):
        message_id = headers.get("message_id", None)
        self.logic.on_device_change_announcement(topic, message_id)        
        
    @PubSub.subscribe("pubsub", POWER_USE_TOPIC)
    def on_power_consumption_announcement(self, peer, sender, bus, topic, headers, message):
        message_id = headers.get("message_id", None)
        self.logic.on_device_change_announcement(topic, message_id)
        
    @PubSub.subscribe("pubsub", SET_POWER_TOPIC)
    def on_set_power_announcement(self, peer, sender, bus, topic, headers, message):
        message_id = headers.get("message_id", None)
        self.logic.on_device_change_announcement(topic, message_id)
    
    
    @PubSub.subscribe("pubsub", TIME_UNTIL_NEXT_EVENT_TOPIC_GLOBAL)
    def on_time_until_next_event(self, peer, sender, bus, topic, headers, message):
        agent_id = headers[headers_mod.FROM]
        message_id = headers.get("message_id", None)
        timestamp = headers.get("timestamp", None)
        timestamp = float(timestamp)
        time_until_next_event = float(message["time_until_next_event"])
        responding_to = headers.get("responding_to", None)
        self.logic.on_time_until_next_event(topic, agent_id, message_id, timestamp, responding_to, time_until_next_event)
                
    def end_scenario_run(self):        
        self.terminating_scenatio = True
        self.end_scenario_run_msg_id = str(uuid4()) 
        headers = {"message_id" :  self.end_scenario_run_msg_id}
        headers[headers_mod.FROM] = self.agent_id
        headers["timestamp"] = self.scenario_end_timestamp
        message = {"timestamp" : self.scenario_end_timestamp}
        
        self.vip.pubsub.publish("pubsub", TERMINATE_TOPIC, headers, message)
                    
        
    def send_new_time(self, agent_id, message_id, timestamp):        

        headers = {"message_id" : message_id }
        if timestamp > int(timestamp):
            timestamp = int(timestamp) + 1
        old_time = self.time
        self.time += timestamp        
        
#        if self.scenario_end_timestamp and self.scenario_end_timestamp < self.time:
#            self.end_scenario_run()
#            return
        
        headers[headers_mod.FROM] = self.agent_id
        headers["timestamp"] = self.time
        message = {"timestamp" : self.time}
        #self.times_until_next_event[agent_id] = {"responding_to_message_id" : None, "timestamp" : None, "time_until_next_event" : None}
        self.messages_waiting_on[headers["message_id"]] = {"agent_ids" : [agent_id]}
        self.vip.pubsub.publish("pubsub", SYSTEM_TIME_TOPIC_SPECIFIC_AGENT.format(id = agent_id), headers, message)
        

def main(argv=sys.argv):
    '''Main method called by the eggsecutable.'''
    utils.vip_main(SupervisorAgent)


if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv))
    except KeyboardInterrupt:
        pass
