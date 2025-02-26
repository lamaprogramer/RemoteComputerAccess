from util import udp_packet
from typing import Tuple

import multiprocessing.managers
import multiprocessing.synchronize
import multiprocessing, socket, random, queue, time, threading


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
    self.packet_keep_ratio = packet_keep_ratio
    self.address = address
    self.running = True
    
    # Data Storage
    self.manager = multiprocessing.Manager()
    self.whitelisted_packet_ids = self.manager.list()
    
    self.packets = self.manager.dict()
    self.packet_chunks = self.manager.Queue(maxsize=500)
    self.complete_packets = self.manager.Queue(maxsize=5)
    
    # Create Processes
    self._processing_thread_count = processor_count
    self._processing_lock = multiprocessing.Lock()
    self._processing_threads = [
      multiprocessing.Process(
        target=self._process, args=(
          self.packets, 
          self._processing_lock, 
          self.whitelisted_packet_ids, 
          self.packet_chunks, 
          self.complete_packets
        ), daemon=True)
      for i in range(self._processing_thread_count)
    ]
    
    self._collection_thread_count = collector_count
    self._collection_lock = threading.Lock()
    self._collection_threads = [
      threading.Thread(
        target=self._collect, args=(
          self.address, 
          self.whitelisted_packet_ids, 
          self.packet_chunks, 
          self.complete_packets, 
          self.max_packet_size
        ), daemon=True)
      for i in range(self._collection_thread_count)
    ]
    
  def start(self):
    for i in self._collection_threads:
      i.start()
    for i in self._processing_threads:
      i.start()
  
  def recive(self):
    try:
      return self.complete_packets.get(timeout=0.1)
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
      sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1024*1024) # 1 MB
      sock.settimeout(1)
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
              packet_chunks.put((packet, packet_id, sequence_id), block=False)
          else:
            packet_chunks.put((packet, packet_id, sequence_id), block=False)

        except (queue.Full, TimeoutError):
          continue
        
    except Exception as e:
      raise e
    
  @staticmethod
  def post_collection(data):
    return data
  
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
        
        try:
          packet, packet_id, sequence_id = packet_chunks.get(block=False)
        except queue.Empty:
          continue
        
        with processing_lock:
          # If packet does not have an entry, create one.
          if packet_id not in packets:
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
          
          packet_entry["last_updated"] = time.time()
          packets[packet_id] = packet_entry
        
        # Add completed packets to queue for retrival.
        try:
          if len(packets[packet_id]["data"]) == packets[packet_id]["sequence_size"]:
            buf = b"".join(packets[packet_id]["data"])
            complete_packets.put(buf, block=False)
            packets.pop(packet_id)
            
            if packet_id in whitelisted_packet_ids:
              try:
                whitelisted_packet_ids.remove(packet_id)
              except ValueError:
                pass
            
            # Cleanup
            marked_for_removal = [
              key for key, packet in packets.items() 
              if time.time() - packet["last_updated"] >= 3
            ]
                
            for key in marked_for_removal:
              try:
                del packets[key]
                whitelisted_packet_ids.remove(key)
              except (ValueError, KeyError):
                pass
              
        except (queue.Full, KeyError):
          pass
        
    except Exception as e:
      raise e