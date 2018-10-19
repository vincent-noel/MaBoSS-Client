
from setuptools import setup, find_packages

setup(name='maboss_client',
	version="0.6.3",
	packages=find_packages(exclude=["test"]),
	py_modules = ["maboss_client"],
	author="Vincent Noël",
	author_email="contact@vincent-noel.fr",
	description="A python Client for MaBoSS Server",
	install_requires = [
		"pandas",
		"matplotlib",
	])
