#!/usr/bin/python3
# -*- coding: utf-8 -*-
# a lancer en crontab toutes les heures
#0 * * * * python3 /home/jahislove/owl/relance_owl.py

import time
import datetime
import os.path
import MySQLdb   # python3-mysqldb must be installed by yourself

DB_SERVER ='192.168.0.222'  # MySQL : IP server (localhost if mySQL is on the same machine)
DB_PORT = 3307
DB_BASE='owl_intuition'     # MySQL : database name
DB_USER='owl_intuition'     # MySQL : user  
DB_PWD='ttp2570'            # MySQL : password 
PATH_OWL = "/home/jahislove/owl/" #path to this script

def query_db(sql):
    try:
        db = MySQLdb.connect(host=DB_SERVER, user=DB_USER, passwd=DB_PWD, db=DB_BASE, port=DB_PORT)
        cursor = db.cursor()
        cursor.execute(sql)
        result = cursor.fetchone ()
        db.commit()
        db.close()
            
    except MySQLdb.Error:
        result = 0
        
    finally:
        return result

result = query_db("""SELECT date FROM journalier ORDER BY id DESC LIMIT 1""")
lastDate = result[0].timestamp()
lastDateText = result[0].strftime("%Y-%m-%d %H:%M:%S")
dateNow = datetime.datetime.now().timestamp()
difference = dateNow - lastDate

print(result[0].strftime("%Y-%m-%d %H:%M:%S"))
print(dateNow)

print(difference)

if difference > 3600: # si plus de 3600s depuis dernier update en bdd alors on relance le service
    logfile = open(PATH_OWL + "restart.log", "a")
    retour = os.popen('sudo service owl restart')
    msg = retour.read()
    log = time.strftime('%Y-%m-%d %H:%M:%S') + " now \n" + lastDateText + " BDD last update \n" + msg + "\n"
    logfile.write(log)
    logfile.close
