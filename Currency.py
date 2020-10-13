from cryptography.ecdhcrypto import *
from cryptography.block_helper import *
from cryptography.P2PNetNode import *
from cryptography.P2PNetWallet import *
import time        
                        

def process_commands(command):
    global node
    global wallet
    
    if command == "help":
        print("Commands:")
        print("help: Displays this message")
        print("keygen: Generates Keys")

    elif command == "connect":

        connect_peer() #CONNECT PEER TO NETWORK

        time.sleep(1) #SLEEP MAIN THREAD TO ALLOW NODE TO FINISH CONNECTING

        node.download_chain() #REQUEST NODE TO DOWNLOAD CHAIN

        node.update_pool() #UPDATE THE MEMORY POOL

        node.key_directory = wallet.key_location #SET THE KEY DIRECTORY
        

    elif command == "listpeers":

        if node == None:

            print("Must Connect First")

            return

        node.listpeers() #LIST PEERS ON NETWORK

    elif command == "mine": #MINE THE CHAIN

        if node == None:

            print("Must Connect First")

            return

        node.download_chain() #UPDATE THE CHAIN

        node.chain_mine() #MINE THE CHAIN


    elif command == "readpool":

        node.read_pool() #READ TXNS IN POOL


    elif command == "sendtxn": #SEND TRANSACTION

        if node == None:

            print("Must Connect First")

            return

        address = input("Address: ") #ASK USER FOR ADDRESS TO SEND FUNDS

        amount = float(input("Amount: ")) #ASK USER THE AMOUNT TO SEND

        
        wallet.send_transaction(node, amount, [{"address":address,"value":amount}]) #SEND THE TRANSACTION


    elif command == "recvtxn":

        key = wallet.recv_transaction() #OBTAIN ADDRESS OF WHERE SOMEONE WILL SEND TRANSACTION

        print("Address To Send To: ", key.hex()) #SHOW USER ADDRESS

    
    elif command == "getbalance":

        if node == None:

            print("Must Connect First")

            return
        
        node.download_chain() #DOWNLOAD THE CHAIN
        
        wallet_balance, unconfirmed_balance, usable_balance = wallet.get_wallet_balance(node) #GET BALANCES

        print("Balance Is: ", wallet_balance) #PRINT WALLET BALANCE

        print("Unconfirmed Balance Is: ", unconfirmed_balance) #PRINT UNCONFIRMED BALANCE

        print("Usable Balance Is: ", usable_balance) #PRINT USABLE BALANCE

        print("Unused TXNs") #PRINT UNUSED TXNS

        wallet.list_utxos() #PRINT UTXOS

    elif command == "chkeydir":

        wallet.update_key_location(input("Location: ")) #CHANGE DIRECTORY WALLET KEYS ARE STORED



def connect_peer():
    initial_port = input("Initial Port: ")

    if initial_port == "":

        initial_port = 2454

    server_port = input("Server Port: ")

    if server_port == "":

        server_port = 2666
    
    chain_dir = input("Chain Directory: ")

    global node

    node = P2PNetNode(int(initial_port),int(server_port),chain_dir)


if __name__ == "__main__":
    #Loop Command Line
    wallet = P2PWallet()
    command = input("Enter Command: ")
    while True:
        process_commands(command)
        command = input("Enter Command: ")
    #gen_key()