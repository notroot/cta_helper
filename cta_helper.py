#!/usr/bin/python

from urllib2 import Request, urlopen, URLError
import xml.etree.ElementTree as ET
import ConfigParser
from datetime import datetime
from time import gmtime, strftime

# Flask imports
from flask import Flask, request, session, g, redirect, url_for, \
     abort, render_template, flash
from werkzeug.contrib.fixers import ProxyFix

app = Flask(__name__)
app.config.from_object(__name__)

app.config.update(dict(
        DEBUG=True,
))

config = ConfigParser.RawConfigParser()
config.read('cta.cfg')

api_key = config.get('Options','api_key')

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


def getTimes(buss_stop):

	bus = buss_stop.bus
	stop = buss_stop.stop_id
	#app.logger.debug("Getting log for %s, %s" % (bus, stop))
	
	request = "http://www.ctabustracker.com/bustime/api/v1/getpredictions?key=%s&rt=%s&stpid=%s" % (api_key,bus,stop)

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
		prdtms.append({'prdtm':prdtm,'minutes':timeTilDepart(prdtm)})
	
	#app.logger.debug("Got times for %s, %s: %s" % (bus, stop, prdtms))
	return prdtms

def timeTilDepart(prdtm):
	pieces = prdtm.split(" ")
	time = pieces[1]

	(hour, minute) = time.split(":")
	hour = int(hour)
	minute = int(minute)

	now = datetime.now()

	c_hour = now.hour
	c_minute = now.minute

	if ( c_hour == hour):
		ttd =  minute - c_minute
	else:
		ttd =  (minute + 60) - c_minute

	if ttd < 2:
		return "Due"
	else:
		return ttd

def convertToMin(prdtms):
	mins = []
	for prdtm in prdtms:
		mins.append(timeTilDepart(prdtm))

	return mins

def getBusses():
	week_day = int(strftime("%w"))
	hour = int(strftime("%H"))
	
	busses = []

	# weekday morning
	if (week_day > 0 and week_day < 6 and hour > 4 and hour < 12):
		busses.append(BussStop("Sheridan & Surf", 156, 1076, "South"))
		busses.append(BussStop("Sheridan & Surf", 134, 1076, "South"))
		busses.append(BussStop("Diversey & Sheridan", 76, 11037, "West"))
	# weekday commute
	elif (week_day > 0 and week_day < 6 and hour > 12 and hour < 19):
		busses.append(BussStop("Jackson & River", 156, 14461, "North"))
		busses.append(BussStop("Franklin & Jackson", 134, 6711, "North"))
		busses.append(BussStop("Diversey & Brown Line", 76, 11028, "East"))
	# weekday evening and weekend
	else:	
		busses.append(BussStop("Clark & Southport", 22, 14439, "South"))
		busses.append(BussStop("Clack & Diversey", 22, 1917, "North"))

	return busses

@app.route('/')
def show_home():	
	current_time = strftime("%I:%M:%S")

	busses = getBusses()
	
	results = []
	for bus_stop in busses:
		prdtms = getTimes(bus_stop)

		bus_stop.prdtms = prdtms
		#bus_stop['ttds'] = convertToMin(prdtms)

		results.append(bus_stop)

	

	return render_template('show_main.html', current_time=current_time, results=results)

app.wsgi_app = ProxyFix(app.wsgi_app)
if __name__ == '__main__':
    app.run(host='0.0.0.0')
