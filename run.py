import subprocess
import time
import signal
import sys
import os

def signal_handler(sig, frame):
    print("\nShutting down InvigiLens System...")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

def run_system():
    # 1. Start Backend
    print("[1/2] Starting Backend Server...")
    backend_path = os.path.join(os.path.dirname(__file__), 'backend')
    
    # Run node directly to avoid npm/shell wrapping issues
    # shell=True required on Windows to find 'node' in path sometimes, or just for ease
    backend = subprocess.Popen('node index.js', cwd=backend_path, shell=True)
    
    # Wait for backend to be ready (approx)
    time.sleep(5)
    
    # 2. Start ML Engine
    print("[2/2] Starting ML Engine...")
    ml_path = os.path.dirname(__file__)
    ml_engine = subprocess.Popen([sys.executable, '-m', 'ml_engine.src.detector'], cwd=ml_path)
    
    print("\n-------------------------------------------")
    print("InvigiLens System Running!")
    print("Frontend: http://localhost:5000")
    print("Press Ctrl+C to Stop Everything.")
    print("-------------------------------------------")
    
    try:
        while True:
            time.sleep(1)
            # Check if processes are alive
            b_poll = backend.poll()
            m_poll = ml_engine.poll()
            
            if b_poll is not None:
                print(f"Backend stopped unexpectedly with code {b_poll}.")
                break
            if m_poll is not None:
                print(f"ML Engine stopped unexpectedly with code {m_poll}.")
                break

    except KeyboardInterrupt:
        pass
    finally:
        print("Terminating processes...")
        # On Windows, terminate() might not close the tree. 
        # Using taskkill for robust cleanup if standard terminate doesn't work well
        if ml_engine:
            ml_engine.terminate()
            # ml_engine.kill() 
        
        # Node can be tricky on Windows as a subprocess of cmd
        subprocess.call(['taskkill', '/F', '/T', '/PID', str(backend.pid)])
        subprocess.call(['taskkill', '/F', '/T', '/PID', str(ml_engine.pid)])
        
        print("Shutdown Complete.")

if __name__ == "__main__":
    run_system()
