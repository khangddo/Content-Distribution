import socket, sys
import ast
import threading, time
import random

import uuid
import json
import time

BUFSIZE = 1024 # size of receiving buffer
ALIVE_SGN_INTERVAL = 0.5 # interval to send alive signal
TIMEOUT_INTERVAL = 10*ALIVE_SGN_INTERVAL
UPSTREAM_PORT_NUMBER = 1111 # socket number for UL transmission

##
#
# FOR TRANSMITTING PACKET USE THE FOLLOWING CODE
#
#self.ul_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#try:
# self.ul_socket.connect((host, backend_port))
# self.ul_socket.send(("STRING TO SEND").encode())
# self.ul_socket.close()
#except socket.error:
# pass
#
#
#
#
class Content_server():
    def __init__(self, conf_file_addr):
        # load and read configuration file
        # ---------------------------------------------------------------------
        self.uuid = ""
        self.name = ""
        self.backend_port = 0
        self.peer_count = 0

        self.peers_passive = []
        self.peers_active = []
        self.known_peers = []
        self.neighbors = {'neighbors': {}}
        self.rank = {'rank': {}}
        # name tracking
        self.uuid_to_name = {self.uuid: self.name}
        self.name_to_uuid = {self.name: self.uuid}

        self.link_state = {} # stores complete network
        self.link_state_seq = {} # trakcs LSA sequence numbers
        self.last_seen = {} # neighbor tracking
        self.lock = threading.Lock()

        self.remain_threads = True
        
        # Extract neighbor information and populate the initial variables
        with open(conf_file_addr, "r") as config_file:
            for line in config_file:
                line = line.strip()
                if line:
                    if (line.split()[0] == 'uuid'):
                        self.uuid = line.split()[2]
                    elif (line.split()[0] == 'name'):
                        self.name = line.split()[2]
                    elif (line.split()[0] == 'backend_port'):
                        backend_port = line.split()[2]  
                        self.backend_port = int(backend_port)
                    elif (line.split()[0] == 'peer_count'):
                        peer_count = line.split()[2]
                        self.peer_count = int(peer_count)
                    else:
                        peer = {'uuid' : line.split()[2][:-1], 
                                'host' : line.split()[3][:-1], 
                                'backend_port' : int(line.split()[4][:-1]), 
                                'metric' : int(line.split()[5])}
                        self.peers_passive.append(peer)
            self.known_peers.extend(self.peers_passive)
            # Initialize network map with entries
            self.map = {'map': {self.name : {}}}
            self.link_state[self.name] = {}
            self.link_state_seq[self.name] = 0

        #======================================================================
            
        # create the receive socket
        self.dl_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.dl_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.dl_socket.bind(('', self.backend_port)) #YOU NEED TO READ THIS FROM CONFIGURATION FILE
        self.dl_socket.listen(100)
        
        # Initialize link state advertisement that repeats using a neighbor variable
        self.alive()
        print("Initial setting complete")
        return
    def addneighbor(self, uuid, host, backend_port, metric):
        # Add neighbor code goes here
        #----------------------------------------------------------------------
        if nb_uuid != self.uuid:
            nb_uuid = uuid
            nb_host = host
            nb_backend_port = int(backend_port)
            nb_metric = int(metric)

            with self.lock:
                if any(peer['uuid'] == nb_uuid for peer in self.peers_active):
                    print(f"Already neighbor")
                    return
                
                peer = {'uuid' : nb_uuid, 
                        'host' : nb_host, 
                        'backend_port' : nb_backend_port, 
                        'metric' : nb_metric}

                self.peers_passive.append(peer)
                self.known_peers.append(peer)

        #======================================================================
        return
    def link_state_adv(self):
        while self.remain_threads:
        # Perform Link State Advertisement to all your neighbors periodically
        #----------------------------------------------------------------------
        # 
        # send out a message to neighbors that this node is created
        # making a giant string

            my_neighbors = {}

            for uuid, data in self.neighbors['neighbors'].items():
                name = self.uuid_to_name.get(uuid, uuid)
                my_neighbors[name] = data['metric']

            packet = {'name': self.name,
                      'uuid': self.uuid,
                      'seq': self.link_state_seq[self.name],
                      'neighbors': my_neighbors}
            
            self.link_state_seq[self.name] += 1

            message = f"LSA!|{json.dumps(packet)}"

            for peer in self.peers_active:
                soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                try:
                    soc.connect((peer['host'], int(peer['backend_port'])))
                    soc.send(message.encode())
                    soc.close()
                except socket.error:
                    pass

            self.link_state_flood('0')
            time.sleep(3)
        #======================================================================
        return
    def link_state_flood(self, new_uuid):
        # If new information then send to all your neighbors, if old information then drop.
        #---------------------------------
        # send out a message to neighbors that a new node is added
        # send information to neighbors
        message = f"Map!|{json.dumps(self.map)}"
        for peer in self.peers_active:
            if peer['uuid'] != new_uuid:
                soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                try:
                    soc.connect((peer['host'], int(peer['backend_port'])))
                    soc.send(message.encode())
                    soc.close()
                except socket.error:
                    pass
            
    def dead_adv(self):
        # Advertise death before kill
        for peer in self.peers_active:
            message = f"Bye!|{self.name}|{self.uuid}|{self.backend_port}|{peer['metric']}"
            soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                soc.connect((peer['host'], int(peer['backend_port'])))
                soc.send(message.encode())
                soc.close()
            except socket.error:
                pass

    def dead_flood(self, message):
        # Forward the death message information to other peers
        for peer in self.peers_active:
            if peer['uuid'] != self.uuid:
                soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                try:
                    soc.connect((peer['host'], int(peer['backend_port'])))
                    soc.send(message.encode())
                    soc.close()
                except socket.error:
                    pass
    
    def keep_alive(self):
        # Tell that you are alive to all your neighbors, periodically.
        message = f"ALIVE|{self.name}|{self.uuid}"
        while self.remain_threads:
            for peer in self.known_peers:
                soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                try:
                    soc.connect((peer['host'], int(peer['backend_port'])))
                    soc.send(message.encode())
                    soc.close()
                except socket.error:
                    pass
            time.sleep(ALIVE_SGN_INTERVAL)

    ## THIS IS THE RECEIVE FUNCTION THAT IS RECEIVING THE PACKETS
    def listen(self):
        self.dl_socket.settimeout(0.1) # for killing the application
        while self.remain_threads:
            try:
                connection_socket, client_address = self.dl_socket.accept()
                msg_string = connection_socket.recv(BUFSIZE).decode()
                # print("received", connection_socket, client_address, msg_string)

            except socket.timeout:
                msg_string = ""
                pass

            if msg_string == "": # empty message
                pass

            elif msg_string.startswith("ALIVE"): # Update the timeout time if known node, otherwise add new neighbor
                # all nodes added will go into passive peers until AlIVE messsage is received from that node
                msg, nb_name, nb_uuid = msg_string.split("|", 2)
                for pas_peer in self.peers_passive:
                    if pas_peer['uuid'] == nb_uuid:
                        # update name mappings
                        self.uuid_to_name[nb_uuid] = nb_name
                        self.name_to_uuid[nb_name] = nb_uuid
                        # udpate active peers
                        self.peers_active.append(pas_peer)
                        # update neighbors
                        self.neighbors['neighbors'][nb_name] = pas_peer
                        # update map with name
                        self.map['map'][self.name][nb_name] = pas_peer['metric']
                        # update passive peers
                        self.peers_passive.remove(pas_peer)
                    break

                self.last_seen[nb_name] = time.time()

            elif msg_string.startswith("LSA!"): # Update the map based on new information, drop if old information
            #If new information, also flood to other neighbors
                msg, packet = msg_string.split("|", 1)
                packet = json.loads(packet)

                if packet['uuid'] not in self.uuid_to_name:
                    self.uuid_to_name[packet['uuid']] = packet['name']
                    self.name_to_uuid[packet['name']] = packet['uuid']
                
                # update map structure
                if packet['name'] not in self.map['map']:
                    self.map['map'][packet['name']] = {}

                # update neighbors in map
                if packet['uuid'] in self.neighbors['neighbors']:
                    peer_info = self.neighbors['neighbors'][packet['uuid']]
                    del self.neighbors['neighbors'][packet['uuid']]
                    self.neighbors['neighbors'][packet['name']] = peer_info

                for nb_name, metric in packet['neighbors'].items():
                    self.map['map'][packet['name']][nb_name] = metric

            elif msg_string.startswith("Bye!"): # Delete the node if it sends the message before executing kill.
            # otherwise the msg is dropped
                msg, nb_name, nb_uuid, nb_port, nb_metric = msg_string.split("|", 4)
                # remove from peers
                pas_peer = {'uuid' : nb_uuid, 
                            'host' : '127.0.0.1', 
                            'backend_port' : int(nb_port), 
                            'metric' : int(nb_metric)}
                
                if pas_peer in self.peers_active:
                    self.peers_passive.append(pas_peer)
                    self.peers_active.remove(pas_peer)
                    # name tracking
                    del self.uuid_to_name[nb_uuid]
                    del self.name_to_uuid[nb_name]
                # print(f"self.peers after remove: {self.peers}")

                # remove form neighbors and map
                if nb_name in self.neighbors['neighbors']:
                    del self.neighbors['neighbors'][nb_name]
                # print(f"neighbors: {self.neighbors}")
                
                if nb_name in self.map['map']:
                    del self.map['map'][nb_name]
                for node in self.map['map']:
                    if nb_name in self.map['map'][node]:
                        del self.map['map'][node][nb_name]
                #print(f"map: {self.map}")

                self.dead_flood(msg_string)

            elif msg_string.startswith("Map!"):
                msg, nb_map = msg_string.split("|", 1)
                map = json.loads(nb_map)
                #print(f"recieved map from neighbor {map}")
                for node, neighbors in map['map'].items():
                    #print(f"node from recieved map: {map['map'][node]}")
                    if node not in self.neighbors['neighbors']:
                        if node in self.map['map'] and self.map['map'][node] != neighbors:
                            del self.map['map'][node]

                        if node not in self.map['map']:
                            self.map['map'][node] = map['map'][node]
            #----------------------------------
            
    def timeout_old(self):
        # drop the neighbors whose information is old
        while self.remain_threads:
            rn = time.time()
            remove_list = []
            for name, peer in self.neighbors['neighbors'].items():
                l = self.last_seen.get(name, 0)
                if rn - l > TIMEOUT_INTERVAL:
                    remove_list.append(name)
                    self.peers.remove(peer)
            for name in remove_list:
                #print(f"Timeout: removing neighbor {name}")
                del self.neighbors['neighbors'][name]
                if name in self.map['map'][self.name]:
                    del self.map['map'][self.name][name]
            
            time.sleep(ALIVE_SGN_INTERVAL)

    def shortest_path(self):
        # derive the shortest path according to the current link state
        rank = {}
        return rank
    def alive(self):
        keep_alive = threading.Thread(target=self.keep_alive) # A thread that keeps sending keep_alive messages
        listen = threading.Thread(target=self.listen) # A thread that keeps listening to incoming packets
        timeout_old = threading.Thread(target=self.timeout_old) # A thread to eliminate old neighbors
        link_state_adv = threading.Thread(target=self.link_state_adv) # A thread that keeps doing link_state_adv
        keep_alive.start()
        listen.start()
        #timeout_old.start()
        link_state_adv.start()
        while self.remain_threads:
            time.sleep(ALIVE_SGN_INTERVAL) # wait for the network to settle
            command_line = input().split(" ")
            command = command_line[0]
            if len(command_line) > 1:
                content = command_line[1:]
            # print("Received command: ", command)
            if command == "kill":
                # Send death message
                # Kill all threads
                self.dead_adv()
                self.remain_threads = False
                self.dl_socket.close()
            elif command == "uuid":
                # Print UUID
                print("{\"uuid\": \"" + str(self.uuid) + "\"}")
            elif command == "neighbors":
                # Print Neighbor information
                neighbors = json.dumps(self.neighbors)
                print(neighbors)
            elif command == "addneighbor":
                # Update Neighbor List with new neighbor
                self.addneighbor(command_line[1][5:], command_line[2][5:], command_line[3][13:], command_line[4][7:])
            elif command == "map":
                # # Print Map
                map = json.dumps(self.map)
                print(map)
            elif command == "rank":
                # Compute and print the rank
                rank = json.dumps(self.rank)
                print(rank)
if __name__ == "__main__":
    content_sever = Content_server(sys.argv[2])