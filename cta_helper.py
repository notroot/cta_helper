#!/usr/bin/python

from urllib2 import Request, urlopen, URLError
import xml.etree.ElementTree as ET
import ConfigParser
from datetime import datetime
from time import strftime, strptime, mktime, time

# Flask imports
from flask import Flask, request, session, g, redirect, url_for, \
	 abort, render_template, flash
from werkzeug.contrib.fixers import ProxyFix

app = Flask(__name__)
app.config.from_object(__name__)
app.secret_key = 'some_secret'

app.config.update(dict(
		DEBUG=True,
))

config = ConfigParser.RawConfigParser()
config.read('cta.cfg')

bus_api_key = config.get('Options','bus_api_key')
train_api_key = config.get('Options','train_api_key')

#DEBUG=False

class BussStop(object):
	def __init__(self, name, bus, stop_id, direction):
		self.name = name
		self.bus = int(bus)
		self.stop_id = int(stop_id)
		self.direction = direction
		self.prdtms = None


	def __repr__(self):
		return '{} - {}, {}'.format(self.name, self.bus, self.stop_id)


class TrainStop(object):
	def __init__(self, platform_id, name=None, line=None, end_stop=None):
		self.name = name
		self.line = line
		self.line_id = getLineID(line)
		self.platform_id = platform_id
		self.end_stop = end_stop
		self.prdtms = None

	def __repr__(self):
		return '{} - {}, {}'.format(self.name, self.line, self.end_stop)



def getLineID(line):
	#Red = Red Line (Howard-95th/Dan Ryan service)
	#Blue = Blue Line (O'Hare-Forest Park service)
	#Brn = Brown Line (Kimball-Loop service)
	#G = Green Line (Harlem/Lake-Ashland/63rd-Cottage Grove service)
	#Org = Orange Line (Midway-Loop service)
	#P = Purple Line (Linden-Howard shuttle service)
	#Pink = Pink Line (54th/Cermak-Loop service)
	#Y = Yellow Line (Skokie-Howard [Skokie Swift] shuttle service)

	lines = {"Red":"Red", "Blue":"Blue", "Brown":"Brn", "Green":"G", "Orange":"Org",\
			"Purple":"P", "Pink":"Pink", "Yellow":"Y"}

	return lines[line]

def getBusTimes(buss_stop):

	bus = buss_stop.bus
	stop = buss_stop.stop_id
	#app.logger.debug("Getting log for %s, %s" % (bus, stop))

	request = "http://www.ctabustracker.com/bustime/api/v1/getpredictions?key=%s&rt=%s&stpid=%s&top=3" % (bus_api_key,bus,stop)

	try:
		response = urlopen(request)
		xml_response = response.read()
		root = ET.fromstring(xml_response)
	except URLError, e:
		print 'API error: Error code:', e

	#bustime-response
	prdtms = []
	for atype in root.findall('prd'):
		#print "Found a bus"
		#ET.dump(atype)
		prdtm = atype.find('prdtm').text
		prdtm = strptime(prdtm, "%Y%m%d %H:%M")
		a_time = strftime("%I:%M", prdtm)
		prdtms.append({'prdtm':prdtm,'minutes':timeTilDepart(prdtm), "a_time":a_time})

	#app.logger.debug("Got times for %s, %s: %s" % (bus, stop, prdtms))
	return prdtms


def getBusesByStopID(stop_id):

	request = "http://www.ctabustracker.com/bustime/api/v1/getpredictions?key=%s&stpid=%s&top=4" % (bus_api_key, stop_id)

	try:
		response = urlopen(request)
		xml_response = response.read()
		root = ET.fromstring(xml_response)
	except URLError, e:
		print 'API error: Error code:', e

	arivals = []
	for atype in root.findall('prd'):
		prdtm = atype.find('prdtm').text
		prdtm = strptime(prdtm, "%Y%m%d %H:%M")
		a_time = strftime("%I:%M", prdtm)
		prdtm = {'prdtm':prdtm,'minutes':timeTilDepart(prdtm), "a_time":a_time}


		stpnm = atype.find('stpnm').text
		rt = int(atype.find('rt').text)
		rtdir = atype.find('rtdir').text
		des = atype.find('des').text
		arivals.append({'stpnm':stpnm,'rt':rt,'rtdir':rtdir,'prdtm':prdtm,'des':des})

	return arivals


def getTrainTimes(train_stop):
	line = train_stop.line
	stop = train_stop.platform_id
	line_id=train_stop.line_id

	#request = "http://lapi.transitchicago.com/api/1.0/ttarrivals.aspx?key=%s&stpid=%s&max=5" % (train_api_key, stop)
	request = "http://lapi.transitchicago.com/api/1.0/ttarrivals.aspx?key=%s&stpid=%s&rt=%s&max=5"\
	 % (train_api_key, stop, line_id)

	app.logger.debug("API query = %s" % request)

	try:
		response = urlopen(request)
		xml_response = response.read()
		root = ET.fromstring(xml_response)
	except URLError, e:
		app.logger.debug('API error: Error code:', e)

	prdtms = []
	for atype in root.findall('eta'):
		is_delayed = atype.find('isDly').text
		#is_delayed = "1"

		arrt = atype.find('arrT').text
		arrt = strptime(arrt, "%Y%m%d %H:%M:%S")

		# get the time that the arrival was estimated at so we can do the correct delta
		estimated_at = atype.find('prdt').text
		estimated_at = strptime(estimated_at, "%Y%m%d %H:%M:%S")
		a_time = strftime("%I:%M", arrt)

		train_destination = atype.find('stpDe').text
		prdtms.append({'prdtm':arrt,'minutes':timeTilDepart(arrt), "a_time":a_time,\
		 "is_delayed":is_delayed, "train_destination":train_destination})



	return prdtms



# returns minutes until departure or "Due" if less than 2 minutes out
# for train data sampled_at should be passed in what time the prediction was generated at
# this provides a better prediction
def timeTilDepart(prdtm, estimated_at=None):
	if estimated_at == None:
		seconds = mktime(prdtm) - time()
	else:
		seconds = mktime(prdtm) - estimated_at

	if seconds < 120:
		return "Due"
	else:
		return int(seconds/60)

def convertToMin(prdtms):
	mins = []
	for prdtm in prdtms:
		mins.append(timeTilDepart(prdtm))

	return mins

def getBuses(user=None):
	week_day = int(strftime("%w"))
	hour = int(strftime("%H"))

	buses = []

	# weekday morning
	if (week_day > 0 and week_day < 6 and hour > 4 and hour < 12):
		if user == "carrie":
			buses.append(BussStop("Sheridan & Surf", 134, 1076, "South"))
			buses.append(BussStop("Sheridan & Surf", 156, 1076, "South"))
			buses.append(BussStop("Diversey & Sheridan", 76, 11037, "West"))
		else:
			buses.append(BussStop("Sheridan & Surf", 134, 1076, "South"))
			buses.append(BussStop("Sheridan & Surf", 156, 1076, "South"))
			buses.append(BussStop("Diversey & Sheridan", 76, 11037, "West"))

	# weekday commute
	elif (week_day > 0 and week_day < 6 and hour > 12 and hour < 19):
		if user == "carrie":
			buses.append(BussStop("LaSelle & Randolph", 134, 4975, "North"))
			buses.append(BussStop("LaSelle & Randolph", 156, 4975, "North"))
			buses.append(BussStop("Diversey & Brown Line", 76, 11028, "East"))
		else:
			buses.append(BussStop("Franklin & Jackson", 134, 6711, "North"))
			buses.append(BussStop("Jackson & River", 156, 14461, "North"))
			buses.append(BussStop("Diversey & Brown Line", 76, 11028, "East"))

	# weekday evening and weekend
	else:
		buses.append(BussStop("Clark & Southport", 22, 14439, "South"))
		buses.append(BussStop("Clark & Diversey", 22, 1917, "North"))

	return buses

def getTrains(user=None):
	week_day = int(strftime("%w"))
	hour = int(strftime("%H"))

	trains = []

	#trains.append(TrainStop("Quincy", "Purple", 30007, "Kimbal"))
	#trains.append(TrainStop("Diversey", "Brown", 30104, "Loop"))
	#def __init__(self, platform_id, name=None, line=None, end_stop=None):

	#trains.append(TrainStop(30007, None, "Purple"))
	# weekday morning
	if (week_day > 0 and week_day < 6 and hour > 4 and hour < 12):
		if user == "carrie":
			trains.append(TrainStop(30104, "Diversy", "Brown"))
			trains.append(TrainStop(30104, "Diversy", "Purple"))
		else:
			trains.append(TrainStop(30104, "Diversy", "Brown"))
			trains.append(TrainStop(30282, "Irving Park", "Brown"))
	# weekday commute
	elif (week_day > 0 and week_day < 6 and hour > 12 and hour < 19):
		if user == "carrie":
			trains.append(TrainStop(30075, "Clark/Lake", "Brown"))
			trains.append(TrainStop(30141, "Washington/Wells", "Purple"))
			trains.append(TrainStop(30211, "Monroe", "Red"))
		else:
			trains.append(TrainStop(30007, "Quincy/Wells", "Purple"))
			trains.append(TrainStop(30008, "Quincy/Wells", "Brown"))
	else:
		trains.append(TrainStop(30104, "Diversy", "Brown"))
		trains.append(TrainStop(30282, "Irving Park", "Brown"))


	return trains

def validateUser(user):
	if user == "carrie" or user == "jim":
		return True
	else:
		return False

@app.route('/')
@app.route('/u/<user>')
def show_home(user=None):
	current_time = strftime("%I:%M:%S")

	if not validateUser(user):
		redirect(request.base_url)

	buses = getBuses(user)

	bus_results = []
	for bus_stop in buses:
		prdtms = getBusTimes(bus_stop)

		if (len(prdtms) > 0):
			bus_stop.prdtms = prdtms
			bus_results.append(bus_stop)

	trains = getTrains(user)

	train_results = []
	for train_stop in trains:
		prdtms = getTrainTimes(train_stop)

		if (len(prdtms) > 0):
			train_stop.prdtms = prdtms
			train_results.append(train_stop)


	return render_template('show_main.html', current_time=current_time, bus_results=bus_results, train_results=train_results)

@app.route('/stop')
def show_busstop():
	current_time = strftime("%I:%M:%S")

	stop_id = request.values['stop_id']

	try:
		stop_id = int(stop_id)
	except ValueError:
		flash("Stop ID must be a numeric value")
		return render_template('show_stop.html', current_time=current_time, arivals=None)

	arivals = getBusesByStopID(stop_id)
	if arivals:
		# use name from first arival, they will all have the same stop name
		stop = arivals[0]['stpnm']
	else:
		stop = None

	return render_template('show_stop.html', current_time=current_time, stop=stop, arivals=arivals)


app.wsgi_app = ProxyFix(app.wsgi_app)
if __name__ == '__main__':
	app.run(host='0.0.0.0')
