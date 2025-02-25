import mss
import multiprocessing
from threading import Event
import struct
import socket
from typing import Callable, Any
import threading

from settings import *
from util import multiprocessor
from util.protocal import ImagePacket

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
  
  def _createThread(self, target, args=()) -> threading.Thread:
    return threading.Thread(target=target, args=(*args, self.connection))
  
  def _createProcess(self, target, args=()) -> multiprocessing.Process:
    return multiprocessing.Process(target=target, args=(*args, BOUNDING_BOX))
  

def packageScreenshot(inputQueue: multiprocessing.Queue, outputQueue: multiprocessing.Queue, bounding_box: dict):
  with mss.mss() as sct:
    while program_running_event.is_set():
      if not outputQueue.full():
        image_bytes = sct.grab(bounding_box).rgb
        packet = ImagePacket.to_bytes(bounding_box["width"], bounding_box["height"], image_bytes)
        #print("create image")
        outputQueue.put(packet)

def sendScreenshot(inputQueue: multiprocessing.Queue, outputQueue: multiprocessing.Queue, connection):
  try:
    conn, address = connection
    while program_running_event.is_set():
      packet = outputQueue.get()
      if packet is not None:
        #connection.sendall(packet)
        #print("sent")
        sendMedia(conn, address, packet, MAX_PACKET_SIZE)
        #conn.sendto(packet, address)
  except (ConnectionAbortedError, ConnectionResetError):
    print("Client Force Closed.")
  finally:
    print("Thread closed successfully.")

def createUDPSocket(ip, port):
  server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
  server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
  server_socket.bind((ip, port))
  return (server_socket, (ip, port))

def main():
  server_socket, address = createUDPSocket(*SERVER_ADDRESS)
  print("Connected.")
  
  image_multiprocessor = ImageMultiprocessor(
    io_task=sendScreenshot, 
    cpu_task=packageScreenshot, 
    connection=(server_socket, CLIENT_ADDRESS), 
    queue_size=IMAGE_QUEUE_SIZE, 
    thread_count=THREAD_COUNT,
    process_count=PROCESS_COUNT
  ).build()
  
  image_multiprocessor.startCPUTasks()
  image_multiprocessor.startIOTasks()

  def shutdown():
    print("Shutting Down.")
    program_running_event.clear()
    image_multiprocessor.stopIOTasks()
    image_multiprocessor.stopCPUTasks()
    server_socket.close()

  try:
    while program_running_event.is_set():
      pass
  except (KeyboardInterrupt, ConnectionAbortedError, ConnectionResetError) as e:
    print("Connection Reset.")
  finally:
    pass

if __name__ == "__main__":
  main()
