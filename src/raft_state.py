"""
RAFT State Machine - manages node state, logs, and persistence
"""
import json
import os
import threading
from enum import Enum
from typing import List, Optional, Dict
import time


class NodeState(Enum):
    """RAFT node states"""
    FOLLOWER = "follower"
    CANDIDATE = "candidate"
    LEADER = "leader"


class LogEntry:
    """Represents a single log entry"""
    
    def __init__(self, term: int, command: str, index: int):
        self.term = term
        self.command = command
        self.index = index
    
    def to_dict(self):
        return {
            "term": self.term,
            "command": self.command,
            "index": self.index
        }
    
    @staticmethod
    def from_dict(data):
        return LogEntry(data["term"], data["command"], data["index"])
    
    def __repr__(self):
        return f"LogEntry(index={self.index}, term={self.term}, cmd={self.command})"


class RaftState:
    """
    Manages RAFT consensus state for a node
    Implements persistent and volatile state as per RAFT paper
    """
    
    def __init__(self, node_id: str, data_dir: str = "data"):
        """
        Initialize RAFT state
        
        Args:
            node_id: Unique identifier for this node
            data_dir: Directory for persistent state
        """
        self.node_id = node_id
        self.data_dir = data_dir
        self.state_file = os.path.join(data_dir, f"node_{node_id}_state.json")
        
        # Thread safety
        self.lock = threading.RLock()
        
        # Persistent state (must be saved to disk)
        self.current_term = 0
        self.voted_for: Optional[str] = None
        self.log: List[LogEntry] = []
        
        # Volatile state on all servers
        self.commit_index = 0  # index of highest log entry known to be committed
        self.last_applied = 0  # index of highest log entry applied to state machine
        self.state = NodeState.FOLLOWER
        self.current_leader: Optional[str] = None
        self.last_heartbeat = time.time()
        
        # Volatile state on leaders (reinitialized after election)
        self.next_index: Dict[str, int] = {}  # for each server, index of next log entry to send
        self.match_index: Dict[str, int] = {}  # for each server, index of highest log entry known to be replicated
        
        # Election state
        self.votes_received = set()
        
        # Create data directory
        os.makedirs(data_dir, exist_ok=True)
        
        # Load persistent state
        self._load_state()
    
    def _load_state(self):
        """Load persistent state from disk"""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                    self.current_term = data.get("current_term", 0)
                    self.voted_for = data.get("voted_for")
                    self.log = [LogEntry.from_dict(entry) for entry in data.get("log", [])]
                    print(f"[State-{self.node_id}] Loaded state: term={self.current_term}, log_len={len(self.log)}")
        except Exception as e:
            print(f"[State-{self.node_id}] Error loading state: {e}")
    
    def _save_state(self):
        """Save persistent state to disk"""
        try:
            data = {
                "current_term": self.current_term,
                "voted_for": self.voted_for,
                "log": [entry.to_dict() for entry in self.log]
            }
            with open(self.state_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[State-{self.node_id}] Error saving state: {e}")
    
    def update_term(self, term: int):
        """Update current term and reset voted_for"""
        with self.lock:
            if term > self.current_term:
                self.current_term = term
                self.voted_for = None
                self._save_state()
                print(f"[State-{self.node_id}] Updated term to {term}")
                return True
            return False
    
    def set_voted_for(self, candidate_id: str):
        """Record vote for a candidate"""
        with self.lock:
            self.voted_for = candidate_id
            self._save_state()
            print(f"[State-{self.node_id}] Voted for {candidate_id} in term {self.current_term}")
    
    def append_log(self, term: int, command: str) -> int:
        """
        Append a new entry to the log
        
        Returns:
            Index of the newly appended entry
        """
        with self.lock:
            index = len(self.log) + 1
            entry = LogEntry(term, command, index)
            self.log.append(entry)
            self._save_state()
            print(f"[State-{self.node_id}] Appended log entry: {entry}")
            return index
    
    def get_last_log_info(self):
        """Get (index, term) of last log entry"""
        with self.lock:
            if self.log:
                last = self.log[-1]
                return last.index, last.term
            return 0, 0
    
    def get_log_entry(self, index: int) -> Optional[LogEntry]:
        """Get log entry at index (1-based)"""
        with self.lock:
            if 0 < index <= len(self.log):
                return self.log[index - 1]
            return None
    
    def truncate_log(self, from_index: int):
        """Remove log entries from index onwards"""
        with self.lock:
            if from_index <= len(self.log):
                self.log = self.log[:from_index - 1]
                self._save_state()
                print(f"[State-{self.node_id}] Truncated log from index {from_index}")
    
    def append_entries(self, prev_log_index: int, prev_log_term: int, 
                      entries: List[LogEntry]) -> bool:
        """
        Append entries as per RAFT AppendEntries RPC
        
        Returns:
            True if entries were appended successfully
        """
        with self.lock:
            # Check if log contains entry at prev_log_index with term prev_log_term
            if prev_log_index > 0:
                if prev_log_index > len(self.log):
                    print(f"[State-{self.node_id}] Log too short: need {prev_log_index}, have {len(self.log)}")
                    return False
                
                if self.log[prev_log_index - 1].term != prev_log_term:
                    print(f"[State-{self.node_id}] Term mismatch at {prev_log_index}")
                    return False
            
            # Delete conflicting entries and append new ones
            if entries:
                # Find where new entries should start
                log_index = prev_log_index
                for entry in entries:
                    log_index += 1
                    if log_index <= len(self.log):
                        # Check for conflict
                        if self.log[log_index - 1].term != entry.term:
                            # Delete this and all following entries
                            self.log = self.log[:log_index - 1]
                            self.log.append(entry)
                    else:
                        # Append new entry
                        self.log.append(entry)
                
                self._save_state()
                print(f"[State-{self.node_id}] Appended {len(entries)} entries, log_len={len(self.log)}")
            
            return True
    
    def update_commit_index(self, leader_commit: int):
        """Update commit index based on leader's commit"""
        with self.lock:
            if leader_commit > self.commit_index:
                self.commit_index = min(leader_commit, len(self.log))
                print(f"[State-{self.node_id}] Updated commit_index to {self.commit_index}")
    
    def become_follower(self, term: int, leader_id: Optional[str] = None):
        """Transition to follower state"""
        with self.lock:
            self.state = NodeState.FOLLOWER
            self.current_leader = leader_id
            self.update_term(term)
            self.last_heartbeat = time.time()
            print(f"[State-{self.node_id}] Became FOLLOWER in term {term}, leader={leader_id}")
    
    def become_candidate(self):
        """Transition to candidate state"""
        with self.lock:
            self.state = NodeState.CANDIDATE
            self.current_term += 1
            self.voted_for = self.node_id
            self.votes_received = {self.node_id}
            self.current_leader = None
            self._save_state()
            print(f"[State-{self.node_id}] Became CANDIDATE in term {self.current_term}")
    
    def become_leader(self, peer_ids: List[str]):
        """Transition to leader state"""
        with self.lock:
            self.state = NodeState.LEADER
            self.current_leader = self.node_id
            
            # Initialize leader state
            next_index = len(self.log) + 1
            self.next_index = {peer_id: next_index for peer_id in peer_ids}
            self.match_index = {peer_id: 0 for peer_id in peer_ids}
            
            print(f"[State-{self.node_id}] Became LEADER in term {self.current_term}")
    
    def record_vote(self, voter_id: str):
        """Record a vote received"""
        with self.lock:
            self.votes_received.add(voter_id)
    
    def has_majority(self, cluster_size: int) -> bool:
        """Check if received votes constitute a majority"""
        with self.lock:
            return len(self.votes_received) > cluster_size // 2
    
    def update_heartbeat(self):
        """Update last heartbeat time"""
        with self.lock:
            self.last_heartbeat = time.time()
    
    def time_since_heartbeat(self) -> float:
        """Get time since last heartbeat"""
        with self.lock:
            return time.time() - self.last_heartbeat
