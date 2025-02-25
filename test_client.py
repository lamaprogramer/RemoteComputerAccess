import socket, time
from util import udp_sender
from util import protocal
import settings
import mss

with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
  sock.bind(settings.CLIENT_ADDRESS)
  sender = udp_sender.UDPSender(sock, settings.SERVER_ADDRESS)
  packet_counter = 0
  
  while True:
    #message = b"Hello world"*1000
    with mss.mss() as sct:
      image_bytes = sct.grab(settings.BOUNDING_BOX).rgb
      packet = protocal.ImagePacket.to_bytes(settings.BOUNDING_BOX["width"], settings.BOUNDING_BOX["height"], image_bytes)
      #print("create image")
      
      sender.send(packet_counter, packet, settings.MAX_PACKET_SIZE)
    #sock.sendto(message, settings.SERVER_ADDRESS)
      packet_counter += 1
      time.sleep(1/60)
  
  #message = b"Hello world"
  #sock.sendto(message, address)