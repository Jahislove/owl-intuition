#!/usr/bin/python3
# -*- coding: utf-8 -*-

#==================================================================================================================================
#              test du multicast
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
PATH_OWL = "/home/jahislove/owl/" #path to this script


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




