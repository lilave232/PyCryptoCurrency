import json
import os
from chain.ChainController import *
from chain.Wallet import *
def is_json(myjson):
    try:
        json_object = json.loads(myjson)
    except ValueError as e:
        return False
    return True

def convert_to_obj(msg):
    if is_json(msg):
        msg_object = json.loads(msg)
        return msg_object
    else:
        return False

def parse_client_recvd(node,outgoing_client,msg):
    msg_object = convert_to_obj(msg)
    if msg_object == False:
        print(msg)
        return
    #SERVER SENT CLIENT OTHER POSSIBLE CONNECTIONS
    if 'type' in msg_object and msg_object['type'] == 0:
        node.controller.txn_pool.extend([txn for txn in msg_object['txn_pool'] if txn not in node.controller.txn_pool])
        node.controller.wallet.updateWallet()
        network_connections = [[client.address, client.port] for client in node.clients]
        possible_connections = [server for server in msg_object['network_servers'] if server not in network_connections and (node.server == None or server != [node.server.address,node.server.port])]
        print(possible_connections)
        for connection in possible_connections:
            node.start_client(address=connection[0],port=connection[1])
    #RECEIVE CHAIN SIZE AND DETERMINE WHETHER DOWNLOAD IS NECESSARY
    if 'type' in msg_object and msg_object['type'] == 1:
        node.controller.confirm_chain_size(outgoing_client,msg_object['chain_size'])
    if 'type' in msg_object and msg_object['type'] == 2:
        node.controller.recv_verification(msg_object['block'],msg_object['hash'],msg_object['verified'])
    if 'type' in msg_object and msg_object['type'] == 3:
        node.controller.verify_hash_to_download(msg_object['block'],msg_object['hash'])
    if 'type' in msg_object and msg_object['type'] == 4:
        node.controller.download_block(msg_object['fname'],msg_object['block'],msg_object['hash'])
    if 'type' in msg_object and msg_object['type'] == 5:
        node.controller.recv_target(msg_object['target'])
    if 'type' in msg_object and msg_object['type'] == 6:
        #RESERVED
        pass
    if 'type' in msg_object and msg_object['type'] == 7:
        node.controller.recv_target_confirm(msg_object['target'])
    #BLOCK CONFIRMED
    if 'type' in msg_object and msg_object['type'] == 8:
        node.controller.recv_block_confirm(msg_object['hash'],msg_object['block'])
    #BLOCK ADDED
    if 'type' in msg_object and msg_object['type'] == 9:
        if node.server == None or node.server.connected == False:
            node.lock.acquire()
            if msg_object['hash'] not in node.controller.hashes:
                node.controller.add_block_end(msg_object['block'])
                for txn in msg_object['block']['txns']:
                    if txn in node.controller.txn_pool:
                        node.controller.txn_pool.remove(txn)
            node.lock.release()
    if 'type' in msg_object and msg_object['type'] == 10:
        if node.server == None or node.server.connected == False:
            if msg_object['txn'] not in node.controller.txn_pool:
                node.controller.txn_pool.append(msg_object['txn'])
            node.wallet.updateWallet()
        
    
    



def parse_server_recvd(node, incoming_client, msg):
    msg_object = convert_to_obj(msg)
    if msg_object == False:
        print(msg)
        return
    #CLIENT SENT SERVER CONNECT ADDRESS
    if 'type' in msg_object and msg_object['type'] == 0:
        #print(msg_object)
        try:
            if 'Server_Address' in msg_object:
                node.start_client(address=msg_object['Server_Address'],port=msg_object['Server_Port'])
            network_servers = [(client.address, client.port) for client in node.clients]
            message = {'type':0,'network_servers':network_servers,'txn_pool':node.controller.txn_pool}
            #node.server.write_client(incoming_client,json.dumps(message))
            node.server.broadcast(json.dumps(message))
        except:
            return
    #RECEIVE REQUEST TO SEND CHAIN AND SEND CHAIN SIZE
    if 'type' in msg_object and msg_object['type'] == 1:
        print("Client Requested Chain")
        message = {'type':1,'chain_size':node.controller.get_chain_size()}
        node.server.write_client(incoming_client,json.dumps(message))
    #VERIFY HASH
    if 'type' in msg_object and msg_object['type'] == 2:
        node.controller.index_chain()
        print("Client Requested Confirmation")
        if len(node.controller.hashes) > msg_object['block']:
            message = {'type':2,'block':msg_object['block'],'hash':msg_object['hash'],'verified':msg_object['hash'] == node.controller.hashes[msg_object['block']]}
        else:
            message = {'type':2,'block':msg_object['block'],'hash':msg_object['hash'],'verified':False}
        node.server.write_client(incoming_client,json.dumps(message))
    #REQUESTED BLOCK HASH
    if 'type' in msg_object and msg_object['type'] == 3:
        print("Client Request Block Hash")
        if len(node.controller.hashes) > msg_object['block']:
            message = {'type':3,'block':msg_object['block'],'hash':node.controller.hashes[msg_object['block']]}
            node.server.write_client(incoming_client,json.dumps(message))
        else:
            message = {'type':3,'block':msg_object['block'],'hash':False}
            node.server.write_client(incoming_client,json.dumps(message))
    #REQUEST TO DOWNLOAD
    if 'type' in msg_object and msg_object['type'] == 4:
        print("Client Requested Download")
        blk = node.controller.get_block_hash(msg_object['hash'])
        fname = os.path.basename(node.controller.get_block_file(msg_object['hash']))
        if blk and fname:
            message = {'type':4,'fname':fname,'block':blk,'hash':msg_object['hash']}
            node.server.write_client(incoming_client,json.dumps(message))
    #REQUEST FOR TARGET
    if 'type' in msg_object and msg_object['type'] == 5:
        if node.controller.block_target != None:
            node.server.write_client(incoming_client, json.dumps({'type':5,'target':node.controller.block_target}))
        else:
            node.server.write_client(incoming_client, json.dumps({'type':5,'target':False}))
    #RECEIVE NEW TARGET
    if 'type' in msg_object and msg_object['type'] == 6:
        if node.controller.block_target == None:
            print("Received Target")
            node.controller.block_target = msg_object['target']
            node.controller.confirm_target()
    #CONFIRM TARGET
    if 'type' in msg_object and msg_object['type'] == 7:
        message = {'type':7,'target':node.controller.block_target}
        node.server.write_client(incoming_client, json.dumps(message))
    #CONFIRM BLOCK
    if 'type' in msg_object and msg_object['type'] == 8:
        node.controller.confirm_block(msg_object['block'],msg_object['pubkey'],msg_object['signature'])
    #TRANSACTION RECEIVED
    if 'type' in msg_object and msg_object['type'] == 9:
        node.controller.confirm_txn(msg_object['txn'],msg_object['pubkeys'])
    #TRANSACTION CONFIRMATION RECEIVED
    if 'type' in msg_object and msg_object['type'] == 10:
        node.controller.recv_txn_confirm(msg_object['txnid'],msg_object['txn'])

    

    
