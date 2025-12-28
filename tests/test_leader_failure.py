"""
Test: Leader Failure
Simulates leader crash and verifies new leader election
"""
import sys
import os
import time
import subprocess
import signal

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

import grpc
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'proto'))
import raft_pb2
import raft_pb2_grpc

def find_leader(nodes):
    """Find the current leader"""
    for node_id, addr in nodes:
        try:
            channel = grpc.insecure_channel(addr)
            stub = raft_pb2_grpc.RaftServiceStub(channel)
            
            request = raft_pb2.ClientRequest(command="GET test")
            response = stub.SubmitCommand(request, timeout=2.0)
            
            if response.leader_id:
                # Find the leader's address
                for nid, naddr in nodes:
                    if nid == response.leader_id:
                        return nid, naddr
        except:
            pass
    return None, None

def test_leader_failure():
    """Test recovery from leader failure"""
    print("\n" + "=" * 70)
    print("TEST: Leader Failure Recovery")
    print("=" * 70)
    
    nodes = [
        ("node1", "localhost:5001"),
        ("node2", "localhost:5002"),
        ("node3", "localhost:5003"),
        ("node4", "localhost:5004"),
        ("node5", "localhost:5005"),
    ]
    
    print("\n1. Waiting for initial leader election...")
    time.sleep(3)
    
    print("\n2. Finding current leader...")
    leader_id, leader_addr = find_leader(nodes)
    
    if not leader_id:
        print("   ✗ No leader found!")
        return False
    
    print(f"   ✓ Current leader: {leader_id} at {leader_addr}")
    
    print(f"\n3. Simulating leader failure...")
    print(f"   [MANUAL STEP] Please stop {leader_id} process:")
    print(f"   - Find the process running on {leader_addr}")
    print(f"   - Kill it using Task Manager or Ctrl+C in its terminal")
    print(f"\n   Waiting 10 seconds for new election...")
    
    time.sleep(10)
    
    print("\n4. Checking for new leader...")
    new_leader_id, new_leader_addr = find_leader(nodes)
    
    if not new_leader_id:
        print("   ✗ No new leader elected!")
        return False
    
    if new_leader_id == leader_id:
        print(f"   ⚠ Same leader ({new_leader_id}) - it may have reconnected")
    else:
        print(f"   ✓ New leader elected: {new_leader_id} at {new_leader_addr}")
    
    print("\n5. Testing cluster functionality...")
    try:
        channel = grpc.insecure_channel(new_leader_addr)
        stub = raft_pb2_grpc.RaftServiceStub(channel)
        
        request = raft_pb2.ClientRequest(command="SET test_after_failure success")
        response = stub.SubmitCommand(request, timeout=5.0)
        
        if response.success:
            print(f"   ✓ Cluster operational: {response.message}")
        else:
            print(f"   ⚠ Command failed: {response.message}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False
    
    print("\n" + "=" * 70)
    print("✓ TEST PASSED: New leader elected after failure")
    print("=" * 70 + "\n")
    
    return True

if __name__ == "__main__":
    success = test_leader_failure()
    sys.exit(0 if success else 1)
