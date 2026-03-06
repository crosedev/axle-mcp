"""MCP server for AXLE - Axiom Lean Engine CLI."""

import json
import os
import subprocess
import tempfile
from typing import Optional

from mcp.server.fastmcp import FastMCP

AXLE_BIN = os.environ.get("AXLE_BIN", "axle")
DEFAULT_ENV = os.environ.get("AXLE_DEFAULT_ENVIRONMENT", "lean-4.28.0")

mcp = FastMCP("axle")


def _run(args: list[str], stdin: Optional[str] = None) -> str:
    """Run axle with the given args, optionally passing content via stdin."""
    result = subprocess.run(
        [AXLE_BIN] + args,
        input=stdin,
        capture_output=True,
        text=True,
    )
    output = result.stdout.strip()
    # Try to parse and return JSON portion; fall back to raw output
    if output:
        # axle sometimes prints non-JSON before/after JSON (e.g. file paths written)
        # Find the JSON block
        try:
            # Find first '{' and last '}' to extract JSON
            start = output.index("{")
            end = output.rindex("}") + 1
            json_str = output[start:end]
            parsed = json.loads(json_str)
            # Include any non-JSON lines (e.g. "Wrote file.lean") as extra context
            prefix = output[:start].strip()
            suffix = output[end:].strip()
            if prefix or suffix:
                parsed["_output"] = "\n".join(filter(None, [prefix, suffix]))
            return json.dumps(parsed, indent=2)
        except (ValueError, json.JSONDecodeError):
            return output
    if result.stderr.strip():
        return result.stderr.strip()
    return ""


def _common_args(
    environment: str,
    names: Optional[str],
    indices: Optional[str],
    ignore_imports: bool,
    timeout: int,
) -> list[str]:
    args = ["--environment", environment]
    if names:
        args += ["--names", names]
    if indices:
        args += ["--indices", indices]
    if ignore_imports:
        args.append("--ignore-imports")
    if timeout != 120:
        args += ["--timeout-seconds", str(timeout)]
    return args


@mcp.tool()
def axle_environments() -> str:
    """List all available Lean environments (versions + Mathlib combinations)."""
    return _run(["environments"])


@mcp.tool()
def axle_check(
    code: str,
    environment: str = DEFAULT_ENV,
    mathlib_linter: bool = False,
    ignore_imports: bool = False,
    timeout: int = 120,
) -> str:
    """
    Evaluate Lean code and report all messages (errors, warnings, info).
    Use this to check if Lean code is valid. Faster than verify-proof.

    Args:
        code: Lean source code to check.
        environment: Lean environment/version to use (e.g. "lean-4.28.0").
        mathlib_linter: Enable Mathlib linters.
        ignore_imports: Ignore import mismatches.
        timeout: Max execution time in seconds.
    """
    args = ["check", "--environment", environment]
    if mathlib_linter:
        args.append("--mathlib-linter")
    if ignore_imports:
        args.append("--ignore-imports")
    if timeout != 120:
        args += ["--timeout-seconds", str(timeout)]
    args.append("-")
    return _run(args, stdin=code)


@mcp.tool()
def axle_verify_proof(
    formal_statement: str,
    code: str,
    environment: str = DEFAULT_ENV,
    permitted_sorries: Optional[str] = None,
    ignore_imports: bool = False,
    timeout: int = 120,
) -> str:
    """
    Validate a candidate Lean proof against a formal statement (sorry'd theorem).
    Returns whether the proof correctly proves the stated theorem.

    Args:
        formal_statement: The sorry'd theorem to verify against (Lean source).
        code: The candidate proof to verify (Lean source).
        environment: Lean environment/version to use.
        permitted_sorries: Comma-separated theorem names allowed to use sorry.
        ignore_imports: Ignore import mismatches.
        timeout: Max execution time in seconds.
    """
    # Write formal_statement to a temp file (it's a positional arg, not stdin)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".lean", delete=False) as f:
        f.write(formal_statement)
        stmt_path = f.name
    try:
        args = ["verify-proof", "--environment", environment]
        if permitted_sorries:
            args += ["--permitted-sorries", permitted_sorries]
        if ignore_imports:
            args.append("--ignore-imports")
        if timeout != 120:
            args += ["--timeout-seconds", str(timeout)]
        args += [stmt_path, "-"]
        return _run(args, stdin=code)
    finally:
        os.unlink(stmt_path)


@mcp.tool()
def axle_extract_theorems(
    code: str,
    environment: str = DEFAULT_ENV,
    ignore_imports: bool = False,
    timeout: int = 120,
) -> str:
    """
    Split a Lean file into separate units, each containing a single theorem
    with its required dependencies. Returns rich metadata per theorem including
    dependency analysis, tactic counts, type information, and token lists.

    Args:
        code: Lean source code to split.
        environment: Lean environment/version to use.
        ignore_imports: Ignore import mismatches.
        timeout: Max execution time in seconds.
    """
    args = ["extract-theorems", "--environment", environment]
    if ignore_imports:
        args.append("--ignore-imports")
    if timeout != 120:
        args += ["--timeout-seconds", str(timeout)]
    args.append("-")
    return _run(args, stdin=code)


@mcp.tool()
def axle_rename(
    code: str,
    declarations: str,
    environment: str = DEFAULT_ENV,
    ignore_imports: bool = False,
    timeout: int = 120,
) -> str:
    """
    Rename declarations in Lean code. Updates all references automatically.

    Args:
        code: Lean source code.
        declarations: Mapping of old to new names (format: "old=new,old2=new2").
        environment: Lean environment/version to use.
        ignore_imports: Ignore import mismatches.
        timeout: Max execution time in seconds.
    """
    args = [
        "rename",
        "--environment", environment,
        "--declarations", declarations,
    ]
    if ignore_imports:
        args.append("--ignore-imports")
    if timeout != 120:
        args += ["--timeout-seconds", str(timeout)]
    args.append("-")
    return _run(args, stdin=code)


@mcp.tool()
def axle_theorem2lemma(
    code: str,
    environment: str = DEFAULT_ENV,
    target: str = "lemma",
    names: Optional[str] = None,
    indices: Optional[str] = None,
    ignore_imports: bool = False,
    timeout: int = 120,
) -> str:
    """
    Convert between `theorem` and `lemma` declaration keywords.

    Args:
        code: Lean source code.
        environment: Lean environment/version to use.
        target: Target keyword — "lemma" or "theorem".
        names: Comma-separated declaration names to process (all if omitted).
        indices: Comma-separated 0-based indices to process.
        ignore_imports: Ignore import mismatches.
        timeout: Max execution time in seconds.
    """
    args = ["theorem2lemma", "--environment", environment, "--target", target]
    args += _common_args(environment, names, indices, ignore_imports, timeout)[2:]
    args.append("-")
    return _run(args, stdin=code)


@mcp.tool()
def axle_theorem2sorry(
    code: str,
    environment: str = DEFAULT_ENV,
    names: Optional[str] = None,
    indices: Optional[str] = None,
    ignore_imports: bool = False,
    timeout: int = 120,
) -> str:
    """
    Replace theorem proof bodies with `sorry`. Useful for creating problem
    templates or proof obligations from complete solutions.

    Args:
        code: Lean source code.
        environment: Lean environment/version to use.
        names: Comma-separated theorem names to process (all if omitted).
        indices: Comma-separated 0-based indices to process.
        ignore_imports: Ignore import mismatches.
        timeout: Max execution time in seconds.
    """
    args = ["theorem2sorry"] + _common_args(environment, names, indices, ignore_imports, timeout)
    args.append("-")
    return _run(args, stdin=code)


@mcp.tool()
def axle_merge(
    documents: list[str],
    environment: str = DEFAULT_ENV,
    include_alts_as_comments: bool = False,
    ignore_imports: bool = False,
    timeout: int = 120,
) -> str:
    """
    Combine multiple Lean code snippets into a single file, deduplicating
    imports and shared definitions.

    Args:
        documents: List of Lean source code strings to merge.
        environment: Lean environment/version to use.
        include_alts_as_comments: Preserve alternate versions as comments.
        ignore_imports: Ignore import mismatches.
        timeout: Max execution time in seconds.
    """
    tmp_files = []
    try:
        for doc in documents:
            f = tempfile.NamedTemporaryFile(mode="w", suffix=".lean", delete=False)
            f.write(doc)
            f.close()
            tmp_files.append(f.name)

        args = ["merge", "--environment", environment]
        if include_alts_as_comments:
            args.append("--include-alts-as-comments")
        if ignore_imports:
            args.append("--ignore-imports")
        if timeout != 120:
            args += ["--timeout-seconds", str(timeout)]
        args += tmp_files
        return _run(args)
    finally:
        for path in tmp_files:
            os.unlink(path)


@mcp.tool()
def axle_simplify_theorems(
    code: str,
    environment: str = DEFAULT_ENV,
    names: Optional[str] = None,
    indices: Optional[str] = None,
    simplifications: Optional[str] = None,
    ignore_imports: bool = False,
    timeout: int = 120,
) -> str:
    """
    Simplify theorem proofs by removing redundant tactics, unused `have`
    statements, and unnecessary steps.

    Args:
        code: Lean source code.
        environment: Lean environment/version to use.
        names: Comma-separated theorem names to process (all if omitted).
        indices: Comma-separated 0-based indices to process.
        simplifications: Comma-separated simplification passes to apply.
        ignore_imports: Ignore import mismatches.
        timeout: Max execution time in seconds.
    """
    args = ["simplify-theorems"] + _common_args(environment, names, indices, ignore_imports, timeout)
    if simplifications:
        args += ["--simplifications", simplifications]
    args.append("-")
    return _run(args, stdin=code)


@mcp.tool()
def axle_repair_proofs(
    code: str,
    environment: str = DEFAULT_ENV,
    names: Optional[str] = None,
    indices: Optional[str] = None,
    repairs: Optional[str] = None,
    terminal_tactics: Optional[str] = None,
    ignore_imports: bool = False,
    timeout: int = 120,
) -> str:
    """
    Attempt to repair broken theorem proofs (e.g. those using `sorry`) by
    applying various fix strategies. Default terminal tactic is `grind`.

    Args:
        code: Lean source code with broken/sorry proofs.
        environment: Lean environment/version to use.
        names: Comma-separated theorem names to repair (all if omitted).
        indices: Comma-separated 0-based indices to repair.
        repairs: Comma-separated repair strategies to apply.
        terminal_tactics: Comma-separated tactics to try for closing goals.
        ignore_imports: Ignore import mismatches.
        timeout: Max execution time in seconds.
    """
    args = ["repair-proofs"] + _common_args(environment, names, indices, ignore_imports, timeout)
    if repairs:
        args += ["--repairs", repairs]
    if terminal_tactics:
        args += ["--terminal-tactics", terminal_tactics]
    args.append("-")
    return _run(args, stdin=code)


@mcp.tool()
def axle_have2lemma(
    code: str,
    environment: str = DEFAULT_ENV,
    names: Optional[str] = None,
    indices: Optional[str] = None,
    include_have_body: bool = False,
    reconstruct_callsite: bool = False,
    verbosity: int = 0,
    ignore_imports: bool = False,
    timeout: int = 120,
) -> str:
    """
    Extract `have` statements from theorem proofs and lift them into standalone
    top-level lemmas with the appropriate context as parameters.

    Args:
        code: Lean source code.
        environment: Lean environment/version to use.
        names: Comma-separated theorem names to process (all if omitted).
        indices: Comma-separated 0-based indices to process.
        include_have_body: Include proof bodies in extracted lemmas.
        reconstruct_callsite: Replace have statement with a lemma call.
        verbosity: Pretty-printer verbosity level (0-2).
        ignore_imports: Ignore import mismatches.
        timeout: Max execution time in seconds.
    """
    args = ["have2lemma"] + _common_args(environment, names, indices, ignore_imports, timeout)
    if include_have_body:
        args.append("--include-have-body")
    if reconstruct_callsite:
        args.append("--reconstruct-callsite")
    if verbosity:
        args += ["--verbosity", str(verbosity)]
    args.append("-")
    return _run(args, stdin=code)


@mcp.tool()
def axle_have2sorry(
    code: str,
    environment: str = DEFAULT_ENV,
    names: Optional[str] = None,
    indices: Optional[str] = None,
    ignore_imports: bool = False,
    timeout: int = 120,
) -> str:
    """
    Replace `have` statement proof bodies with `sorry`, keeping the statements.
    Useful for creating targeted exercises from complete proofs.

    Args:
        code: Lean source code.
        environment: Lean environment/version to use.
        names: Comma-separated theorem names to process (all if omitted).
        indices: Comma-separated 0-based indices to process.
        ignore_imports: Ignore import mismatches.
        timeout: Max execution time in seconds.
    """
    args = ["have2sorry"] + _common_args(environment, names, indices, ignore_imports, timeout)
    args.append("-")
    return _run(args, stdin=code)


@mcp.tool()
def axle_sorry2lemma(
    code: str,
    environment: str = DEFAULT_ENV,
    names: Optional[str] = None,
    indices: Optional[str] = None,
    extract_sorries: bool = True,
    extract_errors: bool = True,
    reconstruct_callsite: bool = False,
    verbosity: int = 0,
    ignore_imports: bool = False,
    timeout: int = 120,
) -> str:
    """
    Extract `sorry` placeholders and type errors from proofs and lift them
    into standalone top-level lemmas with the full proof context as parameters.

    Args:
        code: Lean source code.
        environment: Lean environment/version to use.
        names: Comma-separated theorem names to process (all if omitted).
        indices: Comma-separated 0-based indices to process.
        extract_sorries: Extract sorry placeholders (default True).
        extract_errors: Extract type errors (default True).
        reconstruct_callsite: Replace sorry with a lemma call.
        verbosity: Pretty-printer verbosity level (0-2).
        ignore_imports: Ignore import mismatches.
        timeout: Max execution time in seconds.
    """
    args = ["sorry2lemma"] + _common_args(environment, names, indices, ignore_imports, timeout)
    if not extract_sorries:
        args.append("--no-extract-sorries")
    if not extract_errors:
        args.append("--no-extract-errors")
    if reconstruct_callsite:
        args.append("--reconstruct-callsite")
    if verbosity:
        args += ["--verbosity", str(verbosity)]
    args.append("-")
    return _run(args, stdin=code)


@mcp.tool()
def axle_disprove(
    code: str,
    environment: str = DEFAULT_ENV,
    names: Optional[str] = None,
    indices: Optional[str] = None,
    terminal_tactics: Optional[str] = None,
    ignore_imports: bool = False,
    timeout: int = 120,
) -> str:
    """
    Attempt to disprove theorems by proving their negation and finding
    counterexamples using property-based testing (plausible).

    Args:
        code: Lean source code with theorems to attempt to disprove.
        environment: Lean environment/version to use.
        names: Comma-separated theorem names to try to disprove (all if omitted).
        indices: Comma-separated 0-based indices to try.
        terminal_tactics: Comma-separated tactics to use when disproving.
        ignore_imports: Ignore import mismatches.
        timeout: Max execution time in seconds.
    """
    args = ["disprove"] + _common_args(environment, names, indices, ignore_imports, timeout)
    if terminal_tactics:
        args += ["--terminal-tactics", terminal_tactics]
    args.append("-")
    return _run(args, stdin=code)


@mcp.tool()
def axle_normalize(
    code: str,
    environment: str = DEFAULT_ENV,
    normalizations: Optional[str] = None,
    ignore_imports: bool = False,
    timeout: int = 120,
) -> str:
    """
    Standardize Lean file formatting to prepare for merge operations.

    Args:
        code: Lean source code to normalize.
        environment: Lean environment/version to use.
        normalizations: Comma-separated normalization passes to apply.
        ignore_imports: Ignore import mismatches.
        timeout: Max execution time in seconds.
    """
    args = ["normalize", "--environment", environment]
    if normalizations:
        args += ["--normalizations", normalizations]
    if ignore_imports:
        args.append("--ignore-imports")
    if timeout != 120:
        args += ["--timeout-seconds", str(timeout)]
    args.append("-")
    return _run(args, stdin=code)


if __name__ == "__main__":
    mcp.run()
