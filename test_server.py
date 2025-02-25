import socket, multiprocessing
from util import udp_reciever
import settings

# with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
#   #sock.close()
#   sock.bind(settings.SERVER_ADDRESS)
if __name__ == "__main__":
  #multiprocessing.set_start_method("spawn")
  reciver = udp_reciever.UDPReciever(settings.SERVER_ADDRESS, settings.MAX_PACKET_SIZE, processor_count=5, collector_count=2)
  reciver.start()
  print("started")
  try:
    while True:
      message = reciver.recive()
      # if message is not None:
      #   print(message)
      
  except Exception as e:
    reciver.stop()
    raise e