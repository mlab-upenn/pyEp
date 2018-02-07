import xml.etree.ElementTree as ET
import os
import json
import argparse

class cd:
	"""Context manager for changing the current working directory"""
	def __init__(self, newPath):
		self.newPath = os.path.expanduser(newPath)

	def __enter__(self):
		self.savedPath = os.getcwd()
		os.chdir(self.newPath)

	def __exit__(self, etype, value, traceback):
		os.chdir(self.savedPath)

def opc_append(pre, arr):
	ret = pre
	for ele in arr:
		ret = ret + "." + ele
	return ret


def addSubElement(parent, name):
	child = ET.SubElement(parent, "PSTAliasGroup")
	child.set("name", name)
	return child

def addTag(parent, name):
	child = ET.SubElement(parent, "PSTAlias")
	child.set("name", name)
	child.set("itemPath", "")
	child.set("type", "3")
	child.set("dataType", "5")
	scaling = ET.SubElement(child, "Scaling")
	scaling.set("enabled", "0")
	scaling.set("type", "0")
	events = ET.SubElement(child, "Events")
	events.set("enabled", "0")
	events.set("source", "Alias")
	events.set("severity", "1")
	events.set("trigger", "0")
	events.set("timestep", "0")
	return child

def run(campus_path):

	configs = {}

	OPC_server_prefix = "EPSimServer.EnergyPlus.Buildings"
	mapping = {}

	with cd(campus_path):
		buildings = next(os.walk('.'))[1]
		for building in buildings:
			configs[building] = {}
			mapping[building] = {}
			OPC_prefix = opc_append(OPC_server_prefix, [building])
			print(building)
			with cd(os.path.join(campus_path, building)):
				tree = ET.parse('variables.cfg')
				root = tree.getroot()
				control = []
				inputs = []
				outputs = {}
				unknowns = []


				control_tags = []
				input_tags = []
				num_inputs = 0
				output_tags = []
				num_outputs = 0

				control.append("TimeStep")
				control_tags.append(opc_append(OPC_prefix, ["Control", "TimeStep"]))
				control.append("InputRdy")
				control_tags.append(opc_append(OPC_prefix, ["Control", "InputRdy"]))
				control.append("OutputRdy")
				control_tags.append(opc_append(OPC_prefix, ["Control", "OutputRdy"]))

				for bcvtb_var in root:
					input_type = bcvtb_var.attrib["source"]
					if input_type == "Ptolemy":
						setpoint_name = bcvtb_var[0].attrib["schedule"]
						inputs.append(setpoint_name)

						input_tags.append(opc_append(OPC_prefix, ["Inputs", setpoint_name]))
						num_inputs = num_inputs + 1
					else:
						var_name, var_type = bcvtb_var[0].attrib["name"], bcvtb_var[0].attrib["type"]
						num_outputs = num_outputs + 1
						if var_name == "EMS":
							output_group = "EMS"
							if output_group not in outputs:
								outputs[output_group] = []
							outputs[output_group].append(var_type)

							output_tags.append(opc_append(OPC_prefix, ["Outputs", output_group, var_type]))
						elif var_name == "ENVIRONMENT" or var_name == "Environment":
							output_group = "Environment"
							if output_group not in outputs:
								outputs[output_group] = []
							outputs[output_group].append(var_type)

							output_tags.append(opc_append(OPC_prefix, ["Outputs", output_group, var_type]))
						elif var_name == "Whole Building":
							output_group = "WholeBuilding"
							if output_group not in outputs:
								outputs[output_group] = []
							outputs[output_group].append(var_type)

							output_tags.append(opc_append(OPC_prefix, ["Outputs", output_group, var_type]))
						elif var_type == "Zone Air Temperature":
							output_group = "ZoneAirTemp"
							if output_group not in outputs:
								outputs[output_group] = []
							outputs[output_group].append(var_name) #NOTE: VAR_NAME not var_type

							output_tags.append(opc_append(OPC_prefix, ["Outputs", output_group, var_name]))						
						elif var_type == "Schedule Value":
							output_group = "Schedule"
							if output_group not in outputs:
								outputs[output_group] = []
							outputs[output_group].append(var_name)

							output_tags.append(opc_append(OPC_prefix, ["Outputs", output_group, var_name]))						
						elif "Chiller" in var_type or "Boiler" in var_type:
							output_group = "EquipTemp"
							if "EquipTemp" not in outputs:
								outputs["EquipTemp"] = []
							outputs["EquipTemp"].append(var_name)

							output_tags.append(opc_append(OPC_prefix, ["Outputs", output_group, var_name]))												
						else:
							unknowns.append(var_name + var_type)
				configs[building]["Inputs"] = inputs
				configs[building]["Outputs"] = outputs
				configs[building]["Unknown"] = unknowns
				configs[building]["Control"] = control

				mapping[building]["Control"] = control_tags
				mapping[building]["Inputs"] = input_tags
				mapping[building]["Outputs"] = output_tags



	matrikon = ET.Element("Matrikon.OPC.Simulation")
	CSimRootDevLink = ET.SubElement(matrikon, "CSimRootDevLink")
	CSimRootDevLink.set("name", "")
	CSimRootDevLink.set("description", "Sim Server Root")
	PSTAlias = ET.SubElement(matrikon, "PSTAliasGroup")
	EpSimServer = addSubElement(PSTAlias, "EPSimServer")
	EP = addSubElement(EpSimServer, "EnergyPlus")
	 #Add Status Control Tag 
	addTag(EP, "Status")
	#Add Total Consumption Tag
	addTag(EP, "TotalPower")
	#Add LMP Tag
	addTag(EP, "LMP")

	Buildings = addSubElement(EP, "Buildings")

	for building_name in configs.keys():
		building = configs[building_name]
		Building = addSubElement(Buildings, building_name)
		
		control = building["Control"]
		Control = addSubElement(Building, "Control")
		for ctr in control:
			addTag(Control, ctr)

		setpoints = building["Inputs"]
		Inputs = addSubElement(Building, "Inputs")
		for setpoint in setpoints:
			addTag(Inputs, setpoint)

		output_dict = building["Outputs"]
		Outputs = addSubElement(Building, "Outputs")
		for output in output_dict.keys():
			Category = addSubElement(Outputs, output)
			for value in output_dict[output]:
				addTag(Category, value)

		unknowns = building["Unknown"]
		Invalid = addSubElement(Building, "Unknown")
		for unknown in unknowns:
			addTag(Invalid, unknown)

	#ET.dump(matrikon)
	tree = ET.tostring(matrikon)

	print(json.dumps(mapping))
	map = json.dumps(mapping)

	with open("BuildingsConfig.xml", "w") as f:
		f.write(tree)
		f.close()

	with open("mapping.json", "w") as f:
		f.write(map)
		f.close()

if __name__ == "__main__":
	parser = argparse.ArgumentParser(description="OPC Server Configuration Builder for Matrikon Simulation OPC Server")
	parser.add_argument('--path', '-p', help="Absolute Path to EnergyPlus buildings") #Buildings to connect
	
	args = parser.parse_args();

	if args.path is None:
		raise ValueError("Path to Buildings Not Specified")

	run(args.path)