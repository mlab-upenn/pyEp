import OpenOPC

def write_status(status, status_tag):
	""" 
	Writes the status of the simulation to the opc tag

	Arguments
		status -- the integer status to write. 0 is setup, 1 is simulating, 2 is simulation finished, 3 is resetting, 4 is closed

	"""
	opc.write((status_tag, status))

def read_status(status_tag):
	""" 
	Reads the status of the simuation

	Returns
		status -- the integer status

	"""
	return int(opc.read(status_tag, timeout=1000)[0])


def get_ready_building(output_ready_pairs):
	""" 
	Determines which building is to be advanced next

	Arguments
		output_ready_pairs -- list of tuples of (building_name, opc_tag), where opc_tag is the output_ready tag of a building

	Returns
		building_name -- the name of the first ready building, or None if no buildings are ready
	"""
	tags = [pair[1] for pair in output_ready_pairs]
	values = opc_read(tags)
	
	for i, value in enumerate(values):
		if int(value[1]) is 1:
			return output_ready_pairs[i][0]
	return None



def get_input_group(building_name, mapping):
	"""
	Gets input tags for a specified building

	Arguments
		building_name -- the name of the building

	Returns
		input_group -- list of opc_tags, in the order specified by mapping.json, corresponding to the inputs of the specified building
	"""
	return mapping[building_name]["Inputs"]


def get_building_timestep(building_name, mapping):
	"""
	Gets the timestep tag for a specified building

	Arguments
		building_name -- the name of the building

	Returns
		timestep_tag -- the timestep_tag corresponding to the specified building
	"""
	controls = mapping[building_name]["Control"]
	for tag in controls:
		if "TimeStep" in tag:
			return tag

def write_inputs(input_group, setpoints, time_tag, time):
	"""
	Writes the new setpoints and simulation time to the corresponding opc tags

	Arguments
		input_group -- list of opc_tags, in the order specified by mapping.json, corresponding to the inputs of the specified building
		setpoints -- list of new setpoint values, in the order specified by mapping.json
		time_tag -- the timestep_tag
		time -- the new time to write, in seconds
	"""
	payload = zip(input_group, setpoints)
	payload.append((time_tag, time))
	opc.write(payload)

def write(tags, values):
	"""
	Writes the values to the tags
	
	Arguments
		tags -- list of opc_tags, in the order specified by mapping.json, corresponding to the inputs of the specified building
		values -- list of new values, in the order specified by mapping.json
	
	"""
	if not isinstance(tags, list):
		tags = [tags]

	if not isinstance(values, list):
		values = [values]

	payload = zip(tags, values)
	opc.write(payload)

def toggle_ready(building_name, mapping):
	"""
	Marks new inputs are ready, and signifies that outputs are read.

	Arguments
		building_name -- the name of the building
	"""
	controls = mapping[building_name]["Control"]
	tags = [s for s in controls if "InputRdy" in s or "OutputRdy" in s]
	values = [1, 0]
	payload = zip(tags, values)
	opc.write(payload)


def get_output_group(building_name, mapping):
	"""
	Gets output tags for a specified building

	Arguments
		building_name -- the name of the building

	Returns
		output_group -- list of opc_tags, in the order specified by mapping.json, corresponding to the outputs of the specified building
	"""
	return mapping[building_name]["Outputs"]


def read_outputs(output_tags):
	"""
	Reads the new outputs from the specified opc tags

	Arguments
		output_tags -- list of output_tags to read

	Returns
		values -- list of float values, in order
	"""	
	values = opc_read(output_tags)

	return [float(value[1]) for value in values]


def read(tags):
	"""
	Reads the new outputs from the specified opc tags

	Arguments
		output_tags -- list of output_tags to read

	Returns
		values -- list of float values, in order
	"""	
	values = opc_read(tags)

	return [float(value[1]) for value in values]


def time_synced(time_pairs):
	"""
	Determines if all buildings are at the same timestep

	Arguments
		time_pairs -- list of tuples of (building_name, timestep_tag)

	Returns
		synced -- True or False, if all buildings are at the same timestep
	"""
	tags = [pair[1] for pair in time_pairs]
	values = opc_read(tags)

	first = values[0][1]	
	for value in values:
		if value[1] is not first:
			return False
	return True


def get_output_ready_pairs(mapping):
	"""
	Gets a list of the output ready tags for all buildings

	Returns
		output_ready_pairs -- list of tuples (building_name, output_ready_tag) for each building, in the order specified by mapping.json

	"""
	output_group = []
	for building_name in mapping.keys():
		controls = mapping[building_name]["Control"]
		outputrdy = [s for s in controls if "OutputRdy" in s]
		output_group.append((building_name, outputrdy[0]))
	return output_group


def get_time_pairs(mapping):
	"""
	Gets a list of the timestep_tags for all buildings

	Returns
		time_pairs -- list of tuples of (building_name, timestep_tag), in the order specified by mapping.json
	"""
	ts_group = []
	for building_name in mapping.keys():
		controls = mapping[building_name]["Control"]
		print(controls)
		ts = [s for s in controls if "TimeStep" in s]
		print(ts)
		ts_group.append((building_name, ts[0]))
	return ts_group


#Wrapper fuction in case of timeout
#Unclear what the cause of timeout is, but trying again usually works
def opc_read(payload):
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

def connect_to_server(server):
	opc = OpenOPC.open_client()
	opc.connect(server)
	print("Connected to " +server)
	return opc
