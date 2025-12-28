# RAFT Implementation - Architecture & Workflow Diagrams

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          RAFT CLUSTER (5 Nodes)                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐          │
│  │  Node 1  │    │  Node 2  │    │  Node 3  │    │  Node 4  │ ┌─────┐  │
│  │  :5001   │◄──►│  :5002   │◄──►│  :5003   │◄──►│  :5004   │◄│Node5│  │
│  │ LEADER   │    │ FOLLOWER │    │ FOLLOWER │    │ FOLLOWER │ │:5005│  │
│  └────┬─────┘    └──────────┘    └──────────┘    └──────────┘ └─────┘  │
│       │                                                                   │
│       │ AppendEntries RPC (Heartbeat + Log Replication)                 │
│       └──────────────────────────────────────────────────────────►       │
│                                                                           │
│  ◄────────────────── RequestVote RPC (Elections) ────────────────────►  │
│                                                                           │
└─────────────────────────────────────────────────────────────────────────┘
                                    ▲
                                    │ gRPC
                                    │ SubmitCommand
                                    │
                            ┌───────┴────────┐
                            │     CLIENT     │
                            │  (client.py)   │
                            └────────────────┘
```

## Node Internal Architecture

```
┌────────────────────────────────────────────────────────────────────┐
│                         RaftNode (node.py)                         │
├────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │                  RAFT State Machine                         │   │
│  │                 (raft_state.py)                             │   │
│  ├────────────────────────────────────────────────────────────┤   │
│  │  Persistent State (Disk):                                  │   │
│  │    • current_term (election term number)                   │   │
│  │    • voted_for (candidate voted for in current term)       │   │
│  │    • log[] (log entries; each entry contains command)      │   │
│  ├────────────────────────────────────────────────────────────┤   │
│  │  Volatile State (Memory):                                  │   │
│  │    • state (FOLLOWER | CANDIDATE | LEADER)                 │   │
│  │    • commit_index (highest log entry known to be committed)│   │
│  │    • last_applied (highest log entry applied to state)     │   │
│  ├────────────────────────────────────────────────────────────┤   │
│  │  Leader State (Volatile, reinitialized after election):    │   │
│  │    • next_index[] (for each server, next log to send)      │   │
│  │    • match_index[] (for each server, highest known replicated)│ │
│  └────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │              Key-Value Store (kvstore.py)                  │   │
│  ├────────────────────────────────────────────────────────────┤   │
│  │  • Persistent JSON file: data/node_X_db.json              │   │
│  │  • Operations: SET, GET, DELETE                            │   │
│  │  • Thread-safe with RLock                                  │   │
│  │  • Applies committed log entries                           │   │
│  └────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │               gRPC Service Handlers                        │   │
│  ├────────────────────────────────────────────────────────────┤   │
│  │  • RequestVote(term, candidateId, lastLogIndex, ...)       │   │
│  │  • AppendEntries(term, leaderId, entries[], ...)           │   │
│  │  • SubmitCommand(command)                                  │   │
│  │  • Isolate(isolated_nodes[])  [Testing]                    │   │
│  └────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │                    Background Threads                       │   │
│  ├────────────────────────────────────────────────────────────┤   │
│  │  1. Election Timer Thread:                                 │   │
│  │     → Monitors heartbeat timeout                           │   │
│  │     → Starts election if timeout                           │   │
│  │                                                             │   │
│  │  2. Heartbeat Sender Thread (Leader only):                 │   │
│  │     → Sends periodic AppendEntries (50ms interval)         │   │
│  │     → Includes log entries if any                          │   │
│  │                                                             │   │
│  │  3. Apply Thread:                                          │   │
│  │     → Monitors commit_index vs last_applied                │   │
│  │     → Applies committed entries to key-value store         │   │
│  └────────────────────────────────────────────────────────────┘   │
│                                                                      │
└────────────────────────────────────────────────────────────────────┘
```

## Leader Election Workflow

```
Initial State: All nodes are FOLLOWERS
             │
             │ (Election Timeout: 150-300ms random)
             ▼
     ┌───────────────┐
     │ TIMEOUT       │
     │ No heartbeat  │
     │ from leader   │
     └───────┬───────┘
             │
             ▼
     ┌───────────────────┐
     │ Become CANDIDATE  │
     │ • term++          │
     │ • vote for self   │
     │ • reset timeout   │
     └───────┬───────────┘
             │
             ▼
     ┌─────────────────────────┐
     │ Send RequestVote RPC    │
     │ to all peers            │
     └──────┬─────────┬────────┘
            │         │
    ┌───────▼───┐  ┌─▼─────────┐
    │ Receive   │  │ Discover  │
    │ majority  │  │ higher    │
    │ votes     │  │ term      │
    └─────┬─────┘  └─────┬─────┘
          │              │
          ▼              ▼
    ┌───────────┐  ┌──────────┐
    │  Become   │  │ Become   │
    │  LEADER   │  │ FOLLOWER │
    └─────┬─────┘  └──────────┘
          │
          ▼
    ┌──────────────────┐
    │ Initialize        │
    │ • next_index[]    │
    │ • match_index[]   │
    └─────┬─────────────┘
          │
          ▼
    ┌──────────────────┐
    │ Send heartbeats   │
    │ (AppendEntries)   │
    │ every 50ms        │
    └───────────────────┘
```

## Log Replication Workflow

```
Client submits command
         │
         ▼
┌─────────────────────┐
│ Leader receives     │
│ command             │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│ Leader appends to   │
│ local log           │
│ Index = N           │
└──────┬──────────────┘
       │
       ▼
┌──────────────────────┐
│ Send AppendEntries   │
│ RPC to all followers │
│ with new entry       │
└──────┬───────────────┘
       │
       ├──────────────────────────┐
       │                          │
       ▼                          ▼
┌──────────────┐          ┌──────────────┐
│ Follower 1   │          │ Follower 2   │
│ receives,    │          │ receives,    │
│ checks       │          │ checks       │
│ consistency  │          │ consistency  │
└──────┬───────┘          └──────┬───────┘
       │                         │
       │ (prev_log matches?)     │
       │                         │
       ▼                         ▼
┌──────────────┐          ┌──────────────┐
│ Append entry │          │ Append entry │
│ to log       │          │ to log       │
└──────┬───────┘          └──────┬───────┘
       │                         │
       │ Send ACK                │ Send ACK
       └────────┬────────────────┘
                │
                ▼
       ┌─────────────────┐
       │ Leader receives │
       │ ACKs            │
       └────────┬────────┘
                │
                ▼
       ┌─────────────────┐
       │ Majority ACKs?  │
       │ (3 out of 5)    │
       └────────┬────────┘
                │ Yes
                ▼
       ┌─────────────────┐
       │ Advance         │
       │ commit_index    │
       └────────┬────────┘
                │
                ▼
       ┌─────────────────┐
       │ Apply to state  │
       │ machine         │
       │ (KV store)      │
       └────────┬────────┘
                │
                ▼
       ┌─────────────────┐
       │ Notify followers│
       │ in next         │
       │ AppendEntries   │
       └────────┬────────┘
                │
                ▼
       ┌─────────────────┐
       │ Followers commit│
       │ and apply       │
       └─────────────────┘
```

## Failure Scenarios

### Leader Failure

```
    BEFORE                    FAILURE                   RECOVERY
    
┌─────────┐              ┌─────────┐              ┌─────────┐
│ Leader  │              │ Leader  │              │ Old     │
│ Node 1  │──heartbeat──►│ Node 1  │ ✗ CRASH     │ Leader  │
│         │              │  (DOWN) │              │ (DOWN)  │
└────┬────┘              └─────────┘              └─────────┘
     │
     │                    ┌─────────┐              ┌─────────┐
     ├──heartbeat────────►│Follower │              │ NEW     │
     │                    │ Node 2  │──timeout────►│ LEADER  │
     │                    └─────────┘   election   │ Node 2  │
     │                                              └────┬────┘
     │                    ┌─────────┐                   │
     ├──heartbeat────────►│Follower │              ┌───▼────┐
     │                    │ Node 3  │◄─heartbeat───│Follower│
     │                    └─────────┘              │ Node 3 │
     │                                             └────────┘
     │                    ┌─────────┐
     └──heartbeat────────►│Follower │              Cluster
                          │ Node 4  │              operational
                          └─────────┘              with new leader
                          
Timeline: ~200-600ms for new election
```

### Network Partition

```
    BEFORE PARTITION          DURING PARTITION           AFTER HEALING
    
    ┌───────────┐            ┌───────────┐              ┌───────────┐
    │  Leader   │            │  Leader   │              │  Leader   │
    │  Node 1   │            │  Node 1   │              │  Node 1   │
    └─────┬─────┘            └─────┬─────┘              └─────┬─────┘
          │                        │                           │
    ┌─────┼─────┐            GROUP A (Majority)          ┌────┼─────┐
    │     │     │            CAN COMMIT                   │    │     │
    │     │     │            ┌─────┴─────┐               │    │     │
    ▼     ▼     ▼            ▼           ▼               ▼    ▼     ▼
┌──────┬──────┬──────┐   ┌──────┐   ┌──────┐        ┌──────┬──────┬──────┐
│Node 2│Node 3│Node 4│   │Node 2│   │Node 3│        │Node 2│Node 3│Node 4│
└──────┴──────┴──────┘   └──────┘   └──────┘        └──────┴──────┴──────┘
                              ║                             │
    Full connectivity         ║ NETWORK                     │
    All nodes can             ║ PARTITION                   │
    communicate               ║                             │
                              ║                             ▼
                         ┌────╩─────┐                  ┌──────┐
                         │          │                  │Node 4│
                         ▼          ▼                  │Node 5│
                     ┌──────┐  ┌──────┐               └──────┘
                     │Node 4│  │Node 5│               Sync logs
                     └──────┘  └──────┘               from leader
                         
                     GROUP B (Minority)              Full consensus
                     CANNOT COMMIT                   restored
                     No leader election
                     Wait for majority
```

## File System Layout

```
data/                           (Created during runtime)
├── node_1_db.json             ← Key-value store for node 1
├── node_1_state.json          ← RAFT state (term, voted_for, log)
├── node_2_db.json
├── node_2_state.json
├── node_3_db.json
├── node_3_state.json
├── node_4_db.json
├── node_4_state.json
├── node_5_db.json
└── node_5_state.json

Example node_1_db.json:
{
  "key1": "value1",
  "key2": "value2",
  "name": "Alice"
}

Example node_1_state.json:
{
  "current_term": 5,
  "voted_for": "node1",
  "log": [
    {"term": 1, "command": "SET key1 value1", "index": 1},
    {"term": 3, "command": "SET key2 value2", "index": 2},
    {"term": 5, "command": "SET name Alice", "index": 3}
  ]
}
```

## Thread Model

```
┌──────────────────────────────────────────────────────────────┐
│                        Main Thread                            │
│  • Initializes node                                           │
│  • Starts gRPC server                                         │
│  • Waits for termination signal                               │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│                    Election Timer Thread                      │
│  Loop:                                                        │
│    1. Check time since last heartbeat                        │
│    2. If timeout: Start election                             │
│    3. Sleep 10ms                                              │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│                  Heartbeat Sender Thread                      │
│  Loop (only if LEADER):                                       │
│    1. Send AppendEntries RPC to all followers                │
│    2. Include log entries if any                             │
│    3. Update next_index/match_index                          │
│    4. Sleep 50ms                                              │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│                     Apply Thread                              │
│  Loop:                                                        │
│    1. If last_applied < commit_index:                        │
│       - Get log entry at last_applied + 1                    │
│       - Apply command to key-value store                     │
│       - Increment last_applied                               │
│    2. Sleep 100ms                                             │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│                    gRPC Server Threads                        │
│  ThreadPoolExecutor (10 workers):                            │
│    • Handle incoming RequestVote RPCs                        │
│    • Handle incoming AppendEntries RPCs                      │
│    • Handle client SubmitCommand requests                    │
│    • Handle isolation requests (testing)                     │
└──────────────────────────────────────────────────────────────┘
```

## Data Flow: Client Request

```
┌────────┐
│ Client │ SET key value
└───┬────┘
    │ 1. SubmitCommand RPC
    ▼
┌─────────────┐
│   Node 2    │ Not leader, redirect
│ (Follower)  │────────┐
└─────────────┘        │
                       │ 2. Retry with leader
                       ▼
                 ┌─────────────┐
                 │   Node 1    │
                 │  (Leader)   │
                 └──────┬──────┘
                        │ 3. Append to log
                        │
                        ▼
                 ┌──────────────────┐
                 │ Log Entry:        │
                 │ index=5, term=3  │
                 │ cmd="SET key val"│
                 └──────┬───────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
        ▼               ▼               ▼
    ┌───────┐       ┌───────┐       ┌───────┐
    │Node 2 │       │Node 3 │       │Node 4 │
    │Append │       │Append │       │Append │
    │  ACK  │       │  ACK  │       │  ACK  │
    └───┬───┘       └───┬───┘       └───┬───┘
        │               │               │
        └───────────────┼───────────────┘
                        │ 4. Majority ACKs (3/5)
                        ▼
                 ┌──────────────┐
                 │ Leader       │
                 │ commit_index │
                 │ = 5          │
                 └──────┬───────┘
                        │ 5. Apply to KV store
                        ▼
                 ┌──────────────┐
                 │ kvstore      │
                 │ {"key":"val"}│
                 └──────┬───────┘
                        │ 6. Return success
                        ▼
                 ┌──────────────┐
                 │ Client gets  │
                 │ "OK: SET..." │
                 └──────────────┘
```

## Summary

This architecture provides:
- ✅ **Fault Tolerance**: Survives 2 node failures (in 5-node cluster)
- ✅ **Consistency**: All nodes have identical committed data
- ✅ **Availability**: Cluster operational with majority
- ✅ **Partition Tolerance**: Handles network splits gracefully

**Key Insight**: RAFT uses majority consensus (quorum) to ensure safety while maintaining liveness when majority is available.
