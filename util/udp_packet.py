import struct

PACKET_SEQUENCE_FORMAT = "<II"
PACKET_HEADER_FORMAT = PACKET_SEQUENCE_FORMAT + "I"

PACKET_HEADER_SIZE = struct.calcsize(PACKET_HEADER_FORMAT)
PACKET_SEQUENCE_SIZE = struct.calcsize(PACKET_SEQUENCE_FORMAT)

def packHeader(packet_id: int, sequence_number: int, sequence_size: int):
  return struct.pack(PACKET_HEADER_FORMAT, packet_id, sequence_number, sequence_size)

def unpackHeader(data, without_sequence=False):
  if without_sequence:
    return struct.unpack_from("<I", data, struct.calcsize(PACKET_SEQUENCE_FORMAT))
  
  return struct.unpack_from(PACKET_HEADER_FORMAT, data, 0)


def packSequence(packet_id: int, sequence_number: int):
  return struct.pack(PACKET_SEQUENCE_FORMAT, packet_id, sequence_number)

def unpackSequence(data):
  return struct.unpack_from(PACKET_SEQUENCE_FORMAT, data, 0)