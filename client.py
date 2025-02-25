import cv2
import numpy as np
import struct
from threading import Event, Thread
from typing import Callable, Any
import multiprocessing
import math

from settings import *
from util import multiprocessor
from util.protocal import ImagePacket
import socket

program_running_event = Event()
program_running_event.set()

class ImageMultiprocessor(multiprocessor.Multiprocessor):
  def __init__(self, 
      io_task: Callable[[multiprocessing.Queue, Any], None] = None, 
      cpu_task: Callable[[multiprocessing.Queue, Any], None] = None,
      connection = None,
      queue_size=1,
      thread_count=1,
      process_count=1,
      auto_start=False):
    super().__init__(io_task, cpu_task, queue_size, thread_count, process_count, auto_start) 
    self.connection = connection
  
  def _createThread(self, target, args=()) -> Thread:
    return Thread(target=target, args=(*args, self.connection))
  
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

def displayImage(inputQueue, outputQueue, connection):
  while True:
    image = outputQueue.get()
      
    if image is not None:
      cv2.imshow('Screen Share', image)
      
    if cv2.waitKey(1) & 0xFF == ord('q'):
      break

def createSocket(ip, port):
  client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  #client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 2**20)
  client_socket.connect((ip, port))
  return client_socket

def createUDPSocket():
  client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
  #client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 2**20)
  client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
  client_socket.bind(CLIENT_ADDRESS)
  return (client_socket, CLIENT_ADDRESS)

def main():
  client_socket, address = createUDPSocket()
  
  print("Connected To Server.")
  
  image_multiprocessor = ImageMultiprocessor(
    cpu_task=processImage,
    #io_task=displayImage,
    #connection=client_socket,
    queue_size=IMAGE_QUEUE_SIZE, 
    process_count=PROCESS_COUNT,
    #thread_count=THREAD_COUNT
  ).build()
  
  image_multiprocessor.startCPUTasks()
  #image_multiprocessor.startIOTasks()
  
  def shutdown():
    program_running_event.clear()
    #image_multiprocessor.stopIOTasks()
    image_multiprocessor.stopCPUTasks()
    client_socket.shutdown(socket.SHUT_RDWR)
    client_socket.close()
    cv2.destroyAllWindows()

  try:
    while program_running_event.is_set():
      print("test")
      data = reciveUDPMedia(client_socket)
      if data is None:
        continue
      
      print("recived packet")
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