import os
import json
import pickle
import time
import random
import threading
import uuid

from ecdsa.ecdsa import Private_key, Signature
from crypto.cryptography import *
from chain.Wallet import *

class ChainController(object):

	## Initialization Functions ##
	##                          ##
	##############################
	def __init__(self,node,directory):
		## INIT VARIABLES
		self.node = None
		self.directory = None
		self.index_directory = None
		self.wallet = None
		self.chain_downloaded = False
		self.chain_verified = False
		##
		## DOWNLOAD CHAIN VARIABLES
		self.chain_size_confirmations = {}
		self.hash_verifications = {}
		self.download_hash_verifications = {}
		self.confirmed_size = 0
		##
		## INDEX VARIABLES
		self.chain_size = 0
		self.hashes = []
		self.hash_to_file = {}
		##
		## MINING VARIABLES
		self.block_confirmations = {}
		self.mining = False
		self.block_target = None
		self.block_mined = False
		self.target_receipts = {}
		self.target_confirmations = {}
		self.target_confirmed = False
		self.txn_pool = []
		self.confirmed_txns = []
		self.txn_confirmations = {}
		self.loop = False
		##
		self.node = node
		self.set_directory(directory)
		self.index_chain()

	def set_wallet(self, wallet):
		self.wallet = wallet

	def set_directory(self, directory):
		self.chain_downloaded = False
		self.chain_verified = False
		self.directory = directory
		self.index_directory = directory + "_indices"
		if os.path.isdir(directory) == False:
			path = os.getcwd()
			os.mkdir(os.path.join(path,directory))
		if os.path.isdir(self.index_directory) == False:
			path = os.getcwd()
			os.mkdir(os.path.join(path,self.index_directory))
		self.index_chain()

	#################################################################

	## Indexing Functions   ##
	##                      ##
	##########################
	def index_chain(self):
		block_files = [os.path.join(self.directory,name) for name in os.listdir(self.directory) if os.path.splitext(name)[1] == '.blk']
		block_files.sort(key=self.blk_sort_key)
		chain_hashes = []
		self.indexAllUTXOS()
		for fname in block_files:
			block = json.load(open(fname, "rb" ))
			block_hash = self.hash_block_dict(block).hex()
			chain_hashes.append(block_hash)
			self.hash_to_file[block_hash] = fname
		
			if block_hash not in self.hash_verifications:
				self.hash_verifications[block_hash] = [0,0]
		
		if self.wallet != None:
			self.wallet.updateWallet()

		self.hashes = chain_hashes
		
		pickle.dump(chain_hashes, open(self.index_directory + "/hashes.pkl", "wb" ) )
		pickle.dump(self.hash_to_file, open(self.index_directory + "/hash_to_file.pkl", "wb" ) )

	def indexAllUTXOS(self):
		block_files = [os.path.join(self.directory,name) for name in os.listdir(self.directory) if os.path.splitext(name)[1] == '.blk']
		block_files.sort(key=self.blk_sort_key)
		utxos = {}
		if os.path.isfile(self.index_directory + "/utxos"):
			utxos = pickle.load(open(self.index_directory + "/utxos",'rb'))		
		for fname in block_files:
			block = json.load(open(fname, "rb" ))
			for txn in block['txns']:
				for x, output in enumerate(txn['outputs']):
					utxos[txn['txnid']+str(x)] = {"TxID":txn['txnid'],"Value": output['value'], "Location":x, "Address":output['address']}
				for x, in_val in enumerate(txn['inputs']):
						if in_val['prev_txid'] + str(in_val['prev_txn_output']) in utxos:
								del utxos[in_val['prev_txid'] + str(in_val['prev_txn_output'])]
		pickle.dump(utxos,open(self.index_directory + "/utxos",'wb'))

	def blk_sort_key(self,file):
		return int(os.path.splitext(os.path.split(file)[1])[0])

	def get_chain_size(self):
		self.chain_size = len([name for name in os.listdir(self.directory) if os.path.splitext(name)[1] == '.blk'])
		return self.chain_size
	
	#################################################################

	##################################################################################################
	## MINE BLOCK                                             										##
	## Step 1: Download/Verify Complete Chain														##
	## Step 2: Get Target From Network                          									##
	## Step 3: Request Target																		##
	## Step 4: Receive Target if >50% of nodes returned False Set Target Based on Number of Clients	##
	## Step 5: Ask for confirmation of set target													##
	## Step 6: Receive confirmation of target when >50% of nodes confirm target set					##
	## Step 7: Start mining by looping over blocks until hash below target obtained					##
	## Step 8: When block obtained broadcast to network for confirmation							##
	## Step 9: When >50% of nodes confirm block, block is added to chain							##
	##################################################################################################
	def start_mining(self):
		self.node.lock.acquire()
		if self.node.server == None or self.node.server.connected == False:
			print("Cannot Mine Must Connect to Server")
			return

		if len(self.node.clients) < 1:
			print("Unable to mine not enough connections")
			return

		#threading.Thread(target=self.download_chain).start()
		if self.chain_downloaded == False:
			return
		#while self.chain_downloaded == False:
		#	continue

		if self.chain_downloaded and self.node.server != None and self.node.server.connected and len(self.node.clients) > 0 and self.mining == False:
			self.mining = True
			self.node.lock.release()
			t = time.localtime()
			current_time = time.strftime("%H:%M:%S", t)
			print("Started Mining:",current_time)
			self.block_confirmations = {}
			self.block_target = None
			self.block_mined = False
			self.target_receipts = {}
			self.target_confirmations = {}
			self.target_confirmed = False
			self.confirmed_txns = []

			self.get_target()

			block, block_hash, block_sig, priv_key = self.gen_block()
			if block == False:
				print("Unable to Mine")
				return

			message = {'type':8,'block':block,'pubkey':priv_key.verifying_key.to_string().hex(),'signature':block_sig}

			self.node.client_broadcast(json.dumps(message))
		else:
			self.node.lock.release()

	def gen_coinbase_txn(self,hash):
		reward = int(20 * (1/max(int(2*(time.time() - 1577836800)/315360000),1))) #REWARD CALCULATION VALUE OF REWARD SHOULD HALVE EVERY 10 YEARS
		txid = uuid.uuid4().hex #GENERATE TX ID FOR COINBASE TXN
		#GENERATE TXN MOST IF BASIC EXCEPT OUTPUT IS WRITTEN TO MINERS HASH
		txn = {"txnid":txid,"time":int(time.time()),"inputs":[{"prev_txid":bytearray(16).hex(),"prev_txn_output":0,"sig_prev_out":bytearray(64).hex()}],"outputs":[{"address":hash.hex(),"value":reward}]}
		return txn

	def confirm_txns(self,txns=None,gen=True):
		block_in_value = 0
		block_out_value = 0
		txn_vals = []
		if txns == None:
			txn_vals = self.txn_pool
		else:
			txn_vals = txns

		for x,txn in enumerate(txn_vals):

			if txn in self.confirmed_txns and gen:
				continue

			for x, input_val in enumerate(txn['inputs']):

				prev_txn = self.get_txn(input_val['prev_txid']) #GET PREVIOUS TXN

				if prev_txn == False: #IF THEIR IS NO PREVIOUS TXN ERROR REACHED

					return 0
				
				block_in_value += prev_txn['outputs'][input_val['prev_txn_output']]['value']

			for x, output_val in enumerate(txn['outputs']): #FOR OUTPUT IN TRANSACTION

				block_out_value += output_val['value'] #INCREMENT TOTAL OUTPUT VALUE

			if gen:
				self.confirmed_txns.append(txn)

		if block_in_value - block_out_value > 0:
			print("Inputs:", block_in_value, "Outputs:", block_out_value)

		return float("{:.8f}".format(block_in_value - block_out_value))


	def gen_block(self):
		try:
			print("Building Block")
			hash, priv_key = self.wallet.addKeyPriv()
			prev_block_hash = bytearray(32).hex()
			if (len(self.hashes) > 0):
				prev_block_hash = self.hashes[-1]
			
			time_val = int(time.time())
			nonce = random.randint(0,4294967295)
			nonce = nonce.to_bytes(4, byteorder = 'big').hex()
			coinbase_txn = self.gen_coinbase_txn(hash)

			txns = []

			txns.append(coinbase_txn)

			txns.extend(self.txn_pool)

			block = {"prev_block_hash":prev_block_hash,"time":time_val,"target":self.block_target,"nonce":nonce,"txns":txns}

			reward = self.confirm_txns() 
			
			block['txns'][0]['outputs'][0]['value'] += reward 

			block_hash = self.hash_block_dict(block)

			print("Mining")

			while block_hash > (bytes.fromhex(block['target']) + bytearray(28)):
				
				if self.block_mined:
					return False, False, False, False
				
				block['target'] = self.block_target

				prev_reward = block['txns'][0]['outputs'][0]['value']

				block['txns'] = [] #CREATE TXN ARRAY

				coinbase_txn = self.gen_coinbase_txn(hash)

				block['txns'].append(coinbase_txn) #APPEND COINBASE TXN

				add_reward = self.confirm_txns()

				block['txns'][0]['outputs'][0]['value'] = prev_reward + add_reward

				block['txns'].extend(self.confirmed_txns)
				
				nonce = random.randint(0,4294967295)

				nonce = nonce.to_bytes(4, byteorder = 'big').hex()

				block['nonce'] = nonce #SET NONCE VALUE

				block['time'] = int(time.time()) #SET TIME TO REFLECT MORE RECENT MINE TIME

				block_hash = self.hash_block_dict(block) #HASH BLOCK
			
			print("Block Obtained")

			print("Reward Generated:",block['txns'][0]['outputs'][0]['value'])

			block_sig = sign_msg(block_hash,priv_key)

			return block, block_hash, block_sig, priv_key
		except:
			return False, False, False, False

	def confirm_block(self,block,pubkey,signature):
		self.node.lock.acquire()
		try:
			print("Confirming Block")
			block_hash = self.hash_block_dict(block)

			pubKey = pub_key_from_string(pubkey)

			verify_msg(bytes.fromhex(signature),block_hash,pubKey)
			print("VERIFIED")

			previous_hash = bytearray(32).hex()

			if (len(self.hashes) > 0): #IF LENGTH PREVIOUS HASHES ARRAY GREATER THAN 0
				previous_hash = self.hashes[-1]

			assert (block['prev_block_hash'] == previous_hash) #ENSURE PREVIOUS HASH IS SAME AS PREVIOUS HASH ON BLOCK
			print("VERIFIED PREVIOUS HASH")
			#CHECK TIME
			assert (block['time'] <= int(time.time() + 20*60) and block['time'] >= int(time.time()) - 3600) #ENSURE TIME IS CORRECT BLOCKS WITH TIME GREATER THAN CURRENT TIME OR BLOCKS NOT CONFIRMED AFTER AN HOUR WILL NOT BE CONFIRMED
			print("VERIFIED TIME")
			#VERIFY TRANSACTIONS
			assert (len(block['txns'][0]['inputs']) == 1 and len(block['txns'][0]['outputs']) == 1) #VERIFY COINBASE TRANSACTION HAS ONE INPUT AND ONE OUTPUT
			print("VERIFIED COINBASE")
			#CHECK INPUTS FORMAT TO CONFIRM COINBASE TRANSACTION FORMATTED PROPERLY
			assert (block['txns'][0]['inputs'][0]['prev_txid'] == bytearray(16).hex() and block['txns'][0]['inputs'][0]['prev_txn_output'] == 0 and block['txns'][0]['inputs'][0]['sig_prev_out'] == bytearray(64).hex())
			print("VERIFIED INPUTS")
			#CHECK OUTPUTS TO ENSURE THAT ADDRESS PROVIDED IN COINBASE TRANSACTION IS CORRECT
			assert (block['txns'][0]['outputs'][0]['address'] == hash_v_key(pubKey).hex())
			print("VERIFIED ADDRESS")
			#CHECK VALUE OF COINBASE TRANSACTION EQUAL TO THE CORRECT REWARD VALUE
			reward = int(20 * (1/max(int(2*(time.time() - 1577836800)/315360000),1)))
			if len(block['txns']) > 1:
				reward += self.confirm_txns(txns=block['txns'][1:],gen=False)
			print("Reward Recalculated:", reward)

			assert (block['txns'][0]['outputs'][0]['value'] == reward)
			print("VERIFIED TXNS")

			assert (len(bytes.fromhex(block['txns'][0]['txnid'])) == 16)
			print("VERIFIED TXN ID")

			assert (block_hash < (bytes.fromhex(self.block_target) + bytearray(28)))
			self.node.lock.release()
			print("VERIFIED HASH")
			message = {'type':8,'hash':block_hash.hex(),'block':block}
			self.recv_block_confirm(block_hash.hex(),block)
			self.node.server_broadcast(json.dumps(message))

		except:
			print("COULD NOT CONFIRM")
			message = {'type':8,'hash':False,'block':False}
			self.node.server_broadcast(json.dumps(message))
			self.node.lock.release()
			self.recv_block_confirm(False,False,True)
			return

	def recv_block_confirm(self,hash,block,selfconfirm=False):
		if hash in self.hashes:
			return
		self.node.lock.acquire()
		if hash not in self.block_confirmations:
			self.block_confirmations[hash] = 0
		self.block_confirmations[hash] += 1
		print("Block Confirm Received:",hash,max(self.block_confirmations.values()), "of", (len(self.node.clients)/2))
		if max(self.block_confirmations.values()) > (len(self.node.clients)/2):
			if hash == False:
				print("Failed to Confirm Block")
				self.block_confirmations[hash] = 0
				self.node.lock.release()
				if self.loop:
					if selfconfirm:
						if self.mining:
							print("Continue Mining")
						return
					self.mining = False
					threading.Thread(target=self.start_mining).start()
				return
			print("New Block Confirmed")
			hash = max(self.block_confirmations, key=self.block_confirmations.get)
			self.add_block_end(block)
			message = {'type':9,'block':block,'hash':hash}
			self.node.server_broadcast(json.dumps(message))
			self.block_confirmations = {}
			self.mining = False
			self.block_target = None
			self.block_mined = True
			self.target_receipts = {}
			self.target_confirmations = {}
			self.target_confirmed = False
			for txn in block['txns']:
				if txn in self.txn_pool:
					self.txn_pool.remove(txn)
				if txn in self.confirmed_txns:
					self.confirmed_txns.remove(txn)
			if self.loop:
				self.node.lock.release()
				threading.Thread(target=self.start_mining).start()
				return

		self.node.lock.release()

			

	def get_target(self):
		message = {'type':5}
		self.node.client_broadcast(json.dumps(message))

		print("Waiting For Target")
		while self.block_target == None or self.block_target == False:
			continue
		print("Target Set:",self.block_target)
		self.confirm_target()

	def recv_target(self,target):
		if self.block_target != None:
			return
		self.node.lock.acquire()
		if target not in self.target_receipts:
			self.target_receipts[target] = 0
		self.target_receipts[target] += 1

		if max(self.target_receipts.values()) > (len(self.node.clients)/2):
			print("Target Acquired")
			self.block_target = max(self.target_receipts, key=self.target_receipts.get)
		
			if self.block_target == False:
				print("Setting Target")
				self.set_target()
		
		
		self.node.lock.release()

	def set_target(self):
		lower_bound = 500
		upper_bound = 1000
		if len(self.node.clients) < 2:
			lower_bound = 2000
			upper_bound = 4000
		elif len(self.node.clients) < 10:
			lower_bound = 1000
			upper_bound = 2000
		elif len(self.node.clients) >= 10:
			lower_bound = 500
			upper_bound = 1000
			
		self.block_target = random.randint(lower_bound,upper_bound).to_bytes(4, byteorder='big').hex()

		message = {'type':6,'target':self.block_target}
		self.node.client_broadcast(json.dumps(message))

	def confirm_target(self):
		self.node.lock.acquire()
		if self.block_target == None:
			return
		
		message = {'type':7,'target':self.block_target}
		self.node.client_broadcast(json.dumps(message))

		print("Confirming Target")
		while self.target_confirmed == False:
			continue
		print("Target Confirmed")
		self.node.lock.release()

	def recv_target_confirm(self,target):
		if self.target_confirmed == True or self.block_target == None:
			return
		
		if self.block_target not in self.target_confirmations:
			self.target_confirmations[self.block_target] = [0,0]

		if target == self.block_target:
			self.target_confirmations[self.block_target][0] += 1
		else:
			self.target_confirmations[self.block_target][1] += 1

		if self.target_confirmations[self.block_target][0] > (len(self.node.clients)/2):
			self.target_confirmed = True
			self.target_confirmations = {}
			self.node.lock.release()
			return
		
		if self.target_confirmations[self.block_target][1] > (len(self.node.clients)/2):
			self.block_target = None
			self.target_confirmed = False
			self.target_confirmations = {}
			print("Target Not Confirmed! Stopping Mine")
			#self.get_target()
		return

	##############################################################

	## DOWNLOAD BLOCK                                           ##
	## Step 1: Get and Confirm Hash of Block to Download        ##
	## Step 2: Wait for >50% of Peers to Confirm Hash           ##
	## Step 3: Request Download of Block with Confirmed Hash    ##
	## Step 4: Receive Downloaded Block                         ##
	##############################################################
	def get_download_hash(self,block):
		print("Downloading Block:", block)
		message = {"type":3,"block":block}
		self.node.client_broadcast(json.dumps(message))
	
	def verify_hash_to_download(self,block,hash):
		self.node.lock.acquire()
		if hash not in self.download_hash_verifications:
			self.download_hash_verifications[hash] = 0
		self.download_hash_verifications[hash] += 1

		if max(self.download_hash_verifications.values()) > (len(self.node.clients)/2) and hash != False:
			print("Hash Confirmed Request Download")
			hash = max(self.download_hash_verifications, key=self.download_hash_verifications.get)
			self.request_download(hash)

		self.node.lock.release()

	def request_download(self,hash):
		message = {"type":4,"hash":hash}
		self.node.client_broadcast(json.dumps(message))

	def download_block(self,fname,block,hash):
		self.node.lock.acquire()
		if hash in self.hashes:
			self.node.lock.release()
			return
		if hash == max(self.download_hash_verifications, key=self.download_hash_verifications.get):
			if self.add_block(fname,block):
				self.download_hash_verifications = {}
				block_num = self.hashes.index(hash)
				chain_size = self.get_chain_size()
				print("Block {0} Downloaded".format(block_num))
				if self.confirmed_size == chain_size and self.chain_verified:
					print("Chain Downloaded")
					self.chain_downloaded = True
				else:
					if hash in self.hash_verifications:
						self.hash_verifications[hash] = [0,0]
					message = {"type":2,"block":block_num,"hash":hash}
					self.node.client_broadcast(json.dumps(message))
		self.node.lock.release()
	##########################################################################

	##########################################################################	
	## DOWNLOAD CHAIN                                                       ##
	## Step 1: Request Chain Size                                           ##
	## Step 2: Receive Chain Size Confirmations From Servers                ##
	## Step 3: Wait until 50% of Peers + 1 Confirm Size                     ##
	## Step 4: Verify Current Chain Hashes                                  ##
	## Step 5: Wait until 50% of Peers + 1 Confirm Hashes                   ##
	## Step 6: If Bad Hash Remove and Download Correct (See Above)          ##
	## Step 7: Request Additional Blocks until Chain Matches Confirmed Size ##
	## Step 8: Wait until 50% of Peers + 1 Confirm Additional blocks hash   ##
	## Step 9: Once Confirmation Received Add Block to Chain                ##
	## Step 10: Repeat until all blocks are added                           ##
	##########################################################################

	#Step 1: Start Process by Resetting Variables and Requesting Size Confirmations
	def download_chain(self):
		#self.confirm_chain_hashes()
		self.chain_size_confirmations = {}
		self.hash_verifications = {}
		self.download_hash_verifications = {}
		self.chain_verified = False
		self.chain_downloaded = False
		message = {'type':1}
		self.node.client_broadcast(json.dumps(message))
	
	#Step 2: Receive Chain Size Confirmations
	def confirm_chain_size(self,client,size):
		self.node.lock.acquire()
		if size not in self.chain_size_confirmations:
			self.chain_size_confirmations[size] = []
		if client not in self.chain_size_confirmations[size]:
			self.chain_size_confirmations[size].append(client)
		
		confirmations = [len(self.chain_size_confirmations[key]) for key in self.chain_size_confirmations.keys()]
		#Step 3 Check if >50% of Peers confirm size
		if max(confirmations) > (len(self.node.clients)/2):
			sizes = list(self.chain_size_confirmations.keys())
			size = sizes[confirmations.index(max(confirmations))]
			self.confirmed_size = size
			print("Confirmed Size:", size)
			self.remove_extra_blocks()
			if size == self.get_chain_size():
				print("No Download Necessary")
			else:
				print("Download Required")
			
			self.start_verify_chain()

		self.node.lock.release()
	
	#Step 4: Verify Current Chain Hashes
	def start_verify_chain(self):
		print("Starting Chain Verification")
		self.node.controller.index_chain()
		if len(self.hashes) > 0:
			message = {"type":2,"block":0,"hash":self.hashes[0]}
			self.node.client_broadcast(json.dumps(message))
		else:
			self.chain_verified = True
			self.get_download_hash(0)

	#Step 5: Wait until >50% of Peers Confirm Hashes
	def recv_verification(self,block,hash,result):
		self.node.lock.acquire()
		if self.hash_verifications[hash][0] > (len(self.node.clients)/2):
			self.node.lock.release()
			return
		if result:
			self.hash_verifications[hash][0] += 1
		else:
			self.hash_verifications[hash][1] += 1

		if self.hash_verifications[hash][0] > (len(self.node.clients)/2):
			print("Block {0}: Verified".format(block))
			if block == len(self.hashes) - 1 and self.chain_verified == False:
				print("Local Verification Completed")
				self.chain_verified = True
			elif self.chain_verified == False:
				message = {"type":2,"block":block+1,"hash":self.hashes[block+1]}
				self.node.client_broadcast(json.dumps(message))
			
			if block == self.confirmed_size - 1 and self.chain_verified:
				print("Verified Chain")
				self.chain_downloaded = True
			elif block < self.confirmed_size - 1 and self.chain_verified:
				self.get_download_hash(block+1)

		#Step 6: Servers returned different hash Bad Hash Exists Remove Current Block and Download New Block
		if self.hash_verifications[hash][1] > (len(self.node.clients)/2):
			print("Block {0}: Not Verified".format(block))
			deleted = self.remove_block(block)
			self.hash_verifications[hash] = [0,0]
			self.get_download_hash(block)
		
		self.node.lock.release()

	##########################################################################

	##################################################################################################################################################
	## Getting, Adding and Confirming Transactions  	 																							##
	## Adding																																		##
	## Step 1: Wallet takes input from client to generate unused transaction outputs (utxos) from chain to send										##
	## Step 2: Wallet calculates which utxos to are greater than or equal to the transaction value													##
	## Step 3: Waller passes utxos (inputs), output addresses, value and fee																		##
	## Step 4: gen_txn function generates transaction and signs inputs for later verification by nodes												##
	## Step 5: Wallet passes transaction generated and public keys for inputs to send_txn that broadcasts request to add txn to pool				##
	## Step 6: Using public key and determining whether utxos are actually available for use nodes confirm owndership and availability of amounts	##
	## Step 7: Nodes send confirmation across network and when >50% confirm, transaction is added to pool											##
	## Step 8: Miners add transaction to their potential blocks and once mined amounts are confirmed and added to the chain							##
	## Getting																																		##
	## Node loops through chain files and return transactions by id																					##
	## Confirming																																	##
	## Step 1: Check ID is 16 bytes																													##
	## Step 2: Ensure transaction is not from future or an hour old (transactions expire after an hour if not mined)								##
	## Step 3: Check transaction includes at least one input																						##
	## Step 4: For each input ensure it comes from previous transaction, and public key hash and signature match									##
	## Step 5: Confirm transaction is not in transaction pool																						##
	## Step 6: Confirm input is a utxo																												##
	## Step 7: Ensure at least one output																											##
	## Step 8: Ensure fees are consistent with minimum fee (fee works inverse to reward as rewards lower minimum fee raises)						##
	## Step 9: Confirm outputs ensure address is equal to 32 bytes																					##
	## Step 10: Confirm total transaction outputs + minimum fee <= inputs confirming transaction has required number of inputs						##
	## Step 11: Add confirmation locally and broadcast confirmation over network																	##
	##################################################################################################################################################


	def get_txn(self,txnid):
		block_files = [os.path.join(self.directory,name) for name in os.listdir(self.directory) if os.path.splitext(name)[1] == '.blk']
		block_files.sort(key=self.blk_sort_key)
		for fname in block_files:
			b = json.load(open(fname, "rb" ))

			for txn in b['txns']: #FOR TXN IN TXNS

				if txn['txnid'] == txnid: # LOOK FOR TXNID

					return txn #RETURN TRANSACTION

		return False #IF TRANSACTION COULD NOT BE FOUND RETURN FALSE

	def confirmUtxo(self, input):
		block_files = [os.path.join(self.directory,name) for name in os.listdir(self.directory) if os.path.splitext(name)[1] == '.blk']
		block_files.sort(key=self.blk_sort_key)
		for fname in block_files:
			block = json.load(open(fname, "rb" ))
			for txn in block['txns']:
				if input in txn['inputs']:
					return False
		return True

	def gen_txn(self, output_addresses, input_addresses, total_value, fees):

		txid = uuid.uuid4().hex

		inputs = []

		in_value = 0

		for value in input_addresses:

			signature = sign_msg(bytes.fromhex(value['Address']),priv_key_from_string(value['PrivKey'])) 

			input_value = {"prev_txid":value['TxID'],"prev_txn_output":value['Output'],"sign_prev_out":signature} 

			inputs.append(input_value)

			in_value += float("{:.8f}".format(value['Value']))

			print("Inputs", {"PrevTXID":value['TxID'],"Address:":value['Address'],"Value":float("{:.8f}".format(value['Value']))})
		
		out_value = 0

		for value in output_addresses: #FOR VALUE IN OUT VALUE

			out_value += float("{:.8f}".format(value['value'])) #ADD VALUE TO OUT VALUE

			print("Outputs", {"Address:":value['address'],"Value":float("{:.8f}".format(value['value']))})
		
		if in_value > out_value: #DETERMINE IF IN VALUE GREATER THAN OUT VALUE AND RETURN CHANGE TO FIRST INPUT ADDRESS PROVIDED

			output_addresses.append({"address":input_addresses[0]['Address'],"value":float("{:.8f}".format((in_value-out_value-fees)))}) #GENERATE OUTPUTS

			print({"address":input_addresses[0]['Address'],"value":float("{:.8f}".format((in_value-out_value-fees)))})

			print("Fees: ", fees)

		txn = {"txnid":txid,"time":int(time.time()),"inputs":inputs,"outputs":output_addresses} #BUILD TRANSACTION
		
		return txn #RETURN TXN

	def send_txn(self,txn,pubkeys):

		message = {"type":9,"txn":txn,"pubkeys":pubkeys}

		self.node.client_broadcast(json.dumps(message))

	def confirm_txn(self,txn,pubkeys):

		if txn['txnid'] not in self.txn_confirmations and txn not in self.txn_pool:

			self.txn_confirmations[txn['txnid']] = [0,0]
		
		print("Confirming Transaction")

		try:
			total_in_value = 0 #SET UP TOTAL IN VARIABLE
			#CHECK ID FORMAT
			assert (len(bytes.fromhex(txn['txnid'])) == 16) #ENSURE TXID IS 16 BYTE INTEGER
			#CHECK TIME
			assert (txn['time'] <= int(time.time() + 20*60) and txn['time'] >= int(time.time()) - 3600) #ENSURE TXN IS NOT FROM FUTURE AND NOT FROM AN HOUR IN THE PAST
			#CHECK INPUTS
			assert (len(txn['inputs']) > 0) #AT LEAST ONE INPUT IN TRANSACTION

			print("CONFIRMED GENERAL")

			for x, input_val in enumerate(txn['inputs']): #FOR EACH INPUT

				prev_txn = self.get_txn(input_val['prev_txid']) #GET PREVIOUS TXN

				print("Confirmed Previous Transaction ID")

				if prev_txn == False: #IF THEIR IS NO PREVIOUS TXN ERROR REACHED

					assert(False)

				address = prev_txn['outputs'][input_val['prev_txn_output']]['address'] #GET ADDRESS OF PREVIOUS TXN

				total_in_value += prev_txn['outputs'][input_val['prev_txn_output']]['value'] #GET INPUT VALUE OF TXN

				pubKeyHash = hash_v_key(pub_key_from_string(pubkeys[x])).hex() #HASH TRANSACTION SENDERS PUBLIC KEY
				#VERIFY OWNERSHIP
				#VERIFY PUBKEY PROVIDED = ADDRESS OF INPUT
				assert(address == pubKeyHash) #VERIFY THAT USER SENDING COIN HAS THE PUBLIC KEY CORRESPONDING TO ADDRESS
				print("Confirmed Address and Hash")
				#VERIFY USER OWNS INPUTS BY CHECKING PRIVATE KEY GENERATED SIGNATURE MATCHES PUBKEYHASH THIS VERIFIES OWNERSHIP OF PUBLICKEY AND THEREFORE OWNERSHIP OF COIN BEING SENT
				verify_msg(bytes.fromhex(input_val['sign_prev_out']),bytes.fromhex(address),pub_key_from_string(pubkeys[x]))
				print("Verified Keys")
				for pool_txn in self.txn_pool:
					assert(not any(input_val['prev_txid'] + str(input_val['prev_txn_output']) == d['prev_txid'] + str(d['prev_txn_output']) for d in pool_txn['inputs']))
				print("Confirmed Transaction Pool")
				
				assert(self.confirmUtxo(input_val))
				print("Confirmed UTXOs")

			#CHECK OUTPUTS
			assert (len(txn['outputs']) > 0) #ENSURE AT LEAST ONE OUTPUT

			reward = int(20 * (1/max(int(2*(time.time() - 1577836800)/315360000),1)))

			minimum_fees = float("{:.2f}".format(-((reward - 25)/(reward+10))))

			total_out_value = 0 #SETUP OUTPUT VALUE COUNTER

			for x, output_val in enumerate(txn['outputs']): #FOR OUTPUT IN TRANSACTION

				assert(len(bytes.fromhex(output_val['address'])) == 32) #ENSURE ADDRESS IS EQUAL TO 32 BYTES

				total_out_value += output_val['value'] #INCREMENT TOTAL OUTPUT VALUE

				assert((total_out_value+minimum_fees) <= (total_in_value))

			self.recv_txn_confirm(txn['txnid'],txn)

			print("Transaction Confirmed")

			message = {'type':10,'txnid':txn['txnid'],'txn':txn}

			self.node.client_broadcast(json.dumps(message))

		except:
			message = {'type':10,'txnid':txn['txnid'],'txn':False}
			self.node.client_broadcast(json.dumps(message))
			self.recv_txn_confirm(txn['txnid'],False)
			print("Unable to Confirm Transaction")

	def recv_txn_confirm(self,txnid,txn):
		self.node.lock.acquire()
		print("Transaction Confirmation Received")
		if txn in self.txn_pool:
			self.node.lock.release()
			return
		
		if txnid not in self.txn_confirmations:
			self.txn_confirmations[txnid] = [0,0]
		if txn != False:
			self.txn_confirmations[txnid][0] += 1
		else:
			self.txn_confirmations[txnid][1] += 1

		print(self.txn_confirmations[txnid])

		if self.txn_confirmations[txnid][0] > (len(self.node.clients)/2):
			print("Adding to Mem Pool")
			self.txn_pool.append(txn)
			message = {'type':10,'txn':txn}
			self.node.server_broadcast(json.dumps(message))
			self.wallet.updateWallet()
			del self.txn_confirmations[txnid]
			self.node.lock.release()

			return
		
		if self.txn_confirmations[txnid][1] > (len(self.node.clients)/2):
			del self.txn_confirmations[txnid]
			print("Transaction Rejected")

		self.node.lock.release()
		return




	############################################

	
	
	## BLOCK FUNCTIONS(ADD,REMOVE,GET,HASH)  ##
	##                                       ##
	###########################################
	def add_block(self,fname, block):
		try:
			json.dump(block, open(os.path.join(self.directory,fname), 'w'))
			self.index_chain()
			return True
		except:
			return False

	def add_block_end(self,block):
		try:
			json.dump(block, open(os.path.join(self.directory,"{0}.blk".format(len(self.hashes))), 'w'))
			self.index_chain()
			return True
		except:
			return False


	def remove_block_f(self,file):
		try:
			os.remove(file)
			return True
		except:
			return False


	def remove_block(self,i):
		try:
			os.remove(os.path.join(self.directory,"{0}.blk".format(i)))
			return True
		except:
			return False

	def get_block(self,blk):
		blk = json.load(open(os.path.join(self.directory,"{0}.blk".format(blk)) , "r" ))
		return blk

	def get_block_hash(self,hash):
		if hash in self.hash_to_file:
			file = self.hash_to_file[hash]
			blk = json.load(open(file, "r" ))
			return blk
		else:
			return False

	def get_block_file(self,hash):
		if hash in self.hash_to_file:
			file = self.hash_to_file[hash]
			return file
		else:
			return False

	def remove_extra_blocks(self):
		block_files = [os.path.join(self.directory,name) for name in os.listdir(self.directory) if os.path.splitext(name)[1] == '.blk']
		block_files.sort(key=self.blk_sort_key)
		try:
			while self.blk_sort_key(block_files[-1]) > self.confirmed_size - 1:
				self.remove_block_f(block_files[-1])
				block_files = block_files[:-1]
		except:
			pass
	
	def hash_block_dict(self,block): #HASH BLOCK

		return hash_block(json.dumps(block).encode()) #TAKE BLOCK DICT AND CONVERT TO HASH VALUE

	##########################################################################
