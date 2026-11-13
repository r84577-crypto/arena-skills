#!/usr/bin/env python3
"""Tests for check-env-exposure.py.

A checker that has never failed is not evidence of anything. Each case below
plants a real leak in a temporary tree and asserts the checker reports it —
and that the clean case stays clean, so the checker is not just "always red".
"""

from __future__ import annotations

import os
import pathlib
import subprocess
import sys
import tempfile
import textwrap

SCRIPT = pathlib.Path(__file__).resolve().parent / "check-env-exposure.py"


def run_in(root: pathlib.Path) -> tuple[int, str]:
    """Run the checker against a throwaway tree via ENVCHECK_ROOT."""
    env = {**os.environ, "ENVCHECK_ROOT": str(root)}
    proc = subprocess.run(
        [sys.executable, str(SCRIPT)], capture_output=True, text=True, env=env
    )
    return proc.returncode, proc.stdout + proc.stderr


def case(name: str, files: dict[str, str], want_finding: bool) -> bool:
    with tempfile.TemporaryDirectory() as td:
        root = pathlib.Path(td)
        for rel, content in files.items():
            p = root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
        code, out = run_in(root)
        ok = (code == 1) if want_finding else (code == 0)
        mark = "ok  " if ok else "FAIL"
        print(f"  {mark} {name}")
        if not ok:
            print(textwrap.indent(out.strip()[:600], "        "))
        return ok


def main() -> int:
    results = []

    results.append(
        case(
            "secret name behind a browser prefix is caught",
            {"app/.env.example": "NEXT_PUBLIC_SUPABASE_SERVICE_ROLE_KEY=\n"},
            True,
        )
    )
    results.append(
        case(
            "a committed .env with real values is caught",
            {"app/.env": "RESEND_API_KEY=re_live_abc123\n"},
            True,
        )
    )
    results.append(
        case(
            "a secret-shaped name with a value in the example is caught",
            {"app/.env.example": "GMAIL_APP_PASSWORD=hunter2\n"},
            True,
        )
    )
    results.append(
        case(
            "the anon key is allowed to be public (RLS is the guard)",
            {"app/.env.example": "NEXT_PUBLIC_SUPABASE_URL=https://x.supabase.co\n"},
            False,
        )
    )
    results.append(
        case(
            "empty server-only example is clean",
            {
                "app/.env.example": "RESEND_API_KEY=\nWHATSAPP_TOKEN=\nNEXT_PUBLIC_SUPABASE_ANON_KEY=\n"
            },
            False,
        )
    )
    results.append(
        case(
            "VITE_ prefix is caught too",
            {"app/.env.example": "VITE_STRIPE_SECRET=\n"},
            True,
        )
    )
    results.append(
        case(
            "comments are not findings",
            {"app/.env.example": "# NEXT_PUBLIC_GMAIL_APP_PASSWORD is banned\nRESEND_API_KEY=\n"},
            False,
        )
    )

    failed = results.count(False)
    print(f"\n{len(results) - failed}/{len(results)} cases passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
