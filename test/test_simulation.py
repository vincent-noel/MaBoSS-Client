from unittest import TestCase
from maboss_client import MaBoSSClient, Simulation
from os.path import dirname, join


class TestSimulation(TestCase):

	def testSimulation(self):

		TESTLOC = join(dirname(__file__), "files")

		mbcli = MaBoSSClient(host="localhost", port=7777)


		simulation = Simulation(
			bndfile=TESTLOC + "/cellcycle.bnd",
			cfgfiles=[TESTLOC + "/cellcycle_runcfg.cfg"]
		)

		result = mbcli.launch(simulation)
		mbcli.close()
