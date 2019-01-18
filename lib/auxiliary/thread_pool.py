#!/usr/bin/env python

#/*******************************************************************************
# Copyright (c) 2012 IBM Corp.

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#/*******************************************************************************

from Queue import Queue, Empty
from threading import Thread
from time import sleep
from pwd import getpwuid
from sys import stdout, path
import copy
import traceback

from lib.auxiliary.code_instrumentation import trace, cbdebug, cberr, cbwarn, cbinfo, cbcrit

class Worker(Thread):
    """Thread executing tasks from a given tasks queue"""
    def __init__(self, tasks, pool):
        Thread.__init__(self)
        self.tasks = tasks
        self.daemon = True
        self.abort = False
        self.aborted = False
        self.start()
        self.pool = pool
        self.pid = False

    def run(self):
        while True:
            try:
                func, args, kargs = self.tasks.get(timeout=0.5)
            except Empty:
                if self.abort:
                    self.aborted = True
                    return
                continue
            try: 
                cbdebug("POOL: thread started: " + func.__name__ + ": " + str(args) + " " + str(kargs) + ": " + self.pool.parent_name)
                self.abort = False
                self.aborted = False
                self.pool.results.append(func(*args, **kargs))
                self.aborted = True
            except Exception, e:
                cbdebug("POOL: thread failed: " + func.__name__ + ": " + str(args) + " " + str(kargs) + ": " + self.pool.parent_name)
                for line in traceback.format_exc().splitlines() :
                    cberr(line)
            finally :
                cbdebug("POOL: thread finished: " + func.__name__ + ": " + str(args) + " " + str(kargs) + ": " + self.pool.parent_name)
                self.tasks.task_done()

class ThreadPool:
    """Pool of threads consuming tasks from a queue"""
    def __init__(self, num_threads, parent_name):
        self.pid = False
        self.num_threads = num_threads
        self.parent_name = parent_name
        self.results = [] 
        self.workers = []
        self.tasks = Queue(num_threads)
        for _ in range(num_threads): self.workers.append(Worker(self.tasks, self))

    def add_task(self, func, *args, **kargs):
        """Add a task to the queue"""
        self.tasks.put((func, args, kargs))
        
    def abort(self):
        for worker in self.workers :
            worker.abort = True
        while True :
            all_aborted = True 
            for worker in self.workers :
                if not worker.aborted :
                    all_aborted = False
                    break
            if all_aborted :
                break
            sleep(0.5)
        self.tasks.join()

    def wait_completion(self):
        """Wait for completion of all the tasks in the queue"""
        # FIXME: switch to join()
        while self.tasks.unfinished_tasks > 0 :
            cbdebug("Still waiting for completion: " + self.parent_name + " unfinished: " + str(self.tasks.unfinished_tasks))
            sleep(0.5)
            
        '''
        Reset the results for the next time.
        '''
        result = copy.deepcopy(self.results)
        self.results = []
        return result
