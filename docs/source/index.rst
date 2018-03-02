.. pyEp documentation master file, created by
   sphinx-quickstart on Fri Feb 23 13:42:24 2018.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.



Welcome to pyEp's documentation!
================================

Introduction
============

This is the documentation for pyEp, a Python module that allows for easy cosimulation between the building energy simulation program EnergyPlus and Python. Also included in this module is the EnergyPlus-OPC bridge service, which allows for EnergyPlus simulation over the OPC communications protocol. pyEp is currently supported for Python 2.7 and 3.X.

Installation
============
pyEp is available on PyPi. Simply type ``pip install pyEp`` if you have pip installed. Otherwise you can download it from the github repo `pyEp`_.

.. _pyEp: https://github.com/mlab-upenn/pyEp


Requirements
============

pyEp
---------
The pyEp core module requires Python 2.7 or 3.x. In order to run a simulation with EnergyPlus, you must have a version of EnergyPlus installed. pyEp has been tested with EnergyPlus 8.1 and 8.4, but should work with any 8.x version. EnergyPlus can be downloaded `here`_ 

.. _here: https://energyplus.net/downloads

EnergyPlus-OPC Bridge
---------------------
The EnergyPlus-OPC bridge uses the pyEp core module to run a simulation across an OPC server. The service uses `OpenOPC`_, which requires pywin32, and pyro3. Additionally, a simulated OPC server software must be installed. The recommended server is the `MatrikonOPC Simulation Server`_.

.. _MatrikonOPC Simulation Server: https://www.matrikonopc.com/products/opc-desktop-tools/index.aspx

.. _OpenOPC: https://openopc.sourceforge.net



Contents
--------
.. toctree::
   :maxdepth: 3

   Home <self>
   quickstart
