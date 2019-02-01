import datetime
import hashlib
import os
import json
from flask import Flask


node = Flask(__name__)


@node.route('/blockchain.json', methods=['GET'])
def blockchain():
    node_blocks = sync()
    python_blocks = []
    
    for block in node_blocks:
        python_blocks.append(block.__str__())
    
    json_blocks = json.dumps(python_blocks)
    
    return json_blocks



class Block:
    blockNo = 0
    data = None
    next = None
    hash = None
    nonce = 0
    previous_hash = 0x0
    timestamp = datetime.datetime.now()

    def __init__(self, data):
        self.data = data

    def hash(self):
        h = hashlib.sha256()
        h.update(
        str(self.nonce).encode('utf-8') +
        str(self.data).encode('utf-8') +
        str(self.previous_hash).encode('utf-8') +
        str(self.timestamp).encode('utf-8') +
        str(self.blockNo).encode('utf-8')
        )
        return h.hexdigest()

    def __str__(self):
        return "Block Hash: " + str(self.hash()) + "\nBlockNo: " + str(self.blockNo) + "\nBlock Data: " + str(self.data) + "\nHashes: " + str(self.nonce) + "\n--------------"

    def self_save(self):
    blockchainData = 'chaindata'
    index_string = str(self.blockNo).zfill(6)
    filename = '%s/%s.json' % (blockchainData, index_string)
    with open(filename, 'w') as block_file:
        json.dump(self.__str__(), block_file)


def create_first_block():
    block = Block("Genesis")
    return block

def sync():

    node_blocks = []
    blockchainData = 'chaindata'

    if os.path.exists(blockchainData):
        for filename in os.listdir(blockchainData):
            if filename.endswith('.json'):
                filepath = '%s/%s' % (blockchainData, filename)
                with open(filepath, 'r') as block_file:
                    block_info = json.load(block_file)
                    block_object = Block(block_info)
                    node_blocks.append(block_object)
    
    return node_blocks

class Blockchain:

    diff = 20
    maxNonce = 2**32
    target = 2 ** (256-diff)

    block = Block("Genesis")
    dummy = head = block

    def add(self, block):

        block.previous_hash = self.block.hash()
        block.blockNo = self.block.blockNo + 1

        self.block.next = block
        self.block = self.block.next

    def mine(self, block):
        for n in range(self.maxNonce):
            if int(block.hash(), 16) <= self.target:
                self.add(block)
                print(block)
                break
            else:
                block.nonce += 1

blockchain = Blockchain()

for n in range(10):
    blockchain.mine(Block("Block " + str(n+1)))

while blockchain.head != None:
    print(blockchain.head)
    blockchain.head = blockchain.head.next

if __name__ == '__main__':
    blockchainData = 'chaindata/'
    if not os.path.exists(blockchainData):
        os.mkdir(blockchainData)

    if os.listdir(blockchainData) == []:
        first_block = create_first_block()
        first_block.self_save()

    node.run()
