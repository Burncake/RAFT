# RAFT Implementation Report - Outline Template

**Bộ môn Công nghệ Tri thức**  
**Môn học: Blockchain và ứng dụng**

---

## Report Structure (Max 10 pages)

### 1. GIỚI THIỆU VỀ RAFT (2-3 pages)

#### 1.1 Tổng quan thuật toán RAFT
- Mục đích: Đạt đồng thuận trong hệ thống phân tán
- Đặc điểm chính: Dễ hiểu hơn Paxos, tương đương về tính đúng đắn
- Ứng dụng: etcd, Consul, CockroachDB

#### 1.2 Các thành phần chính

**Leader Election (Bầu cử Leader):**
- Cơ chế timeout ngẫu nhiên
- RequestVote RPC
- Xử lý xung đột khi nhiều candidate

**Log Replication (Sao chép Log):**
- AppendEntries RPC
- Kiểm tra tính nhất quán
- Commit index

**Safety Properties:**
- Election Safety: Tối đa 1 leader mỗi term
- Leader Append-Only: Leader không xóa/ghi đè
- Log Matching: Logs nhất quán
- Leader Completeness: Leader có tất cả committed entries
- State Machine Safety: Mọi node áp dụng cùng lệnh ở cùng index

#### 1.3 Câu trả lời các câu hỏi

**Q1: Làm thế nào RAFT đảm bảo tính nhất quán khi chuyển đổi leader?**

Trả lời:
- Leader mới chỉ commit entries của term hiện tại
- Sử dụng term number để phát hiện log cũ
- Log matching property đảm bảo prefix consistency
- Leader completeness đảm bảo leader có tất cả committed entries

**Q2: Hạn chế của RAFT khi xử lý các hành vi độc hại?**

Trả lời:
- RAFT chỉ chịu được lỗi crash (Crash Fault Tolerance)
- Không chịu được Byzantine faults:
  - Node gửi thông tin sai lệch
  - Node thay đổi dữ liệu đã commit
  - Node giả mạo identity
  - Cần pBFT để xử lý Byzantine faults

**Nguồn tham khảo:**
- Ongaro, D., & Ousterhout, J. (2014). In Search of an Understandable Consensus Algorithm. USENIX ATC '14.
- Raft website: https://raft.github.io/

---

### 2. SO SÁNH RAFT VÀ pBFT (2 pages)

#### 2.1 Bảng so sánh tổng quát

| Tiêu chí | RAFT | pBFT |
|----------|------|------|
| **Mục đích** | Crash Fault Tolerance | Byzantine Fault Tolerance |
| **Số node tối thiểu** | 3 | 4 (3f+1) |
| **Chịu lỗi** | f trong 2f+1 nodes | f trong 3f+1 nodes |
| **Độ phức tạp** | O(n) messages | O(n²) messages |
| **Hiệu năng** | Cao hơn | Thấp hơn (do nhiều rounds) |
| **Bảo mật** | Giả định nodes trung thực | Chịu được Byzantine attacks |
| **Ứng dụng** | Distributed databases | Blockchain, untrusted systems |

#### 2.2 Chi tiết so sánh

**Mô hình lỗi:**
- RAFT: Crash-stop model (node chỉ dừng hoặc hoạt động đúng)
- pBFT: Byzantine model (node có thể hành động độc hại)

**Số lượng node:**
- RAFT: 2f+1 nodes để chịu f lỗi (VD: 5 nodes chịu 2 lỗi)
- pBFT: 3f+1 nodes để chịu f lỗi (VD: 7 nodes chịu 2 lỗi)

**Quy trình consensus:**
- RAFT: Leader → AppendEntries → Majority ACK → Commit
- pBFT: Pre-prepare → Prepare (2f+1) → Commit (2f+1) → Execute

**Xử lý lỗi:**
- RAFT: Re-election khi leader fail, sync log khi rejoin
- pBFT: View change, phát hiện và loại trừ Byzantine nodes

**Hiệu năng:**
- RAFT: ~1000s transactions/sec (etcd benchmark)
- pBFT: ~100s transactions/sec (do complexity cao hơn)

#### 2.3 Khi nào dùng gì?

**Chọn RAFT khi:**
✅ Môi trường đáng tin cậy
✅ Chỉ cần chịu crash faults
✅ Cần hiệu năng cao
✅ Ví dụ: Internal microservices, distributed databases

**Chọn pBFT khi:**
✅ Môi trường không tin cậy
✅ Có thể có Byzantine nodes
✅ Blockchain applications
✅ Ví dụ: Cryptocurrency, public ledger

---

### 3. MÔ TẢ CHƯƠNG TRÌNH ĐÃ CÀI ĐẶT (3-4 pages)

#### 3.1 Kiến trúc tổng quan

```
Component Diagram:
┌─────────────────────────────────────────┐
│         RaftNode                        │
│  ┌──────────────────────────────────┐  │
│  │  RaftState (State Machine)       │  │
│  │  - current_term                  │  │
│  │  - voted_for                     │  │
│  │  - log[]                         │  │
│  │  - commit_index, last_applied    │  │
│  └──────────────────────────────────┘  │
│  ┌──────────────────────────────────┐  │
│  │  KeyValueStore                   │  │
│  │  - apply_command()               │  │
│  │  - File-based persistence        │  │
│  └──────────────────────────────────┘  │
│  ┌──────────────────────────────────┐  │
│  │  gRPC Service                    │  │
│  │  - RequestVote RPC               │  │
│  │  - AppendEntries RPC             │  │
│  │  - SubmitCommand RPC             │  │
│  └──────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

#### 3.2 Các thành phần chính

**A. raft_state.py - RAFT State Machine**

Quản lý trạng thái của node:
- Persistent state: current_term, voted_for, log[]
- Volatile state: commit_index, last_applied
- Leader state: next_index[], match_index[]

Chức năng quan trọng:
```python
- become_follower(): Chuyển sang follower
- become_candidate(): Start election
- become_leader(): Khởi tạo leader state
- append_entries(): Thêm log entries
- update_commit_index(): Advance commit
```

**B. kvstore.py - Key-Value Storage**

Lưu trữ dữ liệu đã commit:
- File-based: `data/node_X_db.json`
- Thread-safe với RLock
- Hỗ trợ: SET, GET, DELETE

**C. node.py - RAFT Node Implementation**

Core logic:
1. **Election Timer Thread**: Phát hiện timeout, start election
2. **Heartbeat Thread**: Leader gửi heartbeat định kỳ
3. **Apply Thread**: Áp dụng committed entries vào state machine

RPC Handlers:
- `handle_request_vote()`: Xử lý yêu cầu vote
- `handle_append_entries()`: Nhận log entries từ leader
- `handle_submit_command()`: Client gửi command

#### 3.3 Workflow

**Leader Election:**
```
1. Follower timeout → become_candidate()
2. Increment term, vote for self
3. Send RequestVote RPCs to all peers
4. If majority votes → become_leader()
5. Else if higher term seen → become_follower()
6. Else retry election
```

**Log Replication:**
```
1. Client → SubmitCommand to leader
2. Leader appends to local log
3. Leader sends AppendEntries to followers
4. Followers append and ACK
5. Leader waits for majority ACKs
6. Leader commits (advance commit_index)
7. Leader notifies followers to commit
8. Apply to state machine (kvstore)
```

**Failure Recovery:**
```
Leader failure:
1. Followers timeout (no heartbeat)
2. New election starts
3. New leader elected
4. Sync logs from new leader

Follower failure:
1. Leader continues with majority
2. When follower rejoins, leader syncs log
3. Follower catches up automatically
```

#### 3.4 Hướng dẫn chạy chương trình

**Bước 1: Cài đặt**
```bash
pip install -r requirements.txt
python scripts/generate_proto.py
```

**Bước 2: Chạy cluster**
```bash
python scripts/start_cluster.py
```

**Bước 3: Gửi commands**
```bash
python scripts/client.py
raft> SET key1 value1
raft> GET key1
```

**Bước 4: Test các tình huống lỗi**

*Test Leader Failure:*
```bash
# Terminal 1: Cluster running
# Terminal 2:
python tests/test_leader_failure.py
# Manually kill leader process when prompted
```

*Test Network Partition:*
```bash
python tests/test_network_partition.py
```

#### 3.5 Thay đổi tham số

**Điều chỉnh số lượng nodes:**

Sửa file `scripts/start_cluster.py`:
```python
NODES = {
    "node1": {"host": "localhost", "port": 5001},
    "node2": {"host": "localhost", "port": 5002},
    "node3": {"host": "localhost", "port": 5003},
    # Thêm nodes...
}
```

**Điều chỉnh timeout:**

Sửa file `scripts/run_node.py`:
```python
parser.add_argument('--election-timeout-min', type=int, default=150)
parser.add_argument('--election-timeout-max', type=int, default=300)
parser.add_argument('--heartbeat-interval', type=int, default=50)
```

**Tắt/bật node:**
- Tắt: Ctrl+C trên terminal của node đó
- Bật: Chạy lại `python scripts/run_node.py ...`

**Kiểm tra dữ liệu:**
```bash
# Xem file JSON trong data/
cat data/node_1_db.json
cat data/node_1_state.json
```

---

### 4. TỰ ĐÁNH GIÁ (1 page)

#### 4.1 Ưu điểm của chương trình

✅ **Đầy đủ chức năng:**
- Implement đầy đủ core RAFT: election, replication, fault tolerance
- Có persistence (lưu state và data)
- Test suite comprehensive

✅ **Dễ sử dụng:**
- Scripts tự động start cluster
- Client interactive mode
- Test scripts rõ ràng

✅ **Code rõ ràng:**
- Comments đầy đủ
- Module hóa tốt (state, storage, node riêng biệt)
- Thread-safe

#### 4.2 Nhược điểm

❌ **Chưa optimize:**
- Không có log compaction (logs tăng mãi)
- Không có snapshot mechanism
- Không có read optimization (linearizable reads)

❌ **Giới hạn:**
- Chỉ chạy trên 1 máy (test only)
- Không support dynamic membership
- Không có authentication/encryption

❌ **Testing:**
- Manual intervention cần thiết cho một số tests
- Không có automated recovery trong tests
- Chưa test edge cases (concurrent elections, log conflicts)

#### 4.3 Cách cải thiện

1. **Log Compaction:**
   - Implement snapshotting
   - Compact log khi đạt threshold
   - InstallSnapshot RPC

2. **Performance:**
   - Batch log entries
   - Pipeline AppendEntries RPCs
   - Read optimization (lease-based reads)

3. **Production-ready features:**
   - TLS encryption
   - Authentication
   - Metrics và monitoring
   - Configuration hot-reload

4. **Robustness:**
   - Better error handling
   - Retry với exponential backoff
   - Network simulation với latency/packet loss

---

### 5. KẾT LUẬN

#### Tổng kết
- Đã cài đặt thành công RAFT consensus algorithm
- Verify được các tính chất safety và liveness
- Test đầy đủ các tình huống lỗi

#### Bài học
- Hiểu sâu về consensus trong distributed systems
- Nắm được trade-offs giữa các thuật toán (RAFT vs pBFT)
- Kinh nghiệm debug distributed systems

#### Áp dụng thực tế
- Có thể dùng cho distributed database
- Nền tảng cho blockchain applications
- Hiểu rõ hạn chế để chọn thuật toán phù hợp

---

## PHỤ LỤC

### A. Screenshots

Bao gồm:
- [ ] Cluster startup
- [ ] Leader election logs
- [ ] Command submission
- [ ] Test results
- [ ] Data files (JSON)
- [ ] Network partition test

### B. Source Code Highlights

Snippet quan trọng:
- Leader election logic
- Log replication mechanism
- Commit advancement

### C. References

1. Ongaro, D., & Ousterhout, J. (2014). In Search of an Understandable Consensus Algorithm. USENIX ATC.
2. Castro, M., & Liskov, B. (1999). Practical Byzantine Fault Tolerance. OSDI.
3. Lamport, L. (1998). The Part-Time Parliament. ACM TOCS.
4. RAFT Visualization: https://raft.github.io/
5. gRPC Documentation: https://grpc.io/

---

**Lưu ý:**
- Tất cả nguồn tham khảo phải trích dẫn đúng format
- Code examples phải có comment giải thích
- Screenshots phải rõ ràng và có caption
- Báo cáo không quá 10 trang A4
