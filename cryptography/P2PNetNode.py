from cryptography.ecdhcrypto import *
from cryptography.block_helper import *
import os
import json
import uuid
from shutil import copyfile

import socket
import sys

import threading

import time

import select

import errno

node = None

wallet = None

chain_directory = "chain"

import time

import random

import sys, signal

class P2PNetNode:

	def __init__(self,server_address,connect_address,initial_port,server_port,chain_directory = "chain", use_gui = False, listbox = None, connect_server = True, external_server = False, external_server_port = False):


		if use_gui:
			import tkinter as tk

		#CONNECTION BASED VARIABLES
		self.server_address = server_address
		self.external_server = external_server
		self.external_server_port = external_server_port
		self.connect_address = connect_address
		self.server_port = server_port
		self.connect_port = initial_port
		#PEER BASED VARIABLES
		self.peer_services = []
		self.peer_clients = []
		self.list_of_clients = []
		self.clients_wo_servers = []
		#CONFIRM CHAIN SIZE VARIABLES
		self.chain_size_confirmations = 0
		self.chain_sizes = []
		self.confirmed_size = 0

		#DOWNLOAD CHAIN BASED VARIABLES
		self.chain_downloaded = False
		self.chain_downloading = False
		self.chain_directory = chain_directory
		self.file_count = 0
		self.chain_size = 0

		self.wait_download = False
		#MINING BASED VARIABLES
		self.node_target = None
		
		#BLOCK CONFIRMATION VARIABLES
		self.block_hashes = []
		self.pending_block_hashes = {}
		self.block_confirmations = 0
		self.block_saving = False
		self.block_added = False

		#TXN CONFIRMATION VARIABLES
		self.txn_confirmations = {}
		self.txn_pool = []
		self.txn_pool_hashes = []

		#MINING VARIABLES
		self.mining = False

		#KEY BASED VARIABLES
		self.key_directory = ""

		#CONFIRMATION VARIABLES
		self.BLOCK_MIN_CONFIRMATIONS = 1
		self.TXN_MIN_CONFIRMATIONS = 1
		self.CHAIN_SIZE_MIN_CONFIRMATIONS = 1
		self.MEM_POOL_MIN_CONFIRMATIONS = 1
		self.TARGET_MIN_CONFIRMATIONS = 1

		#DISPLAY VALUES
		self.GUI = use_gui
		self.listbox = listbox

		#CONFIG VARIABLES
		self.connect_server = connect_server

		#CHAIN DIRECTORY
		if (os.path.exists(os.path.join(self.chain_directory)) == False):
			os.mkdir(self.chain_directory)

		#THREADING SETUP
		if connect_server:
			threading.Thread(target=self.start_server,args=(self.server_address,self.server_port)).start()
		
		threading.Thread(target=self.start_client,args=(self.connect_address,self.connect_port)).start()

	def print(self, string_val):
		if self.GUI:
			self.listbox.insert(tk.END,string_val)
		print(string_val)
	
	def download_chain(self):

		self.chain_downloading = True

		self.chain_size_confirmations = 0

		self.update_chain() #START CHAIN DOWNLOAD BY ENSURING CHAIN IS UP TO DATE

		json_message = {"Type":2} #SEND REQUEST TO DOWNLOAD CHAIN

		#self.broadcast_server_to_client(json.dumps(json_message)) #SEND MESSAGE

		self.broadcast_client_to_server(json.dumps(json_message)) #SEND MESSAGE

		while self.chain_size_confirmations < self.CHAIN_SIZE_MIN_CONFIRMATIONS: #WAIT UNTIL CHAIN SIZE IS CONFIRMED

			if (len(self.peer_services)) < self.CHAIN_SIZE_MIN_CONFIRMATIONS + 1: #IF PEERS ARE LESS THAN 2 CONFIRMATIONS WON'T BE MET

				if len(self.chain_sizes) > 0: #IF PEER SERVICES GREATER THAN ZERO AND UNABLE TO CONFIRM

					self.confirmed_size = max(self.chain_sizes) #CHOOSE LONGEST CHAIN

					break

			if (len(self.peer_services) == 0): #IF THERE ARE NO PEER SERVICES
				break #BREAK YOUR CHAIN IS MOST UP TO DATE

			continue

		
		while self.chain_size < self.confirmed_size: #WHILE CHAIN SIZE LESS THAN CONFIRMED SIZE

			i = 0 #SETUP COUNTER VARIABLE

			while os.path.exists(os.path.join(self.chain_directory,"blk%s.pkl" % i)): #GET MOST UP TO DATE BLOCK ON CHAIN

				i += 1 #INCREMENT COUNTER
			
			json_message = {"Type":12, "File":"blk%s.pkl" % i} #PREPARE MESSAGE TO REQUEST FILE
			
			self.wait_download = True #PREPARE TO ENABLE THREAD HALTING

			self.broadcast_client_to_server(json.dumps(json_message)) #BROADCAST MESSAGE TO RETRIEVE FILE

			while self.wait_download: #HALT THREAD UNTIL FILE IS DOWNLOADED
				continue
			
			path_exists = os.path.exists(os.path.join(self.chain_directory,"blk%s.pkl" % i)) #CHECK IF PATH FINALLY EXISTS

			while not path_exists: #HALT THREAD UNTIL PATH EXISTS

				path_exists = os.path.exists(os.path.join(self.chain_directory,"blk%s.pkl" % i)) #CHECK IF PATH FINALLY EXISTS
			
			self.chain_size += (os.path.getsize(os.path.join(self.chain_directory,"blk%s.pkl" % i))) #INCREMENT CHAIN SIZE

		self.print("Chain Downloaded")
		self.chain_downloaded = True
		self.chain_downloading = False


	def update_chain(self):
		self.chain_size = 0
		self.block_hashes = []
		i = 0

		while os.path.exists(os.path.join(self.chain_directory,"blk%s.pkl" % i)):

			filename = os.path.join(self.chain_directory,"blk%s.pkl" % i)
			
			if ".pkl" in filename:

				self.chain_size += os.path.getsize(filename)

				with open(filename, 'r') as handle:

					b = json.load(handle)

					block_hash = hash_block_dict(b)

				try:

					prev_hash = bytearray(32).hex()

					if len(self.block_hashes) > 0 and i - 1 >= 0:

						prev_hash = self.block_hashes[i - 1]

						assert(b['prev_block_hash'] == prev_hash)

				except:

					raise Exception("Chain Corrupted")

				if block_hash.hex() not in self.block_hashes:

					self.block_hashes.append(block_hash.hex())

				self.file_count += 1

			i += 1

		if self.file_count == 0:
			self.print("No Chain Info Was Found")
		
		self.block_thread = False
	
	def ClientThread(self, conn, addr): 
		
		while True:

			time.sleep(1)

			length = int.from_bytes(conn.recv(8),'big')

			if length > 2048:

				recv_length = 0

				message = bytes()

				recv_amount = 2048

				while recv_length < length:

					message += conn.recv(recv_amount)

					recv_length += 2048

					if (recv_length + 2048 > length):

						recv_amount = length - recv_length

			else:

				message = conn.recv(length)
			
			if message:

				json_message = json.loads(message.decode('utf-8'))

				#SEND SERVER INFORMATION
				if json_message['Type'] == 0:

					print("New Peer Available")

					if json_message['Address'] + ":" + str(json_message['Port']) not in self.peer_services:

						threading.Thread(target=self.start_client,args=(json_message['Address'],json_message["Port"])).start()

						self.broadcast_server_to_client(message.decode('utf-8'), conn)
					

				
				#GET BLOCKCHAIN SIZE
				elif json_message['Type'] == 2 and self.chain_downloaded:

					self.block_thread = True

					self.update_chain()

					while self.block_thread:

						continue
					
					json_return = {'Type':3,'Chain_Size':self.chain_size}

					message = self.prepare_message(json.dumps(json_return))

					conn.send(message)

				# CONFIRM BLOCK
				elif json_message['Type'] == 7 and self.chain_downloaded:

					self.confirm_block(json_message['Block'],json_message["PubKey"],json_message["Signature"],conn)

				#SEND TARGET TO REQUESTING CLIENT OR ASK FOR CLIENT TO SET TARGET
				elif json_message['Type'] == 8 and self.chain_downloaded:
					#ASK CLIENT TO SET TARGET
					if self.node_target == None:

						self.print("No Target To Send")
						message = self.prepare_message(json.dumps(json_message))

						conn.send(message)

					#SEND EXISTING TARGET TO CLIENT
					else:

						self.print("Sending Target:{0}".format(self.node_target))
						#SEND TARGET
						json_message = {'Type':9,'Target':self.node_target}

						message = self.prepare_message(json.dumps(json_message))

						conn.send(message)

				#SET NODE TARGET
				elif json_message['Type'] == 9 and self.chain_downloaded:

					self.node_target = json_message['Target']

					self.print("Chain Target:{0}".format(json_message['Target']))

				#RECEIVE BLOCK CONFIRMATIONS AND SAVE
				elif json_message['Type'] == 10:
					#HASH BLOCK
					block_hash = hash_block_dict(json_message['Block'])
					#CHECK IF BLOCK IS ALREADY ON CHAIN
					if block_hash.hex() not in self.block_hashes:
						#CHECK IF BLOCK IS ALREADY PENDING CONFIRMATIONS
						if block_hash.hex() in self.pending_block_hashes:

							self.pending_block_hashes[block_hash.hex()] += 1
		
						#IF BLOCK NOT PENDING CONFIRMATIONS ADD TO PENDING
						else:
							
							self.pending_block_hashes[block_hash.hex()] = 1

					#CHECKING IF BLOCK CONFIRMATIONS MEETS MINIMUM NUMBER OF CONFIRMATIONS
					if self.pending_block_hashes[block_hash.hex()] >= self.BLOCK_MIN_CONFIRMATIONS and block_hash.hex() not in self.block_hashes and self.block_saving == False:

						self.block_saving = True

						self.block_confirmations = 0 #RESET BLOCK CONFIRMATIONS TO ZERO

						self.pending_block_hashes = {} #RESET PENDING BLOCK CONFIRMATIONS TO BLANK

						self.node_target = None #SET TARGET BACK TO NONE
						print("Target Set To None 331")

						self.block_added = True

						print("SAVING BLOCK")

						save_block(self.chain_directory,json_message['Block']) #WRITE BLOCK TO CHAIN FILE
						
						self.send_peers_wo_servers(json.dumps(json_message))

						if block_hash.hex() not in self.block_hashes: 

							self.block_hashes.append(block_hash.hex()) #APPEND BLOCK HASH TO LIST OF EXISTING HASHES

						self.block_thread = False #RELEASE THREAD

						if (len(json_message['Block']['txns']) > 1): #REMOVE MINED TRANSACTIONS FROM THE MEM POOL TO PREVENT DUPLICATION

							for txn in json_message['Block']['txns'][1:]: #

								if (txn in self.txn_pool):

									self.txn_pool.remove(txn)

						self.update_chain()
						
						self.block_saving = False

				#USER HAS REQUESTED BLOCK FILE INFORMATION
				elif json_message['Type'] == 12:
					
					with open(os.path.join(self.chain_directory,json_message['File']), 'r') as handle: #OPEN REQUESTED FILE
						
						b = json.load(handle) #LOAD REQUESTED

						return_message = {"Type":12,"Filename":json_message['File'],"Block":b} #PREPARE MESSAGE TO SEND TO CLIENT

						message = self.prepare_message(json.dumps(return_message)) #CONVERT MESSAGE TO REQUIRED FORMAT

						conn.send(message) #SEND BLOCK FILE INFORMATION BACK TO CLIENT

				#CONFIRM TRANSACTION BEFORE ADDING TO MEM POOL
				elif json_message['Type'] == 13:

					txn = json_message['Txn'] #GET TXN

					if txn['txnid'] not in self.txn_confirmations and txn not in self.txn_pool: #IF TXN NOT IN CONFIRMATIONS LIST AND TXN NOT ALREADY IN POOL

						self.txn_confirmations[txn['txnid']] = 0 #ADD TO PENDING CONFIRMATIONS LIST

					self.confirm_transaction(json_message['Txn'],json_message['PubKeys']) #CONFIRM TRANSACTION
				
				#RECEIVED CONFIRMATION OF TRANSACTION
				elif json_message['Type'] == 14:

					txn = json_message['Txn'] #GET TXN

					if json_message['TXID'] not in self.txn_confirmations and txn not in self.txn_pool: #IF TXN NOT IN CONFIRMATIONS LIST AND TXN NOT ALREADY IN POOL

						self.txn_confirmations[json_message['TXID']] = 0 #ADD TO PENDING CONFIRMATIONS LIST

					if json_message['TXID'] in self.txn_confirmations: #IF TRNASACTION ALREADY IN PENDING CONFIRMATIONS

						if txn not in self.txn_pool: #IF TXN NOT IN CONFIRMATION POOL

							self.txn_confirmations[json_message['TXID']] += 1 #INCREMENT NUMBER OF CONFIRMATIONS

						if  self.txn_confirmations[json_message['TXID']] >= self.TXN_MIN_CONFIRMATIONS and txn not in self.txn_pool: #IF TXN MEETS REQUIRED CONFIRMATIONS AND NOT ALREADY IN TXN POOL

							json_message = {"Type":15,"TXID":json_message['TXID'],"Txn":json_message['Txn']} #SETUP MESSAGE

							self.broadcast_client_to_server(json.dumps(json_message)) #BROADCAST ADD TO POOL MESSAGE

				#RECEIVED MESSAGE TO ADD TRANSACTION TO TXN POOL
				elif json_message['Type'] == 15:
					
					if json_message['Txn'] not in self.txn_pool: #IF TXN NOT IN TXN POOL

						self.add_txn_to_pool(json_message['Txn']) #ADD TO POOL
				
				#CLIENT REQUESTED TXN POOL
				elif json_message['Type'] == 16:

					json_message = {'Type':16,'Mem_Pool':self.txn_pool} #PREPARE MESSAGE

					message = self.prepare_message(json.dumps(json_message)) #FORMAT MESSAGE

					#print("SENDING MEMPOOL")

					conn.send(message) #SEND TO CLIENT

				elif json_message['Type'] == 17:

					self.clients_wo_servers.append(conn)

					for peer in self.peer_services:
						address = peer.split(":")[0]
						port = peer.split(":")[1]

						json_dict = {"Type":0,"Address":address,"Port":port} #SETUP MESSAGE TO SEND LOCAL SERVER INFO SO OTHER CLIENTS CAN CONNECT
						message = self.prepare_message(json.dumps(json_dict)) #PREPARE MESSAGE
						#print("Sending Peer Back")
						conn.send(message) #SEND MESSAGE TO TO SERVER


				


			else: #IF MESSAGE CONTAINS ERROR

				self.remove(conn) #CLIENT MOST LIKELY DISCONNECTED REMOVE FROM PEERS

				self.print("CONNECTION BROKEN")

				return
				

	def send_peers_wo_servers(self,message):

		for clients in self.clients_wo_servers:  #LOOP THROUGH LIST OF PEERS WITHOUT SERVERS

				try:

					length = len(message.encode()).to_bytes(8, byteorder='big') #GET MESSAGE LENGTH AND CONVERT TO 8 BYTE VALUE

					clients.send(length + message.encode()) #SEND MESSAGE LENGTH AS FIRST 8 BYTES AND MESSAGE AS REMAINING

				except: 

					clients.close() #IF THE MESSAGE COULD NOT BE SEND CLIENT IS DISCONNECTED

					self.clients_wo_servers.remove(clients) #IF THE MESSAGE COULD NOT BE SENT REMOVE THE CLIENT
	
	#SEND MESSAGES FROM SERVER SIDE TO CLIENT SIDE
	def broadcast_server_to_client(self,message, connection):

		for clients in self.list_of_clients:  #LOOP THROUGH LIST OF CLIENTS

				if clients != connection:

					try:

						length = len(message.encode()).to_bytes(8, byteorder='big') #GET MESSAGE LENGTH AND CONVERT TO 8 BYTE VALUE

						clients.send(length + message.encode()) #SEND MESSAGE LENGTH AS FIRST 8 BYTES AND MESSAGE AS REMAINING

					except: 

						clients.close() #IF THE MESSAGE COULD NOT BE SEND CLIENT IS DISCONNECTED

						self.remove(clients) #IF THE MESSAGE COULD NOT BE SENT REMOVE THE CLIENT

	#SEND MESSAGE IN OPPOSITE DIRECTION FROM ABOVE SEND FROM CLIENT CONNECTION TO ALL SERVERS
	def broadcast_client_to_server(self,message):

		for clients in self.peer_clients: #LOOP THROUGH LIST OF ALL LOCAL CLIENTS CONNECTED TO EXTERNAL SERVERS

			try:

				length = len(message.encode()).to_bytes(8, byteorder='big') #GET MESSAGE LENGTH AND CONVERT TO 8 BYTE VALUE

				clients.send(length + message.encode()) #SEND FROM CLIENT CONNECTIONS TO SERVER

			except:
				clients.close() #CLOSE CONNECTION

				self.peer_clients.remove(clients) #REMOVE CLIENT

	#REMOVE CONNECTION
	def remove(self, connection):

		if connection in self.list_of_clients: #IF CONNECTION IN LIST

			self.list_of_clients.remove(connection) #REMOVE FROM LIST
		
		if connection in self.clients_wo_servers:
			self.clients_wo_servers.remove(connection)

	#IF MESSAGES GO DIRECTLY TO INDIVIDUAL CLIENT FORMAT THEM USING THIS FUNCTION
	def prepare_message(self,message): 
		
		length = len(message.encode()).to_bytes(8, byteorder='big') #GET LENGTH OF MESSAGE AS FIXED 8 BYTE VALUE

		message = length + message.encode() #APPEND MESSAGE TO LENGTH

		return message
	
	#START SERVER
	#P2P NETWORK HAS TWO PARTS A SERVER AND A CLIENT
	#SERVER ALLOWS OTHER USERS TO CONNECT FROM EXTERNALLY
	#CLIENT ALLOWS CONNECTION FROM INTERNAL TO EXTERNAL
	def start_server(self, server_address, server_port):

		self.main_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #OPEN SOCKET

		self.main_server.setblocking(0)

		self.main_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) #SET SOCKET OPTIONS

		self.main_server.bind((server_address, server_port)) #BIND SERVER TO ADDRESS AND PORT

		self.main_server.listen(100) #LISTEN TO SOCKET AND QUEUE AS MANY AS 100 CONNECT REQUESTS
		
		self.print("Listening on port:{0}".format(server_port))

		self.list_of_clients = [] #ESTABLISH CLIENT LISTING

		while True: #LOOP WAITING FOR CONNECTION

			try:

				conn, addr = self.main_server.accept() #ACCEPT INCOMING REQUEST

				self.list_of_clients.append(conn) #ADD CONNECTION TO LIST OF CLIENTS

				threading.Thread(target=self.ClientThread,args=(conn,addr)).start() #OPEN THREAD FOR NEW CLIENT CONNECTION
			
			except:
				#raise Exception("Exception Reached")
				return

		self.main_server.close() #CLOSE MAIN SERVER IF WHILE LOOP BROKEN

	def read_client_message(self,client,addr):

		while True:

			time.sleep(1)

			#ENABLE NON BLOCKING SERVER MESSAGE RECEIPT SHOULD RUN IN PARALLEL SO THAT MESSAGES DON'T GET DROPPED
			#sockets_list = self.peer_clients #GET LIST OF SOCKETS

			#read_sockets,write_socket, error_socket = select.select(sockets_list,[],[]) #RUN SELECT TO SPLIT SOCKET INTO WRITE SOCKET AND READ SOCKET

			#for socks in read_sockets:

			#	if socks == client:
			
			length = int.from_bytes(client.recv(8),'big')

			if length > 2048:

				recv_length = 0

				message = bytes()

				recv_amount = 2048

				while recv_length < length:

					time.sleep(1)

					message += client.recv(recv_amount)
					
					#print(message)

					recv_length += 2048

					if (recv_length + 2048 > length):

						recv_amount = length - recv_length

			else:

				time.sleep(1)

				message = client.recv(length)


			if message == b'': #IF MESSAGE RECEIVED CONTAINS NO BYTES CLIENT DISCONNECTED

				self.peer_services.remove(connect_address + ":" + str(connect_port)) #REMOVE VALUE FROM PEER SERVICES

				self.peer_clients.remove(client) #REMOVE FROM PEER CLIENTS LIST

				client.close() #CLOSE CLIENTS

				self.print("Connection Broken")

				return

			if message: #MESSAGE WAS RECEIVED

				json_message = json.loads(message.decode('utf-8')) #LOAD MESSAGE INTO DICT

				#RECEIVED INFORMATION ABOUT ANOTHER SERVER
				if json_message['Type'] == 0: #IF MESSAGE TYPE = 0

					if self.connect_server == False and json_message['Address'] + ":" + str(json_message['Port']) not in self.peer_services:

						threading.Thread(target=self.start_client,args=(json_message['Address'],int(json_message["Port"]))).start() #OPEN NEW THREAD TO CREATE A NEW CLIENT TO CONNECT TO NEW SERVER

					#IF SERVER DOESN'T ALREADY EXIST IN PEER SERVICES AND SERVER NOT LOCAL SERVER
					elif json_message['Address'] + ":" + str(json_message['Port']) not in self.peer_services and json_message['Address'] + ":" + str(json_message['Port']) != (self.server_address + ":" + str(self.server_port)):

						threading.Thread(target=self.start_client,args=(json_message['Address'],json_message["Port"])).start() #OPEN NEW THREAD TO CREATE A NEW CLIENT TO CONNECT TO NEW SERVER

				#RECEIVE CHAIN SIZE
				elif json_message['Type'] == 3:

					#print("Chain Size Received:",json_message['Chain_Size'])
					
					if json_message['Chain_Size'] in self.chain_sizes: #IF CHAIN SIZE HAS ALREADY BEEN RECORDED

						self.chain_size_confirmations += 1 #INCREMENT COUNTER

						if self.chain_size_confirmations >= self.CHAIN_SIZE_MIN_CONFIRMATIONS: #IF CONFIRMATIONS 

							self.confirmed_size = json_message['Chain_Size'] #APPLY CHAIN SIZE AS CONFIRMED CHAIN SIZE

					else:

						self.chain_sizes.append(json_message['Chain_Size']) #IF CHAIN SIZE HAS NOT BEEN SEEN BEFORE ADD IT TO ARRAY

				#IF CHAIN HAS BEEN FULLY DOWNLOADED NETWORK REQUESTS A TARGET FOR THE NEXT BLOCK
				elif json_message['Type'] == 8 and self.chain_downloaded and self.node_target == None:
					#NO TARGET HAS BEEN ESTABLISHED GENERATE TARGET
					lower_bound = 500
					upper_bound = 1000
					if len(self.peer_services) > 1:
						lower_bound = 2000
						upper_bound = 4000
					elif len(self.peer_services) > 2:
						lower_bound = 5000
						upper_bound = 20000
					elif len(self.peer_services) > 10:
						lower_bound = 2500
						upper_bound = 20000

		
					random_number = random.randint(lower_bound,upper_bound)#4096#16777216)#,286331153)#572662306)#1431655765)#268435456,#858993459) #TARGET IS A 8 BYTE INTEGER

					target = random_number.to_bytes(4, byteorder='big').hex() #FORMAT RANDOM NUMBER TO HEX VALUE

					json_message = {'Type':9,'Target':target} #PREPARE RETURN MESSAGE

					self.node_target = target #SET TARGET VALUE

					self.print("Target Established:{0}".format(self.node_target)) #DISPLAY TARGET

					self.broadcast_client_to_server(json.dumps(json_message)) #SEND TARGET FROM CLIENT TO SERVER

				#IF CHAIN DOWNLOADED TARGET ALREADY ESTABLISHED BY CHAIN SET TARGET
				elif json_message['Type'] == 9 and self.chain_downloaded:

					self.node_target = json_message['Target']  #SET TARGET VALUE

					self.print("Chain Target:{0}".format(self.node_target)) #DISPLAY TARGET


				elif json_message['Type'] == 10:

					block_hash = hash_block_dict(json_message['Block'])

					#print("SAVING NEWLY MINED BLOCKED")

					if block_hash.hex() not in self.block_hashes and self.block_saving == False:

						self.block_confirmations = 0 #RESET BLOCK CONFIRMATIONS TO ZERO

						self.pending_block_hashes = {} #RESET PENDING BLOCK CONFIRMATIONS TO BLANK

						print("Setting Target to None")

						self.node_target = None #SET TARGET BACK TO NONE

						self.block_saving = True

						self.block_added = True

						print("SAVING BLOCK 2")

						save_block(self.chain_directory,json_message['Block']) #WRITE BLOCK TO CHAIN FILE

						if block_hash.hex() not in self.block_hashes: 

							self.block_hashes.append(block_hash.hex()) #APPEND BLOCK HASH TO LIST OF EXISTING HASHES

						self.block_thread = False #RELEASE THREAD

						if (len(json_message['Block']['txns']) > 1): #REMOVE MINED TRANSACTIONS FROM THE MEM POOL TO PREVENT DUPLICATION

							for txn in json_message['Block']['txns'][1:]: #

								if (txn in self.txn_pool):

									self.txn_pool.remove(txn)

						self.update_chain()
						
						self.block_saving = False

				
				# IF MESSAGE RECEIVED WITH TYPE 11 MINED BLOCK WAS REJECTED BY THE NETWORK
				elif json_message['Type'] == 11 and self.chain_downloaded:
					self.block_confirmations = -1
				
				# IF TYPE = 12 REQUESTED BLOCK INFORMATION RECEIVED
				elif json_message['Type'] == 12:

					# IF FILE WAS ALREADY RECEIVED BEFORE THIS MESSAGE WAS SENT IGNORE
					if (os.path.exists(os.path.join(self.chain_directory,json_message['Filename']))):
						continue
					
					#CHECK THE CHAIN TO CONFIRM THE BLOCKS RECEIVED ARE CORRECT AND COMPLETE
					try:
						prev_hash = bytearray(32).hex() #INITIALIZE HASH VARIABLE

						if len(self.block_hashes) > 0: #IF BLOCK_HASHES HAS VALUES

							prev_hash = self.block_hashes[-1] #SET PREV HASH TO LAST VALUE IN ARRAY

						assert(json_message['Block']['prev_block_hash'] == prev_hash) #ASSERT LAST HASH IN LOCAL CHAIN EQUAL TO LAST HASH OF RECEIVED BLOCK

					except:
						self.print("Chain Corrupted") #NOTIFY LOCAL CHAIN MAY BE CORRUPTED
						continue
						#raise Exception("Chain Corrupted") RAISE EXCEPTION IF NECESSARY
					
					#IF ASSERTION SUCCESSFUL OPEN FILE TO WRITE TO
					with open(os.path.join(self.chain_directory,json_message['Filename']), 'w') as handle:

						b = json_message['Block'] #LOAD BLOCK FROM RECEIVED MESSAGE

						json.dump(b, handle) #SAVE BLOCK TO CHAIN LOCATION

					block_hash = hash_block_dict(b)

					if block_hash.hex() not in self.block_hashes: 

						self.block_hashes.append(block_hash.hex()) #HASH BLOCK AND ADD TO BLOCK HASHES LISTING

					self.wait_download = False #RELEASE MAIN THREAD OF DOWNLOAD HALT

				#TXN POOL
				#THE TXN POOL IS LISTING OF TRANSACTIONS ACROSS NETWORK THAT NEED TO BE MINED
				#WHEN CONNECTION IS ESTABLISHED UPDATED LISTING OF TXN POOL IS PROVIDED
				elif json_message['Type'] == 16:
					
					mem_pool = json_message["Mem_Pool"] #RECEIVE POOL

					mem_pool_hash = hash_block(json.dumps(mem_pool).encode()) #HASH THE POOL

					if mem_pool_hash in self.txn_pool_hashes: #IF HASH IS ALREADY IN MEM POOL HASHES INCREASE CONFIRMATIONS

						self.mem_pool_confirmations += 1 #INCREMENT CONFIRMATIONS OF MEM POOL

					else:

						self.txn_pool_hashes.append(mem_pool_hash)  #IF HASH DOESN'T ALREADY EXIST IN MEM POOL APPEND

					if self.mem_pool_confirmations >= self.MEM_POOL_MIN_CONFIRMATIONS or len(self.peer_services) < 2: #IF MEM POOL CONFIRMATIONS GREATER THAN OR EQUAL TO MIN CONFIRMATIONS OR AVAILABLE PEERS LESS THAN 2 MEM POOL IS AVAILABLE MEM POOL

						self.txn_pool = mem_pool #SET MEM POOL

						self.block_thread = False #RELEASE MAIN THREAD

	#START CLIENT CONNECTION
	def start_client(self, connect_address, connect_port):
		
		client = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #OPEN SOCKET CLIENT

		try:

			client.connect((connect_address, connect_port)) #CONNECT TO SERVER

			#client.setblocking(0)
			#client.settimeout(10)
			
			

			self.print("Client Connected")

			if self.connect_server:

				json_dict = {"Type":0,"Address":self.server_address,"Port":self.server_port} #SETUP MESSAGE TO SEND LOCAL SERVER INFO SO OTHER CLIENTS CAN CONNECT

				if self.external_server != False and self.external_server_port != False:
					json_dict = {"Type":0,"Address":self.external_server,"Port":self.external_server_port}

				message = self.prepare_message(json.dumps(json_dict)) #PREPARE MESSAGE

				client.send(message) #SEND MESSAGE TO TO SERVER

				json_dict = {"Type":8}

				message = self.prepare_message(json.dumps(json_dict)) #PREPARE MESSAGE

				client.send(message) #SEND MESSAGE TO TO SERVER

			else:

				json_dict = {"Type":17} #NO SERVER INFO TO SEND
				message = self.prepare_message(json.dumps(json_dict)) #PREPARE MESSAGE

				client.send(message) #SEND MESSAGE TO TO SERVER

			self.peer_services.append(connect_address + ":" + str(connect_port)) #ADD SERVER TO PEER SERVICES LIST

			self.peer_clients.append(client) #ADD CLIENT TO LIST OF CLIENTS

			threading.Thread(target=self.read_client_message,args=(client,connect_address)).start()
			
		except:

			self.print("Unable to Connect")
		#	raise Exception("Connection Broken")
			return

	#PROVIDE LISTING OF PEERS ON NETWORK
	def listpeers(self):
		
		self.print(json.dumps(self.peer_services))
		self.print(json.dumps(len(self.clients_wo_servers)))

	#CONFIRMING BLOCK SENT TO NETWORK
	def confirm_block(self,block,pubKey,signature,client = None):

		try:
			print("CONFIRMING BLOCK")
			#CONFIRM SIGNATURE
			block_hash = hash_block_dict(block) #HASH BLOCK

			pubKey = pub_key_from_string(pubKey) #GENERATE PUBKEY OBJECT FROM STRING

			verify_msg(bytes.fromhex(signature),block_hash,pubKey) #VERIFY SIGNATURE PROVIDE TO CONFIRM BLOCK IS THE SAME AS IT WAS SENT AND OWNERSHIP OF BLOCK IS CORRECT FOR MINING REWARD

			previous_hash = bytearray(32).hex() #ESTABLISH PREVIOUS CONFIRMED BLOCK HASH VARIABLE

			if (len(self.block_hashes) > 0): #IF LENGTH PREVIOUS HASHES ARRAY GREATER THAN 0

				previous_hash = self.block_hashes[-1] #SET PREVIOUS HASH AS LAST ELEMENT ON ARRAY

			#CHECK PREVIOUS BLOCK HASH
			assert (block['prev_block_hash'] == previous_hash) #ENSURE PREVIOUS HASH IS SAME AS PREVIOUS HASH ON BLOCK
			
			#CHECK TIME
			assert (block['time'] <= int(time.time() + 20*60) and block['time'] >= int(time.time()) - 3600) #ENSURE TIME IS CORRECT BLOCKS WITH TIME GREATER THAN CURRENT TIME OR BLOCKS NOT CONFIRMED AFTER AN HOUR WILL NOT BE CONFIRMED
			
			#VERIFY TRANSACTIONS
			assert (len(block['txns'][0]['inputs']) == 1 and len(block['txns'][0]['outputs']) == 1) #VERIFY COINBASE TRANSACTION HAS ONE INPUT AND ONE OUTPUT
			
			#CHECK INPUTS FORMAT TO CONFIRM COINBASE TRANSACTION FORMATTED PROPERLY
			assert (block['txns'][0]['inputs'][0]['prev_txid'] == bytearray(16).hex() and block['txns'][0]['inputs'][0]['prev_txn_output'] == 0 and block['txns'][0]['inputs'][0]['sig_prev_out'] == bytearray(64).hex())
			
			#CHECK OUTPUTS TO ENSURE THAT ADDRESS PROVIDED IN COINBASE TRANSACTION IS CORRECT
			assert (block['txns'][0]['outputs'][0]['address'] == hash_v_key(pubKey).hex())
			
			#CHECK VALUE OF COINBASE TRANSACTION EQUAL TO THE CORRECT REWARD VALUE
			reward = int(20 * (1/max(int(2*(time.time() - 1577836800)/315360000),1)))
			
			block_in_value = 0
			block_out_value = 0

			for x,txn in enumerate(block['txns']):

				if x == 0:

					continue

				for x, input_val in enumerate(txn['inputs']):

					prev_txn = get_txn(input_val['prev_txid'],self.chain_directory) #GET PREVIOUS TXN

					if prev_txn == False: #IF THEIR IS NO PREVIOUS TXN ERROR REACHED

						return False
					
					block_in_value += prev_txn['outputs'][input_val['prev_txn_output']]['value']

				for x, output_val in enumerate(txn['outputs']): #FOR OUTPUT IN TRANSACTION

					block_out_value += output_val['value'] #INCREMENT TOTAL OUTPUT VALUE
				
			
			reward += block_in_value - block_out_value  

			print(reward)
			print(block_in_value - block_out_value)  
			print(block['txns'][0]['outputs'][0]['value'])

			assert (block['txns'][0]['outputs'][0]['value'] == reward)

			#MAKE SURE COINBASE TXID IS 16 BYTES
			assert (len(bytes.fromhex(block['txns'][0]['txnid'])) == 16)

			#CHECK BLOCK HASH IS BELOW TARGET
			print("TARGET IS:",self.node_target)
			print(self.block_saving)
			print(block_hash.hex() in self.block_hashes)
			if self.block_saving == True or block_hash.hex() in self.block_hashes:
				json_message = {"Type":10,"Block":block} #PREPARE MESSAGE TO SEND

				message = self.prepare_message(json.dumps(json_message))

				client.send(message)
				return
			assert (block_hash < (bytes.fromhex(self.node_target) + bytearray(28)))

			#CHECK OTHER TRANSACTIONS ONLY AFTER CONFIRMATION ARE THESE ADDED SO RISK IS LOWER
			if (len(block['txns']) > 1):

				for txn in block['txns'][1:]: #FOR EACH TRANSACTION ENSURE THAT THE HASH OF THE TRANSACTION IS THE SAME AS THE CONFIRMED CORRESPONDING TRANSACTION IN THE CONFIRMED TXN POOL

					assert(any(hash_block(json.dumps(d).encode()) == hash_block(json.dumps(txn).encode()) for d in self.txn_pool))
						

			#print("Block Confirmed")
			#print("Sending Confirmation")
			
			#SEND CONFIRMATION
			json_message = {"Type":10,"Block":block} #PREPARE MESSAGE TO SEND

			self.broadcast_client_to_server(json.dumps(json_message)) #BROADCAST CONFIRMATION

			if (len(block['txns']) > 1): #IF BLOCK CONSISTS OF MORE THAN JUST COINBASE TRANSACTION

				for txn in block['txns'][1:]: #LOOP THROUGH TRANSACTIONS

					if self.txn_pool != None:
						if (len(self.txn_pool) > 0): #IF TRANSACTION LEN GREATER THAN O

							self.txn_pool.remove(txn) #REMOVE TRANSACTION FROM POOL
			
			if block_hash.hex() in self.pending_block_hashes:

				self.pending_block_hashes[block_hash.hex()] += 1
			
			else:

				self.pending_block_hashes[block_hash.hex()] = 1

			
			if self.pending_block_hashes[block_hash.hex()] >= self.BLOCK_MIN_CONFIRMATIONS and block_hash.hex() not in self.block_hashes and self.block_saving == False: #IF BLOCK CONFIRMATIONS GREATER THAN MIN CONFIRMATIONS
				
				self.block_saving = True

				self.block_added = True

				self.node_target = None #SET TARGET BACK TO NONE
				print("Setting Target To None")

				print("SAVING BLOCK 3")
				
				save_block(self.chain_directory,block) #SAVE BLOCK TO CHAIN FILE

				print("Telling Peer To Add Block")

				self.send_peers_wo_servers(json.dumps(json_message))

				self.block_confirmations = 0 #RESET CONFIRMATIONS

				self.pending_block_hashes = {} #RESET PENDING HASHES

				if block_hash.hex() not in self.block_hashes: 

					self.block_hashes.append(block_hash.hex()) #ADD BLOCK TO HASHES

				self.block_thread = False #RELEASE MAIN THREAD

				self.update_chain()

				self.block_saving = False
			
		except:
			#BLOCK NOT CONFIRMED
			json_message = {"Type":11}

			
			message = self.prepare_message(json.dumps(json_message)) #PREPARE UNSUCCESSFUL MESSAGE

			if client == None: #IF NO CLIENT WAS SENT WITH FUNCTION

				self.block_confirmations = -1 #SET CONFIRMATIONS TO -1

			else:

				client.send(message) #SEND MESSAGE TO CLIENT SAYING BLOCK REJECTED

			self.print("Unable to Confirm Block")

			raise Exception("BLOCK ERROR")    
		

	def chain_mine(self,loop_mine=False,wait=False):

		self.mining = True

		try:
			if loop_mine == True:
				while len(self.peer_services) == 0:
					continue
				if wait == True:
					time.sleep(10)

			self.download_chain()

			if self.connect_server == False:
				self.print("Cannot Mine Must Connect Server!")
				return

			self.block_added = False
			
			self.block_confirmations = 0 #SET CONFIRMATIONS TO ZERO
			
			print("Resetting Target")

			self.node_target = None #RESET TARGET TO NONE

			self.broadcast_client_to_server(json.dumps({'Type':8})) #SEND MESSAGE REQUESTING TARGET VALUE FOR BLOCK

			print("Waiting for Target")

			timeout = time.time() + 30

			while self.node_target == None:
				if time.time() > timeout:
					self.print("Unable to Obtain Target")
					if loop_mine:
						self.chain_mine(True)
					return
				continue


			hash, priv_key = create_key(self.key_directory) #GENERATE KEY TO RECEIVE REWARDS

			if (len(self.block_hashes) == 0): #IF BLOCK HASHES LIST EQUAL ZERO

				prev_block_hash = bytearray(32).hex() #PREV_BLOCK_HASH = 32 BYTE ARRAY FO ZEROS

			else:

				prev_block_hash = self.block_hashes[-1] #SET PREV_BLOCK_HASH TO LAST CONFIRMED BLOCK HASH
			
			if self.txn_pool == None: #IF TXN_POOL NON

				self.txn_pool = [] #SET IT TO EMPTY ARRAY

			self.update_pool() #UPDATE MEM POOL

			block = gen_block(self.node_target, hash, prev_block_hash, self) #GENERATE A COMPLETE AND FORMATTED BLOCK WITH GIVEN VALUES

			if block == False:
				self.print("Failed to Mine Block")
				return
			
			block_hash = hash_block_dict(block) #GENERATE HASH OF BLOCK

			block_sig = sign_msg(block_hash,priv_key) #SIGN THE BLOCK HASH WITH PRIVATE KEY

			self.block_thread = True #SETUP THREAD BLOCKING

			json_message = {"Type":7,"Block":block,"PubKey":priv_key.verifying_key.to_string().hex(),"Signature":block_sig} #ESTABLISH MESSAGE TO SEND TO NODES FOR CONFIRMATION

			print("SENDING 7")
			print("Message:",json_message)
			length = len(json.dumps(json_message).encode()).to_bytes(8, byteorder='big')
			print(length)

			if block_hash.hex() in self.pending_block_hashes:
				self.pending_block_hashes[block_hash.hex()] += 1 #ADD BLOCK HASH TO PENDING HASHES
			else:
				self.pending_block_hashes[block_hash.hex()] = 1 

			self.broadcast_client_to_server(json.dumps(json_message)) #SEND MESSAGE ASKING FOR CONFIRMATION

			timeout = time.time() + (60*5)

			while self.block_thread: #BLOCK THREAD WAITING FOR CONFIRMATIONS

				if self.block_confirmations == -1 or time.time() > timeout: #IF AT ANY POINT CONFIRMATIONS -1 BLOCK CONTAINED AN ERROR

					self.print("Could Not Mine Block")
					if loop_mine:
						self.chain_mine(True)

					return

				continue
			
			self.print("Block Mined On Chain!!!")

			if loop_mine:
				self.chain_mine(True)

			self.mining = False
		except:
				if loop_mine:
						self.chain_mine(True)
				self.mining = False
		
	#SEND TRANSACTION TO NETWORK
	def send_transaction(self,txn,pubKeys):

		json_message = {"Type":13,"Txn":txn,"PubKeys":pubKeys} #PREPARE MESSAGE TO SEND TO NETWORK

		self.broadcast_client_to_server(json.dumps(json_message)) #BROADCAST MESSAGE

	#UPDATE TXN POOL
	def update_pool(self):

		self.mem_pool_confirmations = 0 #RESET CONFIRMATIONS

		self.block_thread = True #ENABLE THREAD BLOCKING

		txn_pool_hash = hash_block(json.dumps(self.txn_pool).encode()) #HASH TRANSACTION POOL

		self.txn_pool_hashes.append(txn_pool_hash) #APPEND TO LIST OF TRANSACTIONS POOL HASHES

		json_message = {"Type":16} #SEND MESSAGE REQUESTING TRANSACTION POOL

		self.broadcast_client_to_server(json.dumps(json_message)) #SEND MESSAGE

		while self.block_thread == True: #WAIT UNTIL TRANSACTION POOL UPDATES

			if (len(self.peer_services) < 1): #IF PEERS LESS THAN 1 CONFIRMATION REQUIREMENTS CAN'T BE REACHED CONTINUE ANYWAY

				break

			continue
		
		self.print("Mem Pool Updated")
		

	#DEBUGGING TOOL TO READPOOL DATA INCLUDING UNCONFIRMED TRANSACTIONS
	def read_pool(self):
		self.print(json.dumps(self.txn_confirmations))
		self.print(json.dumps(self.txn_pool))
	
	#ADD TRANSACTION TO POOL AFTER CONFIRMATION RECEIVED
	def add_txn_to_pool(self,txn):

		if txn not in self.txn_pool: #ENSURE TXN IS NOT ALREADY IN TXN POOL

			self.txn_pool.append(txn) #APPEND TRANSACTION TO POOL

			del self.txn_confirmations[txn['txnid']] #DELETE IT FROM CONFIRMATIONS PENDING

			self.print("TXN Added to pool")

	def ch_chain_dir(self,chain_dir):
		self.chain_directory = chain_dir
		self.download_chain()




	def confirm_transaction(self,txn,pubKeys):

		self.print("Confirming Transaction")

		try:
			
			total_in_value = 0 #SET UP TOTAL IN VARIABLE
			#CHECK ID FORMAT
			assert (len(bytes.fromhex(txn['txnid'])) == 16) #ENSURE TXID IS 16 BYTE INTEGER
			#CHECK TIME
			assert (txn['time'] <= int(time.time() + 20*60) and txn['time'] >= int(time.time()) - 3600) #ENSURE TXN IS NOT FROM FUTURE AND NOT FROM AN HOUR IN THE PAST
			#CHECK INPUTS
			assert (len(txn['inputs']) > 0) #AT LEAST ONE INPUT IN TRANSACTION

			for x, input_val in enumerate(txn['inputs']): #FOR EACH INPUT

				prev_txn = get_txn(input_val['prev_txid'],self.chain_directory) #GET PREVIOUS TXN

				if prev_txn == False: #IF THEIR IS NO PREVIOUS TXN ERROR REACHED

					assert(False)

				address = prev_txn['outputs'][input_val['prev_txn_output']]['address'] #GET ADDRESS OF PREVIOUS TXN

				total_in_value += prev_txn['outputs'][input_val['prev_txn_output']]['value'] #GET INPUT VALUE OF TXN

				pubKeyHash = hash_v_key(pub_key_from_string(pubKeys[x])).hex() #HASH TRANSACTION SENDERS PUBLIC KEY
				#VERIFY OWNERSHIP
				#VERIFY PUBKEY PROVIDED = ADDRESS OF INPUT
				assert(address == pubKeyHash) #VERIFY THAT USER SENDING COIN HAS THE PUBLIC KEY CORRESPONDING TO ADDRESS
				#VERIFY USER OWNS INPUTS BY CHECKING PRIVATE KEY GENERATED SIGNATURE MATCHES PUBKEYHASH THIS VERIFIES OWNERSHIP OF PUBLICKEY AND THEREFORE OWNERSHIP OF COIN BEING SENT
				verify_msg(bytes.fromhex(input_val['sign_prev_out']),bytes.fromhex(address),pub_key_from_string(pubKeys[x]))

				assert(not any(input_val in d['inputs'] for d in self.txn_pool))
				

			#CHECK OUTPUTS
			assert (len(txn['outputs']) > 0) #ENSURE AT LEAST ONE OUTPUT

			reward = int(20 * (1/max(int(2*(time.time() - 1577836800)/315360000),1)))

			minimum_fees = float("{:.2f}".format(-((reward - 25)/(reward+10))))

			total_out_value = 0 #SETUP OUTPUT VALUE COUNTER

			for x, output_val in enumerate(txn['outputs']): #FOR OUTPUT IN TRANSACTION

				assert(len(bytes.fromhex(output_val['address'])) == 32) #ENSURE ADDRESS IS EQUAL TO 32 BYTES

				total_out_value += output_val['value'] #INCREMENT TOTAL OUTPUT VALUE

				assert((total_out_value+minimum_fees) <= (total_in_value))


			
			#assert(total_out_value == total_in_value) #ENSURE TOTAL OUT VALUE = TOTAL IN VALUE REMOVE THIS ASSERTION IF YOU WANT TO USE TXN FEES, THEN GENERATE BLOCK TO CAPTURE REMAINING INPUT/OUTPUT VALUE

			self.print("Transaction Confirmed")

			if (txn['txnid'] not in self.txn_confirmations and txn not in self.txn_pool): #IF TXN NOT IN CONFIRMATIONS LISTING, AND NOT IN TXN POOL ALREADY

				self.txn_confirmations[txn['txnid']] = 0 #ADD TO CONFIRMATIONS POOL

			if txn['txnid'] in self.txn_confirmations: #IF TXN IN CONFIRMATIONS POOL

				self.txn_confirmations[txn['txnid']] += 1 #INCREMENT
			
			json_message = {"Type":14, "TXID":txn['txnid'],"Txn":txn} #SEND CONFIRMATION MESSAGE

			self.broadcast_client_to_server(json.dumps(json_message)) #BROADCAST MESSAGE

			if  self.txn_confirmations[txn['txnid']] >= self.TXN_MIN_CONFIRMATIONS not in self.txn_pool: #IF CONFIRMATIONS GREATER THAN MIN CONFIRMATIONS

				json_message = {"Type":15,"TXID":txn['txnid'],"Txn":txn} #PREPARE MESSAGE

				self.broadcast_client_to_server(json.dumps(json_message)) #SEND MESSAGE TO ADD TXN TO POOL
			
		except:
			if txn['txnid'] in self.txn_confirmations:
				del self.txn_confirmations[txn['txnid']]
			self.print("Unable to Confirm Transaction")
			raise Exception("Unable to Complete Transaction")
