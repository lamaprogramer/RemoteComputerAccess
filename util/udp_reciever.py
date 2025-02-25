from util import udp_packet
from typing import Tuple

import multiprocessing.managers
import multiprocessing.synchronize
import multiprocessing, socket, random, queue, time, threading
import asyncio


class UDPReciever:
  def __init__(self, 
    address, 
    max_packet_size,
    packet_keep_ratio=1/3, # Ratio at which packets are kept vs. dropped.
    collector_count=1,     # How many packet collectors will be active
    processor_count=1,     # How many packet processors will be active
  ):
    # Socket Info
    self.max_packet_size = max_packet_size
    self.address = address
    self.running = True
    
    self.packet_keep_ratio = packet_keep_ratio
    
    # Data Storage
    self.manager = multiprocessing.Manager()
    self.whitelisted_packet_ids = self.manager.list()
    
    self.packets = self.manager.dict()
    self.packet_chunks = self.manager.Queue(maxsize=500)
    self.complete_packets = self.manager.Queue(maxsize=10)
    
    #self.loop = asyncio.get_running_loop()
    #self.loop.create_datagram_endpoint
    
    # Create Processes
    self._processing_thread_count = processor_count
    self._processing_lock = multiprocessing.Lock()
    self._processing_threads = []
    for i in range(self._processing_thread_count):
      self._processing_threads.append(
        multiprocessing.Process(
          target=self._process, 
          args=(
            self.packets, 
            self._processing_lock, 
            self.whitelisted_packet_ids, 
            self.packet_chunks, 
            self.complete_packets
          ), 
          daemon=True
        )
      )
    
    self._collection_thread_count = collector_count
    self._collection_lock = threading.Lock()
    self._collection_threads = []
    for i in range(self._collection_thread_count):
      self._collection_threads.append(
        threading.Thread(
          target=self._collect, 
          args=(
            self.address, 
            self.whitelisted_packet_ids, 
            self.packet_chunks, 
            self.complete_packets, 
            self.max_packet_size
          ), 
          daemon=True
        )
      )
    
  
  def start(self):
    for i in self._collection_threads:
      i.start()
    for i in self._processing_threads:
      i.start()
  
  def recive(self):
    try:
      return self.complete_packets.get(block=False)
    except queue.Empty:
      return None
  
  def stop(self):
    self.running = False
    for i in self._collection_threads:
      i.join()
    
    for i in self._processing_threads:
      i.join()
    
  @staticmethod
  def _collect(
      addr:                   Tuple[str, int], 
      whitelisted_packet_ids: multiprocessing.managers.ListProxy, 
      packet_chunks:          queue.Queue, 
      complete_packets:       queue.Queue, 
      max_packet_size:        int
    ):
    try:
      sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
      sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
      sock.bind(addr)
      
      while True:
        try:
          if packet_chunks.full() or complete_packets.full():
            continue
          
          packet, address = sock.recvfrom(max_packet_size)
          if packet is None:
            print("packet is none")
            continue
          
          loss_ratio = 1/1
          packet_id, sequence_id = udp_packet.unpackSequence(packet)
          
          if packet_id not in whitelisted_packet_ids:
            if random.random() < loss_ratio:
              whitelisted_packet_ids.append(packet_id)
              packet_chunks.put((packet, packet_id, sequence_id))
          else:
            packet_chunks.put((packet, packet_id, sequence_id))

        except queue.Full:
          continue
        
    except Exception as e:
      raise e
  
  @staticmethod
  def _process(
      packets:                multiprocessing.managers.DictProxy, 
      processing_lock:        multiprocessing.synchronize.Lock, 
      whitelisted_packet_ids: multiprocessing.managers.ListProxy, 
      packet_chunks:          queue.Queue, 
      complete_packets:       queue.Queue
    ):
    try:
      while True:
        if packet_chunks.empty() or complete_packets.full():
          continue
        
        packet, packet_id, sequence_id = packet_chunks.get()
        #print(packet_id)
        
        with processing_lock:
          # If packet does not have an entry, create one.
          if packet_id not in packets:
            print("Created new packet entry.")
            packets[packet_id] = {
              "sequence_size": None,
              "last_updated": time.time(),
              "data": []
            }
          
          # Sort packet chunks.
          packet_entry = packets[packet_id] # Reasoning for this way of object mutation: https://stackoverflow.com/questions/37510076/unable-to-update-nested-dictionary-value-in-multiprocessings-manager-dict/48646169
          if sequence_id == 0:
            packet_entry["sequence_size"] = udp_packet.unpackHeader(packet, without_sequence=True)[0]
            packet_entry["data"].insert(sequence_id, packet[udp_packet.PACKET_HEADER_SIZE:])
          else:
            packet_entry["data"].insert(sequence_id, packet[udp_packet.PACKET_SEQUENCE_SIZE:])
          
          # s = 0
          # for p in packet_entry["data"]:
          #   s += len(p)
          # print(s)
          
          packet_entry["last_updated"] = time.time()
          packets[packet_id] = packet_entry
        
        # Add completed packets to queue for retrival.
        try:
          print(f"Current size: {len(packets[packet_id]["data"])}\n Max Size: {packets[packet_id]["sequence_size"]}")
          if len(packets[packet_id]["data"]) == packets[packet_id]["sequence_size"]:
            print(f"Packet {packet_id} is complete, sending to sompleted packets queue.")
            buf = bytearray()
            
            for packet_chunk in packets[packet_id]["data"]:
              buf.extend(packet_chunk)
            
            complete_packets.put(buf)
            #with processing_lock:
            del packets[packet_id]
            
            if packet_id in whitelisted_packet_ids:
              try:
                whitelisted_packet_ids.remove(packet_id)
              except ValueError:
                pass
        except KeyError:
          pass
          
        # Cleanup
        marked_for_removal = []
        #with processing_lock:
        for key, packet in packets.items():
          if time.time() - packet["last_updated"] >= 3:
            print("Removed unused packet.")
            marked_for_removal.append(key)
            
        for key in marked_for_removal:
          try:
            del packets[key]
            whitelisted_packet_ids.remove(key)
          except (ValueError, KeyError):
            pass
        
    except Exception as e:
      raise e

# class UDPReciever:
#   def __init__(self, sock, max_packet_size):
#     self.sock = sock
#     self.max_packet_size = max_packet_size
    
#     self.packets = {}
#     self.running = True
    
#     self.captured_chunks = queue.Queue()
#     self.complete_packets = queue.Queue()
    
#     self._collection_thread = threading.Thread(target=self._collect, daemon=True)
#     self._processing_thread = threading.Thread(target=self._process, daemon=True)
#     self._cleaning_thread = threading.Thread(target=self._clean, daemon=True)
    
#     self._collection_thread.start()
#     self._processing_thread.start()
#     self._cleaning_thread.start()
    
#   def recive(self):
#     try:
#       return self.complete_packets.get(block=False)
#     except queue.Empty:
#       return None
  
#   def stop(self):
#     self.running = False
#     self._collection_thread.join()
#     self._processing_thread.join()
#     self._cleaning_thread.join()
    
#   def _collect(self):
#     try:
#       while True:
#         if self.captured_chunks.full() or self.complete_packets.qsize() == 5:
#           continue
#         packet, address = self.sock.recvfrom(self.max_packet_size)
#         if packet is None:
#           print("packet is none")
#           continue
        
#         self.captured_chunks.put(packet)
        
#     except Exception as e:
#       raise e
    
#   def _process(self):
#     try:
#       while True:
#         if self.captured_chunks.empty() or self.complete_packets.qsize() == 5:
#           continue
        
#         packet = self.captured_chunks.get()
#         packet_id, sequence_id = udp_packet.unpackSequence(packet)
        
#         # If packet does not have an entry, create one.
#         if packet_id not in self.packets:
#           print("Created new packet entry.")
#           self.packets[packet_id] = {
#             "sequence_size": None,
#             "last_updated": time.time(),
#             "data": []
#           }
        
#         data_list = self.packets[packet_id]["data"]
        
#         if sequence_id == 0:
#           self.packets[packet_id]["sequence_size"] = udp_packet.unpackHeader(packet, without_sequence=True)[0]
#           data_list.insert(sequence_id, packet[udp_packet.PACKET_HEADER_SIZE:])
#         else:
#           data_list.insert(sequence_id, packet[udp_packet.PACKET_SEQUENCE_SIZE:])
          
#         self.packets[packet_id]["last_updated"] = time.time()
        
#         if len(data_list) == self.packets[packet_id]["sequence_size"]:
#           print("Packet is complete, sending to sompleted packets queue.")
#           buf = bytearray()
          
#           for packet_chunk in data_list:
#             buf.extend(packet_chunk)
          
#           self.complete_packets.put(buf)
#           del self.packets[packet_id]
        
#     except Exception as e:
#       raise e
    
#   def _clean(self):
#     try:
#       while True:
#         marked_for_removal = []
        
#         for key, packet in self.packets.items():
#           if time.time() - packet["last_updated"] >= 3:
#             print("Removed unused packet.")
#             marked_for_removal.append(key)
            
#         for key in marked_for_removal:
#           del self.packets[key]
        
#     except Exception as e:
#       raise e
  
  