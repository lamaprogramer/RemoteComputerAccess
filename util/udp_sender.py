from util import udp_packet
import math

class UDPSender:
  
  def __init__(self, sock, address):
    self.sock = sock
    self.address = address
  
  def send(self, packet_id, data, chunk_size): 
    for chunk in self._getChunk(packet_id, data, chunk_size):
      self.sock.sendto(chunk, self.address)
    print(f"Packet Id: {packet_id}, Size: {len(data)}")
    
  def calcMaxChunks(self, data_size, chunk_size):
    prev_chunk_count = 0
    chunk_count = math.ceil(data_size / float(chunk_size))

    while chunk_count != prev_chunk_count:
        prev_chunk_count = chunk_count
        true_data_size = data_size + udp_packet.PACKET_HEADER_SIZE + (udp_packet.PACKET_SEQUENCE_SIZE * (chunk_count - 1))
        chunk_count = math.ceil(true_data_size / float(chunk_size))

    return chunk_count
    
  def _getChunk(self, packet_id, data, chunk_size):
    max_chunks = self.calcMaxChunks(len(data), chunk_size)
    
    collected_data = 0
    created_chunks = 0
    
    while collected_data != len(data):
      start = collected_data
      end = min(collected_data+chunk_size, len(data))
      range = end - start
      
      if created_chunks == 0:
        if range == chunk_size or (chunk_size - range) < udp_packet.PACKET_HEADER_SIZE:
          end -= udp_packet.PACKET_HEADER_SIZE
          
        header = udp_packet.packHeader(packet_id, 0, max_chunks)
        collected_data = end
        created_chunks += 1
        
        yield header + data[start:end]
      else:
        if range == chunk_size or (chunk_size - range) < udp_packet.PACKET_SEQUENCE_SIZE:
          end -= udp_packet.PACKET_SEQUENCE_SIZE
          
        sequence = udp_packet.packSequence(packet_id, created_chunks)
        collected_data = end
        created_chunks += 1
        
        yield sequence + data[start:end]