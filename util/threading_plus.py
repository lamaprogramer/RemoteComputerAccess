from threading import Thread

class SocketThread(Thread):
  def __init__(self, target=None, event=None, sock=None, args=()):
    Thread.__init__(self, target=target, args=args, daemon=True)
  
    self.sock = sock
    self.event = event