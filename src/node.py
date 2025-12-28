"""
RAFT Node - Core implementation with leader election and log replication
"""
import grpc
from concurrent import futures
import threading
import time
import random
import sys
import os

# Add proto directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'proto'))

# Import generated gRPC code (will be generated later)
try:
    import raft_pb2
    import raft_pb2_grpc
except ImportError:
    print("Warning: gRPC proto files not generated yet. Run generate_proto.py first.")

from raft_state import RaftState, NodeState, LogEntry
from kvstore import KeyValueStore


class RaftNode:
    """
    RAFT consensus node implementation
    """
    
    def __init__(self, node_id: str, host: str, port: int, peers: dict, 
                 election_timeout_range=(150, 300), heartbeat_interval=50):
        """
        Initialize RAFT node
        
        Args:
            node_id: Unique identifier for this node
            host: Host address
            port: Port number
            peers: Dictionary of {node_id: "host:port"} for all peers (excluding self)
            election_timeout_range: Range for random election timeout in ms
            heartbeat_interval: Leader heartbeat interval in ms
        """
        self.node_id = node_id
        self.host = host
        self.port = port
        self.address = f"{host}:{port}"
        self.peers = peers  # {node_id: address}
        
        # Timing parameters (in milliseconds)
        self.election_timeout_range = election_timeout_range
        self.heartbeat_interval = heartbeat_interval / 1000.0  # Convert to seconds
        self.election_timeout = self._get_random_election_timeout()
        
        # RAFT state and storage
        self.state = RaftState(node_id)
        self.kvstore = KeyValueStore(node_id)
        
        # Network isolation for testing
        self.isolated_nodes = set()
        self.isolation_lock = threading.Lock()
        
        # gRPC connections to peers
        self.peer_stubs = {}
        self._connect_to_peers()
        
        # Threading
        self.running = False
        self.election_timer_thread = None
        self.heartbeat_thread = None
        self.apply_thread = None
        
        # Server
        self.server = None
    
    def _get_random_election_timeout(self):
        """Get random election timeout"""
        return random.randint(*self.election_timeout_range) / 1000.0  # Convert to seconds
    
    def _connect_to_peers(self):
        """Establish gRPC connections to all peers"""
        for peer_id, peer_address in self.peers.items():
            try:
                channel = grpc.insecure_channel(peer_address)
                self.peer_stubs[peer_id] = raft_pb2_grpc.RaftServiceStub(channel)
                print(f"[Node-{self.node_id}] Connected to peer {peer_id} at {peer_address}")
            except Exception as e:
                print(f"[Node-{self.node_id}] Error connecting to {peer_id}: {e}")
    
    def _is_isolated_from(self, peer_id: str) -> bool:
        """Check if this node is isolated from a peer"""
        with self.isolation_lock:
            return peer_id in self.isolated_nodes
    
    # ==================== RPC Handlers ====================
    
    def handle_request_vote(self, request):
        """Handle RequestVote RPC"""
        with self.state.lock:
            print(f"[Node-{self.node_id}] Received RequestVote from {request.candidate_id} for term {request.term}")
            
            # Update term if needed
            if request.term > self.state.current_term:
                self.state.become_follower(request.term)
            
            vote_granted = False
            
            # Check if we can vote for this candidate
            if request.term < self.state.current_term:
                # Candidate's term is outdated
                pass
            elif self.state.voted_for is not None and self.state.voted_for != request.candidate_id:
                # Already voted for someone else in this term
                pass
            else:
                # Check if candidate's log is at least as up-to-date as ours
                last_log_index, last_log_term = self.state.get_last_log_info()
                
                log_ok = (request.last_log_term > last_log_term or 
                         (request.last_log_term == last_log_term and 
                          request.last_log_index >= last_log_index))
                
                if log_ok:
                    vote_granted = True
                    self.state.set_voted_for(request.candidate_id)
                    self.state.update_heartbeat()  # Reset election timer
                    print(f"[Node-{self.node_id}] Granted vote to {request.candidate_id}")
            
            return raft_pb2.RequestVoteResponse(
                term=self.state.current_term,
                vote_granted=vote_granted
            )
    
    def handle_append_entries(self, request):
        """Handle AppendEntries RPC (log replication and heartbeat)"""
        with self.state.lock:
            # Update term if needed
            if request.term > self.state.current_term:
                self.state.become_follower(request.term, request.leader_id)
            
            success = False
            
            if request.term < self.state.current_term:
                # Leader's term is outdated
                print(f"[Node-{self.node_id}] Rejected AppendEntries: stale term {request.term}")
            else:
                # Valid leader
                self.state.become_follower(request.term, request.leader_id)
                self.state.update_heartbeat()
                
                # Try to append entries
                entries = [LogEntry(e.term, e.command, e.index) for e in request.entries]
                success = self.state.append_entries(
                    request.prev_log_index, 
                    request.prev_log_term, 
                    entries
                )
                
                if success:
                    # Update commit index
                    self.state.update_commit_index(request.leader_commit)
                    
                    if entries:
                        print(f"[Node-{self.node_id}] Appended {len(entries)} entries from leader")
                else:
                    print(f"[Node-{self.node_id}] Failed to append entries")
            
            return raft_pb2.AppendEntriesResponse(
                term=self.state.current_term,
                success=success
            )
    
    def handle_submit_command(self, request):
        """Handle client command submission"""
        with self.state.lock:
            if self.state.state != NodeState.LEADER:
                # Not the leader, redirect to current leader
                return raft_pb2.ClientResponse(
                    success=False,
                    message="Not the leader",
                    leader_id=self.state.current_leader or "unknown"
                )
            
            # Append command to log
            index = self.state.append_log(self.state.current_term, request.command)
            print(f"[Node-{self.node_id}] Leader received command: {request.command}, index={index}")
            
            # Wait for commit (simplified - in real implementation, would use condition variable)
            timeout = 5.0  # 5 second timeout
            start_time = time.time()
            while time.time() - start_time < timeout:
                if self.state.commit_index >= index:
                    return raft_pb2.ClientResponse(
                        success=True,
                        message=f"Command committed at index {index}",
                        leader_id=self.node_id
                    )
                time.sleep(0.1)
            
            return raft_pb2.ClientResponse(
                success=False,
                message="Timeout waiting for commit",
                leader_id=self.node_id
            )
    
    def handle_isolate(self, request):
        """Handle isolation request (for testing)"""
        with self.isolation_lock:
            self.isolated_nodes = set(request.isolated_nodes)
            print(f"[Node-{self.node_id}] Isolated from: {self.isolated_nodes}")
            return raft_pb2.IsolateResponse(
                success=True,
                message=f"Isolated from {len(self.isolated_nodes)} nodes"
            )
    
    # ==================== Leader Election ====================
    
    def _start_election(self):
        """Start a new election"""
        with self.state.lock:
            self.state.become_candidate()
            current_term = self.state.current_term
            last_log_index, last_log_term = self.state.get_last_log_info()
            
            print(f"[Node-{self.node_id}] Starting election for term {current_term}")
        
        # Request votes from all peers
        votes_received = 1  # Vote for self
        votes_needed = (len(self.peers) + 1) // 2 + 1
        
        for peer_id, stub in self.peer_stubs.items():
            if self._is_isolated_from(peer_id):
                continue
            
            try:
                request = raft_pb2.RequestVoteRequest(
                    term=current_term,
                    candidate_id=self.node_id,
                    last_log_index=last_log_index,
                    last_log_term=last_log_term
                )
                
                response = stub.RequestVote(request, timeout=0.5)
                
                with self.state.lock:
                    if response.term > self.state.current_term:
                        # Discovered higher term, step down
                        self.state.become_follower(response.term)
                        return
                    
                    if response.vote_granted and self.state.state == NodeState.CANDIDATE:
                        self.state.record_vote(peer_id)
                        votes_received += 1
                        print(f"[Node-{self.node_id}] Received vote from {peer_id} ({votes_received}/{votes_needed})")
                        
                        if votes_received >= votes_needed:
                            # Won election
                            self.state.become_leader(list(self.peers.keys()))
                            print(f"[Node-{self.node_id}] WON ELECTION for term {current_term}")
                            return
            
            except Exception as e:
                print(f"[Node-{self.node_id}] Error requesting vote from {peer_id}: {e}")
    
    def _election_timer(self):
        """Election timer thread"""
        while self.running:
            time.sleep(0.01)  # Check every 10ms
            
            with self.state.lock:
                if self.state.state == NodeState.LEADER:
                    continue
                
                if self.state.time_since_heartbeat() > self.election_timeout:
                    # Election timeout - start election
                    self.election_timeout = self._get_random_election_timeout()
            
            # Start election outside of lock to avoid deadlock
            if self.state.state != NodeState.LEADER and self.state.time_since_heartbeat() > self.election_timeout:
                self._start_election()
    
    # ==================== Log Replication ====================
    
    def _send_append_entries(self, peer_id: str, stub):
        """Send AppendEntries RPC to a peer"""
        if self._is_isolated_from(peer_id):
            return
        
        with self.state.lock:
            if self.state.state != NodeState.LEADER:
                return
            
            next_index = self.state.next_index[peer_id]
            prev_log_index = next_index - 1
            prev_log_term = 0
            
            if prev_log_index > 0:
                prev_entry = self.state.get_log_entry(prev_log_index)
                if prev_entry:
                    prev_log_term = prev_entry.term
            
            # Get entries to send
            entries = []
            if next_index <= len(self.state.log):
                for i in range(next_index - 1, len(self.state.log)):
                    entry = self.state.log[i]
                    entries.append(raft_pb2.LogEntry(
                        term=entry.term,
                        command=entry.command,
                        index=entry.index
                    ))
            
            request = raft_pb2.AppendEntriesRequest(
                term=self.state.current_term,
                leader_id=self.node_id,
                prev_log_index=prev_log_index,
                prev_log_term=prev_log_term,
                entries=entries,
                leader_commit=self.state.commit_index
            )
        
        try:
            response = stub.AppendEntries(request, timeout=0.5)
            
            with self.state.lock:
                if response.term > self.state.current_term:
                    # Discovered higher term, step down
                    self.state.become_follower(response.term)
                    return
                
                if self.state.state != NodeState.LEADER:
                    return
                
                if response.success:
                    # Update next_index and match_index
                    self.state.next_index[peer_id] = next_index + len(entries)
                    self.state.match_index[peer_id] = next_index + len(entries) - 1
                    
                    # Try to advance commit_index
                    self._advance_commit_index()
                else:
                    # Decrement next_index and retry
                    self.state.next_index[peer_id] = max(1, next_index - 1)
        
        except Exception as e:
            pass  # Silently ignore RPC failures
    
    def _advance_commit_index(self):
        """Advance commit index if majority of followers have replicated"""
        with self.state.lock:
            if self.state.state != NodeState.LEADER:
                return
            
            # Find highest index replicated on majority
            for n in range(self.state.commit_index + 1, len(self.state.log) + 1):
                if self.state.get_log_entry(n).term != self.state.current_term:
                    continue
                
                replicated_count = 1  # Leader has it
                for peer_id in self.peers:
                    if self.state.match_index[peer_id] >= n:
                        replicated_count += 1
                
                if replicated_count > (len(self.peers) + 1) // 2:
                    self.state.commit_index = n
                    print(f"[Node-{self.node_id}] Advanced commit_index to {n}")
    
    def _heartbeat_sender(self):
        """Leader heartbeat thread"""
        while self.running:
            with self.state.lock:
                if self.state.state == NodeState.LEADER:
                    # Send AppendEntries to all peers
                    for peer_id, stub in self.peer_stubs.items():
                        self._send_append_entries(peer_id, stub)
            
            time.sleep(self.heartbeat_interval)
    
    def _apply_committed_entries(self):
        """Apply committed log entries to state machine"""
        while self.running:
            time.sleep(0.1)
            
            with self.state.lock:
                while self.state.last_applied < self.state.commit_index:
                    self.state.last_applied += 1
                    entry = self.state.get_log_entry(self.state.last_applied)
                    
                    if entry:
                        print(f"[Node-{self.node_id}] Applying: {entry.command}")
                        result = self.kvstore.apply_command(entry.command)
                        print(f"[Node-{self.node_id}] Result: {result}")
    
    # ==================== Server Management ====================
    
    def start(self):
        """Start the RAFT node"""
        self.running = True
        
        # Start threads
        self.election_timer_thread = threading.Thread(target=self._election_timer, daemon=True)
        self.heartbeat_thread = threading.Thread(target=self._heartbeat_sender, daemon=True)
        self.apply_thread = threading.Thread(target=self._apply_committed_entries, daemon=True)
        
        self.election_timer_thread.start()
        self.heartbeat_thread.start()
        self.apply_thread.start()
        
        # Start gRPC server
        self.server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        raft_pb2_grpc.add_RaftServiceServicer_to_server(RaftServicer(self), self.server)
        self.server.add_insecure_port(f'{self.host}:{self.port}')
        self.server.start()
        
        print(f"[Node-{self.node_id}] Started at {self.address}")
    
    def stop(self):
        """Stop the RAFT node"""
        print(f"[Node-{self.node_id}] Stopping...")
        self.running = False
        
        if self.server:
            self.server.stop(grace=1)
        
        print(f"[Node-{self.node_id}] Stopped")
    
    def wait_for_termination(self):
        """Wait for server termination"""
        if self.server:
            self.server.wait_for_termination()


class RaftServicer(raft_pb2_grpc.RaftServiceServicer):
    """gRPC service implementation"""
    
    def __init__(self, node: RaftNode):
        self.node = node
    
    def RequestVote(self, request, context):
        return self.node.handle_request_vote(request)
    
    def AppendEntries(self, request, context):
        return self.node.handle_append_entries(request)
    
    def SubmitCommand(self, request, context):
        return self.node.handle_submit_command(request)
    
    def Isolate(self, request, context):
        return self.node.handle_isolate(request)
