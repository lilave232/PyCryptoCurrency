import enum
import os
from crypto.cryptography import *
import pickle
import json
class Wallet(object):

	def __init__(self,node,controller, key_dir="keys"):
		self.directory = None
		self.controller = None
		self.node = None
		self.keys = {}
		self.utxos = {}
		self.unconfirmed_utxos = {}
		self.unconfirmed_inputs = {}
		self.node = node
		self.controller = controller
		self.setkeydir(key_dir)

	def setkeydir(self,directory):
		if os.path.isdir(os.path.join(os.getcwd(),'KeyStores')) == False:
			os.mkdir(os.path.join(os.getcwd(),'KeyStores'))
		self.directory = 'KeyStores' + "/" + directory
		if os.path.isdir(os.path.join(os.getcwd(),self.directory)) == False:
			path = os.getcwd()
			os.mkdir(os.path.join(path,self.directory))
		self.indexKeys()
		self.indexUTXOS()

	def updateWallet(self):
		self.utxos = {}
		self.unconfirmed_utxos = {}
		self.unconfirmed_inputs = {}
		self.indexKeys()
		self.indexUTXOS()

	def addkey(self):
		hash, privKey = create_key(self.directory) #CREATE A KEY
		self.keys[hash.hex()] = privKey
		self.saveIndex()
		return hash #RETURN THE KEYS ADDRESS

	def addKeyPriv(self):
		hash, privKey = create_key(self.directory) #CREATE A KEY
		self.keys[hash.hex()] = privKey
		self.saveIndex()
		return hash,privKey #RETURN THE KEYS ADDRESS

	def saveIndex(self):
		pickle.dump(self.keys,open(os.path.join(self.controller.index_directory,'keys.pkl'), 'wb'))

	def indexKeys(self):

		self.keys = {}

		if (os.path.exists(self.directory)):

			for file in os.listdir(os.path.join(self.directory)):

				filename = os.path.join(self.directory,os.fsdecode(file))

				if '.' not in filename:

					hash, privKey = read_key(filename)

					self.keys[hash.hex()] = privKey
		else:
			print("Could not load keys") #NO DIRECTORY MEANS NO KEYS
			return

		pickle.dump(self.keys,open(os.path.join(self.controller.index_directory,'keys.pkl'), 'wb'))

	

	def indexUTXOS(self):
		block_files = [os.path.join(self.controller.directory,name) for name in os.listdir(self.controller.directory) if os.path.splitext(name)[1] == '.blk']
		block_files.sort(key=self.controller.blk_sort_key)
		self.utxos = {}
		for fname in block_files:
			block = json.load(open(fname, "rb" ))
			if block == False:
				os.remove(fname)
				continue
			self.getUtxosFromBlock(block)

		for txn in self.controller.txn_pool:

			for x, output in enumerate(txn['outputs']):

				if output['address'] in self.keys:

					self.unconfirmed_utxos[txn['txnid'] + str(x)] = {"TxID":txn['txnid'],"Value": output['value'], "Location":x, "Address":output['address']}

					#self.utxos[txn['txnid'] + str(x)] = {"TxID":txn['txnid'],"Value": output['value'], "Location":x, "Address":output['address']}

			for x, in_val in enumerate(txn['inputs']):

				if in_val['prev_txid'] + str(in_val['prev_txn_output']) in self.utxos:

					self.unconfirmed_inputs[in_val['prev_txid'] + str(in_val['prev_txn_output'])] = self.utxos[in_val['prev_txid'] + str(in_val['prev_txn_output'])]

					del self.utxos[in_val['prev_txid'] + str(in_val['prev_txn_output'])]
		
		pickle.dump(self.utxos, open(self.controller.index_directory + "/utxos.pkl", "wb" ) )

	def getUtxosFromBlock(self,block):

		for txn in block['txns']:
			for x, output in enumerate(txn['outputs']):

				if output['address'] in self.keys:

					self.utxos[txn['txnid'] + str(x)] = {"TxID":txn['txnid'],"Value": output['value'], "Location":x, "Address":output['address']}
			
			for x, in_val in enumerate(txn['inputs']):

				if in_val['prev_txid'] + str(in_val['prev_txn_output']) in self.utxos:

					del self.utxos[in_val['prev_txid'] + str(in_val['prev_txn_output'])]


	def sendTransaction(self, value, out_address, fees, forward=False):

		balance = self.getBalance()

		utxos_to_use = [] #SET UTXOS TO USE IN TRANSACTION TO EMPTY

		pubKeys = [] #SET PUBKEYS TO USE AS BLANK

		if balance < (value+fees):

			print("Cannot Send Transaction Insufficient Funds") #TELL USER THE TRANSACTION WILL FAIL

			return False

		value_utxos = 0

		for utxo in self.utxos:

			if (value_utxos > (value+fees)):

				break
				
			else:

				value_utxos += self.utxos[utxo]['Value']

				utxos_to_use.append({"TxID":self.utxos[utxo]['TxID'],"Output":self.utxos[utxo]['Location'],"PubKey":self.keys[self.utxos[utxo]['Address']].verifying_key.to_string().hex(),"PrivKey":self.keys[self.utxos[utxo]['Address']].to_string().hex(),"Address":self.utxos[utxo]['Address'],"Value":self.utxos[utxo]['Value']})

				pubKeys.append(self.keys[self.utxos[utxo]['Address']].verifying_key.to_string().hex())

		txn = self.controller.gen_txn(out_address,utxos_to_use,value,fees)

		self.controller.send_txn(txn,pubKeys,forward)


	def getBalance(self,type=0):

		if type == 0:
			print("CONFIRMED BALANCE:",sum([x['Value'] for x in self.utxos.values()]))
			return float("{:.8f}".format(sum([x['Value'] for x in self.utxos.values()])))

		if type == 1:
			#for x in self.unconfirmed_utxos:
			#	if x not in self.unconfirmed_inputs:
			#		utxos[x] = self.unconfirmed_utxos[x]
			return float("{:.8f}".format(sum([x['Value'] for x in self.utxos.values()]) + sum([self.unconfirmed_utxos[x]['Value'] for x in self.unconfirmed_utxos if x not in self.unconfirmed_inputs])))

		if type == 2:
			#for x in self.unconfirmed_utxos:
			#	if x not in self.unconfirmed_inputs:
			#		utxos[x] = self.unconfirmed_utxos[x]
			return float("{:.8f}".format(sum([x['Value'] for x in self.utxos.values()]) + sum([self.unconfirmed_inputs[x]['Value'] for x in self.unconfirmed_inputs])))

	def getBalanceForKey(self,key):
		utxos = pickle.load(open(self.controller.index_directory + "/utxos",'rb'))

		return sum([utxos[utxo]['Value'] for utxo in utxos.keys() if key == utxos[utxo]['Address']])
