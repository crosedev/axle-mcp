# axle-mcp

An [MCP](https://modelcontextprotocol.io) server that exposes the [AXLE](https://github.com/axiom-ai/axle) (Axiom Lean Engine) CLI as tools for AI assistants like Claude.

AXLE is a remote API for Lean 4 proof engineering — it can check, repair, simplify, extract, and transform Lean theorems without requiring a local Lean installation.

## Tools

| Tool | Description |
|------|-------------|
| `axle_environments` | List available Lean environments (versions + Mathlib) |
| `axle_check` | Validate Lean code and report errors/warnings/info |
| `axle_verify_proof` | Check that a candidate proof matches a formal statement |
| `axle_extract_theorems` | Split a file into one-theorem-per-unit with rich metadata |
| `axle_repair_proofs` | Auto-repair broken proofs (replaces `sorry` with working tactics) |
| `axle_simplify_theorems` | Remove redundant tactics and clean up proof steps |
| `axle_disprove` | Find counterexamples to false theorems via property-based testing |
| `axle_theorem2sorry` | Replace proof bodies with `sorry` (create problem templates) |
| `axle_have2sorry` | Replace `have` proofs with `sorry` (targeted exercises) |
| `axle_sorry2lemma` | Lift `sorry` placeholders into standalone top-level lemmas |
| `axle_have2lemma` | Lift `have` statements into standalone top-level lemmas |
| `axle_theorem2lemma` | Convert between `theorem` and `lemma` keywords |
| `axle_rename` | Rename declarations and update all references |
| `axle_merge` | Combine multiple Lean snippets into one file |
| `axle_normalize` | Standardize Lean file formatting |

## Requirements

- Python 3.11+
- [`mcp`](https://pypi.org/project/mcp/) Python package (`pip install mcp`)
- The `axle` CLI installed and accessible

## Installation

### 1. Install dependencies

```bash
pip install mcp
```

### 2. Clone this repo

```bash
git clone https://github.com/Vilin97/axle-mcp
cd axle-mcp
```

### 3. Register with Claude Code

```bash
claude mcp add axle -s user \
  -e AXLE_BIN=/path/to/axle \
  -e AXLE_DEFAULT_ENVIRONMENT=lean-4.28.0 \
  -- python /path/to/axle-mcp/server.py
```

### 4. Register with Claude Desktop

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "axle": {
      "command": "python",
      "args": ["/path/to/axle-mcp/server.py"],
      "env": {
        "AXLE_BIN": "/path/to/axle",
        "AXLE_DEFAULT_ENVIRONMENT": "lean-4.28.0"
      }
    }
  }
}
```

## Configuration

| Environment variable | Default | Description |
|---------------------|---------|-------------|
| `AXLE_BIN` | `axle` | Path to the axle binary |
| `AXLE_DEFAULT_ENVIRONMENT` | `lean-4.28.0` | Default Lean environment for all tools |

## Usage examples

Once registered, Claude can use these tools directly. Some examples of what you can ask:

- *"Check if this Lean theorem compiles"* → `axle_check`
- *"Repair the sorry'd proofs in this file"* → `axle_repair_proofs`
- *"Turn this proof into a problem set by replacing proofs with sorry"* → `axle_theorem2sorry`
- *"Does this theorem have a counterexample?"* → `axle_disprove`
- *"Extract each theorem into its own self-contained snippet"* → `axle_extract_theorems`
- *"Merge these two Lean files into one"* → `axle_merge`

## Common parameters

Most tools accept these optional parameters:

- `environment` — Lean environment to use (run `axle_environments` to list available ones)
- `names` — comma-separated declaration names to process (default: all)
- `indices` — comma-separated 0-based indices to process
- `timeout` — max execution time in seconds (default: 120)
- `ignore_imports` — ignore import mismatches between the code and the environment

## How it works

Each MCP tool wraps the corresponding `axle` CLI command, passing Lean source code via stdin and returning the structured JSON response from the AXLE API. Tools that require multiple file arguments (`verify-proof`, `merge`) write temporary files automatically and clean them up after the call.
