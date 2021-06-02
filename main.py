#from Users.averypozzobon.Documents.ACTUALPYCRYPTO.v2.frontend_tornado import start_frontend
from node.NodeMain import * 
from FrontEndTornado import *
import sys, signal
import threading
import time

node = P2PNetNode()

def process_commands(command_entry):
	global node
	command = command_entry.split(" ")[0]

	command_values = command_entry.split(" ")
	
	if command == "help":
		print("Available Commands:")
		print("connect: Connects to P2PNet")
		print("loadconfig <filename>: Loads connect configuration file")
		print("listpeers: List connected peers on network")
		print("readpool: Shows pool of unconfirmed transactions")
		print("clear: Clears window")
		print("mine: Attempts to mine block onto chain")
		print("sendtxn <address_to_send_to amount fee>: Sends transaction to an address for the specified amount and fees. Fees must be greater than minimum")
		print("recvtxn: Generates address to receive transactions from, double click address to copy")
		print("getbalance: Gets the wallet balance")
	
	elif command == "start":
		if command_values[1] == "server":
			if len(command_values) == 4:
				node.start_server(command_values[2],int(command_values[3]))
			else:
				node.start_server()
		elif command_values[1] == "client":
			if len(command_values) == 4:
				node.start_client(command_values[2],int(command_values[3]))
			else:
				node.start_client()

	elif command == "send":
		node.client_broadcast('Hello')
	
	elif command == "broadcast":
		node.server_broadcast('Hello')

	elif command == "listpeers":
		node.list_connections()
	
	elif command == "recvtxn":
		key = node.wallet.addkey()
		print("Address To Receive Txn:", key.hex())

	elif command == "download":
		node.controller.download_chain()

	elif command == "setwallet":
		node.wallet.setkeydir(command_values[1])

	elif command == "setchain":
		try:
			node.controller.set_directory(command_values[1])
		except:
			print("Unable to Update Directory")
	
	elif command == "readblk":
		print(node.controller.view_block_file(command_values[1]))

	elif command == "getbalance":
		if len(command_values) > 1:
			print(node.wallet.getBalanceForKey(command_values[1]))
		else:
			print(node.wallet.getBalance())

	elif command == "mine":

		threading.Thread(target=node.controller.start_mining).start()
	
	elif command == "loopmine":
		node.controller.loop = True
		threading.Thread(target=node.controller.start_mining).start()

	elif command == "stopmine":
		node.controller.loop = False

	elif command == "mempool":
		print(node.controller.txn_pool)

	elif command == "sendtxn": #SEND TRANSACTION

		#try:

		if node == None:

			print("Must Connect First")

			return

		address = command_values[1] #ASK USER FOR ADDRESS TO SEND FUNDS

		amount = float(command_values[2])

		fees = 0

		reward = int(20 * (1/max(int(2*(time.time() - 1577836800)/315360000),1)))

		minimum_fees = float("{:.2f}".format(-((reward - 25)/(reward+10))))

		if (len(command_values) > 3):
			fees = float(command_values[3])
			if fees < minimum_fees:
				print("Fees Will Be Set To Mininum Fees:{0}".format(minimum_fees))
				fees = minimum_fees
		else:
			print("Fees Will Be Set To Mininum Fees:{0}".format(minimum_fees))
			fees = minimum_fees

		node.wallet.sendTransaction(amount, [{"address":address,"value":amount}],fees) #SEND THE TRANSACTION
	
	elif command == "frontend":
		print("Starting Web Server")
		start_frontend(node.server.address,node.server.port,8000)
		#threading.Thread(target=start_frontend,args=(node.server.address,node.server.port,8000)).start()
		
		#except:
		#	print("Unable to Send")


def signal_handler(signal, frame):
		global node
		print("\nprogram exiting gracefully")
		node.stop_server()
		sys.exit(0)    

if __name__ == "__main__":

	signal.signal(signal.SIGINT, signal_handler)
	command = input("Enter Command: ")
	while True:
		process_commands(command)
		command = input("Enter Command: ")