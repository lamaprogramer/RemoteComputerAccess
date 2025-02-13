import cv2
import numpy as np
import struct
from threading import Event

from settings import *
from util import multiprocessor
from util.protocal import ImagePacket
import socket

program_running_event = Event()
program_running_event.set()

def reciveMedia(sock):
  buf = bytearray()
  
  size, id = struct.unpack("<lh", sock.recv(6))
  size -= 6
  
  while size > 0:
    data = sock.recv(size)
    if not data:
      return None
    buf.extend(data)
    size -= len(data)
    
  return (id, bytes(buf))
  
def processImage(inputQueue, outputQueue):
  while True:
    data = inputQueue.get()
    if data is None:
      continue
    
    if data[0] == 0:
      packet = ImagePacket.from_bytes(data[1])
      if not packet or packet[2] is None:
        continue
      
      np_array = np.frombuffer(packet[2], np.uint8).reshape(packet[1], packet[0], 3)
      image = cv2.cvtColor(np_array, cv2.COLOR_RGB2BGR)
      outputQueue.put(image)

def createSocket(port):
  client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  client_socket.connect(('localhost', port))
  return client_socket

def main():
  client_socket = createSocket(8089)
  print("Connected To Server.")
  
  image_multiprocessor = multiprocessor.Multiprocessor(
    cpu_task=processImage,
    queue_size=IMAGE_QUEUE_SIZE, 
    process_count=PROCESS_COUNT
  ).build()
  
  image_multiprocessor.startCPUTasks()
  
  def shutdown():
    program_running_event.clear()
    image_multiprocessor.stopCPUTasks()
    client_socket.shutdown(socket.SHUT_RDWR)
    client_socket.close()
    cv2.destroyAllWindows()

  try:
    while program_running_event.is_set():
      data = reciveMedia(client_socket)
      if data is None:
        break
      
      image_multiprocessor.putData(data=data)
      image = image_multiprocessor.getData()
      
      if image is not None:
        cv2.imshow('Screen Share', image)
      
      if cv2.waitKey(1) & 0xFF == ord('q'):
        break
  except (KeyboardInterrupt, ConnectionAbortedError, ConnectionResetError) as e:
    print("Connection Reset.")
  finally:
    shutdown()

if __name__ == "__main__":
  main()