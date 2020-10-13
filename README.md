# PyCurrency
![Alt text](https://github.com/lilave232/PyCurrency/blob/master/PyCurrency.png "Title")
A python project designed to setup a crypto currency network

## Installation

Clone the git repository to your local machine.

Navigate to the cloned directory and install the requirements to be able to run the python3 program.

```python
pip3 install -r requirements.txt 
```
Once the requirements are installed the project is ready to be run.

## Usage

Two methods to run the program, run from empty chain and keys, or existing chain and keys.
To run with empty chain and keys delete the chain1 and chain2 directories plus the keys and keys1 directory.

```bash
python3 Currency_GUI.py
```

The PyCurrency window will open.
In the window type connect and hit submit. The output in the window will be as follows.

```bash
connect
Attempting to Connect...
Chain Downloaded
Mem Pool Updated
Listening on port:2666
Connection Broken
```

Ignore the connection broken message if this is the first PyCurrency instance you have opened.
Next open a second terminal window and run another instance of PyCurrency.

```bash
python3 Currency_GUI.py
```

A second PyCurrency window will open.
In this window type the loadconfig config2.txt and then hit submit. The output will be as follows.

```bash
loadconfig config2.txt
Config Updated: {"Connect Address": "localhost", "Connect Port": 2666, "Server Address": "localhost", "Server Port": 8000, "Connect Server": true, "Chain": "chain2", "Keys": "keys2"}
```

Then in the same window type connect and then hit submit, the output will be as follows.

```bash
connect
Attempting to Connect...
Chain Downloaded
Mem Pool Updated
Listening on port:8000
Client Connected
```

Both clients are now connected to the network.

# Commands

## loadconfig

The program works by utilizing a configuration textfile formatted like a dictionary to determine various initial settings.
In the usage section above we used this command before connecting the second instance. This is because two servers cannot be run with the same Port.
There are several primary settings of these configuration files:

Connect Address: An address used for the peer client to connect to initially so that the network could then send other connection information. (e.g. localhost, 127.0.0.1, 192.168.0.1, etc.)

Connect Port: The port used for the peer client to connect to initially (e.g. 8000, 2666, 7000, etc.)

Server Address: An address to run the server portion of the peer to peer network (e.g. localhost, 127.0.0.1, 192.168.0.1, etc.)

Server Port: The port to run the server portion of the peer to peer network (e.g. 8000, 2666, 7000, etc.)

Connect Server: A boolean to determine whether to setup the server portion or not. If users want to setup a P2P currency outside of their localhost they need to port forward their IP to be able to run a server. If you do not want the hassle of port forwarding just set this to false and it will only run the client side. However, this means you are unable to access some features.

Chain: The directory folder to save the chain files to (note: multiple instances on the same machine should not use the same chain directory or chain may corrupt)

Keys: The directory to store the keys that prove ownership of currency. This is the key location the wallet looks for when determining balances, mining, sending and receiving transactions.

The files config.txt and config2.txt provide examples of configuration files that enable these instances to connect to each other.
Note the connect port and server port of these files are opposite this is because the connect address needs to match the server address of the other instance when 2 instances are running.
If multiple instances are running as long the connect port and connect address is the same as one of the other nodes on the network it will connect to all instances on network.
Note: When running multiple instances on one machine the server port must be unique for each instance, or an "address already in use" error will be raised

To use this command, type loadconfig and then the location of the configuration file. If successful the window will show the updated configuration. Then type connect and click submit to initialize.

```bash
loadconfig config2.txt
```

Note: Only run this command before typing connect. If connect has already been clicked close the window and then close the terminal window and rerun Currency_GUI.py

## listpeers

For alot of the commands to work the functions need to confirmed by at least one other instance of PyCurrency.
To make sure that your instances are connected type listpeers.
The output should look like the following.

```bash
["localhost:8000"]
0
```

There should be a list showing the number of full peers connected to the network. There must be at least one connected peer in the list or the functions will act weird. The number shown on the second line shows the nodes that only act as clients these nodes are unable to mine or confirm network items their functionality is limited to sending, receiving and viewing balances.

## mine
If you started a node from scratch you will have no blocks on the chain. There will be no currency available to send or receive. 
So you will need to mine blocks to the chain. As long as at least two PyCurrency instances are connected you can mine the network.
In one of the open windows type mine and then hit submit.
The output should look like this.

```bash
mine
Chain Downloaded
Mem Pool Updated
Mining
Completed Mining
Block Mined On Chain
```

Now you should have currency in your wallet. The reward issued for mining blocks is set to 20 and set to decrease by half every 10 years.

## getbalance

Now that you have currency you can type getbalance and then hit submit and it will show the balance in your crypto wallet.

```bash
getbalance
Chain Downloaded
Mem Pool Updated
Chain Downloaded
Balance Is: 20.00000000
Unconfirmed Balance Is: 20.00000000
Usable Balance Is: 20.00000000
```

The balance is the actual balance in the wallet. The unconfirmed balance includes any transactions not mined on the chain. The usable balance is the amount of currency that the user can actually use to send transactions.

## recvtxn

Naturally you will want to send currency from one wallet to another. To do that type recvtxn then hit submit, if starting from scratch do this in a window that doesn't already have a balance.
The output should look like this:

```bash 
recvtxn
Address To Send To: eaa7e052706222dbce3acec0461f59b40ac93e2cace2f97c3a33179665d7052b
```

To copy the address double click on the line that says Address To Send To and the address given will be copied.

## sendtxn

To send currency to another wallet. In a window with a wallet that has a usable balance, type the following.

```bash 
sendtxn <address to send to> <amount> <fee (optional)>
e.g.
sendtxn eaa7e052706222dbce3acec0461f59b40ac93e2cace2f97c3a33179665d7052b 10 5
```

There is a minimum fee requirement this is set at 0.17 and increases every 10 years to a maximum of just over 1.
If the fee is not added or the fee added is less than the minimum, the sendtxn command will automatically add the minimum fee to the transactions value, so if you sent 10 the total would be 10.17.
The fee is added to the block and then awarded to the instance of PyCurrency that mined it.
The output of the sendtxn command should be as follows

```bash
sendtxn eaa7e052706222dbce3acec0461f59b40ac93e2cace2f97c3a33179665d7052b 10
Fees will be set to Minimum Fees:0.17
Chain Downloaded
TXN Added to pool
```

Note: For a transaction to be sent successfully at least 2 instances of PyCurrency must be connected. Use listpeers to get available instances if at least one is listed your network is fine.

After entering the send transaction command, if you type getbalance you should notice that the Balance is the same but the Unconfirmed Balance and Usable Balance has now changed.
The Balance, Unconfirmed Balance and Usable Balances will continue to be different until the mine command is run and the transactions are mined on the chain.

## readpool

The readpool command is run to show all of the transactions that are yet to be confirmed by the chain.
After sending a transaction if you want to confirm that it is actually in the pool from any window type readpool and then click submit.
You will should see below.

```bash
{}
[list of transactions]
```

The first dictionary shows the unconfirmed transactions if for example a transaction has not been able to be confirmed by other instances it will sit in that dictionary until the minimum confirmations is met.
The second list will show all the transactions in what is called the "Transaction Pool" these transactions were confirmed by other nodes and are ready to be mined on the chain.
If you are following along check to make sure that there is at least one transaction in the second list.

## clear

The clear command clears the window if it gets to busy and difficult to follow.



