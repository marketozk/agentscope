"""
🧠 SELF-LEARNING CORE для test_agent3_air.py
Система самообучения агента регистрации в Airtable
Решение от GPT-5 Pro

Использование:
1. Импортируй: from self_learning_core import LEARN, _domain_from_url
2. Интегрируй в нужных местах согласно инструкциям GPT-5
"""
# ==================== SELF-LEARNING CORE (drop-in) ====================
import sqlite3
import random
import atexit
import os
import json
from time import perf_counter
from datetime import datetime
from urllib.parse import urlparse
from contextlib import contextmanager

class SelfLearnStore:
    def __init__(self, path="selflearn_airtable.sqlite3", epsilon_env_var="AUTOLEARN_EPS"):
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.cur = self.conn.cursor()
        self._init_schema()
        self.current_run_id = None
        self.step_counter = 0
        # Эпсилон для exploration
        try:
            self.epsilon = float(os.getenv(epsilon_env_var, "0.12"))
        except Exception:
            self.epsilon = 0.12

    def _init_schema(self):
        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT,
                phase TEXT,
                email TEXT,
                result_status TEXT,
                confirmed INTEGER,
                total_ms INTEGER,
                notes TEXT
            )
        """)
        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER,
                step INTEGER,
                action TEXT,
                domain TEXT,
                url TEXT,
                params TEXT,
                success INTEGER,
                error TEXT,
                duration_ms INTEGER,
                created_at TEXT
            )
        """)
        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS params (
                key TEXT,
                context TEXT,
                value TEXT,
                n INTEGER,
                success INTEGER,
                tot_ms INTEGER,
                last_ts TEXT,
                PRIMARY KEY (key, context, value)
            )
        """)
        self.conn.commit()

    def start_run(self, phase: str, email: str | None = None, extra: dict | None = None):
        ts = datetime.now().isoformat()
        self.cur.execute(
            "INSERT INTO runs (ts, phase, email, result_status, confirmed, total_ms, notes) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (ts, phase, email or "", "", 0, 0, json.dumps(extra or {}, ensure_ascii=False))
        )
        self.current_run_id = self.cur.lastrowid
        self.step_counter = 0
        self.conn.commit()
        return self.current_run_id

    def finish_run(self, status: str, confirmed: bool = False, notes: str = "", total_ms: int | None = None):
        if self.current_run_id is None:
            return
        self.cur.execute(
            "UPDATE runs SET result_status=?, confirmed=?, notes=?, total_ms=? WHERE id=?",
            (status or "", int(bool(confirmed)), notes or "", int(total_ms or 0), self.current_run_id)
        )
        self.conn.commit()

    def log_action(self, action: str, domain: str | None, url: str | None, params: dict | None,
                   success: bool, duration_ms: int, error: str | None = None, selector: str | None = None):
        self.step_counter += 1
        self.cur.execute(
            "INSERT INTO actions (run_id, step, action, domain, url, params, success, error, duration_ms, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                self.current_run_id, self.step_counter, action,
                (domain or ""), (url or ""),
                json.dumps(params or {}, ensure_ascii=False),
                int(bool(success)), (error or "")[:4000],
                int(duration_ms or 0), datetime.now().isoformat()
            )
        )
        if selector:
            # Отдельно учитываем «надёжность» селектора
            self.record_param_outcome("selector_ok", f"{domain}:{selector}", "used", success=int(bool(success)), duration_ms=duration_ms)
        self.conn.commit()

    def record_param_outcome(self, key: str, context: str, value, success: bool, duration_ms: int):
        self.cur.execute("""
            INSERT INTO params (key, context, value, n, success, tot_ms, last_ts)
            VALUES (?, ?, ?, 1, ?, ?, ?)
            ON CONFLICT(key, context, value) DO UPDATE SET
                n = n + 1,
                success = success + excluded.success,
                tot_ms = tot_ms + excluded.tot_ms,
                last_ts = excluded.last_ts
        """, (key, context or "", str(value), int(bool(success)), int(duration_ms or 0), datetime.now().isoformat()))
        self.conn.commit()

    def _stats_for(self, key: str, context: str):
        self.cur.execute("SELECT value, n, success, tot_ms FROM params WHERE key=? AND context=?", (key, context or ""))
        rows = self.cur.fetchall()
        stats = {}
        for v, n, s, tot in rows:
            stats[v] = {"n": n, "success": s, "tot_ms": tot, "avg_ms": (tot / (n or 1))}
        return stats

    def choose_option(self, key: str, context: str, options: list, default=None, minimize_time_weight: float = 0.25):
        # epsilon-greedy по reward = success_rate - w * normalized_time
        options = list(options)
        stats = self._stats_for(key, context)
        unexplored = [o for o in options if str(o) not in stats]

        if unexplored:
            choice = random.choice(unexplored)
        else:
            if random.random() < self.epsilon:
                choice = random.choice(options)
            else:
                best = None
                best_score = -1e9
                for o in options:
                    s = stats.get(str(o), {"n": 0, "success": 0, "avg_ms": 2000})
                    n = s["n"]; succ = s["success"]; avg_ms = s["avg_ms"]
                    succ_rate = (succ / n) if n > 0 else 0.5
                    time_penalty = minimize_time_weight * (avg_ms / 5000.0)
                    score = succ_rate - time_penalty
                    if score > best_score:
                        best_score = score
                        best = o
                choice = best if best is not None else (default if default in options else options[0])
        return choice

    def choose_numeric(self, key: str, context: str, candidates: list[int | float], default=None):
        val = self.choose_option(key, context, candidates, default=default)
        try:
            return int(val)
        except Exception:
            return float(val)

    def rank_methods(self, key: str, context: str, default_order: list[str]):
        # Сортировка методов по успешности и скорости
        stats = self._stats_for(key, context)
        def score(m):
            s = stats.get(m, {"n": 0, "success": 0, "avg_ms": 2500})
            n = s["n"]; succ = s["success"]; avg = s["avg_ms"]
            succ_rate = (succ / n) if n > 0 else 0.5
            return succ_rate - 0.2 * (avg / 5000.0)
        known = [m for m in default_order if m in stats]
        unknown = [m for m in default_order if m not in stats]
        ordered = sorted(known, key=lambda m: score(m), reverse=True) + unknown
        # Небольшая эксплорация: иногда меняем местами топ-2
        if len(ordered) >= 2 and random.random() < 0.1:
            ordered[0], ordered[1] = ordered[1], ordered[0]
        return ordered

def _domain_from_url(url: str | None) -> str:
    try:
        if not url:
            return ""
        return (urlparse(url).hostname or "").lower()
    except Exception:
        return ""

LEARN = SelfLearnStore("selflearn_airtable.sqlite3")
atexit.register(lambda: getattr(LEARN, "conn", None) and LEARN.conn.close())
# ======================================================================
