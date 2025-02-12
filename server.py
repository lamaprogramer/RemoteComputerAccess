import mss
import multiprocessing
from threading import Event
import struct
import socket

from settings import *
from util import queue_process
from util.protocal import ImagePacket, ExitPacket
from util.threading_plus import SocketThread

def reciveMedia(sock):
  buf = bytearray()
  header = sock.recv(6)
  if not header:
    return None
  
  size, id = struct.unpack("<lh", header)
  size -= 6
  
  while size > 0:
    data = sock.recv(size)
    if not data:
      return None
    buf.extend(data)
    size -= len(data)
    
  return (id, bytes(buf))

class CaptureScreenThread(SocketThread):
  def __init__(self, event, connection, queue):
    SocketThread.__init__(self, event, connection)
    self.connection = connection
    self.queue = queue
    self.start()
    
  def run(self):
    try:
      while self.is_running():
        packet = self.queue.get()
        if packet is not None:
          self.connection.sendall(packet)
    except (ConnectionAbortedError, ConnectionResetError):
      print("Client Force Closed.")
    finally:
      print("Thread closed successfully.")

  def is_running(self):
    return self.event.is_set()

def packageScreenshot(inputQueue: multiprocessing.Queue, outputQueue: multiprocessing.Queue, bounding_box: dict):
  with mss.mss() as sct:
    while True:
      if not outputQueue.full():
        image_bytes = sct.grab(bounding_box).rgb
        packet = ImagePacket.to_bytes(bounding_box["width"], bounding_box["height"], image_bytes)
        outputQueue.put(packet)
        
def createSocket(port):
  server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  server_socket.bind(('localhost', port))
  
  try:
    print("Waiting for Connection.")
    server_socket.listen(5)
  except (KeyboardInterrupt, ConnectionAbortedError) as e:
    return None

  return server_socket

def createImageProcessor():
  return queue_process.QueueProcess(packageScreenshot, (BOUNDING_BOX), maxsize=IMAGE_QUEUE_SIZE, process_count=PROCESS_COUNT)

def createThreads(program_running_event, connection, image_processor):
  threads = []
  for i in range(THREAD_COUNT):
    threads.append(CaptureScreenThread(program_running_event, connection, image_processor._ouptutQueue))
  return threads

def main():
  program_running_event = Event()
  program_running_event.set()
  
  server_socket = createSocket(8089)
  connection, address = server_socket.accept()
  print("Connected.")
  
  image_processor = createImageProcessor()
  threads = createThreads(program_running_event, connection, image_processor)

  def shutdown():
    print("Shutting Down.")
    program_running_event.clear()
    
    for thread in threads:
      thread.join()
    
    image_processor.terminate()
    connection.close()
    server_socket.close()

  try:
    while program_running_event.is_set():
      data = reciveMedia(connection)
      if data is None:
        break
  except (KeyboardInterrupt, ConnectionAbortedError, ConnectionResetError) as e:
    print("Connection Reset.")
  finally:
    shutdown()

if __name__ == "__main__":
  main()
