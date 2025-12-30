"""
Client to interact with RAFT cluster
Send commands, query status, simulate failures
"""
import grpc
import sys
import os
import argparse
import time

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
            nodes: List of "host:port" addresses or dict of {node_id: address}
        """
        if isinstance(nodes, dict):
            self.node_map = nodes
            self.nodes = list(nodes.values())
        else:
            self.nodes = nodes
            # Build node map from addresses (node1 = localhost:5001, etc)
            self.node_map = {}
            for i, addr in enumerate(nodes, 1):
                self.node_map[f"node{i}"] = addr
        
        self.stubs = {}
        for node_addr in self.nodes:
            channel = grpc.insecure_channel(node_addr)
            self.stubs[node_addr] = raft_pb2_grpc.RaftServiceStub(channel)
    
    def submit_command(self, command, max_retries=5):
        """
        Submit a command to the cluster
        Will automatically retry with different nodes if not leader
        """
        print(f"Submitting command: {command}")
        
        leader_hint = None
        
        for attempt in range(max_retries):
            # Try leader hint first if we have one
            nodes_to_try = list(self.stubs.keys())
            
            if leader_hint and leader_hint in self.node_map:
                leader_addr = self.node_map[leader_hint]
                if leader_addr in nodes_to_try:
                    # Move leader to front
                    nodes_to_try.remove(leader_addr)
                    nodes_to_try.insert(0, leader_addr)
                    print(f"Trying suggested leader: {leader_hint} ({leader_addr})")
            
            for node_addr in nodes_to_try:
                try:
                    stub = self.stubs[node_addr]
                    request = raft_pb2.ClientRequest(command=command)
                    response = stub.SubmitCommand(request, timeout=5.0)
                    
                    if response.success:
                        print(f"✓ Command successful: {response.message}")
                        return True
                    else:
                        # Update leader hint for next retry
                        if response.leader_id and response.leader_id != "unknown":
                            if leader_hint != response.leader_id:
                                leader_hint = response.leader_id
                                print(f"→ Leader is: {leader_hint}")
                                # Try the leader immediately
                                if leader_hint in self.node_map:
                                    leader_addr = self.node_map[leader_hint]
                                    try:
                                        stub = self.stubs[leader_addr]
                                        response = stub.SubmitCommand(request, timeout=5.0)
                                        if response.success:
                                            print(f"✓ Command successful: {response.message}")
                                            return True
                                    except:
                                        pass
                
                except grpc.RpcError as e:
                    if e.code() == grpc.StatusCode.DEADLINE_EXCEEDED:
                        pass  # Silent timeout
                    else:
                        pass  # Silent error
                except Exception as e:
                    pass  # Silent error
            
            if attempt < max_retries - 1:
                print(f"Waiting for leader election... (attempt {attempt + 1}/{max_retries})")
                time.sleep(1.0)  # Wait longer for election
        
        print("✗ Failed to submit command. Is the cluster running with a leader?")
        print("   Try: Wait a few seconds for leader election to complete")
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
    print("  status             - Check cluster status")
    print("  exit               - Exit")
    print("=" * 60)
    print("\nTIP: Wait 3-5 seconds after cluster startup for leader election")
    print("=" * 60 + "\n")
    
    while True:
        try:
            command = input("raft> ").strip()
            
            if not command:
                continue
            
            if command.lower() == "exit":
                break
            
            if command.lower() == "status":
                check_cluster_status(client)
                continue
            
            client.submit_command(command)
        
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except EOFError:
            break

def check_cluster_status(client):
    """Check which nodes are reachable and who is leader"""
    print("\nChecking cluster status...")
    print("-" * 60)
    
    leader_found = None
    reachable_nodes = 0
    
    for node_addr, stub in client.stubs.items():
        try:
            request = raft_pb2.ClientRequest(command="GET __status__")
            response = stub.SubmitCommand(request, timeout=2.0)
            
            reachable_nodes += 1
            node_name = None
            for nid, addr in client.node_map.items():
                if addr == node_addr:
                    node_name = nid
                    break
            
            if response.success or response.leader_id == (node_name or ""):
                print(f"✓ {node_addr} ({node_name}) - LEADER")
                leader_found = node_name
            else:
                leader_info = response.leader_id if response.leader_id != "unknown" else "unknown"
                print(f"✓ {node_addr} ({node_name}) - Follower (leader: {leader_info})")
        
        except Exception as e:
            node_name = None
            for nid, addr in client.node_map.items():
                if addr == node_addr:
                    node_name = nid
                    break
            print(f"✗ {node_addr} ({node_name}) - Unreachable")
    
    print("-" * 60)
    print(f"Reachable nodes: {reachable_nodes}/{len(client.stubs)}")
    if leader_found:
        print(f"Current leader: {leader_found}")
    else:
        print("No leader found - wait for election to complete")
    print()

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
