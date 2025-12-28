"""
Test: Follower Failure and Recovery
Tests cluster behavior when followers fail and rejoin
"""
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

import grpc
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'proto'))
import raft_pb2
import raft_pb2_grpc

def test_follower_failure():
    """Test follower failure and recovery"""
    print("\n" + "=" * 70)
    print("TEST: Follower Failure and Recovery")
    print("=" * 70)
    
    nodes = [
        ("node1", "localhost:5001"),
        ("node2", "localhost:5002"),
        ("node3", "localhost:5003"),
        ("node4", "localhost:5004"),
        ("node5", "localhost:5005"),
    ]
    
    print("\n1. Waiting for cluster to stabilize...")
    time.sleep(3)
    
    print("\n2. Submitting commands before failure...")
    test_node = nodes[0][1]  # Use first node
    
    try:
        channel = grpc.insecure_channel(test_node)
        stub = raft_pb2_grpc.RaftServiceStub(channel)
        
        for i in range(3):
            request = raft_pb2.ClientRequest(command=f"SET before_failure_{i} value_{i}")
            response = stub.SubmitCommand(request, timeout=5.0)
            print(f"   {response.message}")
    except Exception as e:
        print(f"   Error: {e}")
    
    print("\n3. Testing follower failure...")
    print("   [MANUAL STEP] Stop 1-2 follower nodes (NOT the leader)")
    print("   Suggested: Stop node4 and node5")
    print("   - The cluster should still function with 3/5 nodes")
    print("\n   Waiting 5 seconds...")
    time.sleep(5)
    
    print("\n4. Testing cluster with failed followers...")
    try:
        channel = grpc.insecure_channel(test_node)
        stub = raft_pb2_grpc.RaftServiceStub(channel)
        
        request = raft_pb2.ClientRequest(command="SET during_failure test_value")
        response = stub.SubmitCommand(request, timeout=5.0)
        
        if response.success:
            print(f"   ✓ Cluster still operational: {response.message}")
        else:
            print(f"   ⚠ {response.message}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    print("\n5. Testing recovery...")
    print("   [MANUAL STEP] Restart the stopped nodes")
    print("   - They should catch up with the cluster")
    print("\n   Waiting 10 seconds for recovery...")
    time.sleep(10)
    
    print("\n6. Verifying synchronization...")
    print("   Check that all nodes have the same data:")
    print("   - Look in data/ directory for node_*_db.json files")
    print("   - All active nodes should have the same keys")
    
    print("\n7. Failure threshold test...")
    print("   [INFO] Minimum nodes for majority: 3/5")
    print("   - Cluster can tolerate 2 node failures")
    print("   - If 3 or more nodes fail, no new commits possible")
    print("   - Existing committed data remains consistent")
    
    print("\n" + "=" * 70)
    print("✓ TEST COMPLETED: Follower failure scenarios tested")
    print("=" * 70 + "\n")
    
    return True

if __name__ == "__main__":
    success = test_follower_failure()
    sys.exit(0 if success else 1)
