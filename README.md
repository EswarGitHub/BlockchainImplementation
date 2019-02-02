# BlockchainImplementation
  A simple implementation of Blockchain in python


### How to:
  1. Download the .py file into a folder named '*Code*'.
  2. Download .sh file into the folder in which '*Code*' is present.
  3. run .sh file on terminal by following commands one by one with the port number.<br/>
     ``` ./linknodes.sh 5000```<br/>
     ```./linknodes.sh 5001```<br/>
     ```./linknodes.sh 5002```<br/>
     ```./linknodes.sh 5003```<br/>
     (This will create 4 folders, one for each node, with the .py file saved & synchronized among all)
  4. open Code5000 folder in terminal and run the .py file in it with the node number. Keep the **port_number** same as that in the folder name and append -m if you want to start mining at that node. If **port_number** is not specified, the code runs at 5000.
    ```python3 blockchain.py -p <port_number> -m```
  5. Do the same thing with other nodes as well. You will notice that each node shows if the other nodes are running.
  6. Go to ```localhost:5000/blockchain.json``` to check the data at the node. You can verify same data exists across all the nodes.
  
 
### Requirements
  - python3
  - flask
  - requests
  - hashlib<br/>
  ( *if you get a **ModuleNotFound** error, just run* ```pip3 install <module name>``` )
  
  
##### To Do
  - [ ] fix hash errors
