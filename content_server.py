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
        self.host = ""
        self.backend_port = 0
        self.peer_count = 0
        self.peers = []
        self.neighbors = {'neighbors': {}}
        
        with open(conf_file_addr, "r") as config_file:
            print("file read:")
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
            self.map = {'map': {self.name : {}}}
            # Print out node details
            print("uuid: " + self.uuid)
            print("name: " + self.name)
            print("backend_end: " + str(self.backend_port))
            print("peer_count: " + str(self.peer_count))
            for i in range(self.peer_count):
                print("peer_" + str(i) + ": " + 
                    self.peers[i]['uuid'] + ", " + 
                    self.peers[i]['host'] + ", " + 
                    str(self.peers[i]['backend_port']) + ", " + 
                    str(self.peers[i]['metric']))
        
        # create maps
        #======================================================================
            
        # create the receive socket
        self.dl_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.dl_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.dl_socket.bind(("", self.backend_port)) #YOU NEED TO READ THIS FROM CONFIGURATION FILE
        self.dl_socket.listen(100)

        # Create all the data structures to store various variables
        # a list of dictionary 
        
        # Extract neighbor information and populate the initial variables
        # Update the map
        # Initialize link state advertisement that repeats using a neighbor variable
        # print("Initial setting complete")
        self.remain_threads = True
        self.alive()
        return
    def addneighbor(self, uuid, host, backend_port, metric):
        # Add neighbor code goes here
        #----------------------------------------------------------------------
        # update map
        peer = {'uuid' : uuid, 
                'host' : host, 
                'backend_port' : int(backend_port), 
                'metric' : int(metric)}
        self.peers.append(peer)
        print("Inside neigbhor func")
        print(self.peers)
        self.link_state_flood(time.time(), host, peer['backend_port'], metric, "Neighbor!")
        #======================================================================
        return
    def link_state_adv(self):
        while self.remain_threads:
        # Perform Link State Advertisement to all your neighbors periodically
        #----------------------------------------------------------------------
        # 
        # send out a message to neighbors that this node is created
        # making a giant string
            for peer in self.peers:
                peer_uuid = peer['uuid']
                peer_host = peer['host']
                peer_port = peer['backend_port']
                peer_metric = peer['metric']
                # send my name to other nodes
                try:
                    soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    soc.connect((peer_host, int(peer_port)))
                    map = json.dumps(self.neighbors)
                    message = f"LSA!|{map}|{self.name}|{self.uuid}"
                    soc.send(message.encode())
                    soc.close()
                except Exception as e:
                    print(f"link_state_adv, {e}")
                    pass
            
            time.sleep(3)
        #======================================================================
        return
    def link_state_flood(self, send_time, host, backend_port, metric, msg):
        # If new information then send to all your neighbors, if old information then drop.
        #---------------------------------
        # send out a message to neighbors that a new node is added
        # send information to neighbors
        try:
            soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            soc.connect((host, int(backend_port)))
            peers = json.dumps(self.peers)
            message = f"{msg}|{peers}|{self.name}|{self.uuid}|{self.host}|{self.backend_port}|{metric}"
            soc.send(message.encode())
        except Exception as e:
            print(f"link_state_flood, {e}")
            pass
        return
    def dead_adv(self, peer):
        # Advertise death before kill
        return
    def dead_flood(self, send_time, host, peer):
        # Forward the death message information to other peers
        return
    def keep_alive(self):
        # Tell that you are alive to all your neighbors, periodically.
        # 
        
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
            elif msg_string.startswith("LSA!"): # Update the timeout time if known node, otherwise add new neighbor
                msg, map, nb_name, nb_uuid = msg_string.split("|", 3)
                # print(nb_name + " is alive!")
                # print(self.peers)
                for peer in self.peers:
                    if nb_uuid == peer['uuid']:
                        self.neighbors['neighbors'][nb_name] = peer
                nb_nodes = list(self.neighbors['neighbors'].keys())
                for node in nb_nodes:
                    self.map['map'][self.name][node] = self.neighbors['neighbors'][node]['metric']

            elif msg_string == "Link State Packet": # Update the map based on new information, drop if old information
            #If new information, also flood to other neighbors
            #Link_state_flood()
                pass
            elif msg_string == "Death message": # Delete the node if it sends the message before executing kill.
                pass
            # otherwise the msg is dropped

            #----------------------------------
            elif msg_string.startswith("Neighbor!"):
                msg, nb_peers, nb_name, nb_uuid, nb_host, nb_port, metric = msg_string.split("|", 6)
                peer = {'uuid' : nb_uuid, 
                        'host' : nb_host, 
                        'backend_port' : int(nb_port), 
                        'metric' : int(metric)}
                self.peers.append(peer)

    def timeout_old(self):
        # drop the neighbors whose information is old
        print("a")
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
        timeout_old.start()
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
                    self.addneighbor(command_line[1][5:], command_line[2][5:], command_line[3][13:], command_line[4][7:])
                except Exception:
                    continue
                # link_state_flood()
                print("add neighbor done")
            elif command == "map":
                # Print Map
                map = json.dumps(self.map)
                print(map)
            elif command == "rank":
                # Compute and print the rank
                print(self.uuid)
if __name__ == "__main__":
    content_sever = Content_server(sys.argv[2])