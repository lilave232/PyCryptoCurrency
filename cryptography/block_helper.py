from cryptography.ecdhcrypto import *
import os
import json
import uuid
from shutil import copyfile

import socket
import sys
import pickle

import threading

import time

import select

import errno

node = None

chain_info = {}
import time

import random

def gen_coinbase_txn(hash):

    reward = int(20 * (1/max(int(2*(time.time() - 1577836800)/315360000),1))) #REWARD CALCULATION VALUE OF REWARD SHOULD HALVE EVERY 10 YEARS

    txid = uuid.uuid4().hex #GENERATE TX ID FOR COINBASE TXN

    #GENERATE TXN MOST IF BASIC EXCEPT OUTPUT IS WRITTEN TO MINERS HASH
    txn = {"txnid":txid,"time":int(time.time()),"inputs":[{"prev_txid":bytearray(16).hex(),"prev_txn_output":0,"sig_prev_out":bytearray(64).hex()}],"outputs":[{"address":hash.hex(),"value":reward}]}
    
    return txn

def get_txn(txnid,directory):

    for file in os.listdir(os.path.join(directory)): #LOOK FOR FILES IN DIRECTORY

        filename = os.path.join(directory,os.fsdecode(file)) #GET FILENAME
        
        if ".pkl" in filename: #LOOK SPECIFICALLY FOR PKL FILES

            with open(filename, 'r') as handle: #OPEN FILE FOR READING

                b = json.load(handle) #LOAD PICKLE DATA

                for txn in b['txns']: #FOR TXN IN TXNS

                    if txn['txnid'] == txnid: # LOOK FOR TXNID

                        return txn #RETURN TRANSACTION

    return False #IF TRANSACTION COULD NOT BE FOUND RETURN FALSE

def gen_txn(output_addresses, input_addresses, total_value, fees):

    txid = uuid.uuid4().hex #GENERATE ID

    inputs = [] #SETUP INPUTS USED

    in_value = 0 #GET TOTAL IN VALUE

    for value in input_addresses: #SEARCH THROUGH INPUT ADDRESSES

        signature = sign_msg(bytes.fromhex(value['Address']),priv_key_from_string(value['PrivKey'])) #GENERATE SIGNATURE SIGNING ADDRESS WITH PRIVATEKEY

        input_value = {"prev_txid":value['TxID'],"prev_txn_output":value['Output'],"sign_prev_out":signature} #SETUP INPUT

        inputs.append(input_value) #APPEND INPUT TO INPUTS

        in_value += value['Value'] #ADD VALUE TO IN VALUE

        print("Inputs", {"PrevTXID":value['TxID'],"Address:":value['Address'],"Value":value['Value']})
    
    out_value = 0 #SETUP OUT VALUE

    for value in output_addresses: #FOR VALUE IN OUT VALUE

        out_value += value['value'] #ADD VALUE TO OUT VALUE

        print("Outputs", {"Address:":value['address'],"Value":value['value']})

    if in_value > out_value: #DETERMINE IF IN VALUE GREATER THAN OUT VALUE AND RETURN CHANGE TO FIRST INPUT ADDRESS PROVIDED

        output_addresses.append({"address":input_addresses[0]['Address'],"value":(in_value-out_value-fees)}) #GENERATE OUTPUTS

        print({"address":input_addresses[0]['Address'],"value":(in_value-out_value-fees)})

        print("Fees: ", fees)

    txn = {"txnid":txid,"time":int(time.time()),"inputs":inputs,"outputs":output_addresses} #BUILD TRANSACTION
    
    return txn #RETURN TXN

def hash_block_dict(block): #HASH BLOCK

    return hash_block(json.dumps(block).encode()) #TAKE BLOCK DICT AND CONVERT TO HASH VALUE

def save_block(dir,block): #SAVE NEW BLOCK

    i = 0 #SETUP COUNTER

    while os.path.exists(os.path.join(dir,"blk%s.pkl" % i)): #LOOP THROUGH TO GET NEXT BLOCK FILE NAME

        i += 1 #INCREMENT COUNTER

    with open(os.path.join(dir,"blk%s.pkl" % i), 'w') as handle: #OPEN FILE FOR WRITING

        json.dump(block, handle)

        #pickle.dump(block, handle) #SAVE BLOCK

def gen_block(pubKeyHash, prev_block_hash,node): #GENERATE BLOCK
    
    time_val = int(time.time()) #SETUP TIME VALUE FOR FIRST MINING ATTEMPT

    nonce = random.randint(0,4294967295) #SETUP FIRST NONCE VALUE
    nonce = nonce.to_bytes(4, byteorder = 'big').hex() #CONVERT NONCE INT TO HEX


    coinbase_txn = gen_coinbase_txn(pubKeyHash)

    txns = [] #CREATE TXN ARRAY

    txns.append(coinbase_txn) #APPEND COINBASE TXN

    txns.extend(node.txn_pool) #EXTEND ARRAY TO INCLUDE TXNS

    blocks = {"prev_block_hash":prev_block_hash,"time":time_val,"target":node.node_target,"nonce":nonce,"txns":txns} #SETUP BLOCK FORMAT

    block_in_value = 0
    block_out_value = 0

    for x,txn in enumerate(blocks['txns']):

        if x == 0:

            continue

        for x, input_val in enumerate(txn['inputs']):

            prev_txn = get_txn(input_val['prev_txid'],node.chain_directory) #GET PREVIOUS TXN

            if prev_txn == False: #IF THEIR IS NO PREVIOUS TXN ERROR REACHED

                return False
            
            block_in_value += prev_txn['outputs'][input_val['prev_txn_output']]['value']

        for x, output_val in enumerate(txn['outputs']): #FOR OUTPUT IN TRANSACTION

            block_out_value += output_val['value'] #INCREMENT TOTAL OUTPUT VALUE
        
    
    blocks['txns'][0]['outputs'][0]['value'] += block_in_value - block_out_value  

    block_hash = hash_block_dict(blocks) #HASH BLOCK

    node.print("Mining")

    while block_hash > (bytes.fromhex(blocks['target']) + bytearray(28)): #CHECK IF HASH IS BELOW TARGET LOOP UNTIL HASH IS BELOW TARGET

        #print("Mining")

        if node.block_added == True:

            return False

        blocks['target'] = node.node_target

        print(bytes.fromhex(blocks['target']) + bytearray(28))

        blocks['txns'] = [] #CREATE TXN ARRAY

        coinbase_txn = gen_coinbase_txn(pubKeyHash)

        blocks['txns'].append(coinbase_txn) #APPEND COINBASE TXN

        blocks['txns'].extend(node.txn_pool) #EXTEND ARRAY TO INCLUDE TXNS

        block_in_value = 0
        block_out_value = 0

        for x,txn in enumerate(blocks['txns']):

            if x == 0:

                continue

            for x, input_val in enumerate(txn['inputs']):

                prev_txn = get_txn(input_val['prev_txid'],node.chain_directory) #GET PREVIOUS TXN

                if prev_txn == False: #IF THEIR IS NO PREVIOUS TXN ERROR REACHED

                    return False
                
                block_in_value += prev_txn['outputs'][input_val['prev_txn_output']]['value']

            for x, output_val in enumerate(txn['outputs']): #FOR OUTPUT IN TRANSACTION

                block_out_value += output_val['value'] #INCREMENT TOTAL OUTPUT VALUE
            
        
        blocks['txns'][0]['outputs'][0]['value'] += (block_in_value - block_out_value)

        nonce = random.randint(0,4294967295) #GET RANDOM NONCE VALUE

        nonce = nonce.to_bytes(4, byteorder = 'big').hex() #CONVERT RANDOM VALUE TO 4 BYTE INTEGER

        blocks['nonce'] = nonce #SET NONCE VALUE

        blocks['time'] = int(time.time()) #SET TIME TO REFLECT MORE RECENT MINE TIME

        block_hash = hash_block_dict(blocks) #HASH BLOCK

    node.print("Completed Mining")

    return blocks #RETURN BLOCK