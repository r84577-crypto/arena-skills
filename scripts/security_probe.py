#!/usr/bin/env python3
"""Penetration-style checks against a *running* instance of the app.

Every assertion here is one a real attacker would make: strip a header, forge
a token, cross an origin, overflow a body, ask a route to reveal its config.

Why a live suite and not unit tests: header order, proxy behaviour and route
short-circuits cannot be proven by importing a function. The bug found on
2026-11-13 — the provider check answering *before* the session check — only
appeared over HTTP, and it leaked configuration state to anonymous callers.

Usage:
    # start the app first: npm run build && npx next start -p 3111
    python3 scripts/security_probe.py --base http://127.0.0.1:3111
    python3 scripts/security_probe.py --base URL --json report.json

Exit codes: 0 all checks passed, 1 at least one check failed.

Note on `--forwarded-proto`: the suite sends `x-forwarded-proto: https`
because that is what the platform sends after TLS termination. Without it the
app answers 308 and every check would measure the redirect, not the headers.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field

TIMEOUT = 10


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Never follow a redirect.

    The HTTPS check *is* the redirect: following it would chase the app to
    https://127.0.0.1:3111, where the TLS handshake fails and every later
    assertion measures the wrong thing.
    """

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D102
        return None


OPENER = urllib.request.build_opener(_NoRedirect)


@dataclass
class Result:
    check: str
    expected: str
    actual: str
    passed: bool
    item: str = ""


@dataclass
class Suite:
    base: str
    results: list[Result] = field(default_factory=list)

    def ip(self, section: str) -> str:
        """A distinct synthetic client IP per section, per run.

        The limiter lives in server memory, so re-running the suite from one
        address would exhaust its window and make the *second* run report
        failures where the protection is working exactly as designed. Each
        section gets its own address, which is also what real traffic looks
        like: separate clients, separate buckets.
        """
        octets = {"auth": 11, "csrf": 12, "body": 13, "headers": 14, "files": 15}
        return f"198.18.{octets.get(section, 99)}.{int(time.time()) % 250 + 1}"

    def record(self, item: str, check: str, expected: str, actual: str, passed: bool) -> None:
        self.results.append(Result(check, expected, actual, passed, item))

    def get(self, path: str, headers: dict[str, str] | None = None) -> tuple[int, dict[str, str], str]:
        return self.request("GET", path, headers=headers)

    def request(
        self,
        method: str,
        path: str,
        headers: dict[str, str] | None = None,
        body: bytes | None = None,
    ) -> tuple[int, dict[str, str], str]:
        h = {"x-forwarded-proto": "https", "user-agent": "security-probe/1"}
        if headers:
            h.update(headers)
        req = urllib.request.Request(self.base + path, data=body, method=method, headers=h)
        try:
            with OPENER.open(req, timeout=TIMEOUT) as r:
                return r.status, {k.lower(): v for k, v in r.headers.items()}, r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            return e.code, {k.lower(): v for k, v in e.headers.items()}, e.read().decode("utf-8", "replace")
        except urllib.error.URLError as e:
            print(f"cannot reach {self.base}{path}: {e.reason}", file=sys.stderr)
            raise SystemExit(2)


def reason_of(body: str) -> str:
    """The human-readable reason from a JSON error body.

    The app answers with escaped unicode (\u0637...), so a naive substring
    match against Arabic text silently fails and turns a working refusal into
    a false negative. Decode first, then read `reason`.
    """
    try:
        data = json.loads(body)
    except (ValueError, TypeError):
        return body
    if isinstance(data, dict):
        return str(data.get("reason", ""))
    return body


def check_https(s: Suite) -> None:
    """4. HTTPS enforced: a plain-http request never serves content."""
    status, headers, body = s.request(
        "GET", "/", headers={"x-forwarded-proto": "http"}
    )
    location = headers.get("location", "")
    s.record(
        "4",
        "plain HTTP is redirected",
        "308 + https location",
        f"{status} {location}",
        status in (301, 308) and location.startswith("https://"),
    )
    s.record(
        "4",
        "HSTS present with preload",
        "max-age>=31536000; includeSubDomains; preload",
        headers.get("strict-transport-security", "absent"),
        _hsts_ok(headers.get("strict-transport-security", "")),
    )


def _hsts_ok(value: str) -> bool:
    m = re.search(r"max-age=(\d+)", value)
    return bool(
        m
        and int(m.group(1)) >= 31536000
        and "includesubdomains" in value.lower()
        and "preload" in value.lower()
    )


def check_headers(s: Suite) -> None:
    """14. Security headers: present, and the CSP is a real one."""
    status, headers, body = s.get("/")
    csp = headers.get("content-security-policy", "")

    s.record("14", "CSP present", "policy", csp[:60] or "absent", bool(csp))
    s.record(
        "14",
        "script-src has NO unsafe-inline",
        "no unsafe-inline",
        "unsafe-inline" in csp.split("script-src")[1].split(";")[0] if "script-src" in csp else "no script-src",
        "script-src" in csp and "unsafe-inline" not in csp.split("script-src")[1].split(";")[0],
    )
    s.record(
        "14",
        "script-src has NO unsafe-eval",
        "no unsafe-eval",
        "present" if "unsafe-eval" in csp else "absent",
        "unsafe-eval" not in csp,
    )
    s.record("14", "frame-ancestors 'none'", "'none'", "ok" if "frame-ancestors 'none'" in csp else "missing",
             "frame-ancestors 'none'" in csp)
    s.record("14", "object-src 'none'", "'none'", "ok" if "object-src 'none'" in csp else "missing",
             "object-src 'none'" in csp)
    s.record("14", "base-uri 'self'", "'self'", "ok" if "base-uri 'self'" in csp else "missing",
             "base-uri 'self'" in csp)
    s.record("14", "form-action 'self'", "'self'", "ok" if "form-action 'self'" in csp else "missing",
             "form-action 'self'" in csp)
    s.record("14", "no wildcard in connect-src", "no *", "ok" if "connect-src *" not in csp else "wildcard",
             "connect-src *" not in csp)
    s.record("14", "X-Frame-Options DENY", "DENY", headers.get("x-frame-options", "absent"),
             headers.get("x-frame-options", "").upper() == "DENY")
    s.record("14", "X-Content-Type-Options nosniff", "nosniff",
             headers.get("x-content-type-options", "absent"),
             headers.get("x-content-type-options", "").lower() == "nosniff")
    s.record("14", "Referrer-Policy set", "policy", headers.get("referrer-policy", "absent"),
             bool(headers.get("referrer-policy")))
    s.record("14", "Permissions-Policy set", "policy", headers.get("permissions-policy", "absent")[:40],
             bool(headers.get("permissions-policy")))
    s.record("14", "X-Powered-By removed", "absent", headers.get("x-powered-by", "absent"),
             "x-powered-by" not in headers)

    # The nonce must differ between requests, or it is a constant, not a nonce.
    _, _, body1 = s.get("/")
    nonce1 = re.search(r'nonce="([a-f0-9]+)"', body1)
    _, _, body2 = s.get("/")
    nonce2 = re.search(r'nonce="([a-f0-9]+)"', body2)
    s.record(
        "14",
        "nonce rotates per request",
        "two different nonces",
        f"{bool(nonce1)}/{bool(nonce2)}",
        bool(nonce1 and nonce2 and nonce1.group(1) != nonce2.group(1)),
    )
    # Every script tag must carry the nonce (a bare <script src> is blocked by
    # strict-dynamic and would break the page silently).
    total = len(re.findall(r"<script\b", body1))
    nonced = len(re.findall(r'<script\b[^>]*\bnonce="[a-f0-9]+"', body1))
    s.record("14", "every script tag nonce-tagged", f"{total} tags all nonced", f"{nonced}/{total}",
             total > 0 and nonced == total)


def check_csrf(s: Suite) -> None:
    """16. CSRF: foreign origins are refused before anything else happens."""
    payload = json.dumps({"id": 1, "to": "a@b.co", "subject": "s", "body": "b", "scope": "PERSONAL"}).encode()

    for origin, label in [
        ("https://evil.example", "foreign origin"),
        ("https://evil.example:8443", "foreign origin + port"),
        ("https://localhost.evil.tld", "lookalike origin"),
        ("null", "opaque origin (sandboxed iframe)"),
    ]:
        for route in ("/api/send-email", "/api/send-whatsapp"):
            status, _, body = s.request(
                "POST",
                route,
                {"origin": origin, "content-type": "application/json",
                 "x-nf-client-connection-ip": s.ip("csrf")},
                payload,
            )
            reason = reason_of(body)
            s.record(
                "16", f"{label} rejected on {route}", "403 + origin refusal", f"{status} «{reason}»",
                status == 403 and "أصل غير مسموح" in reason,
            )

    # A legitimate same-origin request must get PAST the origin gate and fail
    # on authentication instead — otherwise CSRF protection is simply "deny all"
    # and the app is broken, not safe.
    for route in ("/api/send-email", "/api/send-whatsapp"):
        status, _, body = s.request(
            "POST",
            route,
            {"origin": s.base, "content-type": "application/json",
             "x-nf-client-connection-ip": s.ip("csrf")},
            payload,
        )
        s.record(
            "16", f"same-origin passes the gate on {route}", "fails on auth, not origin",
            f"{status} «{reason_of(body)}»",
            status in (401, 403, 503) and "أصل غير مسموح" not in reason_of(body),
        )

    # No Origin and no Authorization: not a browser request we can attribute.
    status, _, body = s.request(
        "POST", "/api/send-email",
        {"content-type": "application/json", "x-nf-client-connection-ip": s.ip("csrf")},
        payload,
    )
    s.record("16", "no Origin + no token rejected", "403", f"{status}", status == 403)


def check_auth(s: Suite) -> None:
    """1 + 9. Authentication and owner-only authorisation on the API."""
    payload = json.dumps({"id": 1, "to": "a@b.co", "subject": "s", "body": "b", "scope": "PERSONAL"}).encode()
    same_origin = {
        "origin": s.base,
        "content-type": "application/json",
        "x-nf-client-connection-ip": s.ip("auth"),
    }

    forged = (
        "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0."
        "eyJzdWIiOiIwMDAwMDAwMC0wMDAwLTAwMDAtMDAwMC0wMDAwMDAwMDAwMDAiLCJyb2xlIjoiYXV0aGVudGljYXRlZCJ9."
    )
    for i, route in enumerate(("/api/send-email", "/api/send-whatsapp")):
        status, _, body = s.request(
            "POST",
            route,
            {**same_origin, "authorization": f"Bearer {forged}", "x-nf-client-connection-ip": s.ip("auth")},
            payload,
        )
        # A forged token must be refused at the session layer, never reach a provider.
        s.record(
            "1",
            f"forged alg:none JWT refused on {route}",
            "401/403/503 auth failure",
            f"{status} «{reason_of(body)}»",
            status in (401, 403, 503) and "sent" not in body,
        )

    # No token at all: 401, and specifically not a provider complaint.
    status, _, body = s.request("POST", "/api/send-email", same_origin, payload)
    s.record("1", "unauthenticated request refused", "401", f"{status}", status == 401)
    all_bodies = " ".join([body, _anon_probe(s)])
    s.record(
        "2",
        "config state not leaked to anonymous callers",
        "no provider/config detail",
        "leaked" if any(k in all_bodies for k in ("RESEND", "WHATSAPP", "مهيّأ", "configured")) else "clean",
        not any(k in all_bodies for k in ("RESEND", "WHATSAPP", "مهيّأ", "configured")),
    )


def _anon_probe(s: Suite) -> str:
    """Bodies an anonymous caller can obtain from the guarded routes."""
    payload = json.dumps({"id": 1, "to": "a@b.co", "subject": "s", "body": "b", "scope": "PERSONAL"}).encode()
    out = []
    for route in ("/api/send-email", "/api/send-whatsapp"):
        _, _, body = s.request(
            "POST", route,
            {"origin": s.base, "content-type": "application/json",
             "x-nf-client-connection-ip": s.ip("auth")},
            payload,
        )
        out.append(body)
    return " ".join(out)


def check_rate_limit(s: Suite) -> None:
    """12. Rate limiting: the endpoint answers 429 and says when to retry."""
    payload = json.dumps({"id": 1, "to": "a@b.co", "subject": "s", "body": "b", "scope": "PERSONAL"}).encode()
    # A fresh client IP per run: the limiter lives in process memory, so a
    # fixed address would carry a spent window from the previous run and the
    # second run would "fail" while the protection works exactly as designed.
    ip = f"203.0.113.{int(time.time()) % 250 + 1}"
    headers = {
        "origin": s.base,
        "content-type": "application/json",
        "x-nf-client-connection-ip": ip,
        "authorization": "Bearer probe-forced-401",
    }
    statuses = []
    retry_after = None
    for _ in range(14):
        status, h, _ = s.request("POST", "/api/send-email", headers, payload)
        statuses.append(status)
        if status == 429:
            retry_after = h.get("retry-after")
    s.record("12", f"burst from one IP is throttled (ip {ip})", "429 within 14 requests",
             f"statuses={compressed(statuses)}", 429 in statuses)
    s.record("12", "429 carries Retry-After", "integer seconds", retry_after or "absent",
             bool(retry_after and retry_after.isdigit()))


def compressed(seq: list[int]) -> str:
    out: list[str] = []
    for v in seq:
        if out and out[-1].startswith(str(v) + "x"):
            n = int(out[-1].split("x")[1]) + 1
            out[-1] = f"{v}x{n}"
        elif out and out[-1] == str(v):
            out[-1] = f"{v}x2"
        else:
            out.append(str(v))
    return ",".join(out)


def check_body_limits(s: Suite) -> None:
    """6 + 18. Input limits on the body reader itself (unit-level).

    This runs the real function from src/lib/security.ts through Node, not a
    re-implementation: the point is to prove the *implementation* truncates,
    and a Python copy would only prove the copy. Over HTTP the same request
    stops at 401 first, which is correct ordering but hides the limit.
    """
    import shutil
    import subprocess

    node = shutil.which("node")
    if not node:
        s.record("6", "body limit checks", "node available", "node not found", False)
        return

    script = r"""
import { readJsonBody, MAX_API_BODY_BYTES } from "./src/lib/validation.ts";
const cases = [
  ["40KB body",             new Request("http://x/", { method: "POST", body: JSON.stringify({ body: "A".repeat(40000) }) }), 413],
  ["malformed JSON",        new Request("http://x/", { method: "POST", body: '{"id": ' }), 400],
  ["array body",            new Request("http://x/", { method: "POST", body: "[1,2,3]" }), 400],
  ["empty body",            new Request("http://x/", { method: "POST", body: "" }), 400],
  ["valid small body",      new Request("http://x/", { method: "POST", body: JSON.stringify({ id: 1 }) }), null],
];
const out = [];
for (const [name, req, want] of cases) {
  const r = await readJsonBody(req);
  out.push({ name, want, got: r.ok ? "ok" : r.status, pass: want === null ? r.ok : (!r.ok && r.status === want) });
}
console.log(JSON.stringify({ max: MAX_API_BODY_BYTES, out }));
"""
    proc = subprocess.run(
        [node, "--experimental-strip-types", "--no-warnings", "-e", script],
        cwd=str(__import__("pathlib").Path(__file__).resolve().parent.parent / "app"),
        capture_output=True, text=True, timeout=120,
    )
    if proc.returncode != 0:
        s.record("6", "body limit checks ran", "node exits 0", proc.stderr.strip()[:200], False)
        return
    data = json.loads(proc.stdout.strip().splitlines()[-1])
    for case in data["out"]:
        s.record("6", f"{case['name']} handling", str(case["want"]), str(case["got"]), case["pass"])
    s.record("6", "body ceiling is explicit", "<= 64KB", f"{data['max']} bytes", data["max"] <= 65536)


def check_exposed_files(s: Suite) -> None:
    """23 + 20. No sensitive file is served, and errors reveal nothing."""
    for path in (
        "/.env",
        "/.env.local",
        "/.env.production",
        "/.git/config",
        "/.git/HEAD",
        "/app/.env",
        "/package.json",
        "/next.config.ts",
        "/.next/server/app/page.js",
    ):
        status, headers, body = s.get(path)
        leaked = status == 200 and not body.lstrip().startswith("<!DOCTYPE")
        s.record("23", f"{path} not served", "404/redirect, never 200 content", f"{status}", not leaked)

    # Debug-mode: an unknown API route must not answer with a stack trace.
    status, _, body = s.get("/api/does-not-exist")
    s.record(
        "20",
        "unknown API route has no stack trace",
        "no trace/paths",
        f"{status}",
        status in (404, 400, 405) and "at " not in body and "/home/" not in body and "node_modules" not in body,
    )

    # Health must not enumerate configuration.
    status, headers, body = s.get("/api/health")
    s.record("2", "health leaks no config state", "status only", body.strip()[:60],
             status == 200 and "configured" not in body and "commit" not in body)
    s.record("20", "health is not cacheable", "no-store", headers.get("cache-control", "absent"),
             "no-store" in headers.get("cache-control", ""))


def check_methods(s: Suite) -> None:
    """5 + misc. The routes accept one verb; anything else is a 405."""
    for method in ("PUT", "DELETE", "PATCH"):
        status, _, _ = s.request(method, "/api/send-email", {"content-type": "application/json"}, b"{}")
        s.record("9", f"{method} on send route refused", "405", f"{status}", status == 405)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", default="http://127.0.0.1:3111", help="base URL of the running app")
    ap.add_argument("--json", help="write machine-readable results here")
    args = ap.parse_args()

    s = Suite(base=args.base.rstrip("/"))
    for fn in (
        check_https,
        check_headers,
        check_csrf,
        check_auth,
        check_rate_limit,
        check_body_limits,
        check_exposed_files,
        check_methods,
    ):
        fn(s)

    failed = [r for r in s.results if not r.passed]
    by_item: dict[str, list[Result]] = {}
    for r in s.results:
        by_item.setdefault(r.item, []).append(r)

    print(f"\n{'='*78}\nSecurity probe — {s.base}\n{'='*78}")
    for item in sorted(by_item, key=lambda x: (len(x), x)):
        rows = by_item[item]
        bad = [r for r in rows if not r.passed]
        print(f"\n[{item}] {'FAIL ' + str(len(bad)) if bad else 'PASS'} ({len(rows)} checks)")
        for r in rows:
            mark = "  ok  " if r.passed else "  FAIL"
            print(f"{mark} {r.check}")
            if not r.passed:
                print(f"        expected: {r.expected}\n        actual:   {r.actual}")

    print(f"\n{'-'*78}\n{len(s.results) - len(failed)}/{len(s.results)} checks passed"
          f"{'' if not failed else ' — ' + str(len(failed)) + ' FAILED'}\n")

    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(
                {
                    "base": s.base,
                    "total": len(s.results),
                    "failed": len(failed),
                    "results": [r.__dict__ for r in s.results],
                },
                fh,
                ensure_ascii=False,
                indent=2,
            )
        print(f"wrote {args.json}")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
