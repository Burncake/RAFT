"""
Verify RAFT Project Setup
Checks that all components are correctly installed and configured
"""
import os
import sys
import importlib.util

def check_file(filepath, description):
    """Check if a file exists"""
    exists = os.path.exists(filepath)
    status = "✓" if exists else "✗"
    print(f"  {status} {description}: {filepath}")
    return exists

def check_module(module_name):
    """Check if a Python module is installed"""
    spec = importlib.util.find_spec(module_name)
    exists = spec is not None
    status = "✓" if exists else "✗"
    print(f"  {status} {module_name}")
    return exists

def main():
    print("\n" + "=" * 70)
    print("RAFT PROJECT VERIFICATION")
    print("=" * 70)
    
    all_ok = True
    
    # Check project structure
    print("\n1. Checking Project Structure...")
    base_dir = os.path.dirname(os.path.dirname(__file__))
    
    files_to_check = [
        (os.path.join(base_dir, "requirements.txt"), "Requirements file"),
        (os.path.join(base_dir, "README.md"), "README"),
        (os.path.join(base_dir, "proto", "raft.proto"), "Proto file"),
        (os.path.join(base_dir, "src", "node.py"), "Node implementation"),
        (os.path.join(base_dir, "src", "raft_state.py"), "State machine"),
        (os.path.join(base_dir, "src", "kvstore.py"), "Key-value store"),
        (os.path.join(base_dir, "scripts", "generate_proto.py"), "Proto generator"),
        (os.path.join(base_dir, "scripts", "start_cluster.py"), "Cluster starter"),
        (os.path.join(base_dir, "scripts", "client.py"), "Client"),
    ]
    
    for filepath, description in files_to_check:
        if not check_file(filepath, description):
            all_ok = False
    
    # Check Python dependencies
    print("\n2. Checking Python Dependencies...")
    modules = ["grpc", "google.protobuf"]
    
    for module in modules:
        if not check_module(module):
            all_ok = False
            print(f"     → Run: pip install -r requirements.txt")
    
    # Check if proto files are generated
    print("\n3. Checking Generated gRPC Code...")
    proto_dir = os.path.join(base_dir, "proto")
    
    proto_files = [
        (os.path.join(proto_dir, "raft_pb2.py"), "Protocol buffer messages"),
        (os.path.join(proto_dir, "raft_pb2_grpc.py"), "gRPC service stubs"),
    ]
    
    proto_generated = True
    for filepath, description in proto_files:
        if not check_file(filepath, description):
            proto_generated = False
            all_ok = False
    
    if not proto_generated:
        print("\n  → Run: python scripts/generate_proto.py")
    
    # Check test files
    print("\n4. Checking Test Files...")
    tests_dir = os.path.join(base_dir, "tests")
    
    test_files = [
        "test_leader_election.py",
        "test_log_replication.py",
        "test_leader_failure.py",
        "test_follower_failure.py",
        "test_network_partition.py",
    ]
    
    for test_file in test_files:
        filepath = os.path.join(tests_dir, test_file)
        if not check_file(filepath, test_file):
            all_ok = False
    
    # Check Python version
    print("\n5. Checking Python Version...")
    py_version = sys.version_info
    version_ok = py_version.major == 3 and py_version.minor >= 8
    status = "✓" if version_ok else "✗"
    print(f"  {status} Python {py_version.major}.{py_version.minor}.{py_version.micro}")
    
    if not version_ok:
        print("     → Python 3.8 or higher required")
        all_ok = False
    
    # Summary
    print("\n" + "=" * 70)
    if all_ok:
        print("✓ ALL CHECKS PASSED - PROJECT IS READY!")
        print("\nNext steps:")
        print("  1. Generate gRPC code (if not done): python scripts/generate_proto.py")
        print("  2. Start cluster: python scripts/start_cluster.py")
        print("  3. Run tests: python tests/run_all_tests.py")
    else:
        print("✗ SOME CHECKS FAILED - PLEASE FIX ISSUES ABOVE")
        print("\nCommon fixes:")
        print("  1. Install dependencies: pip install -r requirements.txt")
        print("  2. Generate proto: python scripts/generate_proto.py")
    print("=" * 70 + "\n")
    
    return 0 if all_ok else 1

if __name__ == "__main__":
    sys.exit(main())
