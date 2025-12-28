"""
Client to interact with RAFT cluster
Send commands, query status, simulate failures
"""
import grpc
import sys
import os
import argparse

# Add proto directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'proto'))

import raft_pb2
import raft_pb2_grpc

class RaftClient:
    """Client for interacting with RAFT cluster"""
    
    def __init__(self, nodes):
        """
        Initialize client with list of node addresses
        
        Args:
            nodes: List of "host:port" addresses
        """
        self.nodes = nodes
        self.stubs = {}
        
        for node_addr in nodes:
            channel = grpc.insecure_channel(node_addr)
            self.stubs[node_addr] = raft_pb2_grpc.RaftServiceStub(channel)
    
    def submit_command(self, command, max_retries=3):
        """
        Submit a command to the cluster
        Will automatically retry with different nodes if not leader
        """
        print(f"Submitting command: {command}")
        
        for attempt in range(max_retries):
            for node_addr, stub in self.stubs.items():
                try:
                    request = raft_pb2.ClientRequest(command=command)
                    response = stub.SubmitCommand(request, timeout=10.0)
                    
                    if response.success:
                        print(f"✓ Command successful: {response.message}")
                        return True
                    else:
                        if response.leader_id and response.leader_id != "unknown":
                            print(f"Node {node_addr} is not leader. Leader is: {response.leader_id}")
                        else:
                            print(f"Command failed: {response.message}")
                
                except Exception as e:
                    print(f"Error contacting {node_addr}: {e}")
        
        print("✗ Failed to submit command after retries")
        return False
    
    def isolate_node(self, node_addr, isolated_from):
        """
        Tell a node to isolate itself from other nodes (for testing)
        
        Args:
            node_addr: Address of node to isolate
            isolated_from: List of node IDs to isolate from
        """
        try:
            stub = self.stubs[node_addr]
            request = raft_pb2.IsolateRequest(isolated_nodes=isolated_from)
            response = stub.Isolate(request, timeout=5.0)
            
            if response.success:
                print(f"✓ {node_addr} isolated from {isolated_from}")
            else:
                print(f"✗ Isolation failed: {response.message}")
        
        except Exception as e:
            print(f"Error: {e}")

def interactive_mode(client):
    """Interactive command-line interface"""
    print("\n" + "=" * 60)
    print("RAFT Client - Interactive Mode")
    print("=" * 60)
    print("Commands:")
    print("  SET <key> <value>  - Set a key-value pair")
    print("  GET <key>          - Get value for a key")
    print("  DELETE <key>       - Delete a key")
    print("  exit               - Exit")
    print("=" * 60 + "\n")
    
    while True:
        try:
            command = input("raft> ").strip()
            
            if not command:
                continue
            
            if command.lower() == "exit":
                break
            
            client.submit_command(command)
        
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except EOFError:
            break

def main():
    parser = argparse.ArgumentParser(description='RAFT cluster client')
    parser.add_argument('--nodes', default='localhost:5001,localhost:5002,localhost:5003,localhost:5004,localhost:5005',
                       help='Comma-separated list of node addresses')
    parser.add_argument('--command', help='Single command to execute (optional)')
    parser.add_argument('--isolate', help='Isolate node (format: node_addr:node_id1,node_id2)')
    
    args = parser.parse_args()
    
    nodes = args.nodes.split(',')
    client = RaftClient(nodes)
    
    if args.isolate:
        # Parse isolation command
        parts = args.isolate.split(':')
        if len(parts) == 2:
            node_addr = parts[0]
            isolated_from = parts[1].split(',')
            client.isolate_node(node_addr, isolated_from)
        else:
            print("Invalid isolate format. Use: node_addr:node_id1,node_id2")
    elif args.command:
        # Single command mode
        client.submit_command(args.command)
    else:
        # Interactive mode
        interactive_mode(client)

if __name__ == "__main__":
    main()
