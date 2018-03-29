This repository has VOLTTRON agents that wrap LPDM objects from https://github.com/LBNL-ETA/LPDM to allow them to communicate over the VOLTTRON platform.  It also includes simulation agents for running some or all devices in a LPDM experiment virtually.

For agents that just wrap LPDM objects the VOLTTRON code defines some message topics, handles message serialization, and maps message topics and content to LPDM function calls.

The simulation agents provide miscalanious functionality needed to replace parts of the system that would be real devices with simulated devices.  The main duties are performed by a supervisor agent which handles things that would otherwise "just happen" in hardware.

The "just happens" can, roughly, be divided into two parts:  Managing the setup/teardown of a LPDM run and controlling the time during a simulation.

For the setup of a simulation the Supervisor reads the scenario configuration, creates, and initializes the components described by the configuration.  It can generate simulated versions of any of the LPDM objects.  Or at least those that have been used in the simulations already performed.

During a simulation the supervisor is responsible for setting the time.  In a real physical system each device would do whatever it is going to do whenever it is going to do it.  But in a simulated environment it is desirable to be able to run faster than real time.  For a simulation then the supervisor monitors communication across the VOLTTRON message bus, waits until all devices have finished responding to an action, then calculates the next time a change in the system will occur and advances the simulation time to that point.

Use:  The agents parameters map directly to the underlying LPDM parameters so a config file that works for a LPDM object should work for the corresponding LPDM-VOLTTRON agent.  Aside from that the only requirement is all grid controllers must be started first because the only device discovery is currently done on init.  That is, devices announce their connections when they start but only then.  If a non-grid-controller is started before the grid controller it is connected to the grid controller will not know to connect to the device.