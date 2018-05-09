from setuptools import setup, find_packages
# To use a consistent encoding
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

setup(
	name='pyEp',
	version='0.9.4.2',
	description='pyEp: EnergyPlus cosimulation in Python',
	long_description=long_description,
	url='',
	author='Derek Nong',
	author_email='dnong@sas.upenn.edu',
	license='MIT',
	classifiers=[
	'Development Status :: 4 - Beta',
	'Intended Audience :: Science/Research',
	'License :: OSI Approved :: MIT License',
	'Programming Language :: Python :: 2.7',
	'Programming Language :: Python :: 3.5'
	],
	keywords='EnergyPlus simulation',
	packages=['pyEp'],
	package_dir={'pyEp': 'pyEp'},
	include_package_data=True
	)