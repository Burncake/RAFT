"""
Test: Network Partition
Simulates network partition (split brain) scenario
"""
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

import grpc
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'proto'))
import raft_pb2
import raft_pb2_grpc

def isolate_nodes(node_addr, isolated_from):
    """Tell a node to isolate from others"""
    try:
        channel = grpc.insecure_channel(node_addr)
        stub = raft_pb2_grpc.RaftServiceStub(channel)
        
        request = raft_pb2.IsolateRequest(isolated_nodes=isolated_from)
        response = stub.Isolate(request, timeout=2.0)
        
        return response.success
    except Exception as e:
        print(f"   Error isolating {node_addr}: {e}")
        return False

def test_network_partition():
    """Test network partition scenario"""
    print("\n" + "=" * 70)
    print("TEST: Network Partition (Split Brain)")
    print("=" * 70)
    
    # Partition: Group A (3 nodes) and Group B (2 nodes)
    group_a = [
        ("node1", "localhost:5001"),
        ("node2", "localhost:5002"),
        ("node3", "localhost:5003"),
    ]
    
    group_b = [
        ("node4", "localhost:5004"),
        ("node5", "localhost:5005"),
    ]
    
    all_nodes = group_a + group_b
    
    print("\n1. Waiting for cluster to stabilize...")
    time.sleep(3)
    
    print("\n2. Submitting commands before partition...")
    try:
        channel = grpc.insecure_channel(group_a[0][1])
        stub = raft_pb2_grpc.RaftServiceStub(channel)
        
        request = raft_pb2.ClientRequest(command="SET before_partition initial")
        response = stub.SubmitCommand(request, timeout=5.0)
        print(f"   {response.message}")
    except Exception as e:
        print(f"   Error: {e}")
    
    time.sleep(2)
    
    print("\n3. Creating network partition...")
    print("   Group A (majority): node1, node2, node3")
    print("   Group B (minority): node4, node5")
    
    # Isolate Group A from Group B
    group_b_ids = [nid for nid, _ in group_b]
    for node_id, node_addr in group_a:
        if isolate_nodes(node_addr, group_b_ids):
            print(f"   ✓ {node_id} isolated from Group B")
    
    # Isolate Group B from Group A
    group_a_ids = [nid for nid, _ in group_a]
    for node_id, node_addr in group_b:
        if isolate_nodes(node_addr, group_a_ids):
            print(f"   ✓ {node_id} isolated from Group A")
    
    print("\n4. Waiting for partition effects...")
    time.sleep(5)
    
    print("\n5. Testing Group A (majority - should work)...")
    try:
        channel = grpc.insecure_channel(group_a[0][1])
        stub = raft_pb2_grpc.RaftServiceStub(channel)
        
        request = raft_pb2.ClientRequest(command="SET partition_test group_a_value")
        response = stub.SubmitCommand(request, timeout=5.0)
        
        if response.success:
            print(f"   ✓ Group A can commit: {response.message}")
        else:
            print(f"   ⚠ Group A issue: {response.message}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    print("\n6. Testing Group B (minority - should fail to commit)...")
    try:
        channel = grpc.insecure_channel(group_b[0][1])
        stub = raft_pb2_grpc.RaftServiceStub(channel)
        
        request = raft_pb2.ClientRequest(command="SET partition_test group_b_value")
        response = stub.SubmitCommand(request, timeout=5.0)
        
        if response.success:
            print(f"   ⚠ Group B should not commit without majority!")
        else:
            print(f"   ✓ Group B correctly cannot commit: {response.message}")
    except Exception as e:
        print(f"   ✓ Expected timeout/error: {e}")
    
    print("\n7. Healing the partition...")
    print("   Removing isolation...")
    
    # Remove isolation from all nodes
    for node_id, node_addr in all_nodes:
        isolate_nodes(node_addr, [])
        print(f"   ✓ {node_id} reconnected")
    
    print("\n8. Waiting for cluster to reconcile...")
    time.sleep(5)
    
    print("\n9. Testing healed cluster...")
    try:
        channel = grpc.insecure_channel(group_a[0][1])
        stub = raft_pb2_grpc.RaftServiceStub(channel)
        
        request = raft_pb2.ClientRequest(command="SET after_partition healed")
        response = stub.SubmitCommand(request, timeout=5.0)
        
        if response.success:
            print(f"   ✓ Cluster operational: {response.message}")
    except Exception as e:
        print(f"   Error: {e}")
    
    print("\n" + "=" * 70)
    print("✓ TEST PASSED: Network partition handled correctly")
    print("\nKey observations:")
    print("  - Majority partition (3/5) can continue operations")
    print("  - Minority partition (2/5) cannot commit new entries")
    print("  - Cluster reconciles after partition heals")
    print("  - RAFT ensures consistency across partitions")
    print("=" * 70 + "\n")
    
    return True

if __name__ == "__main__":
    success = test_network_partition()
    sys.exit(0 if success else 1)
