"""
Utility functions for measuring performance (time and memory).
"""
import time
import tracemalloc
import sys
import threading
import queue

TIMEOUT_S = 120

def measure(func, *args):
    def run_with_timeout(q, func, args):
        try:
            result = func(*args)
            q.put(('success', result))
        except Exception as e:
            q.put(('error', repr(e)))
    
    tracemalloc.start()
    t0 = time.time()
    
    # Create queue for result
    q = queue.Queue()
    
    # Start function in separate thread
    thread = threading.Thread(target=run_with_timeout, args=(q, func, args))
    thread.daemon = True
    thread.start()
    
    # Wait for result or timeout
    thread.join(TIMEOUT_S)
    
    if thread.is_alive():
        elapsed = (time.time() - t0) * 1000
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        return None, elapsed, peak / 1024
    
    try:
        status, result = q.get_nowait()
    except queue.Empty:
        result = None
        status = 'error'
    
    elapsed = (time.time() - t0) * 1000
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    
    if status == 'error':
        print(f"    ERROR: {result}")
        result = None
    
    return result, elapsed, peak / 1024
