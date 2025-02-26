import socket, time, multiprocessing, queue
from util import udp_sender, protocal
import numpy as np
import settings
import mss, cv2

screenshot_queue = multiprocessing.Queue()

def package_images(sc_queue):
  with mss.mss() as sct:
    while True:
      image_bytes = sct.grab(settings.SCREEN_CAPTURE)
      image_array = np.array(image_bytes)
      
      resized_image = cv2.resize(image_array, settings.COMPRESSED_RESOLUTION)
      
      encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 30]
      result, compressed_image = cv2.imencode(".jpg", resized_image, encode_param)
      compressed_image_bytes = compressed_image.tobytes()
      
      packet = protocal.ImagePacket.to_bytes(settings.COMPRESSED_RESOLUTION[0], settings.COMPRESSED_RESOLUTION[1], compressed_image_bytes)
      sc_queue.put(packet)
  
screenshot_proccesses = [
  multiprocessing.Process(target=package_images, args=(screenshot_queue,))
  for i in range(5)
]

if __name__ == "__main__":
  try:
    for p in screenshot_proccesses:
      p.start()
    
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
      sock.bind(settings.CLIENT_ADDRESS)
      sender = udp_sender.UDPSender(sock, settings.SERVER_ADDRESS)
      packet_counter = 0
      
      while True:
        try:
          packet = screenshot_queue.get(block=False)
          sender.send(packet_counter, packet, settings.MAX_PACKET_SIZE)
          packet_counter += 1
        except queue.Empty:
          pass
  except:
    if len(screenshot_proccesses) != 0:
      for p in screenshot_proccesses:
        p.join()
  
  #message = b"Hello world"
  #sock.sendto(message, address)