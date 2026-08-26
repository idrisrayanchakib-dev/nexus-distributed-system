# 🚀 NEXUS P2P: Decentralized Communication, Causality & Consensus Engine

[![CI Pipeline](https://github.com/your-username/chat-p2p-system/actions/workflows/ci.yml/badge.svg)](https://github.com/your-username/chat-p2p-system/actions)
[![Python Version](https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11%20%7C%203.12-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Architecture: Full-Mesh P2P](https://img.shields.io/badge/Architecture-Full--Mesh%20P2P-purple.svg)]()

**NEXUS P2P** is an enterprise-grade, serverless peer-to-peer (P2P) communication platform built with Python. It implements **Lamport Logical Clocks** for causal event ordering, **End-to-End Encryption (E2EE)** via PBKDF2HMAC-derived symmetric ciphers, **P2P Chunked File Sharing with SHA-256 integrity**, and a **fault-tolerant distributed consensus engine** with automatic election leader failover.

---

## 🏛️ System Architecture

```mermaid
graph TD
    subgraph Core Layer
        SEC[SecurityManager<br/>PBKDF2HMAC + Fernet]
        ID[IdentityManager<br/>UUID & Recovery Hash]
        CLK[LamportClock<br/>Causal Ordering]
        DB[(DatabaseManager<br/>Thread-Safe SQLite)]
    end

    subgraph Network Layer
        DISC[UDPDiscovery<br/>LAN Broadcast Beacon]
        FT[FileTransferManager<br/>Chunking & SHA-256]
        NODE[P2PNode Coordinator<br/>Full-Mesh TCP Sockets]
    end

    subgraph Consensus Layer
        VOTE[DistributedVotingEngine<br/>Leader Election & Fallback]
    end

    subgraph UI Layer
        UI[CustomTkinter App<br/>Cyberpunk Dark UI]
    end

    NODE --> SEC
    NODE --> CLK
    NODE --> DB
    NODE --> DISC
    NODE --> FT
    NODE --> VOTE
    UI --> NODE
```

---

## 🌟 Key Distributed Systems Highlights

### 1. ⏱️ Distributed Causality with Lamport Logical Clocks
In decentralized systems, physical clock drift makes wall-clock ordering unreliable. NEXUS P2P enforces strict **causal partial ordering**:
* Each local event increments the internal clock: $L(e) = L_{local} + 1$.
* Outgoing packet envelopes embed the current $L(e)$.
* Receiving peers synchronize clocks via: $L_{local} = \max(L_{local}, L_{received}) + 1$.
* Chat and state logs are indexed and retrieved strictly by logical clock sequence.

### 2. 🔐 Applied Cryptography & Channel Isolation
* **PBKDF2HMAC Key Derivation:** SHA-256 with 100,000 iterations and static domain salts.
* **Fernet Symmetric Cipher:** Authenticated encryption for zero-knowledge data transit.
* **Room Fingerprinting:** Derives unique 4-character channel fingerprints to instantly drop unauthorized foreign packets.

### 3. 📎 P2P Encrypted File Sharing Engine
* Streams arbitrary binary files (images, PDFs, documents) in 32 KB chunked base64 envelopes.
* Performs full **SHA-256 cryptographic verification** upon reception before writing to `downloads/`.
* Background non-blocking streaming threads ensure uninterrupted UI responsiveness.

### 4. 🗳️ Fault-Tolerant Distributed Consensus & Voting
```mermaid
sequenceDiagram
    participant Leader as Node A (Election Leader)
    participant PeerB as Node B (Peer)
    participant PeerC as Node C (Peer)

    Leader->>PeerB: POLL_START (Question, Options, EndTime)
    Leader->>PeerC: POLL_START (Question, Options, EndTime)
    PeerB->>Leader: VOTE (Choice: Option 0)
    PeerC->>Leader: VOTE (Choice: Option 1)
    
    alt Leader is Healthy
        Leader->>PeerB: POLL_RESULT (Official Tally)
        Leader->>PeerC: POLL_RESULT (Official Tally)
    else Leader Disconnects (Failover)
        Note over PeerB,PeerC: Timeout Triggered -> Local Backup Consensus Computed
    end
```

---

## 📂 Modular Package Structure

```
chat-p2p-system/
├── .github/workflows/
│   └── ci.yml               # GitHub Actions CI Matrix (Win/Ubuntu/Mac)
├── nexus/
│   ├── core/
│   │   ├── security.py      # PBKDF2HMAC, Fernet & Room Fingerprinting
│   │   ├── identity.py      # UUID generation & 4-char Recovery Hashes
│   │   ├── clock.py         # Lamport Logical Clock implementation
│   │   ├── database.py      # Thread-safe SQLite store & causal sorting
│   │   └── protocol.py      # Standardized packet envelope schemas
│   ├── network/
│   │   ├── discovery.py     # UDP broadcast beaconing & listener
│   │   ├── file_transfer.py # Chunked file sender/receiver & SHA-256 check
│   │   └── node.py          # TCP mesh coordinator & packet dispatcher
│   ├── consensus/
│   │   └── election.py      # Distributed ballot engine & fallback tallies
│   └── ui/
│       ├── theme.py         # Cyberpunk Dark color tokens
│       ├── components.py    # Sub-windows (Private Rooms, Message Manager)
│       └── app.py           # CustomTkinter reactive application
├── tests/
│   ├── test_security.py
│   ├── test_clock.py
│   ├── test_database.py
│   ├── test_file_transfer.py
│   └── test_p2p.py
├── main.py                  # Standard application entry point
├── p2p_chat_distributed.py  # Backwards-compatible launcher
├── requirements.txt
└── pyproject.toml
```

---

## 🚀 Quick Start

### 1. Installation
```bash
# Clone the repository
git clone https://github.com/your-username/chat-p2p-system.git
cd chat-p2p-system

# Install dependencies
pip install -r requirements.txt
```

### 2. Launch Multi-Node Mesh
Open two terminal windows:

* **Node 1 (Alice):**
  ```bash
  python main.py
  ```
  * Username: `Alice` | Network Key: `123` $\rightarrow$ Connect.

* **Node 2 (Bob):**
  ```bash
  python main.py
  ```
  * Username: `Bob` | Network Key: `123` $\rightarrow$ Connect.

Nodes automatically discover each other via UDP broadcast beacons and establish direct TCP mesh streams.

---

## 🧪 Running the Test Suite

Execute the full suite of unit, concurrency, and integration tests:

```bash
python -m unittest discover -v -s tests
```

---

## 💼 Resume & Interview Bullet Points

```markdown
### NEXUS P2P: Distributed Secure Messaging & Consensus System | Python, Sockets, Cryptography, SQLite
- Designed a decentralized serverless communication engine using raw TCP sockets, multi-threading, and UDP auto-discovery beacons.
- Implemented Lamport Logical Clocks to enforce strict causal message ordering across asynchronous peer nodes.
- Built End-to-End Encryption (E2EE) with PBKDF2HMAC key derivation (SHA-256, 100k iterations) and Fernet authenticated ciphers.
- Developed an encrypted chunked P2P file transfer engine with SHA-256 checksum verification and non-blocking background streaming.
- Engineered a fault-tolerant distributed consensus protocol featuring election leader coordination and automated local fallback tallies.
- Maintained a modular architecture with 100% test pass rate across a multi-OS CI/CD pipeline (Windows, macOS, Ubuntu).
```