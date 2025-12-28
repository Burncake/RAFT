"""
Start a RAFT cluster with 5 nodes
"""
import subprocess
import sys
import os
import time
import signal

# Configuration for 5-node cluster
NODES = {
    "node1": {"host": "localhost", "port": 5001},
    "node2": {"host": "localhost", "port": 5002},
    "node3": {"host": "localhost", "port": 5003},
    "node4": {"host": "localhost", "port": 5004},
    "node5": {"host": "localhost", "port": 5005},
}

processes = []

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    print("\n\nShutting down cluster...")
    for proc in processes:
        try:
            proc.terminate()
        except:
            pass
    
    # Wait for processes to terminate
    time.sleep(1)
    
    for proc in processes:
        try:
            proc.kill()
        except:
            pass
    
    print("Cluster stopped")
    sys.exit(0)

def start_node(node_id, config):
    """Start a single RAFT node"""
    # Build peers list (all nodes except this one)
    peers = []
    for nid, ncfg in NODES.items():
        if nid != node_id:
            peers.append(f"{nid}={ncfg['host']}:{ncfg['port']}")
    
    peers_str = ",".join(peers)
    
    cmd = [
        sys.executable,
        os.path.join(os.path.dirname(__file__), "run_node.py"),
        "--node-id", node_id,
        "--host", config["host"],
        "--port", str(config["port"]),
        "--peers", peers_str
    ]
    
    print(f"Starting {node_id} at {config['host']}:{config['port']}...")
    proc = subprocess.Popen(cmd)
    return proc

def main():
    """Start all nodes in the cluster"""
    print("=" * 60)
    print("RAFT Cluster Startup")
    print("=" * 60)
    
    # Register signal handler
    signal.signal(signal.SIGINT, signal_handler)
    
    # Start all nodes
    for node_id, config in NODES.items():
        proc = start_node(node_id, config)
        processes.append(proc)
        time.sleep(0.5)  # Stagger startup
    
    print("\n" + "=" * 60)
    print("Cluster started successfully!")
    print("=" * 60)
    print(f"Total nodes: {len(NODES)}")
    for node_id, config in NODES.items():
        print(f"  {node_id}: {config['host']}:{config['port']}")
    print("\nPress Ctrl+C to stop the cluster")
    print("=" * 60 + "\n")
    
    # Wait for all processes
    try:
        for proc in processes:
            proc.wait()
    except KeyboardInterrupt:
        signal_handler(None, None)

if __name__ == "__main__":
    main()
