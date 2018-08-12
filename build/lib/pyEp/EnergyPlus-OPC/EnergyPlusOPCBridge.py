import OpenOPC
import pyEp
import json
import sys, os
import time as delay
import argparse

def find_ts_tag(building_name, mapping):
	controls = mapping[building_name]["Control"]
	ts = [s for s in controls if "TimeStep" in s]
	return ts[0]

def find_input_group(building_name, mapping):
	return mapping[building_name]["Inputs"]
	
def find_output_group(building_name, mapping):
	return mapping[building_name]["Outputs"]

def find_input_rdy(building_name, mapping):
	controls = mapping[building_name]["Control"]
	inp = [s for s in controls if "InputRdy" in s]
	return inp[0]

def find_output_rdy(building_name, mapping):
	controls = mapping[building_name]["Control"]
	out = [s for s in controls if "OutputRdy" in s]
	return out[0]



def map_outputs(building_name, outputs, mapping):

	"""
	Maps outputs from EnergyPlus to OPC tags
	
	Inputs:
	building_name- The name of the building
	outputs- List of values from EnergyPlus
	Outputs:
	[(OPC_tag, value)]- List of tuples of tags and values
	"""
	output_tags = mapping[building_name]["Outputs"]
	ret = []
	for tag, value in zip(output_tags, outputs):
		ret.append((tag, value))

	return ret

def map_inputs(building_name, inputs, mapping):
	"""
	Maps inputs from OPC server to EnergyPlus

	Inputs:
	building_name- The name of the building
	inputs- [(name, value, status, timestamp)] from opc
	Outputs:
	[value]- List of values, in the order specified by E+
	"""
	input_tags = mapping[building_name]["Inputs"]
	ret = []
	for tag in input_tags:
		matching_input = [t for t in inputs if t[0] == tag]
		ret.append(matching_input[0][1])

	return ret



#Wrapper fuction in case of timeout
#Unclear what the cause of timeout is, but trying again usually works
def opc_read(payload, opc):
	attempts = 0
	values = None
	while values is None and attempts < 5:
		try:
			values = opc.read(payload, timeout=1000)
		except OpenOPC.TimeoutError as err:
			print("Caught Timeout Error, trying again")
			attempts = attempts + 1

	if values is None:
		raise Exception("OpenOPC.TimeoutError ocurred too many times. Check that the OPC server is still running, or restart the Bridge")
			
	return values

#Container Class	
class Building:

	def __init__(self, name, ep, output, input, start_tag, end_tag, timestep):
		self.name = name
		self.ep = ep
		#OPC Tags
		self.input_group = input
		self.input_rdy = start_tag
		self.output_rdy = end_tag
		self.timestep = timestep


def run(path, mapping_path, server, eplus_config, default):

	with open(mapping_path, 'r') as f:
		s = f.read()
		mapping = json.loads(s)

	opc = OpenOPC.open_client()
	opc.connect(server)
	print("Connected to: " + server)

	#Default EnergyPlus Version to 8-4-0
	pyEp.set_eplus_dir(default)
	path_to_buildings = path
	
	buildings = []

	command = ""
	prev_command = ""
	while True:
		command,_,_ = opc_read('EPSimServer.EnergyPlus.Status', opc)
		command = int(command)
		print(command)
		if command is not prev_command:
			if command is 0: #setup
				print("Setup")
				builder = pyEp.socket_builder(path_to_buildings)
				configs = builder.build() #[port, building_folder_path, idf]

				#Setup EnergyPlus instances for each building
				for config in configs:
					building_path = config[1]

					building_name = os.path.normpath(building_path).split(os.sep)[-1] 
					print(building_name)

					#Set weather file and EnergyPlus version
					weather_file = eplus_config[building_name][0]
					eplus_path = None
					print(weather_file)
					if len(eplus_config[building_name]) > 1 and eplus_config[building_name][1] is not '':
						eplus_path = eplus_config[building_name][1]

					print(eplus_path)
					ep = pyEp.ep_process('localhost', config[0], building_path, weather_file, eplus_path)

					output = find_output_group(building_name, mapping)
					output_rdy = find_output_rdy(building_name, mapping)
					input = find_input_group(building_name, mapping)
					input_rdy = find_input_rdy(building_name, mapping)
					ts = find_ts_tag(building_name, mapping)

					buildings.append(Building(building_name, ep, output, input, input_rdy, output_rdy, ts))
					opc.write((ts, 0))
					opc.write((input_rdy, 0))
					opc.write((output_rdy, 0))

				print("E+ Iniitalized, Waiting for Start Signal")
			elif command is 2:
				print("EnergyPlus Simulation finished")
			elif command is 3: #reset
				print("Reset")
				for building in buildings:
					building.ep.close()
					delay.sleep(1)
				buildings = []
				delay.sleep(1)
			elif command is 4: #close
				print("Closing")
				for building in buildings:
					building.ep.close()	
				opc.remove(opc.groups())
				opc.close()
				break
				sys.exit(0)
		elif command is 1:
			for building in buildings:
				building_name = building.name
				ep = building.ep
				input_group = building.input_group #OPC group for easy reading from tags
				output_rdy = building.output_rdy
				input_rdy = building.input_rdy
				timestep_tag = building.timestep
				print(building_name)
				outputs = ep.decode_packet_simple(ep.read())
				print("Writing Outputs")
				output_mapping = map_outputs(building_name, outputs, mapping) # Mapping is in (k, v) of TagNames, Value
				for tag, value in output_mapping:
					opc.write((tag, value))

				#Notify controller that outputs are ready
				opc.write((output_rdy, 1))

				print("Waiting for new inputs")
				#Wait for controller to write new inputs

				inputs_ready = int(opc_read(input_rdy, opc)[0])
				while inputs_ready is not 1:
					inputs_ready = int(opc_read(input_rdy, opc)[0])
					temp_command,_,_ = opc_read('EPSimServer.EnergyPlus.Status', opc)
					temp_command = int(temp_command)
					if temp_command is not command:
						print("Got Interrupt")
						break

				print("Sending inputs to EnergyPlus")
				inputs = opc_read(input_group, opc) # [(name, value, status, time)]
				#print(inputs)
				setpoints = [sp for (_, sp, _, _ ) in inputs]
				input_mapping = map_inputs(building_name, inputs, mapping) #input_mapping is a list of the values of the tags, in order
				time, _, _ = opc_read(timestep_tag, opc)
				encoded_packet = ep.encode_packet_simple(input_mapping, time)
				ep.write(encoded_packet)
				inputs_ready = opc.write((input_rdy, 0))

		prev_command = command

if __name__ == "__main__":

	parser = argparse.ArgumentParser(description="Bridge service connecting EnergyPlus to OPC tags")
	parser.add_argument('--path', '-p', help="Absolute Path to EnergyPlus buildings") #Buildings to connect
	parser.add_argument('--mapping', '-m', help="Path to mapping.json file", default="mapping.json") #Path to mapping.json
	parser.add_argument('--server', '-s', help="Name of OPC Server", default="Matrikon.OPC.Simulation.1") #OPC Server Name
	parser.add_argument('--config', '-c', help="Path to config.cfg", default="config.cfg") #Weather File
	parser.add_argument('--default', '-d', help="Path to default EnergyPlus version")

	args = parser.parse_args()

	config = {}
	print(args.config)
	print(args.path)
	print(args.server)
	config_file = args.config
	if config_file.startswith("'") and config_file.endswith("'"):
		config_file = config_file[1:-1]

	print(config_file)

	with open(config_file, 'r') as f:
		for line in f:
			comp = line[:-2].split(',')
			print(comp)
			config[comp[0]] = comp[1:]

	if args.path is None:
		path = os.path.join(os.getcwd(), "ePlusBuildings")
	else:
		path = args.path

	run(path, args.mapping, args.server, config, args.default)