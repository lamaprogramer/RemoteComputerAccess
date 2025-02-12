import cv2
import numpy as np
import struct
from threading import Event

from settings import *
from util import queue_process
from util.protocal import ImagePacket, ExitPacket
from util.threading_plus import SocketThread
import multiprocessing
import socket

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

class CaptureScreenThread(SocketThread):
  def __init__(self, event, socket, queue):
    SocketThread.__init__(self, event, socket)
    self.queue = queue
    self.start()
    
  def run(self):
    while self.is_running():
      image = self.queue.get()
      if image is not None:
        cv2.imshow('Screen Share', image)
      cv2.waitKey(1)
      
  def is_running(self):
    return self.event.is_set()
  
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

def main():
  client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  client_socket.connect(('localhost', 8089))
  print("Connected To Server.")
  
  image_processor = queue_process.QueueProcess(processImage, maxsize=IMAGE_QUEUE_SIZE, process_count=PROCESS_COUNT)
  
  program_running_event = Event()
  program_running_event.set()

  #capture_screen_thread = CaptureScreenThread(program_running_event, client_socket, queue)
  
  def shutdown():
    program_running_event.clear()
    image_processor.terminate()
    client_socket.shutdown(socket.SHUT_RDWR)
    client_socket.close()
    cv2.destroyAllWindows()

  try:
    while program_running_event.is_set():
      data = reciveMedia(client_socket)
      image_processor.putData(data)
      
      image = image_processor._ouptutQueue.get()
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