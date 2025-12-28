"""
Run a single RAFT node
"""
import argparse
import sys
import os

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from node import RaftNode

def parse_peers(peers_str):
    """Parse peers string into dictionary"""
    peers = {}
    if peers_str:
        for peer in peers_str.split(','):
            node_id, address = peer.split('=')
            peers[node_id] = address
    return peers

def main():
    parser = argparse.ArgumentParser(description='Run a RAFT node')
    parser.add_argument('--node-id', required=True, help='Unique node identifier')
    parser.add_argument('--host', default='localhost', help='Host address')
    parser.add_argument('--port', type=int, required=True, help='Port number')
    parser.add_argument('--peers', default='', help='Comma-separated peers (format: id=host:port,id2=host:port)')
    parser.add_argument('--election-timeout-min', type=int, default=150, help='Min election timeout (ms)')
    parser.add_argument('--election-timeout-max', type=int, default=300, help='Max election timeout (ms)')
    parser.add_argument('--heartbeat-interval', type=int, default=50, help='Heartbeat interval (ms)')
    
    args = parser.parse_args()
    
    peers = parse_peers(args.peers)
    
    node = RaftNode(
        node_id=args.node_id,
        host=args.host,
        port=args.port,
        peers=peers,
        election_timeout_range=(args.election_timeout_min, args.election_timeout_max),
        heartbeat_interval=args.heartbeat_interval
    )
    
    try:
        node.start()
        node.wait_for_termination()
    except KeyboardInterrupt:
        node.stop()

if __name__ == "__main__":
    main()
