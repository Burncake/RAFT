"""
Test: Leader Election
Verifies that cluster can elect a leader
"""
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

import grpc
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'proto'))
import raft_pb2
import raft_pb2_grpc

def test_leader_election():
    """Test that a leader is elected"""
    print("\n" + "=" * 70)
    print("TEST: Leader Election")
    print("=" * 70)
    
    nodes = [
        ("node1", "localhost:5001"),
        ("node2", "localhost:5002"),
        ("node3", "localhost:5003"),
        ("node4", "localhost:5004"),
        ("node5", "localhost:5005"),
    ]
    
    print("\n1. Waiting for election to complete...")
    time.sleep(3)  # Give time for initial election
    
    print("\n2. Checking for leader...")
    leader_found = False
    leader_node = None
    
    for node_id, addr in nodes:
        try:
            channel = grpc.insecure_channel(addr)
            stub = raft_pb2_grpc.RaftServiceStub(channel)
            
            # Try to submit a command to see if it's the leader
            request = raft_pb2.ClientRequest(command="GET test")
            response = stub.SubmitCommand(request, timeout=2.0)
            
            if response.success or response.leader_id == node_id:
                print(f"   ✓ {node_id} is the LEADER")
                leader_found = True
                leader_node = node_id
                break
            else:
                print(f"   - {node_id} is follower (leader: {response.leader_id})")
        
        except Exception as e:
            print(f"   ✗ {node_id} unreachable: {e}")
    
    print("\n" + "=" * 70)
    if leader_found:
        print(f"✓ TEST PASSED: Leader elected ({leader_node})")
    else:
        print("✗ TEST FAILED: No leader found")
    print("=" * 70 + "\n")
    
    return leader_found

if __name__ == "__main__":
    success = test_leader_election()
    sys.exit(0 if success else 1)
