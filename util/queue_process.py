import multiprocessing
from typing import Callable, Iterable, Any

class QueueProcess:
  def __init__(self, process: Callable[[multiprocessing.Queue, Any], None], args=(), maxsize: int=2, process_count: int=1):
    self._ouptutQueue = multiprocessing.Queue(maxsize=maxsize)
    self._inputQueue = multiprocessing.Queue(maxsize=maxsize)
    self.processes = []
    
    args2 = (self._inputQueue, self._ouptutQueue, args) if args else (self._inputQueue, self._ouptutQueue)
    for i in range(process_count):
      self.processes.append(multiprocessing.Process(target=process, args=args2))
      self.processes[i].start()
    
  def putData(self, data: Any):
    self._inputQueue.put(data)
  
  def getData(self):
    return self._ouptutQueue.get()
    
  def terminate(self):
    for process in self.processes:
      process.terminate()