import tkinter as tk
from tkmacosx import Button
from cryptography.ecdhcrypto import *
from cryptography.block_helper import *
from cryptography.P2PNetNode import *
from cryptography.P2PNetWallet import *
from tkinter import filedialog

import os

import threading


node = None
wallet = None
connect_server = False
config = None

configuration = {"Connect Address":"localhost","Connect Port":8000,"Server Address":"localhost","Server Port":2666,"Connect Server":False, "Chain":"chain1", "Keys":"keys"}

if os.path.exists("config.txt"):
    with open("config.txt","r") as f:
        configuration = json.loads(f.read())
else:
    with open("config.txt","w") as f:
        f.write(json.dumps(configuration))
        

window = tk.Tk()

def listbox_copy(event):
    window.clipboard_clear()
    selected = listbox.get(tk.ANCHOR)
    if "Address To Send To: " in selected:
        selected = selected.replace("Address To Send To: ","")
    window.clipboard_append(selected)


frame_3 = tk.Frame()
listbox = tk.Listbox(master=frame_3)
listbox.pack(fill=tk.BOTH, side=tk.LEFT, expand=True)
listbox.bind('<Double-Button-1>', listbox_copy)

def command_click(event):
    global node
    global wallet
    global configuration
    command = command_entry.get().split(" ")[0]

    listbox.insert(tk.END,command_entry.get())
    listbox.itemconfig(tk.END,foreground="red")
    
    command_values = command_entry.get().split(" ")

    if command == "listpeers":

        if node == None:

                listbox.insert(tk.END,"Must Connect First")

                return

        node.listpeers() #LIST PEERS ON NETWORK

    elif command == "help":
        listbox.insert(tk.END,"Available Commands:")
        listbox.insert(tk.END,"connect: Connects to P2PNet")
        listbox.insert(tk.END,"loadconfig <filename>: Loads connect configuration file")
        listbox.insert(tk.END,"listpeers: List connected peers on network")
        listbox.insert(tk.END,"readpool: Shows pool of unconfirmed transactions")
        listbox.insert(tk.END,"clear: Clears window")
        listbox.insert(tk.END,"mine: Attempts to mine block onto chain")
        listbox.insert(tk.END,"sendtxn <address_to_send_to amount fee>: Sends transaction to an address for the specified amount and fees. Fees must be greater than minimum")
        listbox.insert(tk.END,"recvtxn: Generates address to receive transactions from, double click address to copy")
        listbox.insert(tk.END,"getbalance: Gets the wallet balance")

    elif command == "loadconfig":
        
        if os.path.exists(command_values[1]) == False:
            listbox.insert(tk.END,"Path Does Not Exist")
            print("Path Does Not Exist")
            return
        
        with open(command_values[1],"r") as f:
            configuration = json.loads(f.read())
        
        listbox.insert(tk.END,"Config Updated: " + json.dumps(configuration))
        listbox.itemconfig(tk.END,foreground="blue")


    elif command == "connect":
        wallet = P2PWallet()
        listbox.insert(tk.END, "Attempting To Connect...")
        node = P2PNetNode(configuration["Server Address"],configuration["Connect Address"],configuration["Connect Port"],configuration["Server Port"],configuration["Chain"],use_gui=True,listbox = listbox, connect_server=configuration["Connect Server"])
        node.download_chain()
        node.update_pool()
        wallet.update_key_location(configuration["Keys"])
        node.key_directory = configuration["Keys"]


    elif command == "readpool":
        if node == None:

            listbox.insert(tk.END,"Must Connect First")

            return

        node.update_pool()
        node.read_pool() #READ TXNS IN POOL
    
    elif command == "clear":
        listbox.delete(0, tk.END)

    elif command == "mine": #MINE THE CHAIN

        if node == None:

            listbox.insert(tk.END,"Must Connect First")

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

        print(minimum_fees)

        
        if (len(command_values) > 3):
            fees = float(command_values[3])
            print(minimum_fees)
            print(fees)
            if fees < minimum_fees:
                node.print("Fees Will Be Set To Mininum Fees:{0}".format(minimum_fees))
                fees = minimum_fees
        else:
            node.print("Fees Will Be Set To Mininum Fees:{0}".format(minimum_fees))
            fees = minimum_fees

        wallet.send_transaction(node, amount, [{"address":address,"value":amount}],fees) #SEND THE TRANSACTION
    
    elif command == "recvtxn":
        if node == None:

            listbox.insert(tk.END,"Must Connect First")

            return

        key = wallet.recv_transaction() #OBTAIN ADDRESS OF WHERE SOMEONE WILL SEND TRANSACTION

        listbox.insert(tk.END,"Address To Send To: {0}".format(key.hex())) #SHOW USER ADDRESS
    
    elif command == "getbalance":

        if node == None:

            listbox.insert(tk.END,"Must Connect First")

            return
        
        node.download_chain() #DOWNLOAD THE CHAIN

        node.update_pool()
        
        wallet_balance, unconfirmed_balance, usable_balance = wallet.get_wallet_balance(node) #GET BALANCES

        listbox.insert(tk.END,"Balance Is: {:.8f}".format(wallet_balance)) #PRINT WALLET BALANCE

        listbox.insert(tk.END,"Unconfirmed Balance Is: {:.8f}".format(unconfirmed_balance)) #PRINT UNCONFIRMED BALANCE

        listbox.insert(tk.END,"Usable Balance Is: {:.8f}".format(usable_balance)) #PRINT USABLE BALANCE

        #listbox.insert(tk.END,"Unused TXNs") #PRINT UNUSED TXNS

        #wallet.list_utxos(node) #PRINT UTXOS
    
    command_entry.delete(0,tk.END)


frame_bottom = tk.Frame()

command_entry = tk.Entry(master=frame_bottom)

command_entry.pack(fill=tk.X, side = tk.LEFT,  expand=True)

command_submit = Button(master=frame_bottom,text="Submit")

command_submit.pack()

command_submit.bind("<Button-1>", command_click)




#frame_top.pack()

#frame_2.pack(fill=tk.BOTH)

frame_3.pack(fill=tk.BOTH, expand = True)

frame_bottom.pack(fill=tk.X)

window.mainloop()