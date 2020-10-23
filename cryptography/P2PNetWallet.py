from cryptography.ecdhcrypto import *
from cryptography.block_helper import *
from cryptography.P2PNetNode import *
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

chain_info = {}
import time

import random


class P2PWallet:



	def __init__(self):

		self.key_location = "keys" #INITIAL KEY LOCATION IF KEYS

		self.keys = {} #SET KEYS TO EMPTY DICTIONARY

		self.utxos = {} #SET UTXOS TO EMPTY DICTIONARY

		self.wallet_balance = 0
		self.unconfirmed_balance = 0
		self.usable_balance = 0

	#GET KEYS
	def get_keys(self):

		self.keys = {}

		if (os.path.exists(self.key_location)): #IF KEY LOCATION EXISTS

			for file in os.listdir(os.path.join(self.key_location)): #LOOP THROUGH FILES IN KEY LOCATION

				filename = os.path.join(self.key_location,os.fsdecode(file)) #GET FILENAME

				if '.' not in filename: #KEY FILES DO NOT CONTAIN A . WHEREAS COMMON HIDDEN FILES DO

					hash, privKey = read_key(filename) #READ KEY TO HASH AND PRIVATE KEY

					self.keys[hash.hex()] = privKey #ADD KEY TO KEYS DICTIONARY

		else:
			print("Could not load keys") #NO DIRECTORY MEANS NO KEYS

	#CHANGE LOCATION OF KEYS
	def update_key_location(self,location, node = None):

		self.key_location = location #SET KEY LOCATION

		if node != None: #IF NODE NOT EQUAL TO NONE

			node.key_directory = location #SET NODE KEY DIRECTORY
	
	#GET WALLET BALANCE
	def get_wallet_balance(self,node):

		node.download_chain()

		self.get_keys() #UPDATE KEYS

		self.utxos = {}

		node.key_directory = self.key_location #SET NODE KEY LOCATION

		wallet_balance = 0 #SETUP WALLET BALANCE VARIABLE

		unconfirmed_balance = 0 #SETUP UNCONFIRMED BALANCE VARIABLE

		usable_balance = 0 #SETUP USABLE BALANCE VARIABLE

		i = 0 #SETUP BLOCK COUNTER VARIABLE

		while os.path.exists(os.path.join(node.chain_directory,"blk%s.pkl" % i)): #IF PATH EXISTS

			filename = os.path.join(node.chain_directory,"blk%s.pkl" % i) #GET FILENAME

			if ".pkl" in filename: #IF FILENAME HAS .PKL BLOCK EXTENSION

				with open(filename, 'r') as handle: #OPEN FILE FOR READING

					b = json.load(handle) #LOAD FILE TO DICTIONARY

					for txn in b['txns']: #LOOP THROUGH TRANSACTIONS

						for x, output in enumerate(txn['outputs']): #LOOP THROUGH OUTPUTS

							if output['address'] in self.keys: #IF OUTPUT ADDRESS IS IN KEYS DICTIONARY

								self.utxos[txn['txnid']] = {"Value":output['value'],"Location":x,"Address":output['address']} #ADD TO UTXOS

						for x, in_val in enumerate(txn['inputs']): #LOOP THROUGH INPUTS

							if in_val['prev_txid'] in self.utxos: #IF TXID IN UTXOS VALUE MAY BE SPENT

								if self.utxos[in_val['prev_txid']]['Location'] == in_val['prev_txn_output']: #CHECK IF LOCATION IN INPUT MATCHES LOCATION FROM OUTPUT

									del self.utxos[in_val['prev_txid']] #TRANSACTION USED DELETE FROM UNUSED TRANSACTIONS
			i += 1
		
		#GET CONFIRMED AND VERIFIED WALLET BALANCE
		for utxo in self.utxos:
		
			wallet_balance += self.utxos[utxo]['Value'] #BALANCE IS SUM OF ALL UTXOS

		#ANALYZE TRANSACTION POOL FOR EVIDENCE OF OUTPUTS SPENT BUT NOT CONFIRMED OR OUTPUTS TO BE RECEIVED
		for txn in node.txn_pool: #FOR TRANSACTION IN TRANSACTION POOL

			for x, output in enumerate(txn['outputs']): #FOR OUTPUT IN TXN

				if output['address'] in self.keys: #IF OUTPUT ADDRESS IN SELF.KEYS

					self.utxos[txn['txnid']] = {"Value":output['value'],"Location":x,"Address":output['address']} #ADD TO UTXOS

			for x, in_val in enumerate(txn['inputs']): #FOR INPUT IN TXN

				if in_val['prev_txid'] in self.utxos: #IF PREV_TXID IN UTXOS 

					if self.utxos[in_val['prev_txid']]['Location'] == in_val['prev_txn_output']: #IF LOCATION AND PREV_OUTPUT ARE EQUAL

						del self.utxos[in_val['prev_txid']] #REMOVE TRANSACTION FROM UTXOS USER INTENDED ON SPENDING ALREADY
		
		for utxo in self.utxos: #GET UNCONFIRMED BALANCE

			unconfirmed_balance += self.utxos[utxo]['Value'] #BALANCE IS SUM OF ALL UTXOS

		#LOOP BACK OVER TXN POOL TRANSACTIONS AND REMOVED UNCONFIRMED OUTPUTS NOT RECEIVED YET AS THESE ARE NOT SPENDABLE
		for txn in node.txn_pool: 
			
			for x, output in enumerate(txn['outputs']): #FOR OUTPUT IN TXN

				if txn['txnid'] in self.utxos: #IF OUTPUT ADDRESS IN SELF.KEYS

					del self.utxos[txn['txnid']] #REMOVE
		
		#OBTAIN SPENDABLE BALANCE
		for utxo in self.utxos:

			usable_balance += self.utxos[utxo]['Value'] #USABLE IS SUM OF UTXOS

		self.wallet_balance = wallet_balance
		self.unconfirmed_balance = unconfirmed_balance
		self.usable_balance = usable_balance

		print("Balance Is: {:.8f}".format(self.wallet_balance)) #PRINT WALLET BALANCE

		print("Unconfirmed Balance Is: {:.8f}".format(self.unconfirmed_balance)) #PRINT UNCONFIRMED BALANCE

		print("Usable Balance Is: {:.8f}".format(self.usable_balance)) #PRINT USABLE BALANCE
	
	#LIST AVAILABLE UTXOS
	def list_utxos(self,node):

		node.print(self.utxos)
		

	#SEND TRANSACTION
	def send_transaction(self, node, value, out_address, fees):

		self.get_keys() #GET KEYS

		_,_,usable_balance = self.get_wallet_balance(node) #OBTAIN USABLE BALANCE

		utxos_to_use = [] #SET UTXOS TO USE IN TRANSACTION TO EMPTY

		pubKeys = [] #SET PUBKEYS TO USE AS BLANK

		if usable_balance < value: #IF USABLE BALANCE LESS THAN VALUE

			node.print("Cannot Send Transaction Insufficient Funds") #TELL USER THE TRANSACTION WILL FAIL

			return False

		#GET WHICH UTXOS TO USE AS INPUTS
		value_utxos = 0 

		for utxo in self.utxos: #LOOP THROUGH UTXOS

			if (value_utxos > (value+fees)): #IF THE VALUE OF THE UTXOS IS GREATER THAN THE VALUE TO SEND BREAK

				break

			else:

				value_utxos += self.utxos[utxo]['Value'] #ADD VALUE OF UTXO TO VALUE

				#APPEND UTXO INFORMATION TO UTXOS TO USE
				utxos_to_use.append({"TxID":utxo,"Output":self.utxos[utxo]['Location'],"PubKey":self.keys[self.utxos[utxo]['Address']].verifying_key.to_string().hex(),"PrivKey":self.keys[self.utxos[utxo]['Address']].to_string().hex(),"Address":self.utxos[utxo]['Address'],"Value":self.utxos[utxo]['Value']})
				
				#ADD CORRESPONDING PUBLIC KEY TO ARRAY
				pubKeys.append(self.keys[self.utxos[utxo]['Address']].verifying_key.to_string().hex())
		
		#UTILIZE FUNCTION TO GENERATE FORMATTED TRANSACTION
		txn = gen_txn(out_address,utxos_to_use,value,fees)

		#SEND THE TRANSACTION OUT
		node.send_transaction(txn,pubKeys)
	

	#GENERATE KEY TO RECV TRANSACTION AT
	def recv_transaction(self):

		hash, privKey = create_key(self.key_location) #CREATE A KEY

		return hash #RETURN THE KEYS ADDRESS