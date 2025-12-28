# RAFT Consensus Algorithm Implementation

A complete implementation of the RAFT consensus algorithm in Python with gRPC for distributed systems and blockchain applications.

## 📋 Overview

This project implements the RAFT consensus algorithm as described in the paper ["In Search of an Understandable Consensus Algorithm"](https://raft.github.io/raft.pdf) by Diego Ongaro and John Ousterhout. It provides a working demonstration of:

- **Leader Election**: Automatic leader election with randomized timeouts
- **Log Replication**: Consistent log replication across all nodes
- **Fault Tolerance**: Recovery from leader failures, follower failures, and network partitions
- **Persistence**: File-based key-value storage for committed entries

## 🏗️ Architecture

```
RAFT/
├── proto/                  # gRPC protocol definitions
│   └── raft.proto         # RAFT RPC specifications
├── src/                   # Core implementation
│   ├── node.py           # Main RAFT node logic
│   ├── raft_state.py     # State machine and log management
│   └── kvstore.py        # Key-value storage
├── scripts/               # Cluster management
│   ├── generate_proto.py # Generate gRPC code
│   ├── start_cluster.py  # Start 5-node cluster
│   ├── run_node.py       # Run individual node
│   └── client.py         # Client interface
├── tests/                 # Fault tolerance tests
│   ├── test_leader_election.py
│   ├── test_log_replication.py
│   ├── test_leader_failure.py
│   ├── test_follower_failure.py
│   └── test_network_partition.py
└── data/                  # Persistent storage (auto-created)
```

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- pip package manager

### Installation

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Generate gRPC code:**
```bash
python scripts/generate_proto.py
```

### Running the Cluster

**Start a 5-node cluster:**
```bash
python scripts/start_cluster.py
```

This will start 5 nodes on localhost:
- node1: localhost:5001
- node2: localhost:5002
- node3: localhost:5003
- node4: localhost:5004
- node5: localhost:5005

**Stop the cluster:**
Press `Ctrl+C` in the terminal running the cluster.

## 💻 Usage

### Interactive Client

Start the interactive client to send commands:

```bash
python scripts/client.py
```

Commands:
```
raft> SET mykey myvalue     # Set a key-value pair
raft> GET mykey             # Get a value
raft> DELETE mykey          # Delete a key
raft> exit                  # Exit client
```

### Single Command

Execute a single command:
```bash
python scripts/client.py --command "SET test value"
```

### Custom Node Configuration

Run a custom node:
```bash
python scripts/run_node.py --node-id node1 --host localhost --port 5001 --peers "node2=localhost:5002,node3=localhost:5003"
```

## 🧪 Testing

### Run All Tests

```bash
# Test 1: Leader Election
python tests/test_leader_election.py

# Test 2: Log Replication
python tests/test_log_replication.py

# Test 3: Leader Failure
python tests/test_leader_failure.py

# Test 4: Follower Failure
python tests/test_follower_failure.py

# Test 5: Network Partition
python tests/test_network_partition.py
```

### Test Scenarios

#### 1. Leader Election
- Verifies that a leader is elected within election timeout
- Confirms only one leader exists at a time

#### 2. Log Replication
- Submits commands to the cluster
- Verifies data consistency across nodes

#### 3. Leader Failure
- Simulates leader crash
- Verifies new leader election
- Tests cluster operation after recovery

#### 4. Follower Failure
- Tests cluster with 1-2 failed followers
- Verifies majority (3/5) can still commit
- Tests synchronization when followers rejoin

#### 5. Network Partition
- Creates split: 3 nodes vs 2 nodes
- Verifies majority partition can commit
- Verifies minority partition cannot commit
- Tests cluster reconciliation after healing

## 🔧 Configuration Parameters

### Timing Parameters

Default values (can be modified in code):

```python
election_timeout_range = (150, 300)  # milliseconds
heartbeat_interval = 50              # milliseconds
```

### Cluster Size

Minimum recommended: **5 nodes** (tolerates 2 failures)

For different sizes:
- 3 nodes: tolerates 1 failure
- 5 nodes: tolerates 2 failures  ✓ Recommended
- 7 nodes: tolerates 3 failures

## 📊 Key Features Implemented

### Core RAFT Features

✅ **Leader Election**
- Randomized election timeouts
- RequestVote RPC
- Vote persistence
- Conflict resolution

✅ **Log Replication**
- AppendEntries RPC
- Log consistency checks
- Heartbeat mechanism
- Commit index advancement

✅ **Safety Properties**
- Election Safety (one leader per term)
- Leader Append-Only
- Log Matching
- Leader Completeness
- State Machine Safety

✅ **Fault Tolerance**
- Leader failure recovery
- Follower failure handling
- Network partition tolerance
- Automatic log synchronization

✅ **Persistence**
- Current term
- Vote record
- Log entries
- Committed key-value pairs

### Testing Features

✅ **Network Isolation**
- Programmatic node isolation via RPC
- Simulate network partitions
- Test split-brain scenarios

✅ **Client Interface**
- Interactive and batch modes
- Automatic leader discovery
- Command retry logic

## 🔍 How RAFT Works

### 1. Leader Election

When a follower doesn't receive heartbeats within the election timeout:
1. Increments term and becomes candidate
2. Votes for itself
3. Sends RequestVote RPCs to all peers
4. Becomes leader if receives majority votes

### 2. Log Replication

When the leader receives a command:
1. Appends entry to its log
2. Sends AppendEntries RPCs to followers
3. Waits for majority acknowledgment
4. Commits entry and applies to state machine
5. Notifies followers to commit

### 3. Handling Failures

**Leader Failure:**
- Followers detect missing heartbeats
- New election starts automatically
- New leader elected within 2x election timeout

**Follower Failure:**
- Leader continues with remaining nodes
- Majority still achieves consensus
- Failed follower catches up when rejoining

**Network Partition:**
- Majority partition elects leader and continues
- Minority partition cannot commit (no majority)
- Clusters reconcile when partition heals

## 📖 RAFT Algorithm Details

### Node States

1. **Follower**: Passive, responds to RPCs
2. **Candidate**: Requesting votes for leadership
3. **Leader**: Handles all client requests, replicates log

### Key Concepts

**Term**: Logical clock that increases monotonically
- Each term has at most one leader
- Servers update to higher terms when discovered

**Log Entry**: Contains:
- Command (e.g., "SET key value")
- Term number
- Index position

**Commit**: Entry is committed when:
- Replicated on majority of servers
- Leader's current term entry is replicated

### Safety Guarantees

1. **Election Safety**: At most one leader per term
2. **Leader Append-Only**: Leader never deletes/overwrites entries
3. **Log Matching**: If two logs contain entry with same index/term, all preceding entries are identical
4. **Leader Completeness**: If entry is committed, it will be in all future leader logs
5. **State Machine Safety**: If a server applies entry at index, no other server will apply different entry at that index

## 🎯 Project Requirements Fulfilled

This implementation satisfies all requirements from the assignment:

✅ **Network Simulation**: 5-node P2P network using gRPC
✅ **Leader Election**: RequestVote RPC with conflict resolution
✅ **Log Synchronization**: AppendEntries with consistency checks
✅ **Fault Handling**:
  - Leader failure: New election triggered
  - Follower failure: Cluster continues, auto-sync on rejoin
  - Network partition: Majority partition operational
✅ **Commit System**: Key-value storage for committed logs
✅ **Testing**: Comprehensive test suite for all scenarios

## 🐛 Troubleshooting

### Common Issues

**1. "Module not found" errors**
```bash
# Make sure you generated the proto files:
python scripts/generate_proto.py
```

**2. "Address already in use"**
```bash
# Kill existing processes on ports 5001-5005
# Windows:
netstat -ano | findstr :5001
taskkill /PID <pid> /F
```

**3. No leader elected**
- Wait 3-5 seconds for election to complete
- Check that all 5 nodes are running
- Verify no firewall blocking localhost connections

**4. Commands not committing**
- Verify at least 3/5 nodes are running (majority)
- Check for network partition
- Ensure you're sending commands to the leader

## 📚 References

1. **RAFT Paper**: [In Search of an Understandable Consensus Algorithm](https://raft.github.io/raft.pdf)
2. **RAFT Visualization**: [https://raft.github.io/](https://raft.github.io/)
3. **gRPC Documentation**: [https://grpc.io/docs/languages/python/](https://grpc.io/docs/languages/python/)

## 🔒 Limitations

### Current Implementation

- **Crash-Fault Tolerance Only**: Does not handle Byzantine (malicious) failures
- **Simplified Snapshot**: No log compaction implemented
- **In-Process Only**: All nodes run on same machine (suitable for testing)
- **Basic Membership**: No dynamic cluster membership changes

### RAFT vs pBFT

**RAFT Limitations** (addressed by pBFT):
- Cannot tolerate malicious nodes
- Assumes all nodes follow protocol
- No protection against data corruption
- Vulnerable to Byzantine failures

**When to use RAFT**:
✅ Trusted environment
✅ Crash faults only
✅ Simpler implementation
✅ Better performance

**When to use pBFT**:
✅ Untrusted environment
✅ Byzantine fault tolerance needed
✅ Can tolerate f malicious nodes out of 3f+1
✅ Blockchain applications

## 📝 Future Improvements

- [ ] Log compaction and snapshots
- [ ] Dynamic cluster membership (add/remove nodes)
- [ ] Configuration changes
- [ ] Read-only queries optimization
- [ ] Leadership transfer
- [ ] Pre-vote optimization
- [ ] pBFT implementation (bonus feature)

## 👥 Assignment Submission

For course submission, create zip file:

```
<MSSV1-MSSV2-MSSV3-MSSV4-MSSV5>.zip
 ├─ project_01_source/
 │   ├─ proto/
 │   ├─ src/
 │   ├─ scripts/
 │   ├─ tests/
 │   ├─ requirements.txt
 │   └─ README.md
 └─ project_01_report/
     └─ report.pdf
```

## 📄 License

This project is for educational purposes as part of the Blockchain and Applications course at the Knowledge Technology Department.

---

**Author**: [Your Name/Team]  
**Course**: Blockchain và ứng dụng  
**Institution**: Bộ môn Công nghệ Tri thức
