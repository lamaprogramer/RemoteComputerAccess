from threading import Thread

class SocketThread(Thread):
  def __init__(self, event, sock):
    Thread.__init__(self, daemon=True)
    
    self.sock = sock
    self.event = event