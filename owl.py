#!/usr/bin/python
# -*- coding: utf-8 -*-

#==================================================================================================================================
#              owl.py
#----------------------------------------------------------------------------------------------------------------------------------
# by JahisLove - 2014, january
# version 0.3 2014-04-07
#----------------------------------------------------------------------------------------------------------------------------------
# ce script est prevu pour fonctionner avec les appareils de mesure de consommation electrique OWL intuition-lc (3 phases)
# utilisable en mono-phase pour surveiller 3 parties differentes d'un tableau electrique
# le boitier OWL intuition envoi la consommmation instantanee (toutes les 12 sec) en multicast par internet sur le serveur OWL
# afin de pouvoir stocker soi meme les donnees sur son propre serveur :
# ce script snif le reseau en attente des envois (multicast) du OWL intuition et les ecrit dans une base MySQL
# en cas de non disponibilité de mysql , les données sont stockées dans une base SQlite3 en local puis automatiquement recopie 
# dans mySQL des que celle ci est de nouveau dispo
#
# 
# tested with python 2.7 on Raspberry pi (wheezy) and MySQL 5.1 on NAS Synology DS411J (DSM 4.1)
#                                                     MariaDB 5.5.34 on NAS Synology DS411J (DSM 5)
#----------------------------------------------------------------------------------------------------------------------------------
#
# la base de données doit avoir cette structure: 
# CREATE TABLE `cout` (
# `id` int(11) NOT NULL AUTO_INCREMENT,
# `date` datetime NOT NULL,
# `costFUL1` float unsigned NOT NULL,
# `costFUL2` float unsigned NOT NULL,
# `costFUL3` float unsigned NOT NULL,
# `costECO1` float unsigned NOT NULL,
# `costECO2` float unsigned NOT NULL,
# `costECO3` float unsigned NOT NULL,
# PRIMARY KEY (`id`)
# ) ENGINE=InnoDB  DEFAULT CHARSET=latin1 AUTO_INCREMENT=427041 ;

# CREATE TABLE `detail` (
# `id` int(11) NOT NULL AUTO_INCREMENT,
# `date` datetime NOT NULL,
# `chan1` smallint(5) unsigned NOT NULL,
# `chan2` smallint(5) unsigned NOT NULL,
# `chan3` smallint(5) unsigned NOT NULL,
# `battery` tinyint(4) NOT NULL,
# `niveau` tinyint(4) NOT NULL,
# PRIMARY KEY (`id`)
# ) ENGINE=InnoDB  DEFAULT CHARSET=latin1 AUTO_INCREMENT=430262 ;

# CREATE TABLE `journalier` (
# `id` int(11) NOT NULL AUTO_INCREMENT,
# `date` datetime NOT NULL,
# `chan1` float NOT NULL,
# `chan2` float NOT NULL,
# `chan3` float NOT NULL,
# PRIMARY KEY (`id`)
# ) ENGINE=InnoDB  DEFAULT CHARSET=latin1 AUTO_INCREMENT=427049 ;

# CREATE TABLE `meteo` (
# `id` int(11) NOT NULL AUTO_INCREMENT,
# `date` datetime NOT NULL,
# `temp` float NOT NULL,
# `weather` char(100) NOT NULL,
# PRIMARY KEY (`id`)
# ) ENGINE=InnoDB  DEFAULT CHARSET=latin1 AUTO_INCREMENT=8505 ;
#
#==================================================================================================================================

#----------------------------------------------------------#
#             package importation                          #
#----------------------------------------------------------#
import re
import socket
import struct
import time
import datetime
import os.path
import MySQLdb   # MySQLdb must be installed by yourself
import sys
import sqlite3

#-----------------------------------------------------------------#
#  constants : use your own values / utilisez vos propres valeurs #
#-----------------------------------------------------------------#
PATH_OWL = "/home/pi/owl/" #path to this script
########## Tarif eletricity in euro/dollar/pound...
costABO = '90.98'              # Standing Charge Per year / abonnement annuel 
kwhCostFULL = '0.1572'           # normal rate per kwh      / tarif du KWh heure pleine 
kwhCostECO = '0.1096'           # Economy rate per kwh     / tarif du KWh heure creuse 

ECO = [["",""],["",""]]  # add a ["",""] if you add a period below
ECO[0][0] = '01:11:00'   # start 1st Economy rate / debut 1ere periode heure creuse  
ECO[0][1] = '07:41:00'   # end   1st Economy rate / fin   1ere periode heure creuse
ECO[1][0] = '12:40:00'  # start 2nd Economy rate / debut 2eme periode heure creuse
ECO[1][1] = '14:10:00'  # end   2nd Economy rate / fin   2eme periode heure creuse
#ECO[2][0] = 'xx:xx:xx'  # start 3rd Economy rate / debut 3eme periode heure creuse .....
#ECO[2][1] = 'xx:xx:xx'  # end   3rd Economy rate / fin   3eme periode heure creuse .....

DB_SERVER ='192.168.0.111'  # MySQL : IP server (localhost if mySQL is on the same machine)
DB_BASE='owl_intuition'     # MySQL : database name
DB_USER='owl_intuition'     # MySQL : user  
DB_PWD='*******'            # MySQL : password 

FREQUENCY = 1               # Periodicity (reduce data volume but lower current accuracy) (no impact on cost)
                            # (1 = all)     1 measure every 12 sec
                            # (5 = 1 in 5)  1 measure every 60 sec
                            # ...

#----------------------------------------------------------#
#             constants : do not modify                    #
#----------------------------------------------------------#
HELLO_GROUP='224.192.32.19' # Adress Multicast OWL
HOST = ''                   # empty : all interfaces
PORT = 22600                # Port du multicast OWL
MSGBUFSIZE=800              # taille du buffer

#----------------------------------------------------------#
#             Variables                                    #
#----------------------------------------------------------#
data = {"signal":0, "battery":0, "phase1_curr":0, "phase1_total":0, "phase2_curr":0, "phase2_total":0, "phase3_curr":0, "phase3_total":0, "full_total":0, "weather":0, "temp":0}
frequencyCount = FREQUENCY  

backup_row = 0
backup_mode = 0
costABO = float(costABO) / 365  
kwhCostFULL = float(kwhCostFULL) 
kwhCostECO = float(kwhCostECO)    
costECO1 = 0
costECO2 = 0
costECO3 = 0
costFUL1 = -1 # used to force reading in MySQl for first run of this script when variable are empty
costFUL2 = 0
costFUL3 = 0

if os.path.isfile(PATH_OWL + 'owl_bck.sqlite3'): # if sqlite exist then resume backup mode
    backup_mode = 1

#----------------------------------------------------------#
#     definition : database query with error handling      #
#----------------------------------------------------------#

def query_db(sql):
    global backup_mode
    global backup_row
    try:
        db = MySQLdb.connect(DB_SERVER, DB_USER, DB_PWD, DB_BASE)
        cursor = db.cursor()
        #---------------------------------------------------------------#
        #     Normal MySQL database INSERT                              #
        #---------------------------------------------------------------#
        if backup_mode == 0:
            cursor.execute(sql)
            db.commit()
            db.close()
        #---------------------------------------------------------------#
        # RESTORE : when MySQL is available again : restore from SQlite #
        #---------------------------------------------------------------#
        else:
            logfile = open(PATH_OWL + "owl.log", "a")
            log = time.strftime('%Y-%m-%d %H:%M:%S') + " INFO : MySQL is OK now : Restore mode started\n"
            logfile.write(log)
            
            db_bck = sqlite3.connect(PATH_OWL + 'owl_bck.sqlite3')
            db_bck.text_factory = str #tell sqlite to work with str instead of unicode
            cursor_bck = db_bck.cursor()

            cursor_bck.execute("""SELECT  date, chan1, chan2, chan3, battery, niveau FROM detail ORDER BY date ASC """)
            result_detail = cursor_bck.fetchall ()
            cursor_bck.execute("""SELECT  date, chan1, chan2, chan3 FROM journalier ORDER BY date ASC """)
            result_journalier = cursor_bck.fetchall ()
            cursor_bck.execute("""SELECT  date, costFUL1, costFUL2, costFUL3, costECO1, costECO2, costECO3 FROM cout ORDER BY date ASC """)
            result_cout = cursor_bck.fetchall ()
            cursor_bck.execute("""SELECT  date, temp, weather FROM meteo ORDER BY date ASC """)
            result_meteo = cursor_bck.fetchall ()
           
            for row in result_detail:
                backup_row += 1
                cursor.execute("""INSERT INTO detail (date, chan1, chan2, chan3, battery, niveau) VALUES ('%s','%s','%s','%s','%s','%s')"""% (row[0],row[1],row[2],row[3],row[4],row[5]))
            for row in result_journalier:
                cursor.execute("""INSERT INTO journalier (date, chan1, chan2, chan3) VALUES ('%s','%s','%s','%s')"""% (row[0],row[1],row[2],row[3]))
            for row in result_cout:
                cursor.execute("""INSERT INTO cout (date, costFUL1, costFUL2, costFUL3, costECO1, costECO2, costECO3) VALUES ('%s','%s','%s','%s','%s','%s','%s')"""% (row[0],row[1],row[2],row[3],row[4],row[5],row[6]))
            for row in result_meteo:
                cursor.execute("""INSERT INTO meteo (date, temp, weather) VALUES ('%s','%s','%s')"""% (row[0],row[1],row[2]))

                
            db_bck.close()
            log = time.strftime('%Y-%m-%d %H:%M:%S') + " INFO : " + str(backup_row) + " rows restored to MySQL\n"
            logfile.write(log)
           
            backup_row = 0
            backup_mode = 0
            os.remove(PATH_OWL + 'owl_bck.sqlite3')
            log = time.strftime('%Y-%m-%d %H:%M:%S') + " INFO : restore done, sqlite3 file deleted, returning to normal mode\n"
            logfile.write(log)
            
            cursor.execute(sql)
            db.commit()
            db.close()
            logfile.close
            # costFUL1, costFUL2, costFUL3, costECO1, costECO2, costECO3 = query_db_2("""SELECT costFUL1, costFUL2, costFUL3, costECO1, costECO2, costECO3 FROM cout  ORDER BY id DESC LIMIT 1""")
            # data["phase1_total"], data["phase2_total"], data["phase3_total"] = query_db_3("""SELECT chan1, chan2, chan3 FROM journalier ORDER BY id DESC LIMIT 1""")


        #---------------------------------------------------------------#
        #     BACKUP : when MySQL is down => local SQlite INSERT        #
        #---------------------------------------------------------------#
    except MySQLdb.Error:
        db_bck = sqlite3.connect(PATH_OWL + 'owl_bck.sqlite3')
        cursor_bck = db_bck.cursor()

        if backup_mode == 0: #create table on first run
            logfile = open(PATH_OWL + "owl.log", "a")
            log = time.strftime('%Y-%m-%d %H:%M:%S') + " WARN : MySQL is down : Backup mode started\n"
            logfile.write(log)
            
            create_meteo = """CREATE TABLE IF NOT EXISTS meteo (`date` datetime NOT NULL,
              temp float NOT NULL, weather tinytext NOT NULL
            ) ;"""
            
            create_cout = """CREATE TABLE IF NOT EXISTS cout (`date` datetime NOT NULL,
              costFUL1 float unsigned NOT NULL, costFUL2 float unsigned NOT NULL, costFUL3 float unsigned NOT NULL,
              costECO1 float unsigned NOT NULL, costECO2 float unsigned NOT NULL, costECO3 float unsigned NOT NULL
            ) ;"""

            create_detail = """ CREATE TABLE IF NOT EXISTS detail (`date` datetime NOT NULL,
              chan1 float unsigned NOT NULL, chan2 float unsigned NOT NULL, chan3 float unsigned NOT NULL,
              battery tinyint(4) NOT NULL, niveau tinyint(4) NOT NULL
            ) ;"""

            create_journalier = """
            CREATE TABLE IF NOT EXISTS journalier ( `date` datetime NOT NULL,
              chan1 float NOT NULL, chan2 float NOT NULL, chan3 float NOT NULL
            );"""

            cursor_bck.execute(create_meteo)
            cursor_bck.execute(create_cout)
            cursor_bck.execute(create_detail)
            cursor_bck.execute(create_journalier)
            
            log = time.strftime('%Y-%m-%d %H:%M:%S') + " WARN : Sqlite created\n"
            logfile.write(log)
            logfile.close

        backup_mode = 1
        cursor_bck.execute(sql)
        db_bck.commit()
        db_bck.close()

#-----used once at first launch------------------------------#
def query_db_2(sql):
    try:
        db = MySQLdb.connect(DB_SERVER, DB_USER, DB_PWD, DB_BASE)
        cursor = db.cursor()
        cursor.execute(sql)
        result = cursor.fetchone ()
        if result == None:
            result = 0,0,0,0,0,0
        db.commit()
        db.close()
            
    except MySQLdb.Error:
        result = 0,0,0,0,0,0
        
    finally:
        return result
        
#-----used once at first launch------------------------------#
def query_db_3(sql):
    try:
        db = MySQLdb.connect(DB_SERVER, DB_USER, DB_PWD, DB_BASE)
        cursor = db.cursor()
        cursor.execute(sql)
        result = cursor.fetchone ()
        if result == None:
            result = 0,0,0
        db.commit()
        db.close()
            
    except MySQLdb.Error:
        result = 0,0,0
        
    finally:
        logfile = open(PATH_OWL + "owl.log", "a")
        log = time.strftime('%Y-%m-%d %H:%M:%S') + " INFO : owl.py started\n" 
        logfile.write(log)
        log = time.strftime('%Y-%m-%d %H:%M:%S') + " INFO : init data : Phase1 = " + str(result[0]) + " Kwh, Phase2 = " + str(result[1]) + " Kwh, Phase3 = " + str(result[2]) + " Kwh\n"
        logfile.write(log)
        logfile.close
        return result

#----------------------------------------------------------#
#        socket for Connection to OWL data MultiCast       #
#----------------------------------------------------------#
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)     # creation du socket en mode UDP
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR,1)                       # permet de re-utiliser le socket, sinon en cas de boucle rapide une erreur apparait car le socket n'a pas le temps de se liberer
s.bind((HOST, PORT))                                                         # on bind le socket (mode ecoute)
mreq = struct.pack ("4sl", socket.inet_aton(HELLO_GROUP), socket.INADDR_ANY) # indique l'interface sur laquelle le socket doit  
s.setsockopt (socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)             #   ecouter le multicast du boitier Owl Intuition


#----------------------------------------------------------#
#             code                                         #
#----------------------------------------------------------#

if  costFUL1 == -1:  #force reading in MySQl for first run of this script when variable are empty
    costFUL1, costFUL2, costFUL3, costECO1, costECO2, costECO3 = query_db_2("""SELECT costFUL1, costFUL2, costFUL3, costECO1, costECO2, costECO3 FROM cout  ORDER BY id DESC LIMIT 1""")
    data["phase1_total"], data["phase2_total"], data["phase3_total"] = query_db_3("""SELECT chan1, chan2, chan3 FROM journalier ORDER BY id DESC LIMIT 1""")


########## gathering data 
while True:
    buffer = s.recv(MSGBUFSIZE) # waiting a packet (waiting as long as s.recv is empty)
    #print(buffer) # for debug only

    datebuff = time.strftime('%Y-%m-%d %H:%M:%S') #formating date for mySQL
    
    # retrieve weather and write in mySQL table meteo
    weather = re.match (r"<weather.*<temperature>([0-9]+\.[0-9]+)</temperature><text>(.*)</text>.*", buffer)
    if weather:
        data["temp"] = float(weather.group(1))
        data["weather"] = weather.group(2)
        query_db("""INSERT INTO meteo (date, temp, weather) VALUES ('%s','%s','%s')""" % (datebuff, data["temp"], data["weather"]))
        continue     # skip code below and return to while, waiting next buffer

    frequencyCount = frequencyCount + 1
    if frequencyCount <= FREQUENCY: 
        continue     # skip code below and return to while, if we want to skip some data 

    frequencyCount = 1    

    # Extracting data from buffer
    signal = re.match (r"<electricity.*rssi='(-[0-9]+)' lqi='([0-9]+)'.*level='([0-9]+)%.*", buffer)
    Phase1 = re.match (r"<electricity.*chan id='0'><curr units='w'>([0-9]+\.[0-9]+)</curr><day units='wh'>([0-9]+\.[0-9]+)</day.*", buffer)
    Phase2 = re.match (r"<electricity.*chan id='1'><curr units='w'>([0-9]+\.[0-9]+)</curr><day units='wh'>([0-9]+\.[0-9]+)</day.*", buffer)
    Phase3 = re.match (r"<electricity.*chan id='2'><curr units='w'>([0-9]+\.[0-9]+)</curr><day units='wh'>([0-9]+\.[0-9]+)</day.*", buffer)

    # retrieve 3 phases value, calculate cost and write in mySQL 
    if Phase1:
        if float(Phase1.group(2)) < data["phase1_total"]: # daily reinit
            data["phase1_total"] = 0
            data["phase2_total"] = 0
            data["phase3_total"] = 0
            costECO1 = 0
            costECO2 = 0
            costECO3 = 0
            costFUL1 = 0
            costFUL2 = 0
            costFUL3 = 0

        for period in ECO: # test if in eco period
            dateStart = "%s %s" % (time.strftime('%Y-%m-%d') , period[0])
            dateEnd = "%s %s" % (time.strftime('%Y-%m-%d') , period[1])
            if dateStart < datebuff < dateEnd:
                modeECO = 1
                break
            else:
                modeECO = 0

        if modeECO == 1:
            costECO1 += (float(Phase1.group(2)) - data["phase1_total"]) / 1000 * kwhCostECO
            costECO2 += (float(Phase2.group(2)) - data["phase2_total"]) / 1000 * kwhCostECO
            costECO3 += (float(Phase3.group(2)) - data["phase3_total"]) / 1000 * kwhCostECO
        else:
            costFUL1 += (float(Phase1.group(2)) - data["phase1_total"]) / 1000 * kwhCostFULL
            costFUL2 += (float(Phase2.group(2)) - data["phase2_total"]) / 1000 * kwhCostFULL
            costFUL3 += (float(Phase3.group(2)) - data["phase3_total"]) / 1000 * kwhCostFULL
                
        #frequencyCount = 1
        data["signal"] = float(signal.group(1))
        data["battery"] = float(signal.group(3))
        data["phase1_curr"] = float(Phase1.group(1))
        data["phase2_curr"] = float(Phase2.group(1))
        data["phase3_curr"] = float(Phase3.group(1))
        data["phase1_total"] = float(Phase1.group(2))
        data["phase2_total"] = float(Phase2.group(2))
        data["phase3_total"] = float(Phase3.group(2))

        query_db("""INSERT INTO detail (date, chan1, chan2, chan3, battery, niveau) VALUES ('%s','%s','%s','%s','%s','%s')
                 """ % (datebuff, data["phase1_curr"], data["phase2_curr"], data["phase3_curr"], data["battery"], data["signal"]))

        query_db("""INSERT INTO journalier (date, chan1, chan2, chan3) VALUES ('%s','%s','%s','%s')
                 """ % (datebuff, data["phase1_total"], data["phase2_total"], data["phase3_total"]))

        query_db("""INSERT INTO cout (date, costFUL1, costFUL2, costFUL3, costECO1, costECO2, costECO3) VALUES ('%s','%s','%s','%s','%s','%s','%s')
                 """ % (datebuff, costFUL1, costFUL2, costFUL3, costECO1, costECO2, costECO3))




