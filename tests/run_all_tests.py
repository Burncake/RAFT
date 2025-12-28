"""
Run all tests sequentially
"""
import subprocess
import sys
import os

def run_test(test_file, description):
    """Run a single test"""
    print("\n" + "=" * 80)
    print(f"Running: {description}")
    print("=" * 80)
    
    result = subprocess.run(
        [sys.executable, test_file],
        capture_output=False
    )
    
    return result.returncode == 0

def main():
    """Run all tests"""
    tests_dir = os.path.dirname(__file__)
    
    tests = [
        ("test_leader_election.py", "Leader Election Test"),
        ("test_log_replication.py", "Log Replication Test"),
        ("test_leader_failure.py", "Leader Failure Test"),
        ("test_follower_failure.py", "Follower Failure Test"),
        ("test_network_partition.py", "Network Partition Test"),
    ]
    
    print("\n" + "=" * 80)
    print("RAFT CONSENSUS ALGORITHM - TEST SUITE")
    print("=" * 80)
    print("\nNOTE: Make sure the cluster is running before executing tests!")
    print("Start cluster: python scripts/start_cluster.py")
    print("\nPress Enter to continue or Ctrl+C to cancel...")
    
    try:
        input()
    except KeyboardInterrupt:
        print("\nCancelled.")
        sys.exit(1)
    
    results = {}
    
    for test_file, description in tests:
        test_path = os.path.join(tests_dir, test_file)
        success = run_test(test_path, description)
        results[description] = success
    
    # Summary
    print("\n\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    for test_name, success in results.items():
        status = "✓ PASSED" if success else "✗ FAILED"
        print(f"{status}: {test_name}")
    
    total = len(results)
    passed = sum(1 for s in results.values() if s)
    
    print(f"\nTotal: {passed}/{total} tests passed")
    print("=" * 80 + "\n")
    
    sys.exit(0 if passed == total else 1)

if __name__ == "__main__":
    main()
