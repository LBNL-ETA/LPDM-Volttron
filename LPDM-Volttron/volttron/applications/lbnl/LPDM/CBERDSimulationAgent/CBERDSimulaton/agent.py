# -*- coding: utf-8 -*- {{{
# vim: set fenc=utf-8 ft=python sw=4 ts=4 sts=4 et:

import logging

logging.basicConfig()

import os

import sys
import cPickle
import threading
from time import sleep

from volttron.platform.vip.agent import Agent, PubSub, Core
from volttron.platform.agent import utils
from volttron.platform.agent.utils import jsonapi
from volttron.platform.agent.matching import match_start
from volttron.platform.messaging import headers as headers_mod

from applications.lbnl.LPDM.EndUseDeviceAgent.endusedevice.agent import EndUseDeviceAgent
from applications.lbnl.LPDM.GridControllerAgent.gridcontroller.agent import GridControllerAgent
from applications.lbnl.LPDM.PowerSourceAgent.powersource.agent import PowerSourceAgent
from applications.lbnl.LPDM.SimulationEventsAgent.simulationevents.agent import SimulationEventsAgent
from applications.lbnl.LPDM.BaseAgent.base.topics import *
from applications.lbnl.LPDM.TalkingClockAgent.TalkingClock.agent import LPDM_TalkingClock
from applications.lbnl.LPDM.SmapUploaderAgent.SmapUploader.agent import SmapUploaderAgent


def log_entry_and_exit(f):
    def _f(*args):
        print "Entering Supervisor {f}".format(f=f.__name__)
        res = f(*args)
        print "Exited Supervisor {f}".format(f=f.__name__)
        return res

    return _f


EUD = "euds"
GRID_CONTROLLER = "grid_controllers"
POWER_SOURCE = "power_sources"


class CBERDSimulation(Agent):
    def __init__(self, config_path, **kwargs):
        import os
        import json

        super(CBERDSimulation, self).__init__(**kwargs)
        self.available_agent_types = {EUD: EndUseDeviceAgent,
                                      GRID_CONTROLLER: GridControllerAgent,
                                      POWER_SOURCE: PowerSourceAgent}
        self.messages_waiting_on = {"any": []}
        try:
            os.remove("/tmp/LPDM.log")
        except:
            pass
        self.time = 0
        self.agent_id = "CBERD_supervisor"
        self.terminating_scenatio = False

        self.scenario_end_timestamp = None
        self.end_scenario_run_msg_id = None
        self.finished_callback = kwargs.get("finished_callback", None)

        self.scenario = kwargs.get("scenario", None)

        if not self.scenario:
            # raise RuntimeError("Missing Scenario")
            fname = "/home/pi/LPDM/scenarios/utility_meter_only.json"
            with open(fname, "r") as f:
                self.scenario = json.load(f)

        self.times_until_next_event = {}
        self.agent_threads = self.process_scenario(self.scenario)

        self.agent_threads["smap_uploader"] = [(-3, threading.Thread(target=utils.vip_main,
                                                                     args=(SmapUploaderAgent,)))]

    #        self.agent_threads["logging"] = [ threading.Thread(target = utils.vip_main,
    #                                                           args = (LoggingAgent, ))]

    @Core.receiver('onstart')
    def on_message_bus_start(self, sender, **kwargs):
        import sys
        if self.events:
            self.agent_threads["events"] = [(-1, threading.Thread(target=utils.vip_main,
                                                                  args=(SimulationEventsAgent,),
                                                                  kwargs={"device_id": "simulation_events_agent",
                                                                          "events": self.events}))]

        self.agent_threads["clock"] = [(-2, threading.Thread(target=utils.vip_main,
                                                             args=(LPDM_TalkingClock,),
                                                             kwargs={"device_id": "talking_clock"}))]
        self.start_agents(self.agent_threads)
        self.grid_controllers = []

    def publish_scenario_id(self):
        message = {"scenario_id": self.scenario_id}
        headers = {headers_mod.FROM: self.agent_id}
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
        # if "smap_uploader" in agent_threads:
        for id, t in agent_threads.get("smap_uploader", []):
            if not t.isAlive():
                t.start()

                # if "logging" in agent_threads:
        for id, t in agent_threads.get("logging", []):
            if not t.isAlive():
                t.start()

                # if "events" in agent_threads:

        for id, t in agent_threads.get("events", []):
            if not t.isAlive():
                t.start()

        for id, t in agent_threads.get("clock", []):
            if not t.isAlive():
                t.start()

        self.publish_scenario_id()

        # first start grid_controllers.  These are the real managers of the system and so should start first
        for id, t in agent_threads.get(GRID_CONTROLLER, []):
            if not t.isAlive():
                t.start()
                # return

        # sleep(1)
        # next start generators.  They are the things that actually provide power so no point having anything
        # using power without something to provide the power
        for id, t in agent_threads.get(POWER_SOURCE, []):
            if not t.isAlive():
                t.start()
                #                return

        # sleep(1)
        # finally start end_use_devices
        for id, t in agent_threads.get(EUD, []):
            if not t.isAlive():
                t.start()

    def get_dashboard_info(self, scenario):
        res = {"host": scenario.get("server_ip"), "port": scenario.get("server_port"),
               "socket_id": scenario.get("socket_id"), "client_id": scenario.get("client_id")}

        if res["host"] is None:
            res = None

        return res

    def process_scenario(self, scenario):
        import json

        if isinstance(scenario, basestring):
            with open(scenario, "r") as f:
                scenario = json.load(f)

        agent_threads = {GRID_CONTROLLER: [], EUD: [], POWER_SOURCE: []}
        scenario_id = scenario.get("client_id", None)  # ["scenario_id"]
        self.scenario_id = scenario_id
        if isinstance(scenario["devices"], basestring):
            device_categories_and_devices = json.loads(scenario["devices"])  # ["components"]
        else:
            device_categories_and_devices = scenario["devices"]

        dashboard_info = self.get_dashboard_info(scenario)

        # for agent_type, agent_params in scenario.items():
        for device_category, device_list in device_categories_and_devices.iteritems():
            for device in device_list:
                device_type = device["device_type"]
                device_params = device
                device_params["dashboard"] = dashboard_info
                device_params["device_id"] = device_params["device_id"] if device_params["device_id"] else \
                    device_params["device_name"]
                if device_category not in self.available_agent_types:
                    raise RuntimeError("Unknown scenario parameter:\t{s}".format(s=device_category))

                t = threading.Thread(target=utils.vip_main,
                                     args=(self.available_agent_types[device_category],),
                                     kwargs=device_params)

                device_id = device_params["device_id"]
                agent_threads[device_category].append((device_id, t))

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

    def post_fininished_message_to_dashboard(self):
        pass

    @PubSub.subscribe("pubsub", FINISHED_PROCESSING_MESSSAGE)
    def on_finished_processing_announcement(self, peer, sender, bus, topic, headers, message):
        responding_to = headers.get("responding_to", None)
        device_id = headers.get(headers_mod.FROM, None)

    @PubSub.subscribe("pubsub", ENERGY_PRICE_TOPIC)
    def on_energy_price_announcement(self, peer, sender, bus, topic, headers, message):
        message_id = headers.get("message_id", None)
        message = cPickle.loads(message)

    @PubSub.subscribe("pubsub", POWER_USE_TOPIC)
    def on_power_change_announcement(self, peer, sender, bus, topic, headers, message):
        message_id = headers.get("message_id", None)
        message = cPickle.loads(message)

    @PubSub.subscribe("pubsub", TIME_UNTIL_NEXT_EVENT_TOPIC_GLOBAL)
    def on_time_until_next_event(self, peer, sender, bus, topic, headers, message):
        agent_id = headers[headers_mod.FROM]
        message_id = headers.get("message_id", None)
        timestamp = headers.get("timestamp", None)
        timestamp = float(timestamp)
        message = cPickle.loads(message)
        time_until_next_event = float(message.value)
        responding_to = headers.get("responding_to", None)


def main(argv=sys.argv):
    '''Main method called by the eggsecutable.'''
    utils.vip_main(CBERDSimulation)


if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv))
    except KeyboardInterrupt:
        pass
