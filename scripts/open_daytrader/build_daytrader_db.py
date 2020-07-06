#!/usr/bin/env python3

import sys,time,urllib.request,urllib.error,urllib.parse
import MySQLdb
from optparse import OptionParser

#----------------------- Option Parser -----------------------------------------
parser = OptionParser()
parser.add_option("--apphost", dest="apphost", default = None, help="IP of Application host")
parser.add_option("--dbhost", dest="dbhost", default = None, help="IP of Database host")
parser.add_option("--dbuser", dest="dbuser", default = "trade", help="USER for DB host")
parser.add_option("--dbpass", dest="dbpass", default = "trade", help="PASSWORD for DB host")
parser.add_option("--dbname", dest="dbname", default = "tradedb", help="NAME of database on DB host")
parser.add_option("--maxuser", dest="user", default = None, help="Max user value")
parser.add_option("--maxquote", dest="quote", default = None, help="Max user value")
parser.add_option("--load_id", dest="loadid", default = None, help="loadid")
parser.add_option("--checkfreq", dest="checkfreq", default = 5, help="Check frequency")
(options, args) = parser.parse_args()

if options.apphost and options.user and options.quote and options.loadid :

    #----------------------- Set DayTrader Max Users -------------------------------
 
    _msg = "Setting number of users on Daytrader DB to " + str(options.user) + "..."
    print(_msg)
    url = "http://%s:8080/daytrader/config?action=updateConfig&MaxUsers=%s" % (options.apphost, options.user)
    response = urllib.request.urlopen(url)
    print(response.msg)
    if response.code != 200 :
        exit(1)

    #----------------------- Set DayTrader Max Quotes ------------------------------

    _msg = "Setting number of quotes on Daytrader DB to " + str(options.quote)  + "..."
    print(_msg)    
    url = "http://%s:8080/daytrader/config?action=updateConfig&MaxQuotes=%s" % (options.apphost, options.quote)
    urllib.request.urlopen(url)
    response = urllib.request.urlopen(url)
    print(response.msg)
    if response.code != 200 :
        exit(1)
            
    #----------------------- Rebuild database --------------------------------------

    if int(options.loadid) == 1 :
        _msg = "Rebuilding Daytrader DB Tables..."
        print(_msg)
        url = "http://%s:8080/daytrader/config?action=buildDBTables" % options.apphost
        repsonse = urllib.request.urlopen(url)
        response = urllib.request.urlopen(url)
        print(response.msg)
        if response.code != 200 :
            exit(1)
        else :
            time.sleep(options.checkfreq)

    _msg = "Rebuilding Daytrader DB Contents..."
    print(_msg)
    url = "http://%s:8080/daytrader/config?action=buildDB" % options.apphost
    urllib.request.urlopen(url)
    response = urllib.request.urlopen(url)
    print(response.msg)
    if response.code != 200 :
        exit(1)    
    
    if options.dbhost :
        _msg = "Waiting until DayTrader DB is fully populated..."
        print(_msg)
        db_building = True
        users_created = False
        previous_generated_quotes = 0
        steady_cycles = 2
        while db_building :
            try :        
                db = MySQLdb.connect(options.dbhost,options.dbuser,options.dbpass,options.dbname)
                cursor = db.cursor()
                
                if not users_created :
                    cursor.execute("select count(*) from accountprofileejb;")
                    nr_users = int(cursor.fetchone()[0]) 
                    if nr_users == int(options.user) :
                        _msg = "All users (" + str(options.user) + ") generated."
                        print(_msg)
                        users_created = True
                    else :
                        _msg = "Still generating users (" + str(nr_users) + ")"
                        print(_msg)
                else :
                    cursor.execute("select count(*) from quoteejb;")
                    generated_quotes = int(cursor.fetchone()[0])
                    if generated_quotes - previous_generated_quotes > 0 :
                        previous_generated_quotes = generated_quotes
                        _msg = "Still generating quotes (n-1:" + str(previous_generated_quotes) + ", n:" + str(generated_quotes) + ")"
                        print(_msg)
                                                
                    else :
                        steady_cycles -= 1
                        
                        if steady_cycles <= 0 :
                            _msg = "A total of " + str(generated_quotes) + " quotes were generated"
                            print(_msg)
                            db_building = False
                        
                time.sleep(options.checkfreq)
                
            except :
                _msg = "Tables not fully created yet"
                print(_msg)
                time.sleep(options.checkfreq)
            
    exit(0)
else :
    print("Usage: build_daytrader.py --apphost <HOST IP> --maxuser <USERS> --maxquote <QUOTES> --load_id")
    exit(1)
