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
        self.peers = []
        self.neighbors = {'neighbors': {}}

        self.link_state = {} # stores complete network
        self.link_state_seq = {} # trakcs LSA sequence numbers
        self.last_seen = {} # neighbor tracking
        self.lock = threading.Lock()

        # name tracking
        self.uuid_to_name = {self.uuid: self.name}
        self.name_to_uuid = {self.name: self.uuid}

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
                        backend_port= line.split()[2]  
                        self.backend_port = int(backend_port)
                    elif (line.split()[0] == 'peer_count'):
                        peer_count = line.split()[2]  
                        self.peer_count = int(peer_count)
                    else:
                        peer = {'uuid' : line.split()[2][:-1], 
                                'host' : line.split()[3][:-1], 
                                'backend_port' : line.split()[4][:-1], 
                                'metric' : line.split()[5]}
                        self.peers.append(peer)

            # Initialize network map with entries
            self.map = {'map': {self.name : {}}}
            self.link_state[self.name] = {}
            self.link_state_seq[self.name] = 0

            for peer in self.peers:
                self.uuid_to_name[peer['uuid']] = None
                self.map['map'][self.name][peer['uuid']] = peer['metric']

            # Update the map
            # Initialize neighbor relationships
            # for peer in self.peers:
            #     self.map['map'][self.name][peer['uuid']] = peer['metric']
            #     self.neighbors['neighbors'][peer['uuid']] = peer
            
                # Print out node details
            print("uuid: " + self.uuid)
            print("name: " + self.name)
            print("backend_port: " + str(self.backend_port))
            print("peer_count: " + str(self.peer_count))
            for i in range(self.peer_count):
                print(f"peer_{i}: {self.peers[i]['uuid']}, {self.peers[i]['host']}, "
                    f"{self.peers[i]['backend_port']}, {self.peers[i]['metric']}")

        #======================================================================
            
        # create the receive socket
        self.dl_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.dl_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.dl_socket.bind(("", self.backend_port)) #YOU NEED TO READ THIS FROM CONFIGURATION FILE
        self.dl_socket.listen(100)
        
        # Initialize link state advertisement that repeats using a neighbor variable
        self.alive()
        print("Initial setting complete")
        return
    def addneighbor(self, uuid, host, backend_port, metric):
        # Add neighbor code goes here
        #----------------------------------------------------------------------
        # Validate host
        if host == 'localhost':
            host = '127.0.0.1'

        # update map
        if not any(peer['uuid'] == uuid for peer in self.peers):
            peer = {'uuid' : uuid, 
                    'host' : host, 
                    'backend_port' : int(backend_port), 
                    'metric' : int(metric)}
            self.peers.append(peer)

            self.map['map'][self.name][uuid] = int(metric)
            self.neighbors['neighbors'][uuid] = peer
            self.uuid_to_name[uuid] = None

            print("before sending message to new neighbor")

            msg = f"Neighbor!|{self.name}|{self.uuid}|{self.backend_port}|{metric}"

            self.link_state_flood(host, peer['backend_port'], msg)
            print("after sending message to new neighbor")
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

            for peer in self.peers:
                try:
                    soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    soc.connect((peer['host'], int(peer['backend_port'])))
                    soc.send(message.encode())
                    soc.close()
                except Exception as e:
                    print(f"LSA send error to {peer['backend_port']}, {e}")
                    pass
            
            time.sleep(3)
        #======================================================================
        return
    def link_state_flood(self, host, port, msg):
        # If new information then send to all your neighbors, if old information then drop.
        #---------------------------------
        # send out a message to neighbors that a new node is added
        # send information to neighbors
        try:
            soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            soc.settimeout(2)
            try:
                soc.connect((host, int(port)))
                soc.send(msg.encode())
            except (socket.timeout, ConnectionRefusedError) as e:
                print(f"Failed to flood to {host}:{port}, {e}")
        except Exception as e:
            print(f"Socket creatrion error: {e}")
            
        # return
    def dead_adv(self, peers):
        # Advertise death before kill
        for peer in peers:
            try:
                soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                soc.connect((peer['host'], int(peer['backend_port'])))
                message = f"Bye!|{self.name}|{self.uuid}"
                soc.send(message.encode())
                soc.close()
            except Exception as e:
                print(f"dead_adv, {e}")
                pass
        return
    def dead_flood(self, send_time, host, peer):
        # Forward the death message information to other peers
        return
    def keep_alive(self):
        # Tell that you are alive to all your neighbors, periodically.
        while self.remain_threads:
            for peer in self.peers.copy():
                try:
                    soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    soc.settimeout(2)
                    try:
                        soc.connect((peer['host'], int(peer['backend_port'])))
                        message = f"ALIVE|{self.name}|{self.uuid}"
                        soc.send(message.encode())
                    except (socket.timeout, ConnectionRefusedError) as e:
                        print(f"Keep_alive(self) failed to {peer['backend_port']} {peer['host']}: {e}")
                    except Exception as e:
                        print(f"Unexpected keep_alive error: {e}")
                    # soc.close()
                except Exception as e:
                    print(f"Socket creation error in keep_alive: {e}")
            time.sleep(ALIVE_SGN_INTERVAL)
        return
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
                msg, nb_name, nb_uuid = msg_string.split("|", 2)

                # update name mappings
                self.uuid_to_name[nb_uuid] = nb_name
                self.name_to_uuid[nb_name] = nb_uuid

                for peer in self.peers:
                    if nb_uuid == peer['uuid']:
                        self.neighbors['neighbors'][nb_name] = peer
                        # update map with name
                        if nb_uuid in self.map['map'][self.name]:
                            del self.map['map'][self.name][nb_uuid]
                            self.map['map'][self.name][nb_name] = peer['metric']
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
                for nb_name, metric in packet['neighbors'].items():
                    self.map['map'][packet['name']][nb_name] = metric

                # forward to other peers (flooding)
                for peer in self.peers:
                    if peer['uuid'] != packet['uuid']:
                        self.link_state_flood(peer['host'], peer['backend_port'], msg_string)
                pass
            elif msg_string.startswith("Bye!"): # Delete the node if it sends the message before executing kill.
            # otherwise the msg is dropped
                msg, nb_name, nb_uuid = msg_string.split("|", 2)
                # remove from peers
                new_peers = []
                for peer in self.peers:
                    if peer['uuid'] != nb_uuid:
                        new_peers.append(peer)
                self.peers = new_peers

                # remove form neighbors and map
                if nb_name in self.neighbors['neighbors']:
                    del self.neighbors['neighbors'][nb_name]
                if nb_name in self.map['map']:
                    del self.map['map'][nb_name]

                for node in self.map['map']:
                    if nb_name in self.map['map'][node]:
                        del self.map['map'][node][nb_name]
                pass

            elif msg_string.startswith("Neighbor!"):
                try:
                    print("New neighbor!")
                    msg, nb_name, nb_uuid, nb_port, nb_metric = msg_string.split("|", 4)

                    nb_host = client_address[0]

                    peer = {'uuid' : nb_uuid, 
                            'host' : nb_host, 
                            'backend_port' : int(nb_port), 
                            'metric' : int(nb_metric)}
                    
                    with self.lock:
                        self.peers = [p for p in self.peers if p['uuid'] != nb_uuid]
                        self.peers.append(peer)
                        self.map['map'][self.name][nb_name] = peer['metric']
                        self.neighbors['neighbors'][nb_name] = peer
                        self.uuid_to_name[nb_uuid] = nb_name
                        self.name_to_uuid[nb_name] = nb_uuid
            
                        print(f"Added neighbor: {nb_name} ({nb_uuid}) at {nb_host}:{nb_port}")

                except Exception as e:
                    print(f"Error processing Neighbor message: {e}")
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
                print(f"Timeout: removing neighbor {name}")
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
            print("Received command: ", command)
            if command == "kill":
                # Send death message
                # Kill all threads
                print("Shutting down...")
                self.dead_adv(self.peers)
                self.remain_threads = False
                self.dl_socket.close()
                print("Node is dead!")
            elif command == "uuid":
                # Print UUID
                print("{\"uuid\": \"" + str(self.uuid) + "\"}")
            elif command == "neighbors":
                # Print Neighbor information
                neighbors = json.dumps(self.neighbors)
                print(neighbors)
            elif command == "addneighbor":
                # Update Neighbor List with new neighbor
                print("add neighbor begin")
                try:
                    print("in")
                    self.addneighbor(command_line[1][5:], command_line[2][5:], command_line[3][13:], command_line[4][7:])
                    print("out")
                except Exception as e:
                    print(f"{e}")
                print("add neighbor done")
            elif command == "map":
                # Print Map
                map_print = {'map':{}}
                for node, neighbors in self.map['map'].items():
                    map_print['map'][node] = {}
                    for neighbor, metric in neighbors.items():
                        name = self.uuid_to_name.get(neighbor, neighbor)
                        map_print['map'][node][name] = metric
                map = json.dumps(map_print)
                print(map)
            elif command == "rank":
                # Compute and print the rank
                print(self.uuid)
if __name__ == "__main__":
    content_sever = Content_server(sys.argv[2])