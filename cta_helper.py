#!/usr/bin/python

from urllib2 import Request, urlopen, URLError
import xml.etree.ElementTree as ET
import ConfigParser
from datetime import datetime

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

def getTimes(stop, bus=None):
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

	return prdtms

def timeTilDepart(prdtm):
	pieces = prdtm.split(" ")
	time = pieces[1]

	(hour, minute) = time.split(":")
	hour = int(hour)
	minute = int(minute)

	now = datetime.now()

	# bad hack right now for EDT
	c_hour = now.hour - 1
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

	
@app.route('/')
def show_home():
	busses=[ {'bus':156,'stop':14461}, {'bus':134,'stop':6711} ]
	busses=[ {'bus':22,'stop':14439} ]

	results = []
	for bus_stop in busses:
		bus = bus_stop['bus']
		stop = bus_stop['stop']
		prdtms = getTimes(stop,bus)

		bus_stop['prdtms'] = prdtms
		#bus_stop['ttds'] = convertToMin(prdtms)

		results.append(bus_stop)
		
		#if (len(prdtms) > 0):
		#	print "The %s's will arrive at the following time(s):"%bus
		#	for prdtm in prdtms:
		#		ttd = timeTilDepart(prdtm)
		#		print "%s minutes (%s)" % (ttd, prdtm)
		#else:
		#	print "No %s's coming anytime soon"%bus

		return render_template('show_main.html', results=results)

app.wsgi_app = ProxyFix(app.wsgi_app)
if __name__ == '__main__':
    app.run(host='0.0.0.0')
