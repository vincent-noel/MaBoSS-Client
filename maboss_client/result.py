
#
# class Result example using maboss communication layer: to be merged with pyMaBoSS/maboss/result.py
#

from .comm import ClientData, DataStreamer


class Result:

    def __init__(self, mbcli, simulation, stdout):
        client_data = ClientData(simulation.getNetwork(), simulation.getConfig())

        data = DataStreamer.buildStreamData(client_data)
        #print("sending data", data)

        data = mbcli.send(data)
        #print("received data", data)

        self._result_data = DataStreamer.parseStreamData(data, stdout)

        if stdout is not None:
            print("self._result_data status=", self._result_data.getStatus(), "errmsg=", self._result_data.getErrorMessage(), file=stdout)
            print("FP", self._result_data.getFP(), file=stdout)
            print("Runlog", self._result_data.getRunLog(), file=stdout)

    def getResultData(self):
        return self._result_data

