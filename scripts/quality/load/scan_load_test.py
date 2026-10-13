"""Prueba de carga del endpoint de escaneo (RNF-REN-001 y RNF-REN-002).

Mide por HTTP real la latencia de ``POST /api/v1/attendance/scan/`` con N
operadores concurrentes, cada uno con su sesion. Solo biblioteca estandar.

    python scripts/quality/load/scan_load_test.py \
        --base-url http://localhost:8000 --seed /tmp/scan-load-seed.json \
        --operators 3 --requests-per-operator 50 --out /tmp/scan-load-result.json

Protocolo del plan (tests_plan.md 10.6): ``--rounds 3 --warmup N`` y al menos 100
confirmaciones medidas por ronda (``--operators x --requests-per-operator``).

El resultado es evidencia del entorno donde se corre, NO una certificacion: el
informe debe declarar host, perfil de recursos y servidor de aplicacion.
Los datos vienen de ``seed_scan_load.py`` (sinteticos).
"""

from __future__ import annotations

import argparse
import json
import math
import platform
import sys
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from http.cookiejar import CookieJar

P95_LIMIT_SECONDS = 2.0  # RNF-REN-001
MIN_MEASURED_PER_ROUND = 100  # protocolo de tests_plan.md 10.6


def percentile(sorted_values: list[float], pct: float) -> float:
    """Percentil por rango mas cercano (nearest-rank). Lista ya ordenada."""
    if not sorted_values:
        raise ValueError("sin muestras")
    rank = max(1, math.ceil(pct / 100 * len(sorted_values)))
    return sorted_values[rank - 1]


def is_created(sample: dict) -> bool:
    return sample["status"] == 200 and sample["outcome"] == "created"


def summarize(samples: list[dict], wall_seconds: float, operators: int) -> dict:
    """Resume muestras ``{"seconds", "status", "outcome"}`` en el reporte."""
    ok = [s for s in samples if is_created(s)]
    durations = sorted(s["seconds"] for s in ok)
    failures: dict[str, int] = {}
    for s in samples:
        if s not in ok:
            key = f"{s['status']}:{s['outcome']}"
            failures[key] = failures.get(key, 0) + 1
    summary = {
        "operators": operators,
        "requests": len(samples),
        "created": len(ok),
        "failures": failures,
        "success_rate_percent": round(100 * len(ok) / len(samples), 2) if samples else 0.0,
        "network_errors": sum(1 for s in samples if s["status"] == 0),
        "wall_seconds": round(wall_seconds, 3),
        "throughput_per_second": round(len(samples) / wall_seconds, 2) if wall_seconds else 0,
    }
    if durations:
        summary["latency_seconds"] = {
            "min": round(durations[0], 4),
            "p50": round(percentile(durations, 50), 4),
            "p95": round(percentile(durations, 95), 4),
            "p99": round(percentile(durations, 99), 4),
            "max": round(durations[-1], 4),
        }
        summary["p95_within_limit"] = percentile(durations, 95) <= P95_LIMIT_SECONDS
    else:
        summary["p95_within_limit"] = False
    summary["lost_or_failed_events"] = len(samples) - len(ok)
    return summary


def code_offset(
    round_index: int,
    operator_index: int,
    operators: int,
    per_operator: int,
    warmup: int,
) -> int:
    """Primer codigo de estudiante de un operador en una ronda (sin solapes)."""
    block = per_operator + warmup
    return (round_index * operators + operator_index) * block


def summarize_rounds(rounds: list[dict]) -> dict:
    """Consolida rondas independientes; cada ronda debe cumplir el limite."""
    pooled_requests = sum(r["requests"] for r in rounds)
    pooled_created = sum(r["created"] for r in rounds)
    smallest = min(r["requests"] for r in rounds)
    return {
        "rounds": rounds,
        "requests": pooled_requests,
        "created": pooled_created,
        "lost_or_failed_events": sum(r["lost_or_failed_events"] for r in rounds),
        "measured_per_round_min": smallest,
        "meets_min_sample": smallest >= MIN_MEASURED_PER_ROUND,
        "p95_within_limit": all(r["p95_within_limit"] for r in rounds),
    }


class Operator:
    """Cliente HTTP con sesion propia (cookies + CSRF)."""

    def __init__(self, base_url: str, username: str, password: str):
        self.base = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.jar = CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))

    def _csrf(self) -> str:
        return next((c.value for c in self.jar if c.name == "csrftoken"), "")

    def _request(self, method: str, path: str, body: dict | None = None):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.base + path, data=data, method=method)
        req.add_header("Content-Type", "application/json")
        req.add_header("Referer", self.base + "/")
        if method != "GET":
            req.add_header("X-CSRFToken", self._csrf())
        try:
            with self.opener.open(req, timeout=30) as resp:
                raw = resp.read()
                return resp.status, json.loads(raw) if raw else None
        except urllib.error.HTTPError as exc:
            raw = exc.read()
            try:
                return exc.code, json.loads(raw) if raw else None
            except ValueError:
                return exc.code, None

    def login(self) -> None:
        self._request("GET", "/api/v1/auth/login/")
        status, _ = self._request(
            "POST",
            "/api/v1/auth/login/",
            {"username": self.username, "password": self.password},
        )
        if status != 200:
            raise RuntimeError(f"login fallido para {self.username}: HTTP {status}")

    def scan(self, item: dict) -> tuple[int, str]:
        status, payload = self._request(
            "POST", "/api/v1/attendance/scan/", {"batch_id": "", "items": [item]}
        )
        outcome = ""
        if status == 200 and isinstance(payload, list) and payload:
            outcome = payload[0].get("outcome", "")
        return status, outcome


def run_round(
    clients: list[Operator],
    seed: dict,
    round_index: int,
    per_operator: int,
    warmup: int,
    think: float,
) -> dict:
    operators = len(clients)
    codes = seed["student_codes"]
    samples: list[dict] = []
    warmup_samples: list[dict] = []
    lock = threading.Lock()
    barrier = threading.Barrier(operators)
    # Todos terminan el calentamiento antes de medir: la ventana de throughput
    # empieza con el primer escaneo medido, no con el primero de calentamiento.
    measured_started: list[float] = []
    measure_barrier = threading.Barrier(
        operators, action=lambda: measured_started.append(time.perf_counter())
    )

    def worker(index: int) -> None:
        client = clients[index]
        base = code_offset(round_index, index, operators, per_operator, warmup)
        barrier.wait()
        for n in range(warmup + per_operator):
            if n == warmup:
                measure_barrier.wait()
            item = {
                "client_event_id": f"load-{int(time.time() * 1000)}-{round_index}-{index}-{n}",
                "student_code": codes[base + n],
                "shift_id": seed["shift_id"],
                "control_point_id": seed["control_point_id"],
                "movement_type": "entry",
                "captured_at": datetime.now(timezone.utc).isoformat(),
            }
            started = time.perf_counter()
            try:
                status, outcome = client.scan(item)
            except Exception as exc:  # error de red = evento perdido, no se oculta
                status, outcome = 0, type(exc).__name__
            elapsed = time.perf_counter() - started
            sample = {"seconds": elapsed, "status": status, "outcome": outcome}
            with lock:  # el calentamiento no entra en los percentiles
                (samples if n >= warmup else warmup_samples).append(sample)
            if think:
                time.sleep(think)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(operators)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    summary = summarize(samples, time.perf_counter() - measured_started[0], operators)
    return add_warmup_failures(summary, warmup_samples)


def add_warmup_failures(summary: dict, warmup_samples: list[dict]) -> dict:
    """Un evento perdido durante el calentamiento sigue siendo un evento perdido."""
    lost = sum(1 for s in warmup_samples if not is_created(s))
    summary["warmup_requests"] = len(warmup_samples)
    summary["warmup_lost_or_failed"] = lost
    summary["warmup_network_errors"] = sum(1 for s in warmup_samples if s["status"] == 0)
    summary["lost_or_failed_events"] += lost
    return summary


def run(
    base_url: str,
    seed: dict,
    operators: int,
    per_operator: int,
    think: float,
    rounds: int = 1,
    warmup: int = 0,
) -> dict:
    needed = rounds * operators * (per_operator + warmup)
    if operators > len(seed["operators"]) or needed > len(seed["student_codes"]):
        raise SystemExit(
            f"la siembra no alcanza: {len(seed['operators'])} operadores / "
            f"{len(seed['student_codes'])} estudiantes; se piden {operators} / {needed}"
        )

    clients = [Operator(base_url, u, seed["password"]) for u in seed["operators"][:operators]]
    for client in clients:  # el login no entra en la medicion
        client.login()

    results = [run_round(clients, seed, r, per_operator, warmup, think) for r in range(rounds)]
    report = summarize_rounds(results)
    report["operators"] = operators
    report["meta"] = {
        "base_url": base_url,
        "host": platform.platform(),
        "python": platform.python_version(),
        "think_seconds": think,
        "rounds": rounds,
        "warmup_requests_per_operator": warmup,
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "note": "evidencia del entorno medido; declarar perfil de recursos y servidor de aplicacion",
    }
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--seed", required=True, help="JSON de seed_scan_load.py")
    parser.add_argument("--operators", type=int, default=3)
    parser.add_argument("--requests-per-operator", type=int, default=50)
    parser.add_argument("--rounds", type=int, default=1, help="rondas independientes (plan: 3)")
    parser.add_argument(
        "--warmup",
        type=int,
        default=0,
        help="escaneos por operador excluidos de los percentiles",
    )
    parser.add_argument("--think", type=float, default=0.0, help="pausa entre escaneos (s)")
    parser.add_argument("--out", help="ruta del JSON de resultados")
    args = parser.parse_args(argv)
    for name in ("operators", "requests_per_operator", "rounds"):
        if getattr(args, name) < 1:
            parser.error(f"--{name.replace('_', '-')} debe ser >= 1")
    if args.warmup < 0 or args.think < 0:
        parser.error("--warmup y --think no pueden ser negativos")

    with open(args.seed, encoding="utf-8") as fh:
        seed = json.load(fh)
    report = run(
        args.base_url,
        seed,
        args.operators,
        args.requests_per_operator,
        args.think,
        args.rounds,
        args.warmup,
    )
    text = json.dumps(report, indent=2, ensure_ascii=False)
    print(text)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
    # RNF-REN-001/002: p95 <= 2 s en cada ronda y ningun evento perdido o fallido.
    # La muestra minima (meets_min_sample) se reporta, pero no cambia el exit code.
    return 0 if report["p95_within_limit"] and report["lost_or_failed_events"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
