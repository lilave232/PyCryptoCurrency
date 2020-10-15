from cryptography.ecdhcrypto import *
from cryptography.block_helper import *
from cryptography.P2PNetNode import *
from cryptography.P2PNetWallet import *
import time  
import sys, signal

node = None
wallet = None
config = None

configuration = {"Connect Address":"localhost","Connect Port":8000,"Server Address":"localhost","Server Port":2666,"Connect Server":False, "Chain":"chain1", "Keys":"keys"}

if os.path.exists("config.txt"):
    with open("config.txt","r") as f:
        configuration = json.loads(f.read())
else:
    with open("config.txt","w") as f:
        f.write(json.dumps(configuration))
                        

def process_commands(command_entry):
    global node
    global wallet
    global configuration

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

    elif command == "listpeers":

        if node == None:

            print("Must Connect First")

            return

        node.listpeers() #LIST PEERS ON NETWORK

    elif command == "loadconfig":
        
        if os.path.exists(command_values[1]) == False:
            print("Path Does Not Exist")
            return
        
        with open(command_values[1],"r") as f:
            configuration = json.loads(f.read())
        
        print("Config Updated: " + json.dumps(configuration))

    elif command == "readpool":
        if node == None:

            print("Must Connect First")

            return

        node.update_pool()
        node.read_pool() #READ TXNS IN POOL

    elif command == "connect":

        wallet = P2PWallet()
        print("Attempting To Connect...")
        node = P2PNetNode(configuration["Server Address"],configuration["Connect Address"],configuration["Connect Port"],configuration["Server Port"],configuration["Chain"],use_gui=False,connect_server=configuration["Connect Server"])
        node.download_chain()
        node.update_pool()
        wallet.update_key_location(configuration["Keys"])
        node.key_directory = configuration["Keys"]

    elif command == "mine": #MINE THE CHAIN

        if node == None:

            print("Must Connect First")

            return

        node.download_chain() #UPDATE THE CHAIN

        threading.Thread(target=node.chain_mine).start() #MINE THE CHAIN


    elif command == "sendtxn": #SEND TRANSACTION

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
                node.print("Fees Will Be Set To Mininum Fees:{0}".format(minimum_fees))
                fees = minimum_fees
        else:
            node.print("Fees Will Be Set To Mininum Fees:{0}".format(minimum_fees))
            fees = minimum_fees

        wallet.send_transaction(node, amount, [{"address":address,"value":amount}],fees) #SEND THE TRANSACTION


    elif command == "recvtxn":
        
        if node == None:

            print("Must Connect First")

            return

        key = wallet.recv_transaction() #OBTAIN ADDRESS OF WHERE SOMEONE WILL SEND TRANSACTION

        print("Address To Send To: {0}".format(key.hex())) #SHOW USER ADDRESS

    
    elif command == "getbalance":

        if node == None:

            print("Must Connect First")

            return
        
        node.download_chain() #DOWNLOAD THE CHAIN

        node.update_pool()
        
        wallet_balance, unconfirmed_balance, usable_balance = wallet.get_wallet_balance(node) #GET BALANCES

        print("Balance Is: {:.8f}".format(wallet_balance)) #PRINT WALLET BALANCE

        print("Unconfirmed Balance Is: {:.8f}".format(unconfirmed_balance)) #PRINT UNCONFIRMED BALANCE

        print("Usable Balance Is: {:.8f}".format(usable_balance)) #PRINT USABLE BALANCE

        wallet.list_utxos(node) #PRINT UTXOS
    elif command == "loopmine":
        if node == None:

            print("Must Connect First")

            return

        node.download_chain() #UPDATE THE CHAIN

        threading.Thread(target=node.chain_mine,args=(True,True)).start() #MINE THE CHAIN

def signal_handler(signal, frame):
        print("\nprogram exiting gracefully")
        sys.exit(0)    



if __name__ == "__main__":

    signal.signal(signal.SIGINT, signal_handler)
    #Loop Command Line
    wallet = P2PWallet()
    command = input("Enter Command: ")
    while True:
        process_commands(command)
        command = input("Enter Command: ")
    #gen_key()