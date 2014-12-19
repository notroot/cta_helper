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


def getTrainTames(train_stop):
	train = train_stop.line
	stop = train_stop.platform_id

	request = "http://lapi.transitchicago.com/api/1.0/ttarrivals.aspx?key=%s&mapid=%s&max=5" % (train_api_key, stop)

	prdtms = []

	return prdtms


def timeTilDepart(prdtm):
	seconds = mktime(prdtm) - time()

	if seconds < 120:
		return "Due"
	else:
		return int(seconds/60)

def convertToMin(prdtms):
	mins = []
	for prdtm in prdtms:
		mins.append(timeTilDepart(prdtm))

	return mins

def getBuses():
	week_day = int(strftime("%w"))
	hour = int(strftime("%H"))
	
	buses = []

	# weekday morning
	if (week_day > 0 and week_day < 6 and hour > 4 and hour < 12):
		buses.append(BussStop("Sheridan & Surf", 156, 1076, "South"))
		buses.append(BussStop("Sheridan & Surf", 134, 1076, "South"))
		buses.append(BussStop("Diversey & Sheridan", 76, 11037, "West"))
	# weekday commute
	elif (week_day > 0 and week_day < 6 and hour > 12 and hour < 19):
		buses.append(BussStop("Jackson & River", 156, 14461, "North"))
		buses.append(BussStop("Franklin & Jackson", 134, 6711, "North"))
		buses.append(BussStop("Diversey & Brown Line", 76, 11028, "East"))
	# weekday evening and weekend
	else:	
		buses.append(BussStop("Clark & Southport", 22, 14439, "South"))
		buses.append(BussStop("Clack & Diversey", 22, 1917, "North"))

	return buses

def getTrains():
	week_day = int(strftime("%w"))
	hour = int(strftime("%H"))

	trains = []


	return trains


@app.route('/')
def show_home():	
	current_time = strftime("%I:%M:%S")

	buses = getBuses()
	
	bus_results = []
	for bus_stop in buses:
		prdtms = getBusTimes(bus_stop)
		
		if (len(prdtms) > 0):
			bus_stop.prdtms = prdtms
			bus_results.append(bus_stop)

	

	return render_template('show_main.html', current_time=current_time, bus_results=bus_results)

app.wsgi_app = ProxyFix(app.wsgi_app)
if __name__ == '__main__':
    app.run(host='0.0.0.0')
