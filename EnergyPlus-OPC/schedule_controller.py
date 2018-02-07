import json
import sys
import time as delay
import OpenOPC
import argparse
from odata_connector import *
import csv
import os

def get_setpoints(building_name, dayTime, setpoints):

	#dayTime is in seconds, csv is in minutes
	time = dayTime/60
	print(time)

	setpoint_arr = setpoints[building_name]
	for schedule in setpoint_arr:
		if schedule[0] >= time:
			return schedule[1:]
	else:
		raise Exception("Setpoint Schedule Invalid for Building %s at time %d".format(building_name, time))

def parse_csv(setpoint_files):
	setpoints = {}
	for file in setpoint_files:
		base = os.path.basename(file)
		name = os.path.splitext(base)[0]
		setpoints[name] = []
		with open(file, 'r') as csvfile:
			reader = csv.reader(csvfile)
			for row in reader:
				setpoints[name].append([float(s) for s in row])
	return setpoints

def setup(status_tag):
	if status is 2 or status is 1:
		write_status(3, status_tag)
		delay.sleep(2)
	write_status(0, status_tag)
	print("Bridge is Ready")

#TODO: Redefine Reset
def reset(status_tag):
	write_status(3, status_tag)
	print("Reseting Bridge")
	delay.sleep(2)
	write_status(0, status_tag)

def kill(status_tag):
	write_status(4, status_tag)
	print("Bridge has been Burned")


def run(mapping_path, output, setpoint_files, status_tag):
	status = read_status(status_tag)

	if status is not 0:
		print("Bridge is not Ready. Call setup first before running the simulation")
		sys.exit(0)

	with open(mapping_path, 'r') as f:
		s = f.read()
		mapping = json.loads(s)


	setpoints = parse_csv(setpoint_files)
	print(setpoints)

	#Initialize
	print(mapping)
	print(mapping.keys())

	output_ready_pairs = get_output_ready_pairs(mapping) #[(building_name, endpoint)]
	ts_pairs = get_time_pairs(mapping) #[(building_name, endpoint)]

	print(ts_pairs)

	output_history = {}
	input_history = {}
	power_history = {}
	for building_name in mapping.keys():
		input_history[building_name] = []
		output_history[building_name] = []
		power_history[building_name] = []

	write_status(1, status_tag)

	""" Simulation Loop """	
	#INVARIANT: All energyplus buildings are on the same timestep, should have same timesteps per hour
	print("Running Simulation")

	EPTimeStep = 4
	SimDays = 1
	kStep = 1
	MAXSTEPS = SimDays*24*EPTimeStep
	deltaT = (60/EPTimeStep)*60;

	num_buildings = len(mapping.keys())
	print("Number of buildings: %d" % num_buildings)
	print("Number of Timesteps: %d" % MAXSTEPS)

	while kStep < MAXSTEPS:

		was_synced = True
		is_synced = True

		time = kStep * deltaT
		dayTime = time % 86400

		print(kStep)
		while not is_synced or was_synced:

			#Determine if a building has outputs that can be read
			ready_building = get_ready_building(output_ready_pairs)
			if ready_building is not None: 
				print(ready_building)

				#Determine setpoints for each building
				building_setpoints = get_setpoints(ready_building, dayTime, setpoints)
				print(building_setpoints)

				#Lookup input tags and write to them				
				time_tag = get_building_timestep(ready_building, mapping)
				input_group = get_input_group(ready_building, mapping)
				write_inputs(input_group, building_setpoints, time_tag, time)

				#Notify bridge that new inputs have been written
				toggle_ready(ready_building, mapping)

				delay.sleep(1)
				#Lookup output tags and read from them. Store them for final output
				output_tags = get_output_group(ready_building, mapping)
				output_values = read_outputs(output_tags)
				output_history[ready_building].append(output_values)
				power_history[ready_building].append(output_values[8])
				print(output_values[2])
				#Edge case in which a single building is always in sync with itself, but kStep should increase
				if num_buildings == 1:
					delay.sleep(1)
					break

			#Determine if all the buildings are on the same timestep
			was_synced = is_synced
			is_synced = time_synced(ts_pairs)

		kStep = kStep + 1

	print("Simulation Finished")

	if output is not None:
		os.mkdir(output)
		for building_name in output_history:
			file = os.path.join(output, building_name) + ".csv"
			with open(file, 'w') as f:
				writ = csv.writer(f)
				for row in output_history[building_name]:
					writ.writerow(row)





if __name__ == "__main__":

	parser = argparse.ArgumentParser(description="Example Controller for Communicating with EnergyPlus over OPC")
	parser.add_argument('--command', '-c', help="Command for Controller: setup, run, reset, kill. See documentation for details") #Command Argument
	parser.add_argument('--mapping', '-m', help="Path to mapping.json file", default="mapping.json") #Path to mapping.json
	parser.add_argument('--output', '-o', help="Enables output saving, in specified file") #Path to output.txt
	parser.add_argument('--server', '-s', help="Name of OPC Server", default="Matrikon.OPC.Simulation.1") #OPC Server Name
	parser.add_argument('--setpoints', '-sp', help="Setpoint Schedule Files", nargs="+")


	args = parser.parse_args()

	if args.command is None:
		print("Command for Controller not specified")
		sys.exit(0)


	if args.setpoints is None:
		setpoint_files = ['LargeHotel.csv', 'LargeOffice.csv']	
	else:
		setpoint_files = args.setpoints;

	print(setpoint_files)
	# Create OpenOPC client and connect to Matrikon OPC server	
	status_tag = "EPSimServer.EnergyPlus.Status"

	opc = connect_to_server(args.server)
	status = read_status(status_tag)

	print(args.mapping)
	if args.command == "setup":
		setup(status_tag)
	elif args.command == "run":
		mapping = {}
		run(args.mapping, args.output, setpoint_files, status_tag)
	elif args.command == "reset":
		reset(status_tag)
	elif args.command == "kill":
		kill(status_tag)
	else:
		print("Command for Controller unknown. Must be setup, run, reset, or kill")
		sys.exit(0)	