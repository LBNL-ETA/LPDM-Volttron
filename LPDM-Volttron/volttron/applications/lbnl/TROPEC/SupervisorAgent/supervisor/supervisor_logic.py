# -*- coding: utf-8 -*- {{{
# vim: set fenc=utf-8 ft=python sw=4 ts=4 sts=4 et:


#from applications.lbnl.TROPEC.EndUseDeviceAgent.endusedevice.agent import EndUseDeviceAgent 
#from applications.lbnl.TROPEC.GridControllerAgent.gridcontroller.agent import GridControllerAgent
#from applications.lbnl.TROPEC.GeneratorAgent.generator.agent import DieselGeneratorAgent
#from applications.lbnl.TROPEC.SimulationEventsAgent.simulationevents.agent import SimulationEventsAgent

from uuid import uuid4

#Thjis is a hack since it is a back dependency from VOLTTRON code
#can we resolve this with something more general that applies to everything?
TOPIC_TTIE = "TROPEC/time_until_next_event/{id}"


class SupervisorLogic(object):
    def __init__(self, **kwargs):
        import os
        import json
        
        self.messages_waiting_on = {"any" : []}
        self.time = 0
        self.agents_and_subscriptions = {}
        self.terminating_scenario = False        
        self.scenario_end_timestamp = None
        self.end_scenario_run_msg_id = None
        self.finished_callback = kwargs.get("finished_callback", lambda : None)
        self.times_until_next_event = {}        
        self.agent_time_functions = {}

    
    def add_event(self, event):
        self.events.append(event)
        
    def set_end_timestamp(self, end_scenario_timestamp):
        self.scenario_end_timestamp = end_scenario_timestamp
    
    def add_agent(self, agent_id, agent_time_function):
        self.agents_and_subscriptions[agent_id] = []
        #Don't know what the message ID of the initial TTIE because it is generated at agent start and not responding to anything
        #so wait on any message id on the agent's TTIE topic
        if "any" not in self.messages_waiting_on:
            self.messages_waiting_on["any"] = []
        self.messages_waiting_on["any"].append({"topic" : TOPIC_TTIE.format(id = agent_id)})
        self.times_until_next_event[agent_id] = {"responding_to_message_id" : None, "timestamp" : None, "time_until_next_event" : None}
        self.agent_time_functions[agent_id] = agent_time_function
        
    def on_subscription_announcement(self, agent_id, subscriptions):
        self.agents_and_subscriptions[agent_id] = subscriptions

    def get_agents_to_watch_for_response(self, topic):
        agents_to_watch_for_response = []
        for agent_id, subscriptions in self.agents_and_subscriptions.items():
            if topic in subscriptions:
                agents_to_watch_for_response.append(agent_id)
        return agents_to_watch_for_response
                    
    def on_device_change_announcement(self, topic, message_id): 
        agents_to_watch = self.get_agents_to_watch_for_response(topic)
        print "on_device_change topic:\t{t}\t agents to watch:\t{a}".format(t = topic, a = agents_to_watch)
        
        if agents_to_watch:
            self.messages_waiting_on[message_id] = {"agent_ids" : agents_to_watch, "topic" : topic}
    
    def on_finished_processing_announcement(self, agent_id, responding_to, topic):
        print "finished_processing topic:  {t}".format(t=topic)
        print
        print "waiting on:\t{w}".format(w = self.messages_waiting_on)
        print
        
        if topic == "TROPEC/finished_processing/Diesel Generator":
            pass
        
        if responding_to and responding_to in self.messages_waiting_on:
            try:
                del self.messages_waiting_on[responding_to]["agent_ids"][self.messages_waiting_on[responding_to]["agent_ids"].index(agent_id)]
            except:
                pass
            if len(self.messages_waiting_on[responding_to]["agent_ids"]) == 0:
                del self.messages_waiting_on[responding_to]
                
        #if there are no more messages waiting on and the topic is the terminate topic
        #this means that hopefully all the agents generated for this simulation have cleaned
        #themselves up and exited.  Post a message to the dashboard saying the simulation is finished
        #then the supervisor can stop itself.
        if not self.messages_waiting_on and responding_to == self.end_scenario_run_msg_id:
            self.finished_callback()
            return
        
        self.check_all_agents_ready_for_next_time()    
            
    
    def on_time_until_next_event(self, topic, agent_id, message_id, timestamp, responding_to, time_until_next_event):
        for id, vals in self.messages_waiting_on.items():
            if id.lower() =="any":
                for i in range(len(vals)):
                    if topic == vals[i]["topic"]:
                        del self.messages_waiting_on[id][i]
                        break
                if len(self.messages_waiting_on[id]) == 0:
                    del self.messages_waiting_on[id]
            else:
                if id == responding_to and agent_id in vals["agent_ids"]:
                    del self.messages_waiting_on[id]["agent_ids"][self.messages_waiting_on[id]["agent_ids"].index(agent_id)]
                if len(self.messages_waiting_on[id]["agent_ids"]) == 0:
                    del self.messages_waiting_on[id]
                    
                
        self.times_until_next_event[agent_id] = {"message_id" : message_id, "responding_to_message_id" : responding_to, "timestamp" : timestamp, "time_until_next_event" : time_until_next_event}
        self.check_all_agents_ready_for_next_time()
        
    def check_all_agents_ready_for_next_time(self):
        if len(self.messages_waiting_on):
            return
        if self.terminating_scenario:
            self.finished_callback()
            return
        
        earliest_next_event = 1e100
        #last_message_timestamp = self.times_until_next_event.values()[0]["timestamp"]
        for agent_id, values in self.times_until_next_event.items():
            ttie = values["time_until_next_event"]
            message_timestamp = values["timestamp"]
            self.time = max(self.time, message_timestamp)
            if ttie is None:
                return
            if ttie < earliest_next_event:
                earliest_agent = agent_id
                earliest_next_event = ttie
                
        self.send_new_time(earliest_agent, earliest_next_event)
               
    def update_times_until_next_event(self, time_skip):
        for agent_id, vals in self.times_until_next_event.items():
            if vals["time_until_next_event"]:
                self.times_until_next_event[agent_id]["time_until_next_event"] = vals["time_until_next_event"] - time_skip
                
    def end_scenario_run(self):        
        self.terminating_scenario = True
        self.end_scenario_run_msg_id = str(uuid4())             
        
    def send_new_time(self, agent_id, timestamp):        

        message_id = str(uuid4())
        # although there is some fractional processing time assumed for agents to process messages
        # when sending time to agents only send whole number times to avoid problems with slight misses with schedules
        if timestamp > int(timestamp):
            timestamp = int(timestamp) + 1
        self.time += timestamp        
        
        if self.scenario_end_timestamp and self.scenario_end_timestamp < self.time:
            self.end_scenario_run()
            return
        
        self.update_times_until_next_event(timestamp)
        self.times_until_next_event[agent_id] = {"responding_to_message_id" : None, "timestamp" : None, "time_until_next_event" : None}
        
        self.agent_time_functions[agent_id](message_id, timestamp)
        self.messages_waiting_on[message_id] = {"agent_ids" : [agent_id]}
        

