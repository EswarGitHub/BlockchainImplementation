import hashlib
import os
import json
import datetime as date
from flask import Flask
import glob
import requests
import sys



CHAINDATA_DIR = 'chaindata/'
BROADCASTED_BLOCK_DIR = CHAINDATA_DIR + 'bblocs/'
NUM_ZEROS = 5

PEERS = [
    'http://localhost:5000/',
    'http://localhost:5001/',
    'http://localhost:5002/',
    'http://localhost:5003/',
    ]

BLOCK_VAR_CONVERSIONS = {'index': int, 'nonce': int, 'hash': str, 'prev_hash': str, 'timestamp': str}



node = Flask(__name__)


def sync(save=False):
    return sync_overall(save=save)

def create_first_block():
    block_data = {}
    block_data['index'] = 0
    block_data['timestamp'] = date.datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
    block_data['data'] = 'First block data'
    block_data['prev_hash'] = ''
    block_data['nonce'] = 0
    return Block(block_data)



def is_valid_chain():
    for b in blockchain:
        if not b.is_valid():
            return False
    return True



def sync_local():
    local_chain = Chain([])
    if os.path.exists(CHAINDATA_DIR):
        for filepath in glob.glob(os.path.join(CHAINDATA_DIR, '*.json')):
            with open(filepath, 'r') as block_file:
                try:
                    block_info = json.load(block_file)
                except:
                    print(filepath)
                local_block = Block(block_info)
                local_chain.add_block(local_block)
    return local_chain

def sync_overall(save=False):
    best_chain = sync_local()
    for peer in PEERS:
        peer_blockchain_url = peer + 'blockchain.json'
        try:
            r = requests.get(peer_blockchain_url)
            peer_blockchain_dict = r.json()
            peer_blocks = [Block(bdict) for bdict in peer_blockchain_dict]
            peer_chain = Chain(peer_blocks)

            if peer_chain.is_valid() and peer_chain > best_chain:
                best_chain = peer_chain

        except requests.exceptions.ConnectionError:
            print("Peer at %s not running. Continuing to next peer." % peer)
        else:
            print("Peer at %s is running. Gathered their blochchain for analysis." % peer)
    print("Longest blockchain is %s blocks" % len(best_chain))
    if save:
        best_chain.self_save()
    return best_chain





def calculate_hash(index, prev_hash, data, timestamp, nonce):
    header_string = generate_header(index, prev_hash, data, timestamp, nonce)
    sha = hashlib.sha256()
    sha.update(header_string)
    return sha.hexdigest()


def mine(last_block):
    index = int(last_block.index) + 1
    timestamp = date.datetime.now()
    data = "I block #%s" % (int(last_block.index) + 1)
    prev_hash = last_block.hash
    nonce = 0

    block_hash = calculate_hash(index, prev_hash, data, timestamp, nonce)
    while str(block_hash[0:NUM_ZEROS]) != '0' * NUM_ZEROS:
        nonce += 1
        block_hash = calculate_hash(index, prev_hash, data, timestamp, nonce)
    
    block_data = {}
    block_data['index'] = index
    block_data['prev_hash'] = last_block.hash
    block_data['timestamp'] = timestamp
    block_data['data'] = "Gimme %s dollars" % index
    block_data['hash'] = block_hash
    block_data['nonce'] = nonce
    return Block(block_data)





@node.route('/blockchain.json', methods=['GET'])
def blockchain():
    local_chain = sync_local()
    json_blocks = json.dumps(local_chain.block_list_dict())
    return json_blocks



class Block(object):
    def __init__(self, dictionary):
        for key, value in dictionary.items():
            if key in BLOCK_VAR_CONVERSIONS:
                setattr(self, key, BLOCK_VAR_CONVERSIONS[key](value))
            else:
                setattr(self, key, value)

        if not hasattr(self, 'nonce'):
            self.nonce = 'None'
        if not hasattr(self, 'hash'):
            self.hash = self.create_self_hash()

    def header_string(self):
        return str(self.index) + self.prev_hash + self.data + str(self.timestamp) + str(self.nonce)

    def generate_header(index, prev_hash, data, timestamp, nonce):
        return str(index) + prev_hash + data + str(timestamp) + str(nonce)

    def create_self_hash(self):
        sha = hashlib.sha256()
        sha.update(self.header_string().encode('utf-8'))
        return sha.hexdigest()

    def self_save(self):
        chaindata_dir = 'chaindata'
        index_string = str(self.index).zfill(6)
        filename = '%s/%s.json' % (chaindata_dir, index_string)
        with open(filename, 'w') as block_file:
            json.dump(self.to_dict(), block_file)

    def to_dict(self):
        info = {}
        info['index'] = str(self.index)
        info['timestamp'] = str(self.timestamp)
        info['prev_hash'] = str(self.prev_hash)
        info['hash'] = str(self.hash)
        info['data'] = str(self.data)
        info['nonce'] = str(self.nonce)
        return info

    def is_valid(self):
        self.update_self_hash()
        if str(self.hash[0:NUM_ZEROS]) == '0' * NUM_ZEROS:
            return True
        else:
            return False

    def __repr__(self):
        return "Block<index: %s>, <hash: %s>" % (self.index, self.hash)

    def __eq__(self, other):
        return (self.index == other.index and self.timestamp == other.timestamp and self.prev_hash == other.prev_hash
                and self.hash == other.hash and self.data == other.data and self.nonce == other.nonce)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __gt__(self, other):
        return self.timestamp < other.timestamp

    def __lt__(self, other):
        return self.timestamp > other.timestamp

class Chain(object):
    def __init__(self, blocks):
        self.blocks = blocks

    def is_valid(self):
        for index, cur_block in enumerate(self.blocks[1:]):
            prev_block = self.blocks[index]
            if prev_block.index+1 != cur_block.index:
                return False
            if not cur_block.is_valid():
                return False
            if prev_block.hash != cur_block.prev_hash:
                return False
        return True

    def self_save(self):
        for b in self.blocks:
            b.self_save()
        return True

    def find_block_by_index(self, index):
        if len(self) <= index:
            return self.blocks[index]
        else:
            return False

    def find_block_by_hash(self, hash):
        for b in self.blocks:
            if b.hash == hash:
                return b
        return False

    def __len__(self):
        return len(self.blocks)

    def __eq__(self, other):
        if len(self) != len(other):
            return False
        for self_block, other_block in zip(self.blocks, other.blocks):
            if self_block != other_block:
                return False
        return True

    def __ne__(self, other):
        return not self.__eq__(other)

    def __gt__(self, other):
        return len(self.blocks) > len(other.blocks)

    def __lt__(self, other):
        return len(self.blocks) < len(other.blocks)

    def __ge__(self, other):
        return self.__eq__(other) or self.__gt__(other)

    def __le__(self, other):
        return self.__eq__(other) or self.__lt__(other)

    def most_recent_block(self):
        return self.blocks[-1]

    def max_index(self):
        return self.blocks[-1].index

    def add_block(self, new_block):
        self.blocks.append(new_block)
        return True

    def block_list_dict(self):
        return [b.to_dict() for b in self.blocks]


node_blocks = sync()


if __name__ == '__main__':
	print('In here')
	chaindata_dir = 'chaindata/'
	if not os.path.exists(chaindata_dir):
	    os.mkdir(chaindata_dir)
	if os.listdir(chaindata_dir) == []:
	    first_block = create_first_block()
	    first_block.self_save()

	if len(sys.argv) >= 2:
		port = sys.argv[1]
	else:
		port = 5000
	node.run(host='127.0.0.1', port=port)
