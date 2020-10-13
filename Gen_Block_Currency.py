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

chain_info = {}
import time

import random

class P2PNetNode:

    def __init__(self,initial_port,server_port):
        self.clients = []
        self.server_address = 'localhost'
        self.server_port = server_port
        self.server_running = False
        self.peer_services = []
        self.peer_clients = []
        self.chain_size_confirmations = 0
        self.chain_sizes = []
        self.confirmed_size = 0
        self.chain_downloaded = False
        self.chain_directory = ""
        self.node_target = None
        self.node_block = None
        self.wait_download = False
        self.block_to_save = None
        self.block_hashes = []
        self.pending_block_hashes = []
        self.block_confirmations = 0
        self.txn_confirmations = {}
        self.txn_pool = []
        self.mem_pool_hashes = []
        self.key_directory = ""
        threading.Thread(target=self.start_server,args=(self.server_address,self.server_port)).start()
        threading.Thread(target=self.start_client,args=(self.server_address,initial_port)).start()
        #self.connect_initial('localhost',initial_port)
        #self.establish_server('localhost',server_port)
        #threading.Thread(target=self.connect_initial,args=('localhost',initial_port)).start()
        #threading.Thread(target=self.establish_server,args=('localhost',server_port)).start()
    
    def update_chain(self):
        print("Loading Data From Directory")
        global chain_info
        file_count = 0
        file_size = 0
        i = 0
        while os.path.exists(os.path.join(self.chain_directory,"blk%s.pkl" % i)):
            filename = os.path.join(self.chain_directory,"blk%s.pkl" % i)
            #print(filename)
            if ".pkl" in filename:
                file_size += os.path.getsize(filename)
                with open(filename, 'rb') as handle:
                    b = pickle.load(handle)
                    block_hash = hash_block_dict(b)
                try:
                    prev_hash = bytearray(32).hex()
                    if len(self.block_hashes) > 0 and i - 1 >= 0:
                        prev_hash = self.block_hashes[i - 1]
                        
                    #print(b['prev_block_hash'])
                    #print(prev_hash)
                    assert(b['prev_block_hash'] == prev_hash)
                except:
                    raise Exception("Chain Corrupted")

                if block_hash.hex() not in self.block_hashes:
                    self.block_hashes.append(block_hash.hex())

                file_count += 1
            i += 1
        chain_info['file_count'] = file_count
        chain_info['chain_size'] = file_size
        #print("Chain size")

        if file_count == 0:
            print("No Chain Info Was Found")
        self.block_thread = False
    
    def clientthread(self, conn, addr): 
        # sends a message to the client whose user object is conn 
        #conn.send("Welcome to this chatroom!".encode())
        global chain_info
    
        while True: 
                #try:
                length = int.from_bytes(conn.recv(8),'big')
                if length > 2048:
                    recv_length = 0
                    message = bytes()
                    recv_amount = 2048
                    while recv_length < length:
                        message = conn.recv(recv_amount)
                        recv_length += 2048
                        if (recv_length + 2048 > length):
                            recv_length = length - recv_length
                else:
                    message = conn.recv(length)
                #print(int.from_bytes(length,'big'))
                if message:
                    json_message = json.loads(message.decode('utf-8'))


                    if json_message['Type'] == 0:
                        if json_message['Address'] + ":" + str(json_message['Port']) not in self.peer_services:
                            threading.Thread(target=self.start_client,args=(self.server_address,json_message["Port"])).start()
                            self.broadcast_server_to_client(message.decode('utf-8'), conn)
                    
                    if json_message['Type'] == 1:
                        print(json_message['Message'])
                    
                    elif json_message['Type'] == 2:
                        self.block_thread = True
                        self.update_chain()
                        while self.block_thread:
                            continue
                        json_return = {'Type':3,'Chain_Size':chain_info['chain_size']}
                        print("Sending Chain Size:",chain_info['chain_size'])
                        message = self.prepare_message(json.dumps(json_return))
                        conn.send(message)
                        time.sleep(1)

                    # CONFIRM BLOCK
                    elif json_message['Type'] == 7 and self.chain_downloaded:
                        self.confirm_block(json_message['Block'],json_message["PubKey"],json_message["Signature"],conn)


                    elif json_message['Type'] == 8 and self.chain_downloaded:
                        #SEND TARGET VALUE TO CLIENT
                        if self.node_target == None:
                            message = self.prepare_message(json.dumps(json_message))
                            conn.send(message)
                        else:
                            print("Sending Target:",self.node_target)
                            #SEND TARGET
                            json_message = {'Type':9,'Target':self.node_target}
                            message = self.prepare_message(json.dumps(json_message))
                            conn.send(message)

                        
                    elif json_message['Type'] == 9 and self.chain_downloaded:
                        self.node_target = json_message['Target']
                        print("Chain Target:",json_message['Target'])

                    elif json_message['Type'] == 10:
                        block_hash = hash_block_dict(json_message['Block'])

                        if block_hash not in self.block_hashes:
                            if block_hash in self.pending_block_hashes:
                                self.block_confirmations += 1
                            else:
                                self.pending_block_hashes.append(block_hash.hex())

                        if self.block_confirmations >= 1:
                            self.block_confirmations = 0
                            self.pending_block_hashes = []
                            save_block(self.chain_directory,json_message['Block'])
                            if block_hash not in self.block_hashes:
                                self.block_hashes.append(block_hash.hex())
                            self.block_thread = False
                            if (len(json_message['Block']['txns']) > 1):
                                for txn in json_message['Block']['txns'][1:]:
                                    if (self.txn_pool != None and len(self.txn_pool) > 0):
                                        self.txn_pool.remove(txn)

                    
                    elif json_message['Type'] == 12:
                        with open(os.path.join(self.chain_directory,json_message['File']), 'rb') as handle:
                            b = pickle.load(handle)
                            return_message = {"Type":12,"Filename":json_message['File'],"Block":b}
                            message = self.prepare_message(json.dumps(return_message))
                            conn.send(message)
                    
                    elif json_message['Type'] == 13:
                        print("Transaction Received Confirming")
                        txn = json_message['Txn']
                        if txn['txnid'] not in self.txn_confirmations and txn not in self.txn_pool:
                            self.txn_confirmations[txn['txnid']] = 0
                        self.confirm_transaction(json_message['Txn'],json_message['PubKeys'])
                    
                    elif json_message['Type'] == 14:
                        print("Confirmation Received")
                        txn = json_message['Txn']
                        if json_message['TXID'] not in self.txn_confirmations and txn not in self.txn_pool:
                            self.txn_confirmations[json_message['TXID']] = 0

                        if json_message['TXID'] in self.txn_confirmations:
                            if txn not in self.txn_pool:
                                self.txn_confirmations[json_message['TXID']] += 1

                            if  self.txn_confirmations[json_message['TXID']] >= 1 and txn not in self.txn_pool:
                                json_message = {"Type":15,"TXID":json_message['TXID'],"Txn":json_message['Txn']}
                                self.broadcast_client_to_server(json.dumps(json_message))

                    elif json_message['Type'] == 15:
                        if json_message['Txn'] not in self.txn_pool:
                            print("Adding To Pool")
                            self.add_txn_to_pool(json_message['Txn'])
                    
                    elif json_message['Type'] == 16:
                        print("Sending Mem Pool")
                        json_message = {'Type':16,'Mem_Pool':self.txn_pool}
                        message = self.prepare_message(json.dumps(json_message))
                        conn.send(message)
                    


                else: 
                    self.remove(conn)
                    break
    
                #except:
                #    continue
    
    def broadcast_server_to_client(self,message, connection):
        for clients in self.list_of_clients: 
            if clients!=connection: 
                try: 
                    length = len(message.encode()).to_bytes(8, byteorder='big')
                    clients.send(length + message.encode())
                except: 
                    clients.close() 
                    self.remove(clients)
                    # if the link is broken, we remove the client 
    def broadcast_client_to_server(self,message):
        for clients in self.peer_clients:
            try:
                length = len(message.encode()).to_bytes(8, byteorder='big')
                clients.send(length + message.encode())
            except:
                #print("Unable to Send Message")
                raise Exception("Unable to Send Message")

    
    def remove(self, connection):
        print("Removing Client Connection")
        if connection in self.list_of_clients: 
            self.list_of_clients.remove(connection)
            #self.peer_services.remove(self.client_to_server[connection])

    def prepare_message(self,message):
        length = len(message.encode()).to_bytes(8, byteorder='big')
        message = length + message.encode()
        return message
    
    def start_server(self, server_address, server_port):
        self.main_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
        self.main_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) 
        self.main_server.bind((server_address, server_port))
        self.main_server.listen(100)
        self.list_of_clients = []

        while True:
            conn, addr = self.main_server.accept()
            self.list_of_clients.append(conn)
            threading.Thread(target=self.clientthread,args=(conn,addr)).start()
        conn.close() 
        self.main_server.close()   

    def start_client(self, connect_address, connect_port):
        #print("Adding Peer At: ", connect_port)
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            client.connect((connect_address, connect_port))
            json_dict = {"Type":0,"Address":self.server_address,"Port":self.server_port}
            self.peer_services.append(connect_address + ":" + str(connect_port))
            self.peer_clients.append(client)
            message = self.prepare_message(json.dumps(json_dict))
            client.send(message)
            #print(self.peer_clients)
        except:
            #print("Unable to Connect")
            return
        while True: 
            # maintains a list of possible input streams 
            sockets_list = [sys.stdin, client] 
            read_sockets,write_socket, error_socket = select.select(sockets_list,[],[]) 
        
            for socks in read_sockets: 
                if socks == client:
                    length = int.from_bytes(socks.recv(8),'big')
                    if length > 2048:
                        recv_length = 0
                        message = bytes()
                        recv_amount = 2048
                        while recv_length < length:
                            message = socks.recv(recv_amount)
                            recv_length += 2048
                            if (recv_length + 2048 > length):
                                recv_length = length - recv_length
                    else:
                        message = socks.recv(length)

                    if message == b'':
                        #print("Peer Disconnected")
                        self.peer_services.remove(connect_address + ":" + str(connect_port))
                        self.peer_clients.remove(client)
                        client.close()
                        return

                    if message:
                        json_message = json.loads(message.decode('utf-8'))
                        if json_message['Type'] == 0:
                            if json_message['Address'] + ":" + str(json_message['Port']) not in self.peer_services and json_message['Address'] + ":" + str(json_message['Port']) != (self.server_address + ":" + str(self.server_port)):
                                threading.Thread(target=self.start_client,args=(self.server_address,json_message["Port"])).start()

                        #RECEIVE CHAIN SIZE
                        elif json_message['Type'] == 3:
                            print("Chain Size Received")
                            if json_message['Chain_Size'] in self.chain_sizes:
                                self.chain_size_confirmations += 1
                                if self.chain_size_confirmations > 0:
                                    self.confirmed_size = json_message['Chain_Size']
                            else:
                                self.chain_sizes.append(json_message['Chain_Size'])
                        
                        elif json_message['Type'] == 8 and self.chain_downloaded:
                            #NO TARGET HAS BEEN ESTABLISHED GENERATE TARGET
                            random_number = random.randint(268435456,858993459)#4294967295)
                            target = format(random_number, 'x')
                            #SEND TARGET
                            json_message = {'Type':9,'Target':target}
                            self.broadcast_client_to_server(json.dumps(json_message))
                            self.node_target = target

                        
                        elif json_message['Type'] == 9 and self.chain_downloaded:
                            self.node_target = json_message['Target']
                            print("Chain Target:",self.node_target)


                        elif json_message['Type'] == 10 and self.chain_downloaded:
                            self.block_confirmations += 1

                        
                        elif json_message['Type'] == 11 and self.chain_downloaded:
                            self.block_confirmations = -1
                        

                        elif json_message['Type'] == 12:
                            if (os.path.exists(os.path.join(self.chain_directory,json_message['Filename']))):
                                continue
                            

                            try:
                                prev_hash = bytearray(32).hex()
                                if len(self.block_hashes) > 0:
                                    prev_hash = self.block_hashes[-1]
                                assert(json_message['Block']['prev_block_hash'] == prev_hash)
                            except:
                                raise Exception("Chain Corrupted")
                            

                            with open(os.path.join(self.chain_directory,json_message['Filename']), 'wb') as handle:
                                b = json_message['Block']
                                pickle.dump(b, handle, protocol=pickle.HIGHEST_PROTOCOL)
                            

                            #chain_info['chain_size'] += (os.path.getsize(os.path.join(self.chain_directory,json_message['Filename'])))
                            self.block_hashes.append(hash_block_dict(b).hex())
                            self.wait_download = False

                        elif json_message['Type'] == 16:
                            mem_pool = json_message["Mem_Pool"]
                            mem_pool_hash = hash_block(json.dumps(mem_pool).encode())
                            if mem_pool_hash in self.mem_pool_hashes:
                                self.mem_pool_confirmations += 1
                            else:
                                self.mem_pool_hashes.append(mem_pool_hash)
                            if self.mem_pool_confirmations > 0 or len(self.peer_services) < 2:
                                self.txn_pool = mem_pool
                                self.block_thread = False
                            
                                
        server.close()

    def listpeers(self):
        print(self.peer_services)
    
    def download_chain(self, update=True):
        if (update == True):
            self.update_chain()
        json_message = {"Type":2}
        self.broadcast_client_to_server(json.dumps(json_message))

    def get_previous_block(self):
        file_count = 0
        for file in  os.listdir(os.path.join(self.chain_directory)):
            filename = os.path.join(self.chain_directory,os.fsdecode(file))
            if ".pkl" in filename:
                file_size = os.path.getsize(filename)
                block_data = open(file, "r")
                file_count += 1
        if file_count == 0:
            return False
        else:
            return block_data

    def new_block(self):
        prev_block = self.get_previous_block()
        if (prev_block==False):
            random_number = random.randint(14540253,16777215)
            target = format(random_number, 'x')
            base_txn = uuid.uuid4().hex
            reward = 10
            block_data = {"prev_block_hash":bytearray(32).hex(),"num_txns":1,"block_size":0,"target":target,"nonce":bytearray(4).hex(),"txns":[]}
            #{"id":base_txn,"input_size":1,"inputs":[{"address":bytearray(32).hex(),"value":reward}],"output_size":1,"outputs":[]}
            return block_data

    def confirm_block(self,block,pubKey,signature,client = None):
        try:
            print("Confirming Block")
            #CONFIRM SIGNATURE
            block_hash = hash_block_dict(block)
            pubKey = pub_key_from_string(pubKey)

            verify_msg(bytes.fromhex(signature),block_hash,pubKey)

            previous_hash = bytearray(32).hex()
            if (len(self.block_hashes) > 0):
                previous_hash = self.block_hashes[-1]
            #CHECK PREVIOUS BLOCK HASH
            assert (block['prev_block_hash'] == previous_hash)
            #CHECK TIME
            assert (block['time'] <= int(time.time()) and block['time'] >= int(time.time()) - 3600)
            #VERIFY TRANSACTIONS
            assert (len(block['txns'][0]['inputs']) == 1 and len(block['txns'][0]['outputs']) == 1)
            #CHECK INPUTS
            assert (block['txns'][0]['inputs'][0]['prev_txid'] == bytearray(16).hex() and block['txns'][0]['inputs'][0]['prev_txn_output'] == 0 and block['txns'][0]['inputs'][0]['sig_prev_out'] == bytearray(64).hex())
            #CHECK OUTPUTS
            assert (block['txns'][0]['outputs'][0]['address'] == hash_v_key(pubKey).hex())
            #CHECK VALUE EQUAL TO CORRECT REWARD
            reward = int(20 * (1/max(int(2*(time.time() - 1577836800)/315360000),1)))
            assert (block['txns'][0]['outputs'][0]['value'] == reward)
            #CHECK TXID
            assert (len(bytes.fromhex(block['txns'][0]['txnid'])) == 16)
            #CHECK HASH BELOW TARGET
            assert (block_hash < (bytes.fromhex(self.node_target) + bytearray(28)))

            if (len(block['txns']) > 1):
                for txn in block['txns'][1:]:
                    assert(any(hash_block(json.dumps(d).encode()) == hash_block(json.dumps(txn).encode()) for d in self.txn_pool))
                        

            print("Block Confirmed")
            print("Sending Confirmation")
            #SEND CONFIRMATION
            json_message = {"Type":10,"Block":block}
            self.broadcast_client_to_server(json.dumps(json_message))

            if (len(block['txns']) > 1):
                for txn in block['txns'][1:]:
                    if (self.txn_pool != None and len(self.txn_pool) > 0):
                        self.txn_pool.remove(txn)
            
            self.block_confirmations += 1
            if self.block_confirmations >= 1:
                save_block(self.chain_directory,block)
                self.block_confirmations = 0
                self.pending_block_hashes = []
                self.block_hashes.append(block_hash.hex())
                self.block_thread = False
            #save_block(self.chain_directory,block)
        except:
            #
            json_message = {"Type":11}
            message = self.prepare_message(json.dumps(json_message))
            if client == None:
                self.block_confirmations = -1
            else:
                client.send(message)
            raise Exception("Unable to Confirm Block")
            

        
            
        

    def chain_mine(self):
        print("Mining Chain")
        print("Requesting Mem Pool")
        #REQUEST TARGET FROM CHAIN
        self.block_confirmations = 0
        self.broadcast_client_to_server(json.dumps({'Type':8}))
        while self.node_target == None:
            continue

        hash, priv_key = create_key(self.key_directory)
        if (len(self.block_hashes) == 0):
            prev_block_hash = bytearray(32).hex()
        else:
            prev_block_hash = self.block_hashes[-1]
        self.update_pool()
        if self.txn_pool == None:
            self.txn_pool = []
        block = gen_block(self.node_target, hash, prev_block_hash,self.txn_pool)
        
        block_hash = hash_block_dict(block)
        block_sig = sign_msg(block_hash,priv_key)
        self.block_thread = True
        json_message = {"Type":7,"Block":block,"PubKey":priv_key.verifying_key.to_string().hex(),"Signature":block_sig}
        self.pending_block_hashes.append(block_hash)
        self.broadcast_client_to_server(json.dumps(json_message))

        while self.block_thread:
            if self.block_confirmations == -1:
                print("Could Not Mine Block")
                #self.chain_mine()
                return
            continue
        #save_block(self.chain_directory,block)
        print("Block Mined On Chain!!!")
        #self.chain_mine()
        #self.confirm_block(json_message['Block'],json_message["PubKey"],json_message["Signature"],conn)
        
    
    def send_transaction(self,txn,pubKeys):
        json_message = {"Type":13,"Txn":txn,"PubKeys":pubKeys}
        self.broadcast_client_to_server(json.dumps(json_message))

    
    def update_pool(self):
        self.mem_pool_confirmations = 0
        self.block_thread = True
        mem_pool_hash = hash_block(json.dumps(self.txn_pool).encode())
        self.mem_pool_hashes.append(mem_pool_hash)
        json_message = {"Type":16}
        self.broadcast_client_to_server(json.dumps(json_message))
        while self.block_thread == True:
            if (len(self.peer_services) < 1):
                break
            continue
        print("Mem Pool Updated")
        

    
    def read_pool(self):
        print(self.txn_confirmations)
        print(self.txn_pool)
    
    def add_txn_to_pool(self,txn):
        if txn not in self.txn_pool:
            self.txn_pool.append(txn)
            del self.txn_confirmations[txn['txnid']]
        print("TXN Added to pool")



    def confirm_transaction(self,txn,pubKeys):
        try:
            total_in_value = 0
            #CHECK ID FORMAT
            assert (len(bytes.fromhex(txn['txnid'])) == 16)
            #CHECK TIME
            assert (txn['time'] <= int(time.time()) and txn['time'] >= int(time.time()) - 3600)
            #CHECK INPUTS
            assert (len(txn['inputs']) > 0)
            for x, input_val in enumerate(txn['inputs']):
                prev_txn = get_txn(input_val['prev_txid'],self.chain_directory)
                if prev_txn == False:
                    assert(False)

                address = prev_txn['outputs'][input_val['prev_txn_output']]['address']
                total_in_value += prev_txn['outputs'][input_val['prev_txn_output']]['value']
                pubKeyHash = hash_v_key(pub_key_from_string(pubKeys[x])).hex()
                #VERIFY OWNERSHIP
                #VERIFY PUBKEY PROVIDED = ADDRESS OF OUTPUT
                assert(address == pubKeyHash)
                #VERIFY USER OWNS INPUTS BY CHECKING PRIVATE KEY GENERATED SIGNATURE MATCHES PUBKEYHASH
                verify_msg(bytes.fromhex(input_val['sign_prev_out']),bytes.fromhex(address),pub_key_from_string(pubKeys[x]))
            #CHECK OUTPUTS
            assert (len(txn['outputs']) > 0)
            total_out_value = 0
            for x, output_val in enumerate(txn['outputs']):
                assert(len(bytes.fromhex(output_val['address'])) == 32)
                total_out_value += output_val['value']
            
            assert(total_out_value == total_in_value)
            print("Transaction Confirmed")

            if (txn['txnid'] not in self.txn_confirmations and txn not in self.txn_pool):
                self.txn_confirmations[txn['txnid']] = 0
            if txn['txnid'] in self.txn_confirmations:
                self.txn_confirmations[txn['txnid']] += 1
            
            json_message = {"Type":14, "TXID":txn['txnid'],"Txn":txn}
            self.broadcast_client_to_server(json.dumps(json_message))

            if  self.txn_confirmations[txn['txnid']] >= 1 not in self.txn_pool:
                json_message = {"Type":15,"TXID":txn['txnid'],"Txn":txn}
                self.broadcast_client_to_server(json.dumps(json_message))
            
        except:
            print("Unable to Confirm Transaction")
            #raise Exception("Unable to Complete Transaction")

class P2PWallet:

    def __init__(self):
        self.key_location = "keys"
        self.addresses = []
        self.keys = {}
        self.utxos = {}

    def get_keys(self):
        if (os.path.exists(self.key_location)):
            for file in os.listdir(os.path.join(self.key_location)):
                filename = os.path.join(self.key_location,os.fsdecode(file))
                if '.' not in filename:
                    hash, privKey = read_key(filename)
                    self.keys[hash.hex()] = privKey
        else:
            print("Could not load keys")
    
    def get_address_balance(self,node,address):
        print("Loading Data From Directory")
        address_balance = 0
        file_count = 0
        file_size = 0
        for file in os.listdir(os.path.join(node.chain_directory)):
            filename = os.path.join(node.chain_directory,os.fsdecode(file))
            if ".pkl" in filename:
                with open(filename, 'rb') as handle:
                    b = pickle.load(handle)
                    for txn in b['txns']:
                        if (not any(d['address'] == address for d in txn['outputs'])):
                            for output in txn['outputs']:
                                if output['address'] == address.hex():
                                    address_balance += output['value']
                                    if txn['txnid'] not in self.utxos:
                                        self.utxos.append({txn['txnid']:output['value']})
                        if (not any(d['prev_txid'] in self.utxos for d in txn['inputs'])):
                            for in_val in txn['inputs']:
                                if in_val['prev_txid'] in  self.utxos:
                                    del self.utxos[txn['txnid']]
        return address_balance

    def update_key_location(self,location):
        self.key_location = location
        if node != None:
            node.key_directory = location
    
    def get_wallet_balance(self,node):
        self.get_keys()
        node.key_directory = self.key_location
        wallet_balance = 0
        unconfirmed_balance = 0
        usable_balance = 0
        file_count = 0
        file_size = 0
        i = 0
        while os.path.exists(os.path.join(node.chain_directory,"blk%s.pkl" % i)):
            filename = os.path.join(node.chain_directory,"blk%s.pkl" % i)
            if ".pkl" in filename:
                with open(filename, 'rb') as handle:
                    b = pickle.load(handle)
                    for txn in b['txns']:
                        for x, output in enumerate(txn['outputs']):
                            if output['address'] in self.keys:
                                self.utxos[txn['txnid']] = {"Value":output['value'],"Location":x,"Address":output['address']}
                        for x, in_val in enumerate(txn['inputs']):
                            if in_val['prev_txid'] in self.utxos:
                                if self.utxos[in_val['prev_txid']]['Location'] == in_val['prev_txn_output']:
                                    del self.utxos[in_val['prev_txid']]
            i += 1
        
        for utxo in self.utxos:
            wallet_balance += self.utxos[utxo]['Value']

        for txn in node.txn_pool:
            for x, output in enumerate(txn['outputs']):
                if output['address'] in self.keys:
                    self.utxos[txn['txnid']] = {"Value":output['value'],"Location":x,"Address":output['address']}
            for x, in_val in enumerate(txn['inputs']):
                if in_val['prev_txid'] in self.utxos:
                    if self.utxos[in_val['prev_txid']]['Location'] == in_val['prev_txn_output']:
                        del self.utxos[in_val['prev_txid']]
        
        for utxo in self.utxos:
            unconfirmed_balance += self.utxos[utxo]['Value']

        for txn in node.txn_pool:
            for x, output in enumerate(txn['outputs']):
                if txn['txnid'] in self.utxos:
                    del self.utxos[txn['txnid']]
        
        for utxo in self.utxos:
            usable_balance += self.utxos[utxo]['Value']


        
        return wallet_balance, unconfirmed_balance, usable_balance
    
    def list_utxos(self):
        print(self.utxos)

    def send_transaction(self, node, value, out_address):
        self.get_keys()
        _,_,usable_balance = self.get_wallet_balance(node)
        utxos_to_use = []
        pubKeys = []
        #if usable_balance < value:
        #    print("Cannot Send Transaction Insufficient Funds")
        #    return False
        value_utxos = 0
        for utxo in self.utxos:
            if (value_utxos > value):
                break
            else:
                value_utxos += self.utxos[utxo]['Value']
                utxos_to_use.append({"TxID":utxo,"Output":self.utxos[utxo]['Location'],"PubKey":self.keys[self.utxos[utxo]['Address']].verifying_key.to_string().hex(),"PrivKey":self.keys[self.utxos[utxo]['Address']].to_string().hex(),"Address":self.utxos[utxo]['Address'],"Value":self.utxos[utxo]['Value']})
                pubKeys.append(self.keys[self.utxos[utxo]['Address']].verifying_key.to_string().hex())
        
        txn = gen_txn(out_address,utxos_to_use,value)

        #node.confirm_transaction(txn,pubKeys)
        node.send_transaction(txn,pubKeys)
    

    
    def recv_transaction(self):
        hash, privKey = create_key(self.key_location)
        return hash
        

        
        





        
def new_block():
    #prev_block = self.get_previous_block()
    prev_block = False
    if (prev_block==False):
        random_number = random.randint(14540253,16777215)
        target = format(random_number, 'x')
        base_txn = uuid.uuid4().hex
        reward = 10
        block_data = {"prev_block_hash":bytearray(32).hex(),"num_txns":1,"block_size":0,"target":target,"nonce":bytearray(4).hex(),"txns":[]}
        #{"id":base_txn,"input_size":1,"inputs":[{"address":bytearray(32).hex(),"value":reward}],"output_size":1,"outputs":[]}
        return block_data

def import_key():
    file = input("Where is the location of the key file? ")
    while(os.path.isfile(file) == False):
        print("Not A Valid Path to Key File")
        file = input("Where is the location of the key file? ")
    try:
        if (os.path.split(os.path.abspath(file))[0] != os.path.abspath("keys")):
            copyfile(file,os.path.join("keys",uuid.uuid4().hex))
        privateKey, publicKeyHash = read_key(file)
        print("Key Imported")
    except:
        raise Exception("Invalid Private Key File")

def list_keys():
    for file in os.listdir("keys"):
        if file[0] != ".":
            filename = os.path.join("keys",os.fsdecode(file))
            #print(filename)
            privateKey, publicKeyHash = read_key(filename)
            print(publicKeyHash.hex())

def load_chain():
    dir = input("Where is your chain: ")
    if (os.path.isdir(dir) == False):
        os.mkdir(dir)
        chain_directory = dir
    else:
        chain_directory = dir
    print("Loading Data From Directory")
    global chain_info
    global node
    node.chain_directory = chain_directory
    file_count = 0
    file_size = 0
    i = 0
    while os.path.exists(os.path.join(dir,"blk%s.pkl" % i)):
        filename = os.path.join(chain_directory,"blk%s.pkl" % i)
        #print(filename)
        if ".pkl" in filename:
            file_size += os.path.getsize(filename)
            with open(filename, 'rb') as handle:
                b = pickle.load(handle)
                block_hash = hash_block_dict(b)
            #print(node.block_hashes)

            try:
                prev_hash = bytearray(32).hex()
                if len(node.block_hashes) > 0 and i - 1 >= 0:
                    prev_hash = node.block_hashes[i-1]
                    
                print(b['prev_block_hash'])
                print(prev_hash)
                assert(b['prev_block_hash'] == prev_hash)
            except:
                raise Exception("Chain Corrupted")

            if block_hash.hex() not in node.block_hashes:
                node.block_hashes.append(block_hash.hex())
            file_count += 1
        i += 1
    #for file in os.listdir(os.path.join(chain_directory)):
    #    filename = os.path.join(chain_directory,os.fsdecode(file))
        
    chain_info['file_count'] = file_count
    chain_info['chain_size'] = file_size
    print("Chain size")
    print(chain_info['chain_size'])

    if file_count == 0:
        print("No Chain Info Was Found")


def chain_download():
    print("Loading Chain")
    load_chain()
    global node

    if node == None:
        print("Connecting Peer")
        connect_peer()

    node.download_chain(False)
    while node.chain_size_confirmations < 1:
        if (len(node.peer_services)) < 2:
            if len(node.chain_sizes) > 0:
                node.confirmed_size = max(node.chain_sizes)
                break
        if (len(node.peer_services)) == 0:
            break
        continue

    while chain_info['chain_size'] < node.confirmed_size:
        print("Downloading Chain")
        i = 0
        while os.path.exists(os.path.join(node.chain_directory,"blk%s.pkl" % i)):
            i += 1
        #print("Current Chain Size:", chain_info['chain_size'])
        #print("Requesting File: ", "blk%s.pkl" % i)

        json_message = {"Type":12, "File":"blk%s.pkl" % i}

        node.wait_download = True

        node.broadcast_client_to_server(json.dumps(json_message))

        while node.wait_download:
            continue

        path_exists = os.path.exists(os.path.join(node.chain_directory,"blk%s.pkl" % i))
        while not path_exists:
            path_exists = os.path.exists(os.path.join(node.chain_directory,"blk%s.pkl" % i))
        chain_info['chain_size'] += (os.path.getsize(os.path.join(node.chain_directory,"blk%s.pkl" % i)))
            
    print("Chain Downloaded")
    node.chain_downloaded = True

def block_from_dict(block_data):
    #BLOCK DICT TO BYTES
    block_size = 0

    prev_block_hash = bytes.fromhex(block_data['prev_block_hash']) #32 bytes
    block_size += len(prev_block_hash)

    num_txns_len = bytes([len(bytes([block_data['num_txns']]))]) #LENGTH OF NUM TXNS
    block_size += len(num_txns_len)

    num_txns = bytes([block_data['num_txns']]) #LENGTH GIVEN PREVIOUS
    block_size += len(num_txns)

    target = bytes.fromhex(block_data['target']) #3 bytes
    block_size += len(target)

    nonce = bytes.fromhex(block_data['nonce']) #32 bytes
    block_size += len(nonce)

    txns = bytearray()

    for txn in block_data['txns']:
        txn_id = bytes.fromhex(txn['id'])
        txns += txn_id
        block_size += len(txn_id)

        input_size = bytes([txn['input_size']])
        txns += input_size
        block_size += len(input_size)

        for in_val in txn['inputs']:
            in_address = bytes.fromhex(in_val['address'])
            txns += in_address
            block_size += len(in_address)

            in_val_size = bytes([len(bytes([in_val['value']]))])
            txns += in_val_size
            block_size += len(in_val_size)

            in_val = bytes([in_val['value']])
            txns += in_val
            block_size += len(in_val)

        out_count = 0
        for out_val in txn['outputs']:
            if bool(out_val):
                out_count += 1
                
                out_count_size = bytes([len(bytes([out_count]))])
                txns += out_count_size
                block_size += len(out_count_size)

                txns += bytes([out_count])
                block_size += len(bytes([out_count]))

                prev_txn = bytes.fromhex(out_val['prev_txn'])
                txns += prev_txn
                block_size += len(prev_txn)

                out_address = bytes.fromhex(out_val['address'])
                txns += out_address
                block_size += len(out_address)

                out_val_size = bytes([len(bytes([out_val['value']]))])
                txns += out_val_size
                block_size += len(out_val_size)

                out_value = bytes([out_val['value']])
                txns += out_value
                block_size += len(out_value)

    len_block_size = bytes([len(bytes([block_size]))])

    while len_block_size != bytes([len(bytes([block_size + len(len_block_size)]))]):
        len_block_size = bytes([len(bytes([block_size]))])
    
    block_size += len(len_block_size)

    prev_block_size = block_size

    while block_size != prev_block_size + len(bytes([block_size])):
        block_size += len(bytes([block_size]))

    block_size = bytes([block_size])

    block = prev_block_hash + num_txns_len + num_txns + len_block_size + block_size + target + nonce + txns

    return block

def dict_from_block(block):
    block_data = {}
    ind_count = 0
    block_data['prev_block_hash'] = block[ind_count:ind_count+32].hex()
    ind_count += 32
    block_data
    #print(block_data)

def get_address_balance(address):
    print("Loading Data From Directory")
    address_balance = 0
    global node
    file_count = 0
    file_size = 0
    for file in os.listdir(os.path.join(node.chain_directory)):
        filename = os.path.join(node.chain_directory,os.fsdecode(file))
        if ".pkl" in filename:
            with open(filename, 'rb') as handle:
                b = pickle.load(handle)
                for txn in b['txns']:
                    if (not any(d['address'] == address for d in txn['outputs'])):
                        for output in txn['outputs']:
                            if output['address'] == address.hex():
                                address_balance += output['value']
    return address_balance
                        
                        



def process_commands(command):
    global node
    global wallet
    
    if command == "help":
        print("Commands:")
        print("help: Displays this message")
        print("keygen: Generates Keys")

    elif command == "importkey":
        import_key()

    elif command == "listkeys":
        list_keys()

    elif command == "connect":
        connect_peer()
        chain_download()
        node.update_pool()
        node.key_directory = wallet.key_location
        

    elif command == "listpeers":
        node.listpeers()

    elif command == "download":
        chain_download()

    elif command == "mine":
        chain_download()
        if (node.chain_downloaded == False):
            print("Updating Chain")
            chain_download()
        else:
            node.chain_mine()

    elif command == "readpool":
        node.read_pool()

    elif command == "newblock":
        dict_from_block(block_from_dict(new_block()))

    elif command == "sendtxn":
        if node == None:
            print("Must Connect First")
            return
        address = input("Address: ")
        amount = float(input("Amount: "))
        #"txns":[{"id":base_txn,"input_size":1,"inputs":[{"address":bytearray(32).hex(),"value":reward}],"output_size":1,"outputs":[]}]
        wallet.send_transaction(node, amount, [{"address":address,"value":amount}])

    elif command == "recvtxn":
        key = wallet.recv_transaction()
        print("Address To Send To: ", key.hex())

    
    elif command == "getbalance":

        if node == None:
            print("Must Connect First")
            return
        
        chain_download()
        
        wallet_balance, unconfirmed_balance, usable_balance = wallet.get_wallet_balance(node)
        print("Balance Is: ", wallet_balance)
        print("Unconfirmed Balance Is: ", unconfirmed_balance)
        print("Usable Balance Is: ", usable_balance)
        print("Unused TXNs")
        wallet.list_utxos()

    elif command == "chkeydir":
        wallet.update_key_location(input("Location: "))



def connect_peer():
    initial_port = input("Initial Port: ")
    if initial_port == "":
        initial_port = 2454

    server_port = input("Server Port: ")
    if server_port == "":
        server_port = 2666
    global node
    node = P2PNetNode(int(initial_port),int(server_port))


if __name__ == "__main__":
    #Loop Command Line
    wallet = P2PWallet()
    command = input("Enter Command: ")
    while True:
        process_commands(command)
        command = input("Enter Command: ")
    #gen_key()