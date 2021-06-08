# ![Alt text](https://github.com/lilave232/PyCurrency/blob/master/PyCurrency.png "Title")
A python project designed to setup a blockchain based crypto currency network

## Installation

Clone the git repository to your local machine.

```bash
git clone https://github.com/lilave232/PyCryptoCurrency.git
```

Navigate to the cloned directory and install the requirements to be able to run the python3 program.

```python
pip3 install -r requirements.txt 
```
Once the requirements are installed the project is ready to be run.

## Usage

```bash
python3 main.py
```

This will start the PyCurrency command line.
Type start server and it will start a server at the default port (4444) and set the address to connect to as localhost. 

If you would like to set a connect address and port type start server address port. Providing the address and port (i.e. start server 127.0.0.1 4444)

```bash
Enter Command: start server localhost 4444
Listening on port:4444
Enter Command:

or 

Enter Command: start server
Listening on port:4444
Enter Command:
```

To test the network on your local machine open a second terminal window and run another instance of PyCurrency.

```bash
python3 main.py
```

A second PyCurrency terminal will start.
In this window type start server localhost 5555 (Note: you can enter any valid address or port). The output will be as follows. 

Note: Ensure when trying to start your server for external connections you must setup port forwarding there are many articles on how to do this online.

```bash
Enter Command: start server localhost 5555
Listening on port:5555
Enter Command:
```

In the same window type start client or if you changed the default in the first window type start client address port and then hit Enter, the output will be as follows.

```bash
Enter Command: start client

or 

Enter Command: start client localhost 4444
```

Both clients are now connected to the network. You can check this by running the listpeers command in either of the windows.

```bash
Enter Command: listpeers
Incoming: 127.0.0.1:51751
Outgoing: localhost:5555
```

to be able to mine blocks without error you need to have both nodes need to have different chain directories. The default node directory is the blockchain directory. To change connect to a different directory in one of the windows type the below replacing "directory" with the directory of the chain.

```bash
Enter Command: setchain directory
Enter Command:
```

To be able access all functions and approve blocks you must download the chain. To do that type download and the node will do three things
1. Request the size of the chain from the other connected nodes once >50% of nodes confirm value it will proceed (If confirmed size is 0 chain is verified and downloaded).
2. Ask nodes to confirm the hash of the existing blocks on the chain.
3. Once existing hashes are confirmed it will download the remaining blocks if necessary.

If starting with two empty chain directories the output would be like below.

```bash
Enter Command: download
Enter Command: Confirmed Size: 0
Chain Has No Blocks. Chain Downloaded
```

Type download into both of the terminals you created and hit enter to bring up the Enter Command again.

Now that your chain has been confirmed, you can start mining. To mine type mine in the command line and enter.

```bash
Enter Command: mine
Started Mining: 23:32:35
Enter Command: Waiting For Target
Target Acquired
Setting Target
Target Set: 000002d1ac54
Asking To Confirm 000002d1ac54
Confirming Target
Target Confirm Received
000002d1ac54
000002d1ac54
Target Confirmed
Building Block
Mining
```

Once the node finds the block it will add the first block to the chain!!


# Commands

## listpeers

For alot of the commands to work the functions need to confirmed by at least one other instance of PyCurrency with a verified and complete chain.
To make sure that your instances are connected type listpeers.
The output should look like the following.
Incoming peers are other clients connected to your server.
Outgoing peers are your clients connected to other servers.

```bash
Enter Command: listpeers
Incoming: 127.0.0.1:51816
Outgoing: localhost:4444
Enter Command:
```

There must be at least one connected peer with the chain downloaded or many functions will be unavailable.

## setchain

The setchain command sets the directory where the chain files will exist the default is in blockchain directory.

```bash
Enter Command: setchain directory
Enter Command:
```

## setwallet

The setwallet command sets the directory where your keys will be stored this directory will contain all private keys that connect to your coins. Without these keys you will not have access to your coins. The default directory is KeyStores/keys

```bash
Enter Command: setwallet keys
Enter Command:
```

## mine
If you started a node from scratch you will have no blocks on the chain. There will be no currency available to send or receive. 
So you will need to mine blocks to the chain. As long as at least two PyCurrency instances are connected you can mine the network.
Type mine and then hit enter.
The output should look like this.

```bash
Enter Command: mine
Started Mining: 23:32:35
Enter Command: Waiting For Target
Target Acquired
Setting Target
Target Set: 000002d1ac54
Asking To Confirm 000002d1ac54
Confirming Target
Target Confirm Received
000002d1ac54
000002d1ac54
Target Confirmed
Building Block
Mining
```

## loopmine
Executes the same functions as mine but instead of halting after one block is mined it loops and attempts to mine the next block unitl stopmine is called.

## stopmine
Exits the mine loop, this will leave the loop once the next block is mined.

## startlog
Shows the log of mining statistics.

## stoplog
Hides the log of mining statistics. If log is showing Command Line will not show this command when typed, however if you just type and hit enter it will execute.

## getbalance

Now that you have currency you can type getbalance and then hit submit and it will show the balance in your crypto wallet.

```bash
Enter Command: getbalance
CONFIRMED BALANCE: 5285.0
5285.0
```

The balance is the actual confirmed and usable balance in the wallet.

## recvtxn

Naturally you will want to send currency from one wallet to another. To do that type recvtxn then hit submit, if starting from scratch do this in a window that doesn't already have a balance.
The output should look like this:

```bash 
recvtxn
Address To Send To: eaa7e052706222dbce3acec0461f59b40ac93e2cace2f97c3a33179665d7052b
```

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
Enter Command: sendtxn 28dee342801f2101f1d3fe9b3d596600c9077a51628fabb5a0bbe591550cd63f 10 5
CONFIRMED BALANCE: 5285.0
Inputs {'PrevTXID': '3c1e98afbce649e485c1059d4f379026', 'Address:': '62c2636a5136a8381ad647223936011c7e888b6f95231ef10429e61602769cc8', 'Value': 7.83}
Inputs {'PrevTXID': '4f2e6849aee24258b9a7397b120713b2', 'Address:': '1dd6b38cf4f315f3e17849a766ab0bef8a43d7924b2b253902776e0a62748eb2', 'Value': 120.0}
Outputs {'Address:': '28dee342801f2101f1d3fe9b3d596600c9077a51628fabb5a0bbe591550cd63f', 'Value': 10.0}
{'address': '62c2636a5136a8381ad647223936011c7e888b6f95231ef10429e61602769cc8', 'value': 112.83}
Fees:  5.0
```

Note: For a transaction to be sent successfully >50% of instances of PyCurrency must be connected. Use listpeers to get available instances if at least one is listed your network is fine. One the connected nodes confirm the transaction it will be added to the pool.

## mempool

The mempool command is run to show all of the transactions that are yet to be confirmed by the chain.
After sending a transaction if you want to confirm that it is actually in the pool from any window type readpool and then click submit.
You will should see below.

```bash
Enter Command: mempool
[list of transactions]
```

The list will show all the transactions in what is called the "Transaction Pool" these transactions were confirmed by other nodes and are ready to be mined on the chain.
