## Streamlit + FastAPI Microservices Demo (Blockchain-Inspired)

### Learning Objectives
By completing this module, students will be able to:
1. **Explain** how distributed ledger systems maintain consistency without a central authority
2. **Demonstrate** the relationship between wallets, transactions, and blocks in a UTXO model
3. **Implement** REST APIs that coordinate state across multiple microservices
4. **Analyze** how proof-of-work mining creates consensus in competing chains
5. **Evaluate** trade-offs between centralized and decentralized system architectures

### Prerequisites
Students should have completed:
- FastAPI fundamentals (request/response models, async endpoints, background tasks)
- Streamlit basics (session state, form handling, live updates)
- Docker Compose essentials (multi-service orchestration, networking, volumes)
- Basic cryptography concepts (hashing, public/private key signatures)

**Estimated time**: 3-4 hours for core demo + 2 hours for optional fork/reorg extensions

---

### What we're building
- **Goal**: a three-service, all-HTTP lab that lets students watch "wallet → mempool → mined block" transitions without needing a real blockchain.
- **Stack**: Streamlit UI + two FastAPI services. Everything runs locally via `docker compose up`.
- **Story**: Students mint faucet coins, craft signed UTXO transactions, push them through a coordinator API, and trigger a proof-of-work toy miner to confirm blocks. The demo visualizes confirmations, forks, and "most accumulated work" decisions.

**Why this matters**: Real-world systems like Bitcoin, Ethereum, and enterprise blockchains all follow this pattern—wallets sign transactions, nodes maintain mempools, and miners/validators batch work into blocks. By implementing a toy version with familiar tools (FastAPI + Streamlit), students see how these pieces interact without drowning in cryptocurrency complexity.

---

### Scope guardrails for v1
- Keep the three services, but limit each to 1–2 source files so students can trace logic linearly.
- `node-miner` mines only when `/node/mine` is called. The handler builds a candidate block, brute-forces nonces (with a fixed attempt cap), and returns success/failure. No background miners, volumes, or reorg logic.
- `tx-coordinator` is a REST proxy with basic validation (non-empty inputs/outputs, simple signature placeholder). It forwards requests verbatim to the node and relays responses—no SSE, websockets, or event fan-out.
- `streamlit-wallet` is a single `app.py` with three tabs: `Home`, `Wallets`, `Blocks & Mempool`. It polls the coordinator every few seconds instead of subscribing to live streams.
- **Signature simplification**: Locking script = address string (no script interpreter). Signature = `sha256(txid + privkey)[:16]` (deterministic, verifiable without ECDSA overhead). This keeps v1 focused on transaction flow rather than cryptography edge cases.
- Rules are intentionally toy-like: PoW is "SHA-256 hash starts with N zero hex chars", and faucet amount is fixed.
- **Advanced features reserved for optional extension module**: Forks, Mining 101 playground with live sliders, drag-and-drop transaction builders, SSE/websockets, and multi-miner reorg demos move to a clearly labeled "Extension Module" roadmap so v1 stays teachable in one sitting.

---

### Teaching Progression (from simple → complex)

#### Session 1: Single wallet, single transaction (30 min)
**Concepts introduced**: UTXO, transaction inputs/outputs, digital signatures  
**Student actions**:
1. Create one wallet via Streamlit UI (generates keypair client-side)
2. Request faucet funds (POST to coordinator, which creates a coinbase UTXO)
3. View balance (GET from coordinator, which queries node's UTXO set)
4. Craft a transaction spending the faucet UTXO to a new address
5. Sign and submit (Streamlit signs locally, POSTs to coordinator)

**Teaching tips**:
- Use analogy: UTXO = a physical check made out to you; spending it = endorsing the check to someone else
- Show the JSON transaction structure on screen before signing so students see inputs referencing prev_txid/prev_index
- Emphasize that the coordinator validates the transaction *before* forwarding to the node (separation of concerns)

**Cognitive checkpoint** (before moving to Session 2):
- Ask students to predict: "If Alice has a 50-token UTXO and sends 30 to Bob, how many outputs will the transaction create?" (Answer: 2—one for Bob, one change back to Alice)
- Quick poll: "Where is your wallet balance stored?" Correct answer: "Nowhere—it's computed by summing UTXOs the node knows about"

**Common misconceptions**:
- "Balance is stored in the wallet" → No, balance = sum of UTXOs you can unlock with your private key
- "Transactions are instant" → No, they sit in the mempool until a miner includes them in a block

#### Session 2: Mining & confirmations (30 min)
**Concepts introduced**: Mempool, blocks, proof-of-work, confirmations  
**Student actions**:
1. Observe the pending transaction in the mempool table
2. Click "Mine Block" (sends POST `/api/mine` to coordinator, which forwards to the node)
3. Read the textual mining log the node returns (e.g., attempts count, winning nonce)
4. See the block appear in the Blocks table once a valid nonce is found
5. Wallet tab polls every few seconds and shows status change from "pending" to "confirmed (1)"

**Teaching tips**:
- Before starting the miner, ask: "Why can't we just add transactions to blocks immediately?"
- Explain the single difficulty knob: lower difficulty = faster demos, higher difficulty = more secure (real-world)
- Show that the block contains the transaction PLUS a coinbase reward for the miner
- Walk through the block header fields (prev_hash links to parent, merkle_root commits to all txs, nonce makes the hash valid)

**Visualization aid**: Streamlit prints log lines, e.g.
```
Target prefix: 0000
Tried 3,522 nonces → success with nonce 3521 (hash 0000c3a1…)
Block contains 1 user tx + coinbase reward
```
Reserve fancy sliders/graphs for the Extension Module.

**Cognitive checkpoint** (before moving to Session 3):
- Show two blocks with different difficulty prefixes (e.g., "000" took 50 attempts, "0000" took 8,000 attempts)
- Ask: "Why did adding one more zero roughly multiply attempts by 16?" (Answer: each hex digit has 16 possibilities—0-9, a-f)

#### Session 3: Multiple wallets & change outputs (20 min)
**Concepts introduced**: Change addresses, transaction fees, UTXO consolidation  
**Student actions**:
1. Create a second wallet ("Bob")
2. Send partial funds from first wallet to Bob (e.g., 30 of 50 tokens)
3. Observe that the transaction creates TWO outputs: 30 to Bob, 20 back as change
4. Mine a block to confirm
5. Both wallets now have new UTXOs they can spend

**Teaching tips**:
- Compare to paying with cash: "If you buy a $3 coffee with a $5 bill, you get $2 in change"
- Show the UTXO tree: faucet → Alice(50) → [Bob(30), Alice_change(20)]
- Introduce fees: "If outputs sum to less than inputs, miners keep the difference"

**Cognitive checkpoint**:
- Give students a scenario: "Alice has UTXOs of 10, 20, and 30 tokens. She wants to send 35 to Bob. Which UTXOs should she use?" (Answer: Multiple valid answers—discuss trade-offs between fee size and future spendability)

#### Session 4 (Optional Extension Module): Forks & reorganizations (40 min)
**Concepts introduced**: Chain splits, accumulated work, consensus rules  
**Prerequisite**: Students must complete Sessions 1-3 and pass a short quiz on UTXO mechanics before attempting fork demos.

**Student actions**:
1. Enable the forked miner profile (`docker compose --profile forked up`)
2. Submit a transaction and watch miners compete via CLI logs or a future Fork Visualizer tab
3. Observe two branches at the same height
4. See one branch overtake the other as more blocks accumulate
5. Watch the UI/logs highlight the reorg: orphaned blocks, transactions returning to mempool

**Teaching tips**:
- Emphasize this is NOT an error state—it's how decentralized systems reach agreement
- Ask: "If Alice's payment appeared in the losing branch, is she still paid?" (Answer: No, tx goes back to mempool)
- Real-world parallel: Bitcoin/Ethereum forks happen regularly; exchanges wait 6+ confirmations to consider payments final

**Diagram for whiteboard**:
```
Genesis → Block 1 → Block 2 → Block 3 (miner A) ← WINNING CHAIN (more work)
                  ↘ Block 2' (miner B) ← ORPHANED
```

---

### Service Architecture (plain language first)

#### Design philosophy
- **HTTP everywhere**: Pure REST + polling in v1 (no SSE/websockets). Students already know FastAPI, so the emphasis stays on clear request/response flows.
- **Clear responsibilities**: UI worries about user input, coordinator validates shapes, node enforces consensus rules. This separation makes debugging easier.
- **Observable state**: Every service exposes GET endpoints that return full state (mempool, UTXO set, chain tips) so students can inspect what's happening at each layer.

#### Services (all speak HTTP)
1. **`streamlit-wallet`** (front-end)
   - Single-file Streamlit app acting as wallet + block explorer.
   - Generates keys client-side, stores them in session state, and polls the coordinator for balances, mempool, and blocks every few seconds.
   - Provides buttons for faucet funding, transaction submission, and "Mine Block" (which calls into the coordinator).
   
   **Teaching angle**: This is the "user-facing app" like Coinbase or MetaMask. It knows your private keys but doesn't store the blockchain.

2. **`tx-coordinator`** (backend #1)
   - FastAPI service that exposes a clean REST layer for the UI.
   - Performs lightweight validation (non-empty inputs/outputs, sum checks, deterministic toy signatures) before forwarding requests to the node.
   - No streaming features in v1; it simply proxies REST calls and surfaces node responses verbatim.
   
   **Teaching angle**: This is the "business logic layer." Real companies add rate limiting, user authentication, and analytics here without touching the node code.

3. **`node-miner`** (backend #2)
   - FastAPI service that owns the in-memory blockchain state, mempool, UTXO set, and simplified PoW miner loop.
   - Provides HTTP endpoints for submitting transactions, inspecting chain tips, and adjusting a single difficulty value.
   - Mines synchronously inside `POST /node/mine`: build candidate block from current mempool, brute-force nonce (single SHA-256 hash per attempt) until success or attempt cap; then append block, update UTXOs, prune mempool.
   
   **Teaching angle**: This is the "consensus layer." In Bitcoin, thousands of these nodes run independently. If they disagree, the one with the most accumulated proof-of-work wins.

4. **Optional extra miners** (for fork demos)
   - Exact copies of the node miner that we can spin up to simulate network competition.
   - Marked as Phase 2 so v1 remains linear and approachable.

---

### Concept Glossary (introduce terms progressively)

#### Core concepts (Phase 1)
- **UTXO (Unspent Transaction Output)**: A single coin produced by a past transaction. If a UTXO says "5 tokens locked to Alice's address," only Alice (with her private key) can spend those 5 tokens, split them, or combine them in a new transaction.  
  *Analogy*: Like a signed check made out to you—only you can deposit/endorse it.

- **Transaction input / output**: Inputs point to UTXOs you want to spend (like "I'm cashing this check"). Outputs describe new UTXOs you are creating (like "Write a new check to Bob for $30"). Inputs must add up to at least as much value as the outputs (extra becomes a fee for the miner).

- **Digital signature**: Proves you own the private key for an address without revealing the key itself. Calculated using ECDSA (the same algorithm used in Bitcoin/Ethereum).

#### Mining concepts (Phase 2)
- **Mempool**: Short for "memory pool." Every blockchain node keeps a list of valid-but-not-yet-mined transactions in RAM so miners can pick from them. Transactions wait here until a miner includes them in a block.  
  *Note*: Yes, "mempool" is the standard Bitcoin/Ethereum term. We keep it for authenticity but always define it when teaching.

- **Block**: A batch of transactions plus a header that references the previous block. Together they form an append-only chain where every block depends on the one before it.  
  *Components*: Header (prev_hash, merkle_root, timestamp, nonce) + List of transactions.

- **Proof of Work (PoW)**: A lottery where miners keep hashing the block header with different nonces until the hash is smaller than a target number. Finding such a nonce is computationally hard (billions of attempts); verifying the result is one hash operation. More accumulated work = more security against rewrites.

- **Difficulty / target**: How small the winning hash must be. Smaller target → harder puzzle → longer expected mining time. In v1 we expose this as a single "required zero prefix" input so instructors can show that adding one zero roughly doubles expected work.

- **Confirmation**: Once your transaction sits in a block, each additional block on top counts as another confirmation. More confirmations make it exponentially harder for an attacker to rewrite history (they'd need to redo all the work in every block).  
  *Rule of thumb*: Bitcoin exchanges wait 6 confirmations (~1 hour) before crediting deposits.

#### Advanced concepts (Phase 4)
- **Fork / reorg**: When two miners find blocks at similar times, the chain temporarily splits. Eventually the branch with more accumulated work wins and the other branch is abandoned ("reorganized"). Transactions in orphaned blocks return to the mempool.  
  *Why it matters*: Shows students that blockchain consensus is *probabilistic* not instant. This is why merchants wait for confirmations.

- **Accumulated work**: Sum of difficulty across all blocks in a chain. The chain with the most work is considered canonical. This prevents attackers from creating a longer chain by mining easy blocks quickly.

---

### Teaching Proof-of-Work (detailed lesson plan)

#### Session 1: Console intuition (15 min)
**Materials**: Streamlit "Mine Block" log output  
**Steps**:
1. Show the block header fields returned by the node (`version`, `prev_hash`, `merkle_root`, `timestamp`, `difficulty_prefix`, `nonce`).
2. Mine an empty block so the operation finishes quickly.
3. Read the textual log (attempt count, winning nonce, hash prefix) aloud.
4. Ask students what changed between attempts (only the nonce) to emphasize randomness.

**Key insight**: PoW = “keep hashing until SHA-256(header) starts with N zero hex chars.” No advanced math—just brute force.

#### Session 2: Hands-on mining with one knob (20 min)
**Materials**: Blocks & Mempool tab (auto-refresh table)  
**Steps**:
1. Submit a transaction so it enters the mempool.
2. Set difficulty prefix to `000` via Streamlit input → mine (fast success).
3. Set prefix to `0000` → mine again (notice longer runtime).
4. If max attempts are exceeded, discuss why the node aborts and how to retry.

**Observation prompts**:
- How many attempts did each run take? (Luck-driven.)
- Did transaction content change mining time? (No—difficulty dominates.)
- Why cap attempts per HTTP call? (Prevents a never-ending request.)

#### Session 3: Confirmation depth (15 min)
**Materials**: Wallet + Blocks tabs  
**Steps**:
1. After mining the Alice→Bob block, show the wallet balance and block entry.
2. Mine additional empty blocks to simulate time passing.
3. Point to the confirmation counter increasing with each new block.
4. Explain economic finality: the deeper the block, the harder it is to rewrite.

#### Session 4: Fork & reorg (Phase 2)
Keep dual miners, fork visualizers, and live hash sliders for the optional module once the base experience is solid. When reintroduced, tie them to the same log-based intuition students built in v1.

**Talking point checklist**:
1. Mining = build block header, brute-force nonce until prefix rule passes.
2. Smaller prefix target ⇒ exponentially more work.
3. Verification is cheap (one SHA-256 hash).
4. Blocks chain via previous-hash pointers, so tampering breaks downstream hashes.
5. More confirmations mean more cumulative work to redo, which is why exchanges wait.

---

### Why This Fits the Course

#### Pedagogical alignment
- **Builds on existing skills**: Students already know FastAPI (request handlers, Pydantic models) and Streamlit (forms, session state). This demo just adds blockchain *concepts* without new tools.
- **HTTP-first architecture**: Reinforces REST principles (stateless requests, resource-oriented endpoints, clear separation of concerns) without introducing message queues or gRPC complexity.
- **Observable systems**: Every service exposes GET endpoints for full state inspection—matches course emphasis on debuggable, testable code.
- **Progressive complexity**: Core demo (1 wallet, 1 tx, 1 block) works in 30 minutes. Fork/reorg extensions are optional advanced material.

#### Real-world relevance
- Shows how microservices coordinate state via HTTP contracts (coordinator validates, node enforces consensus)
- Demonstrates deterministic PoW logic that can later be moved into background workers
- Introduces eventual consistency (transactions pending → confirmed, forks resolving over time)
- Connects to industry: students leave understanding why Coinbase waits for confirmations, how Ethereum gas fees work (tx fees in our demo), why "blockchain database" is usually the wrong tool

#### Constraints met
- **Local-first**: Everything runs via `docker compose up`, no cloud accounts or external APIs
- **Minimal dependencies**: Just Python 3.12 + uv + Docker (students already have these from prior modules)
- **Time-bounded**: Core demo = 90 minutes lecture + 60 minutes lab. Fork extensions = optional 2-hour workshop.

---

### Wallet + Node Variations

#### Flexibility for different class sizes
- **Small class (5-10 students)**: Each student runs full stack locally, creates multiple wallets in their own Streamlit session
- **Medium class (15-30)**: Instructor runs shared `node-miner` on classroom server, students connect Streamlit UIs to it (see tx from classmates in mempool)
- **Large class (30+)**: Instructor pre-mines blocks with scripted transactions, students explore read-only via block explorer tabs

#### Advanced extensions (post-lab exercises)
- **Multiple wallets per student**: Streamlit session state can hold keypairs for "Alice", "Bob", "Miner"—students act out multi-party scenarios
- **Faucet variations**: Instructor can fund specific students' addresses via `POST /node/tx` with a pre-signed coinbase
- **Scripted demos**: Python script calls coordinator API in a loop to simulate network activity (students see mempool fill/drain dynamically)
- **Competing miners**: Enable `docker compose --profile forked` to launch 2-3 node replicas—they race to mine blocks, demonstrating probabilistic consensus
- **Custom transaction types**: Advanced students can extend the UTXO model to support multi-sig, timelocks, or atomic swaps (concepts from real Bitcoin script)

---

### What Docker Compose Gives Us

#### Single-command deployment
- `docker-compose.yml` spins up all three services plus a shared bridge network.
- Health checks ensure Streamlit waits for both FastAPI services to report ready before attempting to call them.
- Environment variables keep knobs adjustable (difficulty prefix, faucet amount, max attempts, miner address) without editing code.

#### State management
- All chain data lives in memory inside `node-miner`—restarting the container resets the ledger (handy for rapid demos).
- Optional Phase 2 upgrade: add a persistent volume or JSON snapshot if instructors need continuity across sessions.

#### Optional profiles
- `docker compose up` → core 3-service demo
- `docker compose --profile forked up` → adds `node-miner-2`, `node-miner-3` for fork visualizations
- `docker compose --profile debug up` → enables verbose logging and exposes pdb ports (future extension)

---

### HTTP Surface (high level)

| Service | Endpoint | Method | Description | Teaching Note |
|---------|----------|--------|-------------|---------------|
| streamlit-wallet → tx-coordinator | `/api/wallets` | POST | UI asks for new keypair+faucet; coordinator relays to node | "This is like clicking 'Create Account' in Coinbase" |
| streamlit-wallet → tx-coordinator | `/api/wallets/{address}` | GET | Fetch balance/UTXOs | "Shows spendable coins, not account balance" |
| streamlit-wallet → tx-coordinator | `/api/mempool` | GET | List pending transactions (poll every few seconds) | "Students can watch their tx enter/leave the queue" |
| streamlit-wallet → tx-coordinator | `/api/blocks` | GET | List most recent blocks | "Proof that mining captured the tx" |
| streamlit-wallet → tx-coordinator | `/api/tx` | POST | Submit signed transaction | "Streamlit signs locally (your keys never leave your browser)" |
| streamlit-wallet → tx-coordinator | `/api/mine` | POST | Trigger mining (for classroom control) | "In real Bitcoin, miners run 24/7—here we control it for demos" |
| tx-coordinator → node-miner | `/node/tx` | POST | Validated tx enters mempool if UTXOs exist | "Coordinator already checked signature format; node checks UTXO set" |
| tx-coordinator → node-miner | `/node/utxos/{address}` | GET | Wallet balance/UTXO list | "Node is source of truth for what coins exist" |
| tx-coordinator → node-miner | `/node/chain/head` | GET | Returns tip hash, height, and latest block summary | "Used by Blocks tab to refresh every few seconds" |

**Design rationale**: Coordinator = API gateway pattern. Keeps node focused on consensus logic while coordinator handles UI niceties (request validation now, SSE/fork visualizers later). Students learn to separate concerns across service boundaries.

---

### How the Pieces Work Together (step-by-step walkthroughs)

1. **Faucet / onboarding**
   - Streamlit calls `POST /api/wallets`.
   - Coordinator asks `node-miner` to mint a coinbase-style UTXO for that address and returns the txid.
   - Streamlit triggers a manual refresh (or waits for the next poll) to show the new balance.
2. **Spending**
   - Streamlit lists UTXOs via `GET /api/wallets/{addr}` and lets the student pick inputs + outputs.
   - Streamlit signs locally (using `ecdsa`), shows the raw transaction JSON, and POSTs it.
   - Coordinator recomputes the txid, rejects malformed scripts early, and forwards to the node; node validates against UTXO set and keeps it in the mempool.
3. **Mining + confirmation tracking**
   - Student clicks “Mine Block,” coordinator forwards to node, and the node brute-forces nonces within the request.
   - On success the node returns `{status:"mined"}` plus a summary (attempts, nonce, block hash); coordinator surfaces that text to the UI.
   - Streamlit’s polling loop notices the mempool shrink and the new block entry; balances refresh automatically.
4. **Fork + “most work” demo (Phase 2)**
   - When ready for advanced content, enable the `forked` compose profile or run two node-miner containers manually.
   - Introduce a Fork Visualizer tab or CLI log to show competing branches and how the “most work” rule eventually collapses back to one chain.

---

### Build Specification (hand-off for automation)

#### Repository layout
```
examples/blockchain-demo/
├── docker-compose.yml
├── .env.example
├── README.md (run instructions)
├── shared/
│   └── models.py            # Pydantic/BaseModel schemas shared across services
├── node-miner/
│   ├── Dockerfile
│   ├── pyproject.toml       # uv-managed (python 3.12)
│   └── app/
│       ├── main.py          # FastAPI entrypoint
│       ├── mining.py        # synchronous nonce search helpers
│       ├── chain.py         # UTXO set, block store
│       └── settings.py
├── tx-coordinator/
│   ├── Dockerfile
│   ├── pyproject.toml
│   └── app/main.py
├── streamlit-wallet/
│   ├── Dockerfile
│   ├── pyproject.toml
│   └── app.py               # Streamlit entrypoint
└── tests/
    ├── test_transactions.py
    ├── test_blocks.py
    └── test_end_to_end.py   # uses httpx.AsyncClient against both FastAPI apps
```

#### Dependencies
- Python 3.12, managed via `uv`.
- Shared libs: `pydantic>=2.7`, `fastapi>=0.111`, `uvicorn[standard]`, `httpx`, `ecdsa`, `pysha3` (optional), `uvloop` (prod).
- Streamlit app: `streamlit>=1.36`, `httpx` (or `requests`) for REST polling.

#### Tooling & initialization
- Use `uv init --python 3.12 --package` inside each service folder (`node-miner`, `tx-coordinator`, `streamlit-wallet`) so every project pins Python 3.12 and generates a `pyproject.toml`, `.python-version`, and `.venv/` (ignored via `.gitignore`).
- Shared models live outside of the `uv` projects; reference them by adding `path = "../shared"` entries in each `pyproject.toml` `[tool.uv.sources]`.
- Lock dependencies with `uv lock` and commit the resulting `uv.lock`.
- Standard commands:
  - `uv run fastapi dev app/main.py --port 8000` (node-miner)
  - `uv run fastapi dev app/main.py --port 8001` (tx-coordinator)
  - `uv run streamlit run app.py --server.port 8501` (Streamlit UI)
- When new packages are required use `uv add package-name` from the relevant service directory to keep lockfiles consistent.

#### Dockerfiles
- Each service has its own Dockerfile at the service root (`node-miner/Dockerfile`, etc.).
- **Important**: Shared models must be copied during Docker Compose build via build context, NOT via `COPY ../shared` inside Dockerfile.
- Pattern:
  ```Dockerfile
  FROM python:3.12-slim AS runtime
  RUN pip install --upgrade pip uv
  WORKDIR /app
  COPY pyproject.toml uv.lock ./
  COPY app ./app
  # For Streamlit: COPY app.py ./
  # Shared models will be mounted at build time via compose context
  COPY shared /app/shared
  RUN uv sync --frozen
  ENV PYTHONUNBUFFERED=1
  CMD ["uv", "run", "fastapi", "run", "app/main.py", "--port", "8000"]
  ```
- Streamlit container swaps the final command for `["uv","run","streamlit","run","app.py","--server.port","8501","--server.address","0.0.0.0"]`.

#### Docker Compose contract
- Services:
  - `streamlit-wallet`: builds from `./streamlit-wallet`, exposes `8501`.
    ```yaml
    build:
      context: .
      dockerfile: ./streamlit-wallet/Dockerfile
    ```
  - `tx-coordinator`: builds from `./tx-coordinator`, exposes `8001`.
    ```yaml
    build:
      context: .
      dockerfile: ./tx-coordinator/Dockerfile
    ```
  - `node-miner`: builds from `./node-miner`, exposes `8000` (all state in memory; restart resets chain).
    ```yaml
    build:
      context: .
      dockerfile: ./node-miner/Dockerfile
    ```
  - Optional profile `forked` adds `node-miner-2`, `node-miner-3` containers reusing same image with env `NODE_NAME`.
- Networks: single bridge `blocknet`.
- Health checks: FastAPI endpoints `/healthz`, Streamlit requests `GET /_stcore/health`.
- Environment variables (load from `.env`): `FAUCET_AMOUNT`, `MINER_ADDRESS`, `DEFAULT_DIFFICULTY_PREFIX`, `MAX_MINING_ATTEMPTS`, `STREAMLIT_API_BASE`.

#### Shared models (`shared/models.py`)
- **Simplified for v1** (no full ECDSA):
  - `HexBytes = Annotated[str, StringConstraints(pattern=r"^0x[0-9a-f]+$")]`
  - `Address = Annotated[str, StringConstraints(min_length=10, max_length=64)]`
  - `SimplifiedSignature = Annotated[str, StringConstraints(pattern=r"^0x[0-9a-f]{32}$")]`  # 16-byte hex (deterministic)
  - `TxOut = BaseModel: value:int, locking_script:Address`  # locking_script = recipient address
  - `TxIn = BaseModel: prev_txid:HexBytes, prev_index:int, unlocking_signature:SimplifiedSignature`
  - `Transaction = BaseModel: inputs:list[TxIn], outputs:list[TxOut], locktime:int=0`
  - `BlockHeader = BaseModel: version:int, prev_hash:HexBytes, merkle_root:HexBytes, timestamp:int, difficulty_prefix:str, nonce:int`
  - `Block = BaseModel: header:BlockHeader, transactions:list[Transaction], height:int`
  - `WalletInfo = BaseModel: address:Address, utxos:list[TxOut], balance:int`
  - `MiningResult = BaseModel: status:Literal["mined","no_solution"], attempts:int, nonce:Optional[int], block_hash:Optional[HexBytes], block:Optional[Block]`

**Signature validation rule** (implement in `tx-coordinator` and `node-miner`):
```python
def validate_signature(tx: Transaction, input_idx: int, utxo: TxOut) -> bool:
    """
    V1 simplified signature: sha256(txid + privkey)[:32] as hex.
    For demo purposes, we can't verify without privkey, so coordinator
    just checks format. Node trusts coordinator's validation.
    
    Extension module will replace with proper ECDSA.
    """
    sig = tx.inputs[input_idx].unlocking_signature
    return bool(re.match(r"^0x[0-9a-f]{32}$", sig))
```

#### API contracts
- **Node miner** (`http://node-miner:8000`):
  - `GET /healthz` → `{status:"ok"}`
  - `GET /node/chain/head` → `{height:int, tip:HexBytes, difficulty_prefix:str, latest_block:Block}`
  - `GET /node/blocks` → `{blocks:list[Block]}` (limit query param)
  - `GET /node/mempool` → `{txs:list[Transaction], count:int}`
  - `GET /node/utxos/{address}` → `WalletInfo`
  - `POST /node/tx` body `Transaction` → `{txid:HexBytes, status:"accepted"|"rejected", reason?:str}`
  - `POST /node/mine` body `{difficulty_prefix?:str, max_attempts?:int}` → `{status:"mined"|"no_solution", attempts:int, nonce?:int, hash?:HexBytes, block?:Block}`
- **Tx coordinator** (`http://tx-coordinator:8001`):
  - `POST /api/wallets` → generates or requests wallet+faucet: `{address:str, txid:HexBytes}`
  - `GET /api/wallets/{address}` → `WalletInfo`
  - `GET /api/mempool` → proxied `{txs:list[Transaction], count:int}`
  - `GET /api/blocks` (optional `limit`) → proxied `{blocks:list[Block]}`
  - `POST /api/tx` body `Transaction` → `{"txid":HexBytes,"status":"forwarded"}`
  - `POST /api/mine` body `{difficulty_prefix?:str, max_attempts?:int}` → proxies to node and returns its log output.
- **Streamlit client expectations**:
  - Reads API base URL from `STREAMLIT_API_BASE`.
  - Polls REST endpoints every 2–3 seconds for balances, mempool, and latest blocks.

#### Streamlit UI features (v1)
- Tabs:
  1. `Home`: quick instructions, buttons for "Create Wallet + Faucet" and "Mine Block", plus a textarea that displays the latest mining log returned by the coordinator.
  2. `Wallets`: list stored keypairs (label, address, privkey), show UTXOs/balance for the selected wallet, simple form to build a transaction (select UTXO, enter recipient + amount, optional change address).
  3. `Blocks & Mempool`: polling tables showing pending transactions and the last N blocks (hash, height, included txids). Optional auto-refresh toggle (default every 3 seconds).
- Use `st.session_state` to store wallets `{label,address,privkey}` and autopopulate the transaction form.
- Each tab starts with a short explainer (Markdown in an `st.expander`) so definitions stay close to the controls.
- **Error prevention UI patterns**:
  - Transaction form validates `sum(selected_utxos) >= sum(outputs)` client-side before allowing submission
  - Shows warning if no change output and inputs > outputs: "This will create a {fee} token miner fee. Continue?"
  - Disables "Mine Block" button if mempool is empty with tooltip: "Add transactions first"
  - Color-codes confirmation depth: red (0), yellow (1-2), green (3+)

**Extension module** adds more visualizations (Mining 101 slider, Fork Visualizer) once this core UI is solid.

---

### Troubleshooting Decision Tree (for instructors and TAs)

#### Student reports: "My balance shows 0 after requesting faucet"

1. Check Streamlit UI refresh: Did they wait 3 seconds for polling or manually refresh?
2. Check coordinator logs: `docker compose logs tx-coordinator | grep /api/wallets`
   - If no POST logged → Streamlit form didn't submit correctly
   - If POST logged but no response → check node-miner logs
3. Check node-miner state: `curl http://localhost:8000/node/utxos/{address}`
   - If returns empty → faucet transaction wasn't created
   - If returns UTXO → UI polling issue, try manual refresh button

#### Student reports: "Mining button does nothing"

1. Check mempool: `curl http://localhost:8000/node/mempool`
   - If count=0 → explain empty blocks are allowed, but demo needs a tx for visibility
2. Check max_attempts: If difficulty is too high (e.g., "00000"), increase `MAX_MINING_ATTEMPTS` in `.env` or lower difficulty prefix
3. Check logs: `docker compose logs node-miner | grep "Mining"`
   - If no log lines → request didn't reach node, check coordinator proxy
   - If log shows "no_solution" → explain retry with lower difficulty

#### Student reports: "Transaction rejected: double-spend"

1. Explain: This is correct behavior! UTXO was already consumed.
2. Refresh wallet to see updated UTXO set after previous transaction was mined
3. Teaching moment: Show the UTXO lifecycle diagram (created → spent → removed from set)

#### Student reports: "Confirmations not increasing"

1. Check if they're mining additional blocks: Confirmations only increment when NEW blocks build on top
2. Show block height: If stuck at height N, mine more blocks to see confirmations grow
3. Clarify: "Confirmation count = current_height - block_height_containing_tx"

---

### Assessment Rubric (for lab assignments)

#### Knowledge (40 points)
- **Basic (28/40)**: Can define UTXO, mempool, block, and proof-of-work in own words
- **Intermediate (34/40)**: Explains why transactions need confirmations and how difficulty affects security
- **Advanced (40/40)**: Compares UTXO model to account model, discusses trade-offs

#### Skills (40 points)
- **Basic (28/40)**: Successfully completes wallet creation, faucet request, and transaction submission
- **Intermediate (34/40)**: Demonstrates change outputs, adjusts difficulty, interprets mining logs
- **Advanced (40/40)**: Debugs failed transaction (e.g., insufficient funds), explains why signature validation failed

#### Problem-Solving (20 points)
- **Basic (14/20)**: Follows step-by-step guide without errors
- **Intermediate (17/20)**: Recovers from one error independently (e.g., refreshes UI when balance doesn't update)
- **Advanced (20/20)**: Identifies root cause of issue using logs/curl commands without instructor help

**Partial credit guidelines**:
- Attempted transaction that fails validation → 50% credit if student explains what was wrong
- Incorrect explanation of UTXO but correct demonstration → 70% credit (doing > saying)
- Mining fails due to difficulty too high but student troubleshoots → full credit for problem-solving section

#### Extension Module Bonus (20 points)
- Successfully triggers fork scenario → +10 points
- Correctly predicts which chain will win before simulation completes → +5 points
- Explains accumulated work calculation with example → +5 points

**Total possible**: 100 points (+ 20 bonus for extension module)

---

### Common Student Questions (FAQ for instructors)

**Q: "Why use UTXOs instead of account balances like my bank?"**  
A: Bitcoin's UTXO model makes double-spending impossible—once you spend a UTXO, it's gone forever. Ethereum uses accounts for simplicity, but requires more complex state management. Both models are valid; we teach UTXO first because the constraints make correctness easier to reason about.

**Q: "Can I mine blocks faster by running more Docker containers?"**  
A: Not in this v1 demo—only one miner runs per node container and mining is synchronous. But in real blockchains, yes! More machines = more hashpower = higher chance of winning the race. The extension module demonstrates this with competing miners.

**Q: "What if I sign a transaction but never broadcast it?"**  
A: No one knows you created it. Transactions only exist once miners see them. (Analogy: writing a check but never handing it to the recipient.) This is why blockchain wallets can "draft" transactions offline.

**Q: "Why do we need mining at all? Can't the node just append transactions immediately?"**  
A: Who decides the order? In a distributed system with no central authority, mining is the *lottery* that prevents anyone from unilaterally controlling the chain. The cost (electricity/computation) deters spam and Sybil attacks. This is the core innovation of Bitcoin.

**Q: "Is this code production-ready?"**  
A: No—it's a teaching tool. Real blockchains add: peer-to-peer networking, disk persistence, consensus edge cases (orphan handling, reorg limits), proper ECDSA signature verification, script interpreters, and cryptographic accumulators for UTXO sets.

**Q: "Can I use this for my cryptocurrency project?"**  
A: Please don't. Use established libraries (bitcoinlib, web3.py) or frameworks (Substrate, Cosmos SDK). This demo intentionally simplifies security-critical components (deterministic signatures, no replay protection, no nonce/sequence numbers). See the "Why This Matters" section for pointers to production systems.

**Q: "My transaction disappeared from the mempool without being mined!"**  
A: This shouldn't happen in v1 (no reorgs). Check if node restarted (loses in-memory state). Extension module handles this via reorgs. For now, resubmit the transaction.

---

**Document changelog**:
- v2.1: Added cognitive checkpoints, troubleshooting decision tree, partial-credit rubric, simplified signature model, fixed Docker build context
- v2.0: Restructured with explicit learning objectives, progressive teaching phases, FAQ section
- v1.0: Original implementation-focused spec
