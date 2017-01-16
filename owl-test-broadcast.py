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
#     definition : database query with error handling      #
#----------------------------------------------------------#

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


########## gathering data 
while True:
    buffer = s.recv(MSGBUFSIZE) # waiting a packet (waiting as long as s.recv is empty)
    print(buffer) # for debug only




