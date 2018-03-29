# -*- coding: utf-8 -*- {{{
# vim: set fenc=utf-8 ft=python sw=4 ts=4 sts=4 et:

# Copyright (c) 2016, Battelle Memorial Institute
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in
#    the documentation and/or other materials provided with the
#    distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# The views and conclusions contained in the software and documentation
# are those of the authors and should not be interpreted as representing
# official policies, either expressed or implied, of the FreeBSD
# Project.
#
# This material was prepared as an account of work sponsored by an
# agency of the United States Government.  Neither the United States
# Government nor the United States Department of Energy, nor Battelle,
# nor any of their employees, nor any jurisdiction or organization that
# has cooperated in the development of these materials, makes any
# warranty, express or implied, or assumes any legal liability or
# responsibility for the accuracy, completeness, or usefulness or any
# information, apparatus, product, software, or process disclosed, or
# represents that its use would not infringe privately owned rights.
#
# Reference herein to any specific commercial product, process, or
# service by trade name, trademark, manufacturer, or otherwise does not
# necessarily constitute or imply its endorsement, recommendation, or
# favoring by the United States Government or any agency thereof, or
# Battelle Memorial Institute. The views and opinions of authors
# expressed herein do not necessarily state or reflect those of the
# United States Government or any agency thereof.
#
# PACIFIC NORTHWEST NATIONAL LABORATORY
# operated by BATTELLE for the UNITED STATES DEPARTMENT OF ENERGY
# under Contract DE-AC05-76RL01830
# }}}
from __future__ import absolute_import, print_function

import datetime
import errno
import inspect
import logging
import os, os.path
from pprint import pprint
import re
import sys
import cPickle

from volttron.platform.vip.agent import Core, Agent
from volttron.platform.agent import utils
from volttron.platform import jsonrpc

from applications.lbnl.LPDM.BaseAgent.base.topics import *
from lpdm_event import LpdmPowerEvent


utils.setup_logging()
_log = logging.getLogger(__name__)
__version__ = '0.1'

# Set the bath based upon the currently executing file.  This allows us to
# debug through pycharm, but still have the reference correct when we deploy
# through the normal VOLTTRON control mechanisms.
MY_PATH = os.path.dirname(__file__)
WEBROOT = os.path.join(MY_PATH, "webroot")


class SimpleWebAgent(Agent):
    """
    A simple web enabled agent that will hook up with a volttron message bus
    and allow interaction between it via http.  This example agent shows a
    simple file serving agent, a json-rpc based call, and a websocket based
    connection mechanism.
    """

    def __init__(self, config_path, **kwargs):
        super(SimpleWebAgent, self).__init__(enable_web=True,
                                             **kwargs)
        self.smarthubs = {}

    @Core.receiver("onstart")
    def starting(self, sender, **kwargs):
        """
        Register routes for use through http.

        :param sender:
        :param kwargs:
        :return:
        """

        _log.debug("Starting: {}".format(self.__class__.__name__))

        ####################################################################
        # Path based registration examples
        #
        # Files will need to be in webroot/simpleweb in order for them to be
        # browsed from http://localhost:8080/simpleweb/index.html
        #
        # Note: filename is required as we don't currently autoredirect to
        # any default pages.
        self.vip.web.register_path("/simpleweb", os.path.join(WEBROOT))

        # Files will need to be  in webroot to use within the browser at
        # http://localhost:8080/index.html
        # self.vip.web.register_path("/", os.path.join(WEBROOT))

        self.vip.web.register_endpoint("/register_smarthub", self.register_smarthub)
        self.vip.web.register_endpoint("/smarthub_power_use", self.smarthub_power_use)
        

    def text(self, env, data):
        return "This is some text", [("Content-Type", "text/html")]
    
    def register_smarthub(self, env, data):
        id = ""
        address = ""
        grid_controller = ""
        self.smarthubs[id] = {"address" : address, "grid_controller" : grid_controller}
        return "{id} has been registered to {ip}".format(id=id, ip=address)
    
    def smarthub_power_use(self, env, data):
        id = ""
        power_use = ""
        
        
        message = LpdmPowerEvent(id, target_device_id, time, value)
        
        
        self.smarthubs[id] = address
        return "{id} has been registered to {ip}".format(id=id, ip=address)

    


def main():
    utils.vip_main(SimpleWebAgent)


if __name__ == '__main__':
    # Entry point for script
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        pass