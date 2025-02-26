import struct
import zlib

'''
Little Endian
NAME -> TYPE -> SIZE (in bytes)

packet_size -> long -> 4
packet_id -> short -> 2

image_width -> short -> 2
image_height -> short -> 2
image_data -> bytes -> image_width * image_height * 4 * 4
'''

class ImagePacket:
  
  @staticmethod
  def to_bytes(width=0, height=0, data=b''):
    header_format = "<lhhh"
    compressed_data = zlib.compress(data, level=4)
    data_size = struct.calcsize(header_format) + len(compressed_data)
    return struct.pack(header_format, data_size, 0, width, height) + compressed_data
  
  @staticmethod
  def from_bytes(raw_bytes):
    header_format = "<lhhh"
    image_dimensions = struct.unpack_from(header_format, raw_bytes, 0)
    return (image_dimensions[2], image_dimensions[3], zlib.decompress(raw_bytes[struct.calcsize(header_format):]))

class ExitPacket:
  
  @staticmethod
  def to_bytes():
    header_format = "<lh"
    data_size = struct.calcsize(header_format)
    return struct.pack(header_format, data_size, -1)
  
  @staticmethod
  def from_bytes(raw_bytes):
    return None
