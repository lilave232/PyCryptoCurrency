import tornado.httpserver
import tornado.websocket
import tornado.ioloop
import tornado.web
import socket
import asyncio
from node.NodeMain import P2PNetNode
from node.parse_messages import *
import json
import os
import time


class FrontEnd(object):

	def __init__(self,websocket,loop,wallet,connect_address='localhost',connect_port=4444):
		self.node = P2PNetNode(client_parser=self.parse_p2p_message,key_dir=wallet)
		self.client = self.node.start_client(connect_address,connect_port)
		self.websocket = websocket
		self.loop = loop
		

	def parse_p2p_message(self,client,msg):
		msg_object = convert_to_obj(msg)
		if msg_object == False:
			print(msg)
			return
		#JOINED ADD TRANSACTIONS
		if 'type' in msg_object and msg_object['type'] == 0:
			self.node.controller.txn_pool.extend([txn for txn in msg_object['txn_pool'] if txn not in self.node.controller.txn_pool])
			self.node.controller.wallet.updateWallet()
			msg = {"type":0,"uncbalance":self.getBalance(type=1),"usbalance":self.getBalance(),"conbalance":self.getBalance(type=2)}
			print("Connection Established")
			self.loop.add_callback(self.websocket.write_message,(json.dumps(msg)))
			#asyncio.run_coroutine_threadsafe(self.websocket.write_message(json.dumps(msg)),self.loop)
			
		#BLOCK ADDED
		if 'type' in msg_object and msg_object['type'] == 9:
			if self.node.server == None or self.node.server.connected == False:
				self.node.lock.acquire()
				if msg_object['hash'] not in self.node.controller.hashes:
					for txn in msg_object['block']['txns']:
						if txn in self.node.controller.txn_pool:
							self.node.controller.txn_pool.remove(txn)
				self.node.wallet.updateWallet()
				msg = {"type":0,"uncbalance":self.getBalance(type=1),"usbalance":self.getBalance(),"conbalance":self.getBalance(type=2)}
				print("Block Added")
				self.loop.add_callback(self.websocket.write_message,(json.dumps(msg)))
				#asyncio.run_coroutine_threadsafe(self.websocket.write_message(json.dumps(msg)),self.loop)
				#asyncio.run_coroutine_threadsafe(self.websocket.send(json.dumps(msg)),self.loop)
				self.node.lock.release()
		#TXN ADDED TO POOL
		if 'type' in msg_object and msg_object['type'] == 10:
			print("Adding to Pool")
			if self.node.server == None or self.node.server.connected == False:
				if msg_object['txn'] not in self.node.controller.txn_pool:
					self.node.controller.txn_pool.append(msg_object['txn'])
				self.node.wallet.updateWallet()
				msg = {"type":0,"uncbalance":self.getBalance(type=1),"usbalance":self.getBalance(),"conbalance":self.getBalance(type=2)}
				print("Transaction Added To Pool")
				self.loop.add_callback(self.websocket.write_message,(json.dumps(msg)))
					#asyncio.run_coroutine_threadsafe(self.websocket.write_message(json.dumps(msg)),self.loop)

	def close(self):
		if self.client != None:
			self.client.close()

	def getBalance(self,type=0):
		return(self.node.wallet.getBalance(type=type))

	def getKey(self):
		return self.node.wallet.addkey().hex()

	def sendTxn(self,address,amount,fees):

		reward = int(20 * (1/max(int(2*(time.time() - 1577836800)/315360000),1)))

		minimum_fees = float("{:.2f}".format(-((reward - 25)/(reward+10))))

		if fees < minimum_fees:
			print("Fees Will Be Set To Mininum Fees:{0}".format(minimum_fees))
			fees = minimum_fees
		
		self.node.wallet.sendTransaction(amount, [{"address":address,"value":amount}],fees)


class WSHandler(tornado.websocket.WebSocketHandler):

	global server_address
	global server_port

	def parse_front_end_message(self,msg):
		msg_object = convert_to_obj(msg)
		if msg_object == False:
			print(msg)
			return
		if 'type' in msg_object and msg_object['type'] == 0:
			print(tornado.ioloop.IOLoop.current())
			self.frontend = FrontEnd(self,tornado.ioloop.IOLoop.current(),msg_object['uname'],server_address,server_port)
		if 'type' in msg_object and msg_object['type'] == 1:
			msg = {"type":1,"key":self.frontend.getKey()}
			self.write_message(json.dumps(msg))
		#await websocket.send(json.dumps(msg))
		if 'type' in msg_object and msg_object['type'] == 2:
			self.frontend.sendTxn(msg_object['address'],msg_object['amount'],msg_object['fee'])


	def open(self):
		self.frontend = None
		print('new connection')
	  
	def on_message(self, message):
		#print('message received:  %s' % message)
		self.parse_front_end_message(message)
		#self.write_message(self,message)
 
	def on_close(self):
		if self.frontend != None:
			self.frontend.client.close()
			self.frontend = None
		print('connection closed')
 
	def check_origin(self, origin):
		return True
 
application = tornado.web.Application([
	(r'/', WSHandler),
])
 
 
if __name__ == "__main__":

	server_address = input("Connect Address:")
	server_port = int(input("Connect Port:"))

	http_server = tornado.httpserver.HTTPServer(application)
	http_server.listen(8888)
	myIP = socket.gethostbyname(socket.gethostname())
	print('*** Websocket Server Started at %s***' % myIP)
	tornado.ioloop.IOLoop.instance().start()