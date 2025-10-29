# Optional DuckDB Mini-Lakehouse Lab

This optional lab bolts onto **Session 05 – Persistence** (after students have seen SQLite) or can run as a standalone 2×45-minute workshop. The goal is to help the cohort feel how DuckDB behaves as “SQLite for analytics” with a mini medallion layout and a word-count style map/reduce query—using nothing beyond their laptop.

Learners finish with:
1. A reproducible directory structure for Bronze → Silver → Gold Parquet data.
2. Two DuckDB files (PROD + DEV) wired together with environment variables.
3. CLI and Python patterns for exploring data, refreshing DEV from PROD, and creating views.
4. A “map/reduce” style aggregation that mimics word count across a sample event log.

---

## Before Lab – Preflight (JiTT)
- Install DuckDB CLI (macOS: `brew install duckdb`, Linux: download the static binary from [duckdb.org](https://duckdb.org/docs/installation/index.html), Windows: use winget/MSI).
- Ensure `uv` is on PATH (already required for the course).
- Clone a scratch repo or reuse the EX3 workspace—no external services required.
- Optional: `uv add duckdb polars pandas` if students prefer notebook/Python exploration.

---

## Agenda (2×45 Minutes)
| Segment | Duration | Format | Focus |
| --- | --- | --- | --- |
| Medallion primer + folder scaffold | 20 min | Talk + shell | Bronze/Silver/Gold directories, DEV vs PROD databases. |
| DuckDB CLI tour | 25 min | Live demo | Environment variables, SQL scripts, attaching prod to dev. |
| Break | 10 min | — | Encourage stretch + hydration. |
| Map/Reduce walk-through | 20 min | Guided coding | Word-count style aggregation over parquet event logs. |
| Python automation | 25 min | Guided coding | One Typer script to refresh DEV + run analytics. |
| Wrap | 10 min | Q&A | How to tie this into EX3 without expanding grade scope. |

---

## Part A – Scaffold the Mini Lakehouse (45 Minutes)

### 0. Verify the CLI is ready
```bash
duckdb --version
```
If the command prints a version (e.g., `DuckDB 0.10.2`), you are set. Otherwise, install DuckDB before proceeding.

### 1. Directory structure + environment variables
From the repo root (or a scratch directory), create the folders and export variables:
```bash
export DUCK_WH_DB="$PWD/duck/warehouse/sports_ml_warehouse.duckdb"
export DUCK_DEV_DB="$PWD/duck/dev/sports_ml_warehouse.duckdb"
export LAKE_ROOT="$PWD/duck/lake"

mkdir -p "$(dirname "$DUCK_WH_DB")" "$(dirname "$DUCK_DEV_DB")"/backups \
  "$LAKE_ROOT"/{bronze,silver,gold}
```

> Tip: Drop the three `export` commands into `scripts/duckdb.env` so students can `source scripts/duckdb.env` later:
> ```bash
> mkdir -p scripts
> cat <<'EOF' > scripts/duckdb.env
> export DUCK_WH_DB="$PWD/duck/warehouse/sports_ml_warehouse.duckdb"
> export DUCK_DEV_DB="$PWD/duck/dev/sports_ml_warehouse.duckdb"
> export LAKE_ROOT="$PWD/duck/lake"
> EOF
> ```
> Afterwards, activate the variables in any new shell:
> ```bash
> source scripts/duckdb.env
> ```

### 2. Seed Bronze data with Python (synthetic but realistic)
```bash
uv run python - <<'PY'
from pathlib import Path
import random
import json
import os

lake_root = Path(os.environ["LAKE_ROOT"])
root = lake_root / "bronze" / "events"
root.mkdir(parents=True, exist_ok=True)

actors = ["student", "instructor", "assistant"]
verbs = ["viewed", "updated", "deleted", "created"]
entities = ["movie", "rating", "playlist", "profile"]

records = []
random.seed(42)
for event_id in range(1, 10_001):
    records.append(
        {
            "event_id": event_id,
            "actor": random.choice(actors),
            "verb": random.choice(verbs),
            "entity": random.choice(entities),
            "duration_ms": random.randint(50, 2_500),
        }
    )

bronze_file = root / "events.jsonl"
bronze_file.write_text("\n".join(json.dumps(r) for r in records))
print(f"Wrote {bronze_file} with {len(records)} events")
PY
```

### 3. Load Bronze ➜ Silver (cleaned parquet) via DuckDB CLI
```bash
duckdb "$DUCK_WH_DB" -c "
  CREATE SCHEMA IF NOT EXISTS bronze;
  CREATE SCHEMA IF NOT EXISTS silver;

  COPY (
    SELECT
      event_id,
      lower(actor) AS actor,
      lower(verb) AS verb,
      lower(entity) AS entity,
      duration_ms
    FROM read_json('$LAKE_ROOT/bronze/events/events.jsonl')
  )
  TO '$LAKE_ROOT/silver/events/events.parquet'
  (FORMAT 'parquet', COMPRESSION 'zstd');
"
```

### 4. Build PROD warehouse references
```bash
duckdb "$DUCK_WH_DB" -c "
  CREATE OR REPLACE TABLE bronze.events AS
    SELECT * FROM read_json('$LAKE_ROOT/bronze/events/events.jsonl');

  CREATE OR REPLACE TABLE silver.events AS
    SELECT * FROM read_parquet('$LAKE_ROOT/silver/events/events.parquet');

  CREATE VIEW IF NOT EXISTS gold.event_summary AS
    SELECT
      actor,
      verb,
      COUNT(*) AS event_count,
      AVG(duration_ms)::INTEGER AS avg_duration_ms
    FROM silver.events
    GROUP BY actor, verb
    ORDER BY event_count DESC;
"
```

At this point, students have a persistent `.duckdb` file with Bronze (raw JSON view), Silver (clean parquet), and a Gold aggregate view.

---

## Part B – Map/Reduce Style Analytics (45 Minutes)

### 1. Refresh DEV from PROD without copying raw files
```bash
duckdb "$DUCK_DEV_DB" -c "
  ATTACH '$DUCK_WH_DB' AS prod (READ_ONLY);

  CREATE SCHEMA IF NOT EXISTS bronze_views;
  CREATE OR REPLACE VIEW bronze_views.events AS
    SELECT * FROM prod.bronze.events;

  CREATE SCHEMA IF NOT EXISTS gold_labs;
  CREATE OR REPLACE TABLE gold_labs.event_word_counts AS
    SELECT lower(token) AS token, COUNT(*) AS hits
    FROM prod.silver.events,
         UNNEST(string_split(verb || ' ' || entity, ' ')) AS token
    GROUP BY lower(token)
    ORDER BY hits DESC;
"
```

The `UNNEST(string_split(...))` pattern behaves like a classic map/reduce word count: **map** splits each verb/entity pair into tokens, **reduce** aggregates counts. Students can compare with the canonical Hadoop example, but here it runs locally in milliseconds.

Verify the Gold tables exist and contain data:
```bash
duckdb "$DUCK_DEV_DB" -c "
  SHOW TABLES;
"
```

### 2. Explore the results (CLI)
```bash
duckdb "$DUCK_DEV_DB" -c "
  SELECT * FROM gold_labs.event_word_counts LIMIT 10;
"
```

### 3. Bonus: Sliding window aggregations
Demonstrate richer analytics without leaving DuckDB:
```bash
duckdb "$DUCK_DEV_DB" -c "
  ATTACH '$DUCK_WH_DB' AS prod (READ_ONLY);
  SELECT
    verb,
    COUNT(*) AS total_events,
    AVG(duration_ms) AS avg_duration,
    PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY duration_ms) AS p90_duration
  FROM prod.silver.events
  GROUP BY verb
  ORDER BY total_events DESC;
"
```

### 4. Python helper to automate refresh + query (Typer CLI)
```bash
uv add typer duckdb
cat <<'PY' > duck_tools.py
import duckdb
import typer
import os

app = typer.Typer(help="DuckDB mini-lakehouse helpers")

def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise typer.BadParameter(f"Environment variable {name} is not set")
    return value

@app.command()
def refresh_dev() -> None:
    dev = _require_env("DUCK_DEV_DB")
    prod = _require_env("DUCK_WH_DB")
    with duckdb.connect(dev) as con:
        con.execute("ATTACH ? AS prod (READ_ONLY)", [prod])
        con.execute(
            """
            CREATE OR REPLACE TABLE gold_labs.event_word_counts AS
            SELECT lower(token) AS token, COUNT(*) AS hits
            FROM prod.silver.events,
                 UNNEST(string_split(verb || ' ' || entity, ' ')) AS token
            GROUP BY lower(token)
            ORDER BY hits DESC
            """
        )
    typer.echo("Refreshed DEV gold_labs.event_word_counts")

@app.command()
def top_tokens(limit: int = 10) -> None:
    dev = _require_env("DUCK_DEV_DB")
    with duckdb.connect(dev) as con:
        rows = con.execute(
            "SELECT token, hits FROM gold_labs.event_word_counts LIMIT ?", [limit]
        ).fetchall()
    for token, hits in rows:
        typer.echo(f"{token:>10} : {hits}")

if __name__ == '__main__':
    app()
PY
```

Usage:
```bash
source scripts/duckdb.env
uv run python duck_tools.py refresh-dev
uv run python duck_tools.py top-tokens --limit 5
```

---

## Troubleshooting Cheatsheet
- **“Conflicting lock is held”**: ensure no other DuckDB session is open (`ps aux | rg duckdb`), then remove stale `*.duckdb.wal` files if present.
- **“No such file or directory” errors**: confirm the three environment variables (`DUCK_WH_DB`, `DUCK_DEV_DB`, `LAKE_ROOT`) point to valid paths; rerun the `mkdir -p …` command.
- **Queries return zero rows**: re-run the Bronze → Silver load step to regenerate Parquet, then refresh views.
- **Typer CLI fails**: verify `uv add typer duckdb` succeeded and that you are sourcing the env file before running commands.

---

## Quick Demo – From Empty Folder to Insights
Paste each block (after sourcing `scripts/duckdb.env`) to go from nothing to a working DuckDB analytics sandbox:

```bash
# 1. Scaffold folders and environment
mkdir -p duck && mkdir -p scripts
cat <<'EOF' > scripts/duckdb.env
export DUCK_WH_DB="$PWD/duck/warehouse/sports_ml_warehouse.duckdb"
export DUCK_DEV_DB="$PWD/duck/dev/sports_ml_warehouse.duckdb"
export LAKE_ROOT="$PWD/duck/lake"
EOF
source scripts/duckdb.env
mkdir -p "$(dirname "$DUCK_WH_DB")" "$(dirname "$DUCK_DEV_DB")"/backups \
  "$LAKE_ROOT"/{bronze,silver,gold}

# 2. Generate Bronze JSON
uv run python - <<'PY'
from pathlib import Path
import random
import json
import os

lake_root = Path(os.environ["LAKE_ROOT"])
root = lake_root / "bronze" / "events"
root.mkdir(parents=True, exist_ok=True)

actors = ["student", "instructor", "assistant"]
verbs = ["viewed", "updated", "deleted", "created"]
entities = ["movie", "rating", "playlist", "profile"]

records = []
random.seed(42)
for event_id in range(1, 10_001):
    records.append(
        {
            "event_id": event_id,
            "actor": random.choice(actors),
            "verb": random.choice(verbs),
            "entity": random.choice(entities),
            "duration_ms": random.randint(50, 2_500),
        }
    )

bronze_file = root / "events.jsonl"
bronze_file.write_text("\n".join(json.dumps(r) for r in records))
print(f"Wrote {bronze_file} with {len(records)} events")
PY

# 3. Load into PROD and build Gold view
duckdb "$DUCK_WH_DB" -c "CREATE SCHEMA IF NOT EXISTS bronze; CREATE SCHEMA IF NOT EXISTS silver;"
duckdb "$DUCK_WH_DB" -c "COPY (SELECT event_id, lower(actor) AS actor, lower(verb) AS verb, lower(entity) AS entity, duration_ms FROM read_json('$LAKE_ROOT/bronze/events/events.jsonl')) TO '$LAKE_ROOT/silver/events/events.parquet' (FORMAT 'parquet', COMPRESSION 'zstd');"
duckdb "$DUCK_WH_DB" -c "CREATE OR REPLACE TABLE bronze.events AS SELECT * FROM read_json('$LAKE_ROOT/bronze/events/events.jsonl'); CREATE OR REPLACE TABLE silver.events AS SELECT * FROM read_parquet('$LAKE_ROOT/silver/events/events.parquet'); CREATE VIEW IF NOT EXISTS gold.event_summary AS SELECT actor, verb, COUNT(*) AS event_count, AVG(duration_ms)::INTEGER AS avg_duration_ms FROM silver.events GROUP BY actor, verb ORDER BY event_count DESC;"

# 4. Refresh DEV views and run map/reduce
duckdb "$DUCK_DEV_DB" -c "ATTACH '$DUCK_WH_DB' AS prod (READ_ONLY); CREATE SCHEMA IF NOT EXISTS bronze_views; CREATE OR REPLACE VIEW bronze_views.events AS SELECT * FROM prod.bronze.events; CREATE SCHEMA IF NOT EXISTS gold_labs; CREATE OR REPLACE TABLE gold_labs.event_word_counts AS SELECT lower(token) AS token, COUNT(*) AS hits FROM prod.silver.events, UNNEST(string_split(verb || ' ' || entity, ' ')) AS token GROUP BY lower(token) ORDER BY hits DESC;"
duckdb "$DUCK_DEV_DB" -c "SELECT * FROM gold_labs.event_word_counts LIMIT 5;"
```

Replace the `uv run python` line with the inline script from Part A, Step 2 if you prefer not to store a separate helper file.

---

## Where This Fits in the Course
- Use it after **Session 05** to contrast transactional SQLite (row-oriented) with analytical DuckDB (columnar).
- Reinforce local-first analytics: everything runs without cloud accounts, matching the course ethos.
- Treat the map/reduce demo as a bridge to big-data concepts without leaving a single laptop.
- Optional extension: challenge advanced students to add a Gold table that rolls up activity per 5-minute interval using `WINDOW` functions.
