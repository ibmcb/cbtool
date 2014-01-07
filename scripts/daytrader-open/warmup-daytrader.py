import sys,time,urllib2
import threading,logging
from optparse import OptionParser

#----------------------- Option Parser -----------------------------------------
parser = OptionParser()
parser.add_option("-s", "--host", dest="host",
        help="IP of host")
parser.add_option("-u", "--maxuser", dest="user",
        help="Max user value")
parser.add_option("-q", "--maxquote", dest="quote",
        help="Max user value")
parser.add_option("-t", "--threads", dest="threads",
        help="Number of warmup threads to run agasint the server")
(options, args) = parser.parse_args()

#----------------------- Set DayTrader Max Users -------------------------------

url = "http://%s:8080/daytrader/config?action=updateConfig&MaxUsers=%s" % (options.host,options.user)
urllib2.urlopen(url)

#----------------------- Set DayTrader Max Quotes ------------------------------

url = "http://%s:8080/daytrader/config?action=updateConfig&MaxQuotes=%s" % (options.host,options.quote)
urllib2.urlopen(url)

#----------------------- Rebuild database --------------------------------------

url = "http://%s:8080/daytrader/config?action=buildDB" % options.host
urllib2.urlopen(url)

time.sleep(90)

#----------------------- Warm Up -----------------------------------------------
class WarmUp ( threading.Thread ) :
        def run ( self ) :
		while 1:
                	urllib2.urlopen("http://%s:8080/daytrader/servlet/PingJDBCRead" % options.host)
                	urllib2.urlopen("http://%s:8080/daytrader/servlet/PingJDBCWrite" % options.host)
                	urllib2.urlopen("http://%s:8080/daytrader/servlet/PingServlet2JNDI" % options.host)
                	urllib2.urlopen("http://%s:8080/daytrader/scenario" % options.host)

for x in xrange(int(options.threads)):
        WarmUp().start()

#----------------------- Workload ----------------------------------------------

#----------------------- Clean up ----------------------------------------------
