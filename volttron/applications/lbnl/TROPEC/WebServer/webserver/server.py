import sys
import threading

from volttron.platform.agent import utils
from applications.lbnl.TROPEC.SupervisorAgent.supervisor.agent import SupervisorAgent
from flask import Flask, request

import json
from uuid import uuid1

app = Flask(__name__)

@app.route("/run_simulation")#, methods=['POST'])
def do_tropec_run():
    kwargs = {}
    scenario = None
    
    scenario_params = request.values
    
    with open("/home/bob/workspace/volttron/applications/lbnl/TROPEC/SupervisorAgent/supervisor/scenarios/test_scenario.json", "r") as f:
        scenario_params = json.load(f)
        
    kwargs["scenario"] = scenario_params
    
    if not hasattr(app, "scenario_threads"):
        app.scenario_threads = {}
        
    thread_uuid = uuid1()        
    kwargs["thread_uuid"] = thread_uuid
    #kwargs["kill_thread"] = 
    supervisor_thread = threading.Thread(target = utils.vip_main, 
                             args = (SupervisorAgent, ), 
                             kwargs = kwargs)
    
    app.scenario_threads[thread_uuid] = supervisor_thread
    
    supervisor_thread.start()
    
    return "Success"
    
def kill_thread(thread_uuid):
    if thread_uuid in app.scenario_threads:        
        del app.scenario_threads[thread_uuid]

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)