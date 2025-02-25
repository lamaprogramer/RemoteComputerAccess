import multiprocessing, threading
from typing import Callable, Any

"""
Groups together processes for cpu tasks and threads for io tasks into one place.
"""

class Multiprocessor:
  def __init__(self, 
      io_task: Callable[[multiprocessing.Queue, Any], None] = None, 
      cpu_task: Callable[[multiprocessing.Queue, Any], None] = None,
      queue_size=1,
      thread_count=1,
      process_count=1,
      auto_start=False):
    
    self._ouptutQueue = multiprocessing.Queue(maxsize=queue_size)
    self._inputQueue = multiprocessing.Queue(maxsize=queue_size)
    
    self.io_tasks = []
    self.cpu_tasks = []
    
    self.io_task = io_task
    self.cpu_task = cpu_task
    
    self.thread_count = thread_count
    self.process_count = process_count
    self.auto_start = auto_start
    
  
  
  """
  Populate io_tasks and cpu_tasks with appropriete number of processes and threads.
  """
  def build(self):
    if len(self.io_tasks) > 0:
      raise Exception("Processor already has IO tasks running.")
    
    if len(self.cpu_tasks) > 0:
      raise Exception("Processor already has CPU tasks running.")
    
    for i in range(self.thread_count):
      self.io_tasks.append(self._createThread(target=self.io_task, args=(self._inputQueue, self._ouptutQueue)))
      if self.auto_start: self.io_tasks[i].start()
    
    for i in range(self.process_count):
      self.cpu_tasks.append(self._createProcess(target=self.cpu_task, args=(self._inputQueue, self._ouptutQueue)))
      if self.auto_start: self.cpu_tasks[i].start()
    return self
  
  
  """
  Start execution of processes and threads.
  """
  def start(self):
    self.startIOTasks()
    self.startCPUTasks()
    
  def startIOTasks(self):
    if (len(self.io_tasks) == 0):
      raise Exception("No IO tasks to start.")
    
    for io_task in self.io_tasks:
      io_task.start()
      
  def startCPUTasks(self):
    if (len(self.cpu_tasks) == 0):
      raise Exception("No CPU tasks to start.")
    
    for cpu_task in self.cpu_tasks:
      cpu_task.start()
      
      
  """
  Input and output data from their respective queues.
  """
  def putData(self, data: Any):
    self._inputQueue.put(data)
    
  def getData(self):
    return self._ouptutQueue.get()
      
  
  """
  Stop execution of processes and threads.
  """
  def stop(self):
    self.stopIOTasks()
    self.stopCPUTasks()
  
  def stopIOTasks(self):
    for io_task in self.io_tasks:
      io_task.join()
    self.io_tasks.clear()
  
  def stopCPUTasks(self): 
    for cpu_task in self.cpu_tasks:
      cpu_task.terminate()
      cpu_task.join()
    self.cpu_tasks.clear()
    
  
  """
  Create process or thread with provided target methods.
  May be overloaded to return custom threads or processes.
  """
  def _createThread(self, target, args=()) -> threading.Thread:
    return threading.Thread(target=target, args=args)
  
  def _createProcess(self, target, args=()) -> multiprocessing.Process:
    return multiprocessing.Process(target=target, args=args)