## Streamlit + FastAPI Microservices Demo (Blockchain-Inspired)

### What we’re building
- **Goal**: a three-service, all-HTTP lab that lets students watch “wallet → mempool → mined block” transitions without needing a real blockchain.
- **Stack**: Streamlit UI + two FastAPI services. Everything runs locally via `docker compose up`.
- **Story**: Students mint faucet coins, craft signed UTXO transactions, push them through a coordinator API, and trigger a proof-of-work toy miner to confirm blocks. The demo visualizes confirmations, forks, and “most accumulated work” decisions.
- **UTXO**: “Unspent Transaction Output” is a spendable coin created by a previous transaction; owning its locking script gives you the right to consume its value as an input in a future transaction.

### Services (all speak HTTP)
1. **`streamlit-wallet`** (front-end)
   - Streamlit app acting as wallet + block explorer.
   - Generates keys client-side, stores them in session state, and shows live data pulled from the coordinator.
   - Can POST signed transactions and trigger “mine block” actions for classroom demos.
2. **`tx-coordinator`** (backend #1)
   - FastAPI service that exposes a clean REST layer for the UI.
   - Validates requests (shapes, signature sanity checks), fans out to the node, and fans in responses for the UI.
   - Hosts Server-Sent Events (SSE) so Streamlit can subscribe to new tx/block notifications without websockets.
3. **`node-miner`** (backend #2)
   - FastAPI service that owns the in-memory blockchain state, mempool, UTXO set, and simplified PoW miner loop.
   - Provides HTTP endpoints for submitting transactions, inspecting chain tips, and adjusting mining difficulty for live demos.
   - Runs a background task that repeatedly builds blocks from the mempool, brute-forces a nonce, and commits to the canonical chain when the header hash beats the target.

### Service quick reference (plain language)
- **Streamlit wallet**: the UI students click on. It lets them make wallets, see balances, craft transactions, and watch blocks appear. Think of it as “the phone app” in traditional crypto wallets.
- **Transaction coordinator**: the helpful receptionist. Every UI request hits it first; it checks that the data looks sane and then forwards the real work to the node. Doing this keeps the node lean and lets us add classroom-friendly features (SSE, validations) without poking core consensus code.
- **Node miner**: the pretend blockchain node. It stores the ledger (list of blocks), the mempool (pending transactions), and a toy proof-of-work miner. When it mines a block, it decides which transactions are officially confirmed.
- **Optional extra miners**: exact copies of the node miner that we can spin up to simulate network competition. They talk HTTP just like the primary node, so students focus on behavior rather than networking internals.

### Concept glossary
- **UTXO (Unspent Transaction Output)**: a single coin produced by a past transaction. If a UTXO says “5 tokens locked to Alice’s address,” only Alice (with her private key) can spend those 5 tokens, split them, or combine them in a new transaction.
- **Transaction input / output**: inputs point to UTXOs you want to spend; outputs describe new UTXOs you are creating. Inputs must add up to at least as much value as the outputs (extra becomes a fee).
- **Mempool**: short for “memory pool.” Every blockchain node keeps a list of valid-but-not-yet-mined transactions in RAM so miners can pick from them. Yes, “mempool” is the standard Bitcoin/Ethereum term, so we keep it for authenticity—just make sure to define it once (like above) when teaching.
- **Block**: a batch of transactions plus a header that references the previous block. Together they form an append-only chain where every block depends on the one before it.
- **Proof of Work (PoW)**: a lottery where miners keep hashing the block header with different nonces until the hash is smaller than a target number. Finding such a nonce is hard; verifying the result is one hash. More work = more security.
- **Difficulty / target**: how small the winning hash must be. Smaller target → harder puzzle → longer expected mining time. We expose this as a slider in the demo.
- **Confirmation**: once your transaction sits in a block, each additional block on top counts as another confirmation. More confirmations make it exponentially harder for an attacker to rewrite history.
- **Fork / reorg**: when two miners find blocks at similar times, the chain temporarily splits. Eventually the branch with more accumulated work wins and the other branch is abandoned (“reorganized”). Our optional extra miners help demonstrate this.

### Blockchain concepts (zero-background primer)
- **Hashing**: SHA-256 turns any input into a deterministic 256-bit “fingerprint.” Change the input by a single bit and the output becomes completely different, which is why hashes reveal tampering instantly.
- **Blocks & nonces**: Each block contains its data plus a nonce. Miners iterate nonces until the block hash satisfies a rule (e.g., starts with four zeros or is below a numeric target). That search is the “work” in Proof of Work.
- **Chaining/immutability**: Every block stores the previous block’s hash. Changing old data would require recomputing that block’s hash and every block after it, making retroactive edits impractical once a chain grows.
- **Distribution & consensus**: Multiple peers hold full copies. When two versions disagree, nodes choose the chain with the most accumulated work (i.e., the longer/“heavier” chain). Comparing tip hashes makes disagreement obvious.
- **Tokens & coinbase**: Transactions describe transfers between UTXOs; there are no account balances. A special “coinbase” transaction appears at the top of each block to mint the miner’s reward. Anyone can follow provenance by tracing outputs back through earlier blocks.

### Wallet + node variations
- Streamlit spawns any number of wallets per user session—each address just maps to a generated keypair stored in Streamlit session state, so students can juggle multiple identities (e.g., “Alice”, “Bob”, “Miner”) simultaneously.
- The faucet endpoint supports creating many wallets quickly by calling `POST /api/wallets` repeatedly or uploading pre-made mnemonic/privkey files for scripted demos.
- Docker Compose can optionally launch extra `node-miner` replicas (`node-miner-2`, `node-miner-3`) behind the same API contract to mimic a small network. Only one node is authoritative by default, but instructors can flip a profile (e.g., `docker compose --profile forked up`) to watch competing miners race and demonstrate reorgs.
- Keeping just three core services (UI + coordinator + primary node) preserves simplicity for students, while the optional additional miners remain a toggle for advanced demos rather than a required baseline.

### What Docker Compose gives us
- A single `docker-compose.yml` spins up all three services plus a shared bridge network.
- `node-miner` is the only service with a persistent volume (bind-mount) so instructors can reset chain data by removing `./tmp_node_state`.
- Environment variables keep knobs adjustable (difficulty target, faucet amount, default miner address, etc.) without editing code.
- Health checks ensure Streamlit waits for both FastAPI services to report ready before attempting to call them.
- Optional profile `compose --profile forked` can start a second miner container to demonstrate competing chains.

### HTTP surface (high level)
| Service | Endpoint | Description |
|---------|----------|-------------|
| streamlit-wallet → tx-coordinator | `POST /api/wallets` | UI asks for new keypair/faucet; coordinator relays to node. |
| streamlit-wallet → tx-coordinator | `POST /api/tx` | Submit a signed transaction payload; coordinator re-hashes + forwards to node. |
| streamlit-wallet → tx-coordinator | `POST /api/mine` | Button that instructs node to try mining immediately (difficulty knob included). |
| tx-coordinator → node-miner | `POST /node/tx` | Validated tx enters mempool if all referenced UTXOs exist. |
| tx-coordinator → node-miner | `GET /node/utxos/{address}` | Wallet balance/UTXO list. |
| tx-coordinator → node-miner | `GET /node/chain/head` | Returns tip hash, height, accumulated work. |
| tx-coordinator → node-miner | `GET /node/events/stream` | Long-poll endpoint delivering tx + block events that coordinator re-broadcasts via SSE. |

### How the pieces work together
1. **Faucet / onboarding**
   - Streamlit calls `POST /api/wallets`.
   - Coordinator requests a fresh keypair from `node-miner`, which creates a “coinbase” UTXO locked to that address and updates its state.
   - Coordinator emits an SSE event, Streamlit refreshes the balances panel.
2. **Spending**
   - Streamlit lists UTXOs via `GET /api/wallets/{addr}` and lets the student pick inputs + outputs.
   - Streamlit signs locally (using `ecdsa`), shows the raw transaction JSON, and POSTs it.
   - Coordinator recomputes the txid, rejects malformed scripts early, and forwards to the node; node validates against UTXO set and keeps it in the mempool.
3. **Mining + confirmation tracking**
   - Miner loop continuously tries nonces (difficulty intentionally low so blocks land every few seconds).
   - When a block is found, node updates UTXOs, prunes spent outputs from mempool, and emits a block event.
   - Coordinator relays the event to Streamlit, which updates confirmation counters and a mini block explorer table.
4. **Fork + “most work” demo**
   - Instructors enable the optional `forked-miner` Compose service or manually call `POST /node/mine?branch=alt`.
   - Streamlit visualizes both branches as they race; when one accumulates more work, the UI highlights the reorg and shows which transactions rolled back into the mempool.

### Teaching Proof-of-Work step by step
- **Concept primer (5 min)**: Instructors flip to the “Mining 101” Streamlit tab that lists the block header fields (`version`, `prev_hash`, `merkle_root`, `timestamp`, `bits`, `nonce`) and displays the SHA256d hash updating live as sliders tweak the nonce. This makes it obvious that PoW is just “find a nonce so hash < target”.
- **Hands-on mining panel (10 min)**: Streamlit exposes a difficulty slider plus a “start mining” button that calls `POST /api/mine`. Students watch:
  - hash attempts/sec (reported from node-miner via SSE),
  - current target + numeric representation,
  - pending transactions included in the candidate block,
  - live count of nonce iterations before success.
  The UI charts block time vs. target so instructors can show why lowering the target slows everything down.
- **Chain reaction (10 min)**: After mining a block, the UI automatically highlights which UTXOs were consumed and what new outputs appeared. Students refresh the wallet balances to see their tx move from “pending” to “confirmed (1/6)”.
- **Fork + most-work demo (10 min)**: Enable the extra miner profile; Streamlit’s timeline draws both branches with accumulated work and confirmation counts. Instructors pause and ask students to predict which branch will win, then resume and show the reorg message (“Block 12 orphaned; tx abcd re-entered mempool”).
- **Take-home exercise**: Provide a lab where students tweak miner code to implement a “speed boost” (e.g., skip odd nonces) and observe whether it statistically changes block-find time, reinforcing the probabilistic nature of PoW.
- **Talking point checklist** (so the .md stays self-contained for instructors):
  1. Mining = building block header + brute-forcing nonce.
  2. Target encoded via `bits`; halving the target doubles expected work.
  3. Valid block instantly verifiable by anyone (one hash compare).
  4. Forks resolve by cumulative work, not wall-clock time.
  5. Economic intuition: once enough confirmations pile up, rewriting history becomes infeasible unless attacker controls >50% hashpower.

### Why this fits the course
- Keeps the course emphasis on FastAPI + Streamlit while sneaking in microservice and blockchain fundamentals.
- Shows how HTTP services coordinate state via clearly-defined edges instead of message buses.
- Lets students run everything locally without extra dependencies (just Docker + Compose), matching the class constraints.
- Provides rich talking points: REST design, background workers, eventual consistency, and how PoW secures append-only logs.

### Build specification (hand-off for automation)

#### Repository layout
```
examples/blockchain-demo/
├── docker-compose.yml
├── .env.example
├── README.md (run instructions)
├── shared/
│   └── models.py            # Pydantic/BaseModel schemas shared across services
├── node-miner/
│   ├── pyproject.toml       # uv-managed (python>=3.11)
│   └── app/
│       ├── main.py          # FastAPI entrypoint
│       ├── mining.py        # background miner loop
│       ├── chain.py         # UTXO set, block store
│       └── settings.py
├── tx-coordinator/
│   ├── pyproject.toml
│   └── app/main.py
├── streamlit-wallet/
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
- Streamlit app: `streamlit>=1.36`, `plotly`, `requests`, `websocket-client` (for SSE fallback).

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
- Each service has its own Dockerfile at the project root (`node-miner/Dockerfile`, etc.).
- Pattern:
  ```Dockerfile
  FROM python:3.12-slim AS runtime
  RUN pip install --upgrade pip uv
  WORKDIR /app
  COPY pyproject.toml uv.lock ./
  COPY app ./app
  # Streamlit adds app.py, shared models mounted via build context
  COPY ../shared /app/shared
  RUN uv sync --frozen
  ENV PYTHONUNBUFFERED=1
  CMD ["uv", "run", "fastapi", "run", "app/main.py", "--port", "8000"]
  ```
- Streamlit container swaps the final command for `["uv","run","streamlit","run","app.py","--server.port","8501","--server.address","0.0.0.0"]`.
- Docker Compose builds each service with `context: ./service-name` and `target` optional for multi-stage (e.g., `builder` vs `runtime`) if we later add unit tests to images.

#### Docker Compose contract
- Services:
  - `streamlit-wallet`: builds from `./streamlit-wallet`, exposes `8501`.
  - `tx-coordinator`: builds from `./tx-coordinator`, exposes `8001`.
  - `node-miner`: builds from `./node-miner`, exposes `8000`, mounts `./tmp_node_state:/data`.
  - Optional profile `forked` adds `node-miner-2`, `node-miner-3` containers reusing same image with env `NODE_NAME`.
- Networks: single bridge `blocknet`.
- Health checks: FastAPI endpoints `/healthz`, Streamlit requests `GET /_stcore/health`.
- Environment variables (load from `.env`): `FAUCET_AMOUNT`, `MINER_ADDRESS`, `DIFFICULTY_BITS`, `BLOCK_INTERVAL_TARGET`, `STREAMLIT_API_BASE`.

#### Shared models (`shared/models.py`)
- `HexBytes = constr(regex="^0x[0-9a-f]+$")`
- `TxOut { value:int, locking_script:str }`
- `TxIn { prev_txid:HexBytes, prev_index:int, signature:HexBytes, pubkey:HexBytes }`
- `Transaction { vin:list[TxIn], vout:list[TxOut], locktime:int=0 }`
- `BlockHeader { version:int, prev_hash:HexBytes, merkle_root:HexBytes, timestamp:int, bits:int, nonce:int }`
- `Block { header:BlockHeader, txs:list[Transaction], height:int }`
- `Event { type:Literal["tx","block","reorg"], payload:dict, timestamp:int }`
- `WalletInfo { address:str, utxos:list[TxOut], balance:int }`

#### API contracts
- **Node miner** (`http://node-miner:8000`):
  - `GET /healthz` → `{status:"ok"}`
  - `GET /node/chain/head` → `{height:int, tip:HexBytes, accumulated_work:int, difficulty:int}`
  - `GET /node/blocks` → `{blocks:list[Block]}` (limit query param)
  - `GET /node/mempool` → `{txs:list[Transaction], count:int}`
  - `GET /node/utxos/{address}` → `WalletInfo`
  - `POST /node/tx` body `Transaction` → `{txid:HexBytes, status:"accepted"|"rejected", reason?:str}`
  - `POST /node/mine` body `{force:bool=False, difficulty_bits?:int}` → `{started:bool}`
  - `GET /node/events/stream` → SSE stream sending `Event` JSON (id increments)
- **Tx coordinator** (`http://tx-coordinator:8001`):
  - `POST /api/wallets` → generates or requests wallet+faucet: `{address:str, txid:HexBytes}`
  - `GET /api/wallets/{address}` → `WalletInfo`
  - `POST /api/tx` body `Transaction` → `{"txid":HexBytes,"status":"forwarded"}`
  - `POST /api/mine` body `{difficulty_bits?:int}` → proxies to node.
  - `GET /api/events` → SSE endpoint that multiplexes node events to the UI.
- **Streamlit client expectations**:
  - Reads base URL from `STREAMLIT_API_BASE`.
  - Uses SSE to update dashboards; fallback to polling every 3s if SSE unavailable.

#### Streamlit UI features
- Pages:
  1. `Home` – instructions + start/stop mining buttons.
  2. `Wallets` – create wallets, view balances, build transactions (drag inputs → outputs).
  3. `Mempool & Blocks` – tables for pending txs, recent blocks, block time chart.
  4. `Mining 101` – nonce slider, live hash display, difficulty visualization.
  5. `Fork Visualizer` – tree diagram of competing chains when fork profile enabled.
- Use `st.session_state` to store wallets `{label,address,privkey}` and autopopulate tx builder.
- Every page includes a short explainer panel (`st.expander` + Markdown) that restates key terms (wallet, mempool, block, PoW, fork) so students see definitions right where they interact with the UI. Tooltips on table headers clarify fields like “TxID”, “Nonce”, “Work”, and “Confirmations”.

#### Mining & background tasks
- `node-miner` launches an `asyncio.Task` at startup:
  1. Sleep for `MINING_LOOP_POLL_SECONDS` (default 0.1).
  2. If `auto_mine` or forced, build candidate block from mempool (coinbase first).
  3. Loop over nonce 0..2^32-1 computing `sha256d(header)`.
  4. On success, persist block (in-memory list + optional JSON file in `/data`), mutate UTXO set, drop spent txs, push `block` event.
  5. If exhausted nonce space, refresh timestamp + rebuild coinbase (extranonce).
- Use `asyncio.create_task` and FastAPI lifespan events; ensure graceful shutdown cancels miner task.

#### Event semantics
- SSE data framed as `event:<type>` and `data:<json>`.
- `tx` payload: `{txid, inputs:[{txid,index,value}], outputs:[{address,value}], status:"mempool"}`
- `block` payload: `{height, hash, txids, work, orphaned:false}`
- `reorg` payload: `{old_tip, new_tip, dropped_blocks:[hash], replayed_txs:[txid]}`

#### Acceptance criteria
1. `docker compose up` exposes Streamlit on `localhost:8501` and it can create a wallet, request faucet funds, submit a tx, and mine a block end-to-end.
2. Unit tests under `examples/blockchain-demo/tests` pass via `uv run pytest -q`.
3. Mining difficulty slider demonstrably affects average block time in the UI chart.
4. Optional `forked` profile spins up at least two miners; Streamlit fork visualizer shows a reorg after one chain surpasses the other.
5. Documentation (`examples/blockchain-demo/README.md`) explains setup, env vars, and teaching tips in <500 words.

#### Feature checklist aligned with goal
- ✅ Multiple wallets per Streamlit session with faucet funding and signed transactions.
- ✅ Coordinator validates and forwards all transactions/mining commands, exposes SSE feed.
- ✅ Node miner maintains mempool, UTXO set, block list, and adjustable PoW loop plus optional replicas for fork demos.
- ✅ Streamlit dashboards: Wallets, Mempool & Blocks, Mining 101 (nonce slider), Fork Visualizer.
- ✅ Full Docker/uv toolchain so instructors run `uv run pytest` locally or `docker compose up` for class demos without extra setup.
- 🎯 Teaching objective: give students an end-to-end feel for how wallets, mempools, and proof-of-work mining interact while still using familiar Python + FastAPI + Streamlit patterns from the main course.

### Next implementation steps
1. Scaffold the three services: `examples/blockchain-demo/{streamlit-wallet,tx-coordinator,node-miner}` with their own `pyproject.toml` managed by `uv`.
2. Author the Compose file with health checks, named volumes, shared environment file, and optional forked miner profile.
3. Implement shared `models.py` (Pydantic) so both FastAPI services agree on transaction, block, and event schemas.
4. Build the Streamlit pages: wallet dashboard, mempool table, block explorer timeline, and “fork visualizer”.
5. Add integration tests under `examples/blockchain-demo/tests/` that spin up the FastAPI apps in-memory to validate tx + block rules without Docker.
