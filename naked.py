import requests
import json
import datetime
import time
import yaml
import mysql.connector
import logging
import logging.config

from configparser import ConfigParser

from datetime import datetime
from mysql.connector import Error

print('Asteroid processing service')

# Initiating and reading config values
print('Loading configuration from file')

# Loading logging configuration
with open('./log_worker.yaml', 'r') as stream:
    log_config = yaml.safe_load(stream)

logging.config.dictConfig(log_config)

# Creating logger
logger = logging.getLogger('root')

logger.info('Asteroid processing service')

# Initiating and reading config values
logger.info('Loading configuration from file')

try:
	config = ConfigParser()
	config.read('config.ini')

	nasa_api_key = config.get('nasa', 'api_key')
	nasa_api_url = config.get('nasa', 'api_url')
	mysql_config_mysql_host = config.get('mysql_config', 'mysql_host')
	mysql_config_mysql_db = config.get('mysql_config', 'mysql_db')
	mysql_config_mysql_user = config.get('mysql_config', 'mysql_user')
	mysql_config_mysql_pass = config.get('mysql_config', 'mysql_pass')
except:
	print('')
print('DONE')

def init_db():
	global connection
	connection = mysql.connector.connect(host=mysql_config_mysql_host, database=mysql_config_mysql_db, user=mysql_config_mysql_user, password=mysql_config_mysql_pass)

def get_cursor():
	global connection
	try:
		connection.ping(reconnect=True, attempts=1, delay=0)
		connection.commit()
	except mysql.connector.Error as err:
		logger.error("No connection to db " + str(err))
		connection = init_db()
		connection.commit()
	return connection.cursor()

# Check if asteroid exists in db
def mysql_check_if_ast_exists_in_db(request_day, ast_id):
	records = []
	cursor = get_cursor()
	try:
		cursor = connection.cursor()
		result  = cursor.execute("SELECT count(*) FROM ast_daily WHERE `create_date` = '" + str(request_day) + "' AND `ast_id` = '" + str(ast_id) + "'")
		records = cursor.fetchall()
		connection.commit()
	except Error as e :
		logger.error("SELECT count(*) FROM ast_daily WHERE `create_date` = '" + str(request_day) + "' AND `ast_id` = '" + str(ast_id) + "'")
		logger.error('Problem checking if asteroid exists: ' + str(e))
		pass
	return records[0][0]

# Asteroid value insert
def mysql_insert_ast_into_db(create_date, hazardous, name, url, diam_min, diam_max, ts, dt_utc, dt_local, speed, distance, ast_id):
	cursor = get_cursor()
	try:
		cursor = connection.cursor()
		result  = cursor.execute( "INSERT INTO `ast_daily` (`create_date`, `hazardous`, `name`, `url`, `diam_min`, `diam_max`, `ts`, `dt_utc`, `dt_local`, `speed`, `distance`, `ast_id`) VALUES ('" + str(create_date) + "', '" + str(hazardous) + "', '" + str(name) + "', '" + str(url) + "', '" + str(diam_min) + "', '" + str(diam_max) + "', '" + str(ts) + "', '" + str(dt_utc) + "', '" + str(dt_local) + "', '" + str(speed) + "', '" + str(distance) + "', '" + str(ast_id) + "')")
		connection.commit()
	except Error as e :
		logger.error( "INSERT INTO `ast_daily` (`create_date`, `hazardous`, `name`, `url`, `diam_min`, `diam_max`, `ts`, `dt_utc`, `dt_local`, `speed`, `distance`, `ast_id`) VALUES ('" + str(create_date) + "', '" + str(hazardous) + "', '" + str(name) + "', '" + str(url) + "', '" + str(diam_min) + "', '" + str(diam_max) + "', '" + str(ts) + "', '" + str(dt_utc) + "', '" + str(dt_local) + "', '" + str(speed) + "', '" + str(distance) + "', '" + str(ast_id) + "')")
		logger.error('Problem inserting asteroid values into DB: ' + str(e))
		pass

def push_asteroids_arrays_to_db(request_day, ast_array, hazardous):
	for asteroid in ast_array:
		if mysql_check_if_ast_exists_in_db(request_day, asteroid[9]) == 0:
			logger.debug("Asteroid NOT in db")
			mysql_insert_ast_into_db(request_day, hazardous, asteroid[0], asteroid[1], asteroid[2], asteroid[3], asteroid[4], asteroid[5], asteroid[6], asteroid[7], asteroid[8], asteroid[9])
		else:
			logger.debug("Asteroid already IN DB")

if __name__ ==  "__main__":
	connection = None
	connected = False

	init_db()

	# Opening connection to mysql DB
	logger.info('Connecting to MySQL DB')
	try:
		# connection = mysql.connector.connect(host=mysql_config_mysql_host, database=mysql_config_mysql_db, user=mysql_config_mysql_user, password=mysql_config_mysql_pass)
		cursor = get_cursor()
		if connection.is_connected():
			db_Info = connection.get_server_info()
			logger.info('Connected to MySQL database. MySQL Server version on ' + str(db_Info))
			cursor = connection.cursor()
			cursor.execute("select database();")
			record = cursor.fetchone()
			logger.debug('Your connected to - ' + str(record))
			connection.commit()
	except Error as e :
		logger.error('Error while connecting to MySQL' + str(e))

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
						# Getting id of asteroid
						tmp_ast_id = val["id"]
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
							ast_hazardous.append([tmp_ast_name, tmp_ast_nasa_jpl_url, tmp_ast_diam_min, tmp_ast_diam_max, tmp_ast_close_appr_ts, tmp_ast_close_appr_dt_utc, tmp_ast_close_appr_dt, tmp_ast_speed, tmp_ast_miss_dist, tmp_ast_id])
						else:
							ast_safe.append([tmp_ast_name, tmp_ast_nasa_jpl_url, tmp_ast_diam_min, tmp_ast_diam_max, tmp_ast_close_appr_ts, tmp_ast_close_appr_dt_utc, tmp_ast_close_appr_dt, tmp_ast_speed, tmp_ast_miss_dist, tmp_ast_id])
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
			push_asteroids_arrays_to_db(request_date, ast_hazardous, 1)
# Print a message when no hazardous asteroids are passing close to Earth today. Phew...
		else:
			print("No asteroids close passing earth today")
		push_asteroids_arrays_to_db(request_date, ast_hazardous, 1)
		push_asteroids_arrays_to_db(request_date, ast_safe, 0)
	# Print error message when unable to get a response from API
	else:
		print("Unable to get response from API. Response code: " + str(r.status_code) + " | content: " + str(r.text))
