import pyEp
import os
import matplotlib.pyplot as plt
import socket

pyEp.set_eplus_dir("C:\\EnergyPlusV8-1-0")

path_to_buildings = os.path.join(os.getcwd(),'pyEp', 'example_buildings')

builder = pyEp.socket_builder(path_to_buildings)
configs = builder.build() # Configs is [port, building_folder_path, idf]
weather_file = 'SPtMasterTable_587017_2012_amy'
ep = pyEp.ep_process('localhost', configs[0][0], configs[0][1], weather_file)


#	Cosimulation
outputs = []

EPTimeStep = 12
SimDays = 1
kStep = 1
MAXSTEPS = int(SimDays*24*EPTimeStep)
deltaT = (60/EPTimeStep)*60;

print("Running Cosimulation with Total Steps " + str(MAXSTEPS))

while kStep < MAXSTEPS:
		
		time = (kStep-1) * deltaT
		
		dayTime = time % 86400

		if dayTime == 0:
			print(kStep)
		
		output = ep.decode_packet_simple(ep.read())
		outputs.append(output)

		setpoints = [24, 6.7, 0.7]

		if(dayTime < 5 * 3600):
			setpoints = [27, 6.7, 0.05]
		elif(dayTime < 6 * 3600):
			setpoints = [27, 6.7, 0.01]
		elif(dayTime < 7 * 3600):
			setpoints = [24, 6.7, 0.1]
		elif(dayTime < 8 * 3600):
			setpoints = [24, 6.7, 0.3]
		elif(dayTime < 17 * 3600):
			setpoints = [24, 6.7, 0.9]
		elif(dayTime < 18 * 3600):
			setpoints = [24, 6.7, 0.7]
		elif(dayTime < 20 * 3600):
			setpoints = [24, 6.7, 0.5]
		elif(dayTime < 22 * 3600):
			setpoints = [24, 6.7, 0.4]
		elif(dayTime < 23 * 3600):
			setpoints = [24, 6.7, 0.1]
		elif(dayTime < 24 * 3600):
			setpoints = [24, 6.7, 0.05]

		ep.write(ep.encode_packet_simple(setpoints, (kStep-1) * deltaT))
	

		kStep = kStep + 1

ep.close()
plt.plot([output[0] for output in outputs])
plt.show()