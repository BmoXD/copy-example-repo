import requests
import json
import datetime
import time
import yaml

from configparser import ConfigParser

from datetime import datetime
print('Asteroid processing service')

# Initiating and reading config values
print('Loading configuration from file')

try:
	config = ConfigParser()
	config.read('config.ini')

	nasa_api_key = config.get('nasa', 'api_key')
	nasa_api_url = config.get('nasa', 'api_url')
except:
	print('')
print('DONE')

# Getting todays date
dt = datetime.now()
request_date = str(dt.year) + "-" + str(dt.month).zfill(2) + "-" + str(dt.day).zfill(2)  
print("Generated today's date: " + str(request_date))

#Send an api request to NASA for today's astreoid information 
print("Request url: " + str(nasa_api_url + "rest/v1/feed?start_date=" + request_date + "&end_date=" + request_date + "&api_key=" + nasa_api_key))
r = requests.get(nasa_api_url + "rest/v1/feed?start_date=" + request_date + "&end_date=" + request_date + "&api_key=" + nasa_api_key)

# Printing API response data. For debugging!
print("Response status code: " + str(r.status_code))
print("Response headers: " + str(r.headers))
print("Response content: " + str(r.text))

# Check if API returned succesfuly. Check if response code is 200
if r.status_code == 200:

	# Load in data in JSON format
	json_data = json.loads(r.text)

	ast_safe = []
	ast_hazardous = []
	
	# Check if there are any asteroids in the request
	if 'element_count' in json_data:
		# Get how many astreoids there are in the request and print the amount
		ast_count = int(json_data['element_count'])
		print("Asteroid count today: " + str(ast_count))
		
		# If there are astreoids use the response data
		if ast_count > 0:
			# Loop for how many astreoids that are near earth and each iteration save the asteroid info in val
			for val in json_data['near_earth_objects'][request_date]:
				# Check if specific keys are found in asteroid's data
				if 'name' and 'nasa_jpl_url' and 'estimated_diameter' and 'is_potentially_hazardous_asteroid' and 'close_approach_data' in val:
					# Save astreoid's name and japanese URL
					tmp_ast_name = val['name']
					tmp_ast_nasa_jpl_url = val['nasa_jpl_url']
					# Check if there is a measurment of the asteroid's diameter in kilometers
					if 'kilometers' in val['estimated_diameter']:
						# Check if there are any available diamater values
						if 'estimated_diameter_min' and 'estimated_diameter_max' in val['estimated_diameter']['kilometers']:
							# Calculate and round the minimum and maximum diameters to 3 decimal places
							tmp_ast_diam_min = round(val['estimated_diameter']['kilometers']['estimated_diameter_min'], 3)
							tmp_ast_diam_max = round(val['estimated_diameter']['kilometers']['estimated_diameter_max'], 3)
						# If there is no diameter values then set placeholder values
						else:
							tmp_ast_diam_min = -2
							tmp_ast_diam_max = -2
					# If there is no diameter values then set placeholder values
					else:
						tmp_ast_diam_min = -1
						tmp_ast_diam_max = -1
					# Save to boolean value if the asteroid is unsafe/hazardous
					tmp_ast_hazardous = val['is_potentially_hazardous_asteroid']

					# Check if there is close approach data for the asteroid
					if len(val['close_approach_data']) > 0:
						# Check if there is releveant info about the astreoid's close approach
						if 'epoch_date_close_approach' and 'relative_velocity' and 'miss_distance' in val['close_approach_data'][0]:
							# Extract relevant information from the first close approach data point
							tmp_ast_close_appr_ts = int(val['close_approach_data'][0]['epoch_date_close_approach']/1000)
							tmp_ast_close_appr_dt_utc = datetime.utcfromtimestamp(tmp_ast_close_appr_ts).strftime('%Y-%m-%d %H:%M:%S')
							tmp_ast_close_appr_dt = datetime.fromtimestamp(tmp_ast_close_appr_ts).strftime('%Y-%m-%d %H:%M:%S')

							# Check if there is there is speed data for the asteroid
							if 'kilometers_per_hour' in val['close_approach_data'][0]['relative_velocity']:
								# Extract and convert the speed to an integer
								tmp_ast_speed = int(float(val['close_approach_data'][0]['relative_velocity']['kilometers_per_hour']))
							# If there is no speed data then set placeholder value
							else:
								tmp_ast_speed = -1

							# Check if there is distance between earth an asteroid present in asteroid data
							if 'kilometers' in val['close_approach_data'][0]['miss_distance']:
								# Extract and round the miss distance to 3 decimal places
								tmp_ast_miss_dist = round(float(val['close_approach_data'][0]['miss_distance']['kilometers']), 3)
							# Set placeholder value if distance is missing
							else:
								tmp_ast_miss_dist = -1
						# Set placeholder values if any of the required keys are missing in close approach data
						else:
							tmp_ast_close_appr_ts = -1
							tmp_ast_close_appr_dt_utc = "1969-12-31 23:59:59"
							tmp_ast_close_appr_dt = "1969-12-31 23:59:59"
					# Set placeholder values if there is no close approach data at all and print appropriate message
					else:
						print("No close approach data in message")
						tmp_ast_close_appr_ts = 0
						tmp_ast_close_appr_dt_utc = "1970-01-01 00:00:00"
						tmp_ast_close_appr_dt = "1970-01-01 00:00:00"
						tmp_ast_speed = -1
						tmp_ast_miss_dist = -1

					# Print gathered asteroid information
					print("------------------------------------------------------- >>")
					print("Asteroid name: " + str(tmp_ast_name) + " | INFO: " + str(tmp_ast_nasa_jpl_url) + " | Diameter: " + str(tmp_ast_diam_min) + " - " + str(tmp_ast_diam_max) + " km | Hazardous: " + str(tmp_ast_hazardous))
					print("Close approach TS: " + str(tmp_ast_close_appr_ts) + " | Date/time UTC TZ: " + str(tmp_ast_close_appr_dt_utc) + " | Local TZ: " + str(tmp_ast_close_appr_dt))
					print("Speed: " + str(tmp_ast_speed) + " km/h" + " | MISS distance: " + str(tmp_ast_miss_dist) + " km")
					
					# Adding asteroid data to the corresponding array
					if tmp_ast_hazardous == True:
						ast_hazardous.append([tmp_ast_name, tmp_ast_nasa_jpl_url, tmp_ast_diam_min, tmp_ast_diam_max, tmp_ast_close_appr_ts, tmp_ast_close_appr_dt_utc, tmp_ast_close_appr_dt, tmp_ast_speed, tmp_ast_miss_dist])
					else:
						ast_safe.append([tmp_ast_name, tmp_ast_nasa_jpl_url, tmp_ast_diam_min, tmp_ast_diam_max, tmp_ast_close_appr_ts, tmp_ast_close_appr_dt_utc, tmp_ast_close_appr_dt, tmp_ast_speed, tmp_ast_miss_dist])
		# If there are no astreoid print appropriate message	
		else:
			print("No asteroids are going to hit earth today")

	# Print how many hazardous and safe asteroids we found
	print("Hazardous asteorids: " + str(len(ast_hazardous)) + " | Safe asteroids: " + str(len(ast_safe)))

	# Check if there is one or more hazardous asteroids
	if len(ast_hazardous) > 0:

		# Sort hazardous asteroids by approach time in ascending order
		ast_hazardous.sort(key = lambda x: x[4], reverse=False)

		# Print a header indicating possible apocalypse times
		print("Today's possible apocalypse (asteroid impact on earth) times:")

		# Iterate through hazardous asteroids and print their information
		for asteroid in ast_hazardous:
			print(str(asteroid[6]) + " " + str(asteroid[0]) + " " + " | more info: " + str(asteroid[1]))

		# Sort hazardous asteroids by closest passing distance in ascending order
		ast_hazardous.sort(key = lambda x: x[8], reverse=False)

		# Print the closest passing distance and associated asteroid information
		print("Closest passing distance is for: " + str(ast_hazardous[0][0]) + " at: " + str(int(ast_hazardous[0][8])) + " km | more info: " + str(ast_hazardous[0][1]))
	# Print a message when no hazardous asteroids are passing close to Earth today. Phew...
	else:
		print("No asteroids close passing earth today")

# Print error message when unable to get a response from API
else:
	print("Unable to get response from API. Response code: " + str(r.status_code) + " | content: " + str(r.text))
