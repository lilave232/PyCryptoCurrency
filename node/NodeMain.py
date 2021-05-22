import threading
import socket
import select
import errno
import sys
import json
import time
from node.parse_messages import *
from chain.ChainController import *
from chain.Wallet import *

class Peer:
	address = None
	client = None
	port = None
	def __init__(self,addr,client,port):
		self.address = addr
		self.client = client
		self.port = port

	def __str__(self):
		return self.address + ":" + str(self.port)

class Server:
	address = None
	port = None
	server = None
	connected = False
	clients = []
	node = None
	server_thread  = None
	lock = None
	def __init__(self,addr,server,port,node,lock = None):
		self.address = addr
		self.port = port
		self.server = server
		self.node = node
		self.lock = lock

	def connect(self):
		try:
			self.server = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
			self.server.bind(("0.0.0.0", self.port))
			self.server.listen(100)
			self.connected = True
			self.server_thread = threading.Thread(target=self.run)
			if self.server_thread.is_alive() == False:
				self.server_thread.start()
				print("Listening on port:{0}".format(self.port))
			else:
				print("Server Already Running")
		except:
			self.node.stop_server()
			print("Unable to Start Server")
	
	def close(self):
		if self.connected:
			self.server.close()
			self.connected = False
	
	def run(self):
		try:
			while self.connected:
				conn, info = self.server.accept()
				peer = Peer(info[0],conn,info[1])
				self.clients.append(peer)
				threading.Thread(target=self.read,args=(peer,)).start()
		except socket.error as socketerror:
			print("Error: ", socketerror)
		except KeyboardInterrupt:
			self.server.close()

	def read(self,client):
		try:
			while self.connected:
				received = bytes("",'utf-8')
				data = client.client.recv(1024)
				if len(data) == 0:
					print("CLIENT DISCONNECTED")
					if client in self.clients:
						self.clients.remove(client)
					sys.exit()
				while data:
					received += data
					if received[-5:] == bytes("<EOM>",'utf-8'):
						break
					data = client.client.recv(1024)
					if len(data) == 0:
						print("CLIENT DISCONNECTED")
						if client in self.clients:
							self.clients.remove(client)
						sys.exit()
				for msg in received.decode('utf-8').split("<EOM>"):
					self.node.parse_server_message(client,msg)
		except:
			if client in self.clients:
				self.clients.remove(client)
			sys.exit()
			
	
	def broadcast(self,msg):
		for client in self.clients:
			ret = self.write_client(client,msg)
			if ret == False:
				self.clients.remove(client)

	def write_client(self,client,msg):
		conn = client.client
		data = bytes(msg + "<EOM>",'utf-8')
		data_size = len(data)
		total_sent = 0
		while len(data):
			try:
				sent = client.client.send(data)
				total_sent += sent
				data = data[sent:]
				#print('Sending data')
			except socket.error as e:
				if e.errno != errno.EAGAIN:
					raise e
				print('Blocking with', len(data), 'remaining')
				select.select([], [client.client], [])  # This blocks until
			except:
				self.clients.remove(client)
				return False

		assert total_sent == data_size

		return True
	
class Client:
	address = None
	port = None
	client = None
	connected = False
	node = None
	def __init__(self,addr,client,port,node):
		self.address = addr
		self.port = port
		self.client = client
		self.node = node

	def __str__(self):
		return self.address + ":" + str(self.port)

	def connect(self):
		try:
			self.client.connect((self.address, self.port))
			self.connected = True
			if self.node.server != None:
				message = {'type':0,'Server_Address':self.node.server.address,'Server_Port':self.node.server.port}
				self.write(json.dumps(message))
			else:
				message = {'type':0}
				self.write(json.dumps(message))
			threading.Thread(target=self.read).start()
		except:
			self.connected = False
			print("Unable to Connect")
			return


	def write(self,msg):
		if self.connected:
			data = bytes(msg + "<EOM>",'utf-8')
			data_size = len(data)
			total_sent = 0
			while len(data):
				try:
					sent = self.client.send(data)
					total_sent += sent
					data = data[sent:]
				except socket.error as e:
					if e.errno != errno.EAGAIN:
						raise e
					print('Blocking with', len(data), 'remaining')
					select.select([], [self.client], [])  # This blocks until
				except:
					return False

			assert total_sent == data_size
			return True
		else:
			return False

	def read(self):
		# try:
		while self.connected:
			received = bytes("",'utf-8')
			data = self.client.recv(1024)
			if len(data) == 0:
				print("DATA FAILURE 1")
				print("SERVER DISCONNECTED")
				self.client.close()
				self.connected = False
				self.node.remove_client(self)
				sys.exit()
			while data:
				received += data
				if received[-5:] == bytes("<EOM>",'utf-8'):
					break
				data = self.client.recv(1024)
				if len(data) == 0:
					print("DATA FAILURE 2")
					print("SERVER DISCONNECTED")
					self.client.close()
					self.connected = False
					self.node.remove_client(self)
					sys.exit()
			for msg in received.decode('utf-8').split("<EOM>"):
				self.node.parse_client_message(self,msg)
		# except:
		# 	print("OVERALL FAILURE")
		# 	print("SERVER DISCONNECTED")
		# 	self.client.close()
		# 	self.connected = False
		# 	self.node.remove_client(self)
		# 	sys.exit()

class P2PNetNode:
	initial_connect_address = "localhost"
	inital_connect_port = 4444
	chain_directory = "chain"
	server_thread = None
	client_thread = None
	server = None
	clients = []
	pause = False
	lock = None
	controller = None
	wallet = None
	###
	# Initialize Node
	###
	def __init__(self,init_connect_addr="localhost",init_connect_port=4444,chain_directory="blockchain"):
		#SETUP CONNECTION VARIABLES
		self.controller = ChainController(self,chain_directory)
		self.wallet = Wallet(self,self.controller)
		self.controller.set_wallet(self.wallet)
		self.inital_connect_address = init_connect_addr
		self.inital_connect_port = init_connect_port
		self.chain_directory = chain_directory
		self.lock = threading.Lock()

	def setconfig(self,file):
		try:
			js_config = json.load(open(file, "r"))
			print(js_config)
		except:
			print("Unable to Set Config")

	def start_server(self,server_address = "localhost",server_port=4444):
		if self.server == None or self.server.connected == False:
			self.server = Server(server_address,socket.socket(socket.AF_INET,socket.SOCK_STREAM), server_port,self)
			self.server.connect()
		else:
			print("Server Already Running")

	def remove_client(self,client):
		if client in self.clients:
			self.clients.remove(client)
	
	def stop_server(self):
		self.server.close()
		self.server.connected = False
		self.server_thread = False
		

	def start_client(self,address="localhost",port=4444):
		self.lock.acquire()
		print("Attempting to Connect To: ", address, port)
		if (self.server != None and address == self.server.address and port == self.server.port) or ((address,port) in [(client.address, client.port) for client in self.clients]):
			self.pause = False
			print("CLIENT NOT STARTED")
			self.lock.release()
			return
		client = Client(address,socket.socket(socket.AF_INET, socket.SOCK_STREAM),port,self)
		client.connect()
		if client.connected:
			print("CLIENT CONNECTED TO: ", address, port)
			self.clients.append(client)
		else:
			print("CLIENT NOT STARTED")
		self.lock.release()
		return client


	def server_broadcast(self,msg):

		self.server.broadcast(msg)
	
	def client_broadcast(self,msg):
		for client in self.clients:
			ret = client.write(msg)
			if ret == False:
				self.clients.remove(client)
	## PARSE MESSAGE RECEIVED BY SERVER
	def parse_server_message(self,client,msg):
		parse_server_recvd(self,client,msg)
	## PARSE MESSAGE RECEIVED BY CLIENT
	def parse_client_message(self,client,msg):
		parse_client_recvd(self,client,msg)
		
	def list_connections(self):
		self.list_incoming()
		self.list_outgoing()

	def list_incoming(self):
		if self.server != None:
			print("Incoming: " + ','.join([str(client) for client in self.server.clients]))
		else:
			print("Incoming Not Connected")
	
	def list_outgoing(self):
		print("Outgoing: " + ','.join([str(client) for client in self.clients]))
		

		




