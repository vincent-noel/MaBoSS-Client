# coding: utf-8
# MaBoSS (Markov Boolean Stochastic Simulator)
# Copyright (C) 2011-2018 Institut Curie, 26 rue d'Ulm, Paris, France
   
# MaBoSS is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
   
# MaBoSS is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
   
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA 

# Module: maboss/comm.py
# Authors: Eric Viara <viara@sysra.com>
# Date: May-July 2018

import os
import sys
import time
import signal
import socket
import pandas
from pandas.compat import StringIO
from .atexit import register
import matplotlib.pyplot as plt
from time import time

#
# MaBoSS Communication Layer
#

LAUNCH = "LAUNCH"
MABOSS = "MaBoSS-2.0"
NETWORK = "Network:"
CONFIGURATION = "Configuration:"
CONFIGURATION_EXPRESSIONS = "Configuration-Expressions:"
CONFIGURATION_VARIABLES = "Configuration-Variables:"
RETURN = "RETURN"
STATUS = "Status:"
ERROR_MESSAGE = "Error-Message:"
STATIONARY_DISTRIBUTION = "Stationary-Distribution:"
TRAJECTORY_PROBABILITY = "Trajectory-Probability:"
TRAJECTORIES = "Trajectories:"
FIXED_POINTS = "Fixed-Points:"
RUN_LOG = "Run-Log:"

class HeaderItem:

    def __init__(self, directive, _from=None, to=None, value=None):
        self._directive = directive
        self._from = _from
        self._to = to
        self._value = value

    def getDirective(self):
        return self._directive

    def getFrom(self):
        return self._from

    def getTo(self):
        return self._to

    def getValue(self):
        return self._value

class DataStreamer:

    @staticmethod
    def buildStreamData(client_data):
        data = ""
        offset = 0
        o_offset = 0

        header = LAUNCH + " " + MABOSS + "\n"

        config_data = client_data.getConfig()
        offset += len(config_data)
        data += config_data

        (header, o_offset) = DataStreamer._add_header(header, CONFIGURATION, o_offset, offset)

        network_data = client_data.getNetwork()
        offset += len(network_data)
        data += network_data

        (header, o_offset) = DataStreamer._add_header(header, NETWORK, o_offset, offset)

        return header + "\n" + data

    @staticmethod
    def parseStreamData(ret_data, stdout):
        result_data = ResultData()
        magic = RETURN + " " + MABOSS
        magic_len = len(magic)
        if ret_data[0:magic_len] != magic:
            result_data.setStatus(1)
            result_data.setErrorMessage("magic " + magic + " not found in header")
            return result_data

        offset = magic_len
        pos = ret_data.find("\n\n", magic_len)
        if pos < 0:
            result_data.setStatus(2)
            result_data.setErrorMessage("separator double nl found in header")
            return result_data

        offset += 1
        header = ret_data[offset:pos+1]
        data  = ret_data[pos+2:]
        if stdout is not None:
            print("HEADER", header, file=stdout)
            #print("DATA", data[0:200])

        header_items = []
        err_data = DataStreamer._parse_header_items(header, header_items)
        if err_data:
            result_data.setStatus(3)
            result_data.setErrorMessage(err_data)
            return result_data

        for header_item in header_items:
            directive = header_item.getDirective()
            if directive == STATUS:
                result_data.setStatus(int(header_item.getValue()))
            elif directive == ERROR_MESSAGE:
                result_data.setErrorMessage(header_item.getValue())
            else:
                data_value = data[header_item.getFrom():header_item.getTo()+1]
                if directive == STATIONARY_DISTRIBUTION:
                    result_data.setStatDist(data_value)
                elif directive == TRAJECTORY_PROBABILITY:
                    result_data.setProbTraj(data_value)
                elif directive == TRAJECTORIES:
                    result_data.setTraj(data_value)
                elif directive == FIXED_POINTS:
                    result_data.setFP(data_value)
                elif directive == RUN_LOG:
                    result_data.setRunLog(data_value)
                else:
                    result_data.setErrorMessage("unknown directive " + directive)
                    result_data.setStatus(4)
                    return result_data

        return result_data

    @staticmethod
    def _parse_header_items(header, header_items):
        opos = 0
        pos = 0
        while True:
            pos = header.find(':', opos)
            if pos < 0:
                break
            directive = header[opos:pos+1]
            opos = pos+1
            pos = header.find("\n", opos)
            if pos < 0:
                return "newline not found in header after directive " + directive

            value = header[opos:pos]
            opos = pos+1
            pos2 = value.find("-")
            if directive == STATUS or directive == ERROR_MESSAGE:
                header_items.append(HeaderItem(directive = directive, value = value))
            elif pos2 >= 0:
                header_items.append(HeaderItem(directive = directive, _from = int(value[0:pos2]), to = int(value[pos2+1:])))
            else:
                return "dash - not found in value " + value + " after directive " + directive

        return ""

    @staticmethod
    def _add_header(header, directive, o_offset, offset):
        if o_offset != offset:
            header += directive + str(o_offset) + "-" + str(offset-1) + "\n"

        return (header, offset)

class ClientData:

    def __init__(self, network = None, config = None):
        self._network = network
        self._config = config

    def getNetwork(self):
        return self._network

    def getConfig(self):
        return self._config

    def setNetwork(self, network):
        self._network = network

    def setConfig(self, config):
        self._config = config

class ResultData:

    def __init__(self):
        self._status = 0
        self._errmsg = ""
        self._stat_dist = None
        self._prob_traj = None
        self._traj = None
        self._FP = None
        self._runlog = None
        self._prob_traj_dict = None
        self._node_prob_traj_dict = None
        self._time = None

    def setStatus(self, status):
        self._status = status

    def getStatus(self):
        return self._status

    def setErrorMessage(self, errmsg):
        self._errmsg = errmsg

    def getErrorMessage(self):
        return self._errmsg

    def setStatDist(self, data_value):
        self._stat_dist = data_value

    def getStatDist(self):
        return self._stat_dist

    def setProbTraj(self, data_value):
        self._prob_traj = data_value

    def getProbTraj(self):
        return self._prob_traj

    def setTraj(self, data_value):
        self._traj = data_value

    def getTraj(self):
        return self._traj

    def setFP(self, data_value):
        self._FP = data_value

    def getFP(self):
        return self._FP

    def setRunLog(self, data_value):
        self._runlog = data_value

    def getRunLog(self):
        return self._runlog

    def getListOfNodes(self):

        nodes = []
        for state in self.getProbTrajDict().keys():
            if " -- " in state:
                nodes += state.split(" -- ")
            else:
                if state != "<nil>":
                    nodes.append(state)
        return list(set(nodes))

    def getProbTrajDict(self):

        if self._prob_traj_dict is None and self._prob_traj is not None:
            self._build_prob_traj_dict()

        return self._prob_traj_dict

    def getNodeTrajDict(self):

        if self._node_prob_traj_dict is None and self.getProbTrajDict() is not None:
            self._build_node_prob_traj_dict()

        return self._node_prob_traj_dict

    def _build_time(self):

        time_set = set()
        for times in self._prob_traj_dict.values():
            time_set = time_set.union(set(times.keys()))

        self._time = list(time_set)

    def getTime(self):

        if self._time is None:
            self._build_time()

        return self._time

    def _build_node_prob_traj_dict(self):

        self._node_prob_traj_dict = {}

        for node in self.getListOfNodes():
            states = [key for key in self._prob_traj_dict.keys() if node in key.split(" -- ")]
            values = {t: 0 for t in self.getTime()}
            for state in states:
                for t, value in self._prob_traj_dict[state].items():
                    if t in values.keys():
                        existing = values[t]
                    else:
                        existing = 0.0
                    values.update({t: existing + value})

            self._node_prob_traj_dict.update({node: values})

    def _build_prob_traj_dict(self):
        # t0 = time()
        self._prob_traj_dict = {}
        prob_traj = pandas.read_csv(StringIO(self._prob_traj), sep="\t")
        states = {}
        for i, t in prob_traj["Time"].items():

            state = prob_traj.loc[i]["State"]
            proba = prob_traj.loc[i]["Proba"]

            if state not in self._prob_traj_dict.keys():
                self._prob_traj_dict.update({state: {}})

            self._prob_traj_dict[state].update({t: proba})

            ii = 1
            while ("Proba.%d" % ii) in list(prob_traj.keys()):

                state = prob_traj.loc[i]["State.%d" % ii]
                proba = prob_traj.loc[i]["Proba.%d" % ii]

                if not isinstance(state, float):
                    if state not in self._prob_traj_dict.keys():
                        self._prob_traj_dict.update({state: {}})

                    self._prob_traj_dict[state].update({t: proba})
                ii += 1
        # print("Built state prob traj dict in %.2gs" % ((time()-t0)/1000))

    def get_xy_trajectory(self, trajectory):
        xs = []
        ys = []
        for key in sorted(trajectory.keys()):
            xs.append(key)
            ys.append(trajectory[key])
        return (xs, ys)

    def plot_nodes(self, nodes=None, ax=None, title=None, color=None):

        if nodes is None:
            nodes = self.getListOfNodes()

        if ax is None:
            plt.figure()

        tmin = 1e+30
        tmax = 0
        for node in nodes:
            if node in self.getNodeTrajDict().keys():
                values_node = self.get_xy_trajectory(self.getNodeTrajDict()[node])
            else:
                values_node = (self.getTime(), [0]*len(self.getTime()))

            tmin = min(tmin, values_node[0][0])
            tmax = max(tmax, values_node[0][len(values_node[0]) - 1])

            if ax is None:
                plt.plot(values_node[0], values_node[1], color=color)
            else:
                ax.plot(values_node[0], values_node[1], color=color)
        if ax is None:
            plt.legend(nodes)
            plt.xlim(tmin, tmax)
            plt.ylim(-0.05, 1.05)
        else:
            ax.legend(nodes)
            ax.set_xlim(tmin, tmax)
            ax.set_ylim(-0.05, 1.05)
            if title is not None:
                ax.set_title(title)

    def plot_states(self, states=None, ax=None, title=None, color=None):

        if states is None:
            states = self.getProbTrajDict().keys()

        if ax is None:
            plt.figure()

        tmin = 1e+30
        tmax = 0
        for state in states:
            values_state = self.get_xy_trajectory(self.getProbTrajDict()[state])
            tmin = min(tmin, values_state[0][0])
            tmax = max(tmax, values_state[0][len(values_state[0])-1])
            if ax is None:
                plt.plot(values_state[0], values_state[1], color=color)
            else:
                ax.plot(values_state[0], values_state[1], color=color)

        if ax is None:
            plt.legend(states, loc='upper center', bbox_to_anchor=(0.5, -0.05), fancybox=True, shadow=True)
            plt.xlim(tmin, tmax)
            plt.ylim(-0.05, 1.05)
        else:
            ax.legend(states)
            ax.set_xlim(tmin, tmax)
            ax.set_ylim(-0.05, 1.05)
            if title is not None:
                ax.set_title(title)

class MaBoSSClient:
    
    SERVER_NUM = 1 # for now

    def __init__(self, host = None, port = None, maboss_server = None, stdout=sys.stdout):
        if not maboss_server:
            maboss_server = "MaBoSS-server"

        self._maboss_server = maboss_server
        self._host = host
        self._port = port
        self._pid = None
        self._mb = bytearray()
        self._mb.append(0)
        self._pidfile = None
        self._stdout = stdout

        if host == None:
            if port == None:
                port = '/tmp/MaBoSS_pipe_' + str(os.getpid()) + "_" + str(MaBoSSClient.SERVER_NUM)

            self._pidfile = '/tmp/MaBoSS_pidfile_' + str(os.getpid()) + "_" + str(MaBoSSClient.SERVER_NUM)
            MaBoSSClient.SERVER_NUM += 1

            try:
                pid = os.fork()
            except OSError as e:
                print("error fork:", e, file=sys.stderr)
                return

            if pid == 0:
                try:
                    args = [self._maboss_server, "--host", "localhost", "-q", "--port", port, "--pidfile", self._pidfile]
                    os.execv(self._maboss_server, args)
                except e:
                    print("error execv:", e, file=sys.stderr)

            self._pid = pid
            register(self.close)
            server_started = False
            MAX_TRIES = 20
            TIME_INTERVAL = 0.1
            for try_cnt in range(MAX_TRIES):
                if os.path.exists(self._pidfile):
                    server_started = True
                    break
                time.sleep(TIME_INTERVAL)

            if not server_started:
                raise Exception("MaBoSS server on port " + port + " not started after " + str(MAX_TRIES*TIME_INTERVAL) + " seconds")

            self._socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self._socket.connect(port)
        else:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.connect((host, port))
            
    def launch(self, simulation):
        from .result import Result

        return Result(self, simulation, self._stdout)

    def send(self, data):
        self._socket.send(data.encode('utf8'))
        self._term()
        SIZE = 4096
        ret_data = ""
        while True:
            databuf = self._socket.recv(SIZE)
            if not databuf or len(databuf) <= 0:
                break
            ret_data += databuf.decode('utf8')

        return ret_data

    def _term(self):
        self._socket.send(self._mb)

    def close(self):
        if self._pid != None:
            #print("kill", self._pid)
            os.kill(self._pid, signal.SIGTERM)
            if self._pidfile:
                os.remove(self._pidfile)
            self._pid = None
        self._socket.close()
