import hashlib
import os
import json
import datetime as date
from flask import Flask,request, jsonify
import glob
import requests
import sys
import apscheduler
import argparse

import logging
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

from apscheduler.schedulers.background import BackgroundScheduler
sched = BackgroundScheduler(standalone=True)














CHAINDATA_DIR = 'chaindata/'
BROADCASTED_BLOCK_DIR = CHAINDATA_DIR + 'bblocs/'
NUM_ZEROS = 0

STANDARD_ROUNDS = 100000

PEERS = [
    'http://localhost:5000/',
    'http://localhost:5001/',
    'http://localhost:5002/',
    'http://localhost:5003/',
    ]

BLOCK_VAR_CONVERSIONS = {'index': int, 'nonce': int, 'hash': str, 'prev_hash': str, 'timestamp': str}



node = Flask(__name__)













def dict_from_block_attributes(**kwargs):
	info = {}
	for key in kwargs:
		if key in BLOCK_VAR_CONVERSIONS:
	  		info[key] = BLOCK_VAR_CONVERSIONS[key](kwargs[key])
		else:
	  		info[key] = kwargs[key]
	return info



def create_new_block_from_prev(prev_block=None, data=None, timestamp=None):
	if not prev_block:
		index = 0
		prev_hash = ''
	else:
		index = int(prev_block.index) + 1
		prev_hash = prev_block.hash

	if not data:
		filename = '%sdata.txt' % (CHAINDATA_DIR)
		with open(filename, 'r') as data_file:
	  		data = data_file.read()

	if not timestamp:
		timestamp = date.datetime.utcnow().strftime('%Y%m%d%H%M%S%f')

	nonce = 0
	block_info_dict = dict_from_block_attributes(index=index, timestamp=timestamp, data=data, prev_hash=prev_hash, nonce=nonce)
	new_block = Block(block_info_dict)
	return new_block

def create_first_block():
    block_data = {}
    block_data['index'] = 0
    block_data['timestamp'] = date.datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
    block_data['data'] = 'First block data'
    block_data['prev_hash'] = ''
    block_data['nonce'] = 0
    return Block(block_data)


def sync(save=True):
    return sync_overall(save=save)


def sync_local():
    blocks = []
    if os.path.exists(CHAINDATA_DIR):
        for filepath in glob.glob(os.path.join(CHAINDATA_DIR, '*.json')):
            with open(filepath, 'r') as block_file:
                try:
                    block_info = json.load(block_file)
                except:
                    print(filepath)
                local_block = Block(block_info)
                blocks.append(local_block)
    blocks.sort(key=lambda block: block.index)
    #print(blocks)
    local_chain = Chain(blocks)
    return local_chain

def sync_overall(save=True):
    best_chain = sync_local()
    for peer in PEERS:
        peer_blockchain_url = peer + 'blockchain.json'
        try:
            print('Inside1')
            r = requests.get(peer_blockchain_url)
            print('Inside2')
            peer_blockchain_dict = r.json()
            peer_blocks = [Block(bdict) for bdict in peer_blockchain_dict]
            peer_chain = Chain(peer_blocks)
            print('Inside1')
            print(peer_chain.is_valid())
            if peer_chain.is_valid() and len(peer_chain) > len(best_chain):
                best_chain = peer_chain
                print('lksdvnlirhbvnrin')

        except requests.exceptions.ConnectionError:
            print("Peer at %s not running. Continuing to next peer." % peer)
        else:
            print("Peer at %s is running. Gathered their blochchain for analysis." % peer)
    print("Longest blockchain is %s blocks" % len(best_chain))
    if save:
        best_chain.self_save()
    return best_chain



def mine_for_block(chain=None, rounds=STANDARD_ROUNDS, start_nonce=0, timestamp=None):
	if not chain:
		chain = sync_local()
	prev_block = chain.most_recent_block()
	return mine_from_prev_block(prev_block, rounds=rounds, start_nonce=start_nonce, timestamp=timestamp)


def mine_from_prev_block(prev_block, rounds=STANDARD_ROUNDS, start_nonce=0, timestamp=None):
	new_block = create_new_block_from_prev(prev_block=prev_block, timestamp=timestamp)
	return mine_block(new_block, rounds=rounds, start_nonce=start_nonce)

def mine_block(new_block, rounds=STANDARD_ROUNDS, start_nonce=0):
	print("Mining for block %s. start_nonce: %s, rounds: %s" % (new_block.index, start_nonce, rounds))
	nonce_range = [i+start_nonce for i in range(rounds)]
	for nonce in nonce_range:
		new_block.nonce = nonce
		new_block.create_self_hash()
		if str(new_block.hash[0:NUM_ZEROS]) == '0' * NUM_ZEROS:
			print("block %s mined. Nonce: %s" % (new_block.index, new_block.nonce))
			assert new_block.is_valid()
			return new_block, rounds, start_nonce, new_block.timestamp

	return None, rounds, start_nonce, new_block.timestamp



def mine_for_block_listener(event):
	if event.job_id == 'mining':
		new_block, rounds, start_nonce, timestamp = event.retval
	if new_block:
		print("Mined a new block")
		new_block.self_save()
		broadcast_mined_block(new_block)
		sched.add_job(mine_from_prev_block, args=[new_block], kwargs={'rounds':STANDARD_ROUNDS, 'start_nonce':0}, id='mining') #add the block again
	else:
	  print(event.retval)
	  sched.add_job(mine_for_block, kwargs={'rounds':rounds, 'start_nonce':start_nonce+rounds, 'timestamp': timestamp}, id='mining') #add the block again
	sched.print_jobs()


def broadcast_mined_block(new_block):
	block_info_dict = new_block.to_dict()
	for peer in PEERS:
		endpoint = "%s%s" % (peer[0], peer[1])
		try:
			r = requests.post(peer+'mined', json=block_info_dict)
		except requests.exceptions.ConnectionError:
			print("Peer %s not connected" % peer)
			continue
	return True


def validate_possible_block(possible_block_dict):
	possible_block = Block(possible_block_dict)
	if possible_block.is_valid():
		possible_block.self_save()
		sched.print_jobs()
		try:
			sched.remove_job('mining')
			print("removed running mine job in validating possible block")
		except apscheduler.jobstores.base.JobLookupError:
			print("mining job didn't exist when validating possible block")

		print("readding mine for block validating_possible_block")
		print(sched)
		print(sched.get_jobs())
		sched.add_job(mine_for_block, kwargs={'rounds':STANDARD_ROUNDS, 'start_nonce':0}, id='mining')
		print(sched.get_jobs())
		return True
	return False












@node.route('/blockchain.json', methods=['GET'])
def blockchain():
    local_chain = sync_local()
    json_blocks = json.dumps(local_chain.block_list_dict())
    return json_blocks


@node.route('/mined', methods=['POST'])
def mined():
	possible_block_dict = request.get_json()
	print(possible_block_dict)
	print(sched.get_jobs())
	print(sched)

	sched.add_job(validate_possible_block, args=[possible_block_dict], id='validate_possible_block') #add the block again

	return jsonify(received=True)











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
        self.create_self_hash()
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
                print('index error')
                return False
            if not cur_block.is_valid():
                print(cur_block.index)
                print('Block error')
                return False
            if prev_block.hash != cur_block.prev_hash:
                print('hash error')
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




















if __name__ == '__main__':

    

    parser = argparse.ArgumentParser(description='JBC Node')
    parser.add_argument('--port', '-p', default='5000', help='what port we will run the node on')
    parser.add_argument('--mine', '-m', dest='mine', action='store_true')
    args = parser.parse_args()

    chaindata_dir = 'chaindata/'
    if not os.path.exists(chaindata_dir):
        os.mkdir(chaindata_dir)

    node_blocks = sync(True)

    if os.listdir(chaindata_dir) == []:
        first_block = create_first_block()
        first_block.self_save()



    filename = '%sdata.txt' % (CHAINDATA_DIR)
    with open(filename, 'w') as data_file:
        data_file.write("Mined by node on port %s" % args.port)


    
    if args.mine:
        sched.add_job(mine_for_block, kwargs={'rounds':STANDARD_ROUNDS, 'start_nonce':0}, id='mining')
        sched.add_listener(mine_for_block_listener, apscheduler.events.EVENT_JOB_EXECUTED)
    
    sched.start()
    node.run(host='127.0.0.1', port=args.port)
