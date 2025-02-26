import socket, multiprocessing
from util import udp_reciever, protocal
import numpy as np
import cv2
import settings

if __name__ == "__main__":
  reciver = udp_reciever.UDPReciever(settings.SERVER_ADDRESS, settings.MAX_PACKET_SIZE, processor_count=3, collector_count=1)
  reciver.start()
  
  try:
    while True:
      data = reciver.recive()
      if data is None:
        continue
      
      packet = protocal.ImagePacket.from_bytes(data)
      if packet and packet[2]:
        
        np_array = np.frombuffer(packet[2], np.uint8)#.reshape(packet[1], packet[0], 4)
        decompressed_image = cv2.imdecode(np_array, cv2.IMREAD_COLOR)
        
        #image = cv2.cvtColor(decompressed_image, cv2.COLOR_RGB2BGR)
        cv2.imshow('Screen Share', decompressed_image)
          
        if cv2.waitKey(1) & 0xFF == ord('q'):
          break
      
  except Exception as e:
    print(e)
    reciver.stop()
    raise e