"""
tierbroker.broker — fair scheduling + failover across many providers.

Core idea: you have N providers (free-tier accounts, services, GPU hosts,
API keys) each with their own rate limit and quota. tierbroker picks the
best available provider for each job using weighted least-recently-used
selection, tracks usage, enforces per-provider rate limits and quotas,
applies exponential backoff on failure, and fails over automatically.

No network code, no vendor lock-in, no hidden endpoints. You pass a
callable that does the actual work for each provider.
"""
from __future__ import annotations

import time
import threading
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Any


class QuotaExceeded(Exception):
    """Raised when a provider has exhausted its configured quota."""


class NoProviderAvailable(Exception):
    """Raised when no provider can accept a job right now (all rate-limited/cooling/exhausted)."""


@dataclass
class Provider:
    """
    A single work provider.

    name:        identifier for logging/metrics.
    handler:     callable(job) -> result. You implement the actual call.
    rate_per_sec: max jobs/second this provider accepts (0 = unlimited).
    quota:       total jobs allowed before exhausted (None = unlimited).
    weight:      relative share of traffic (higher = picked more often).
    """
    name: str
    handler: Callable[[Any], Any]
    rate_per_sec: float = 0.0
    quota: Optional[int] = None
    weight: float = 1.0

    # runtime state
    used: int = 0
    _last_call: float = 0.0
    _cooldown_until: float = 0.0
    failures: int = 0

    def available(self, now: float) -> bool:
        if self.quota is not None and self.used >= self.quota:
            return False
        if now < self._cooldown_until:
            return False
        if self.rate_per_sec > 0:
            min_gap = 1.0 / self.rate_per_sec
            if now - self._last_call < min_gap:
                return False
        return True

    def score(self, now: float) -> float:
        # weighted least-recently-used: prefer high weight + idle longest
        idle = now - self._last_call
        return self.weight * (idle + 0.001)


class Broker:
    """Schedules jobs across providers with failover + backoff."""

    def __init__(self, providers: Optional[List[Provider]] = None,
                 max_retries: int = 3, backoff_base: float = 0.5) -> None:
        self._providers: List[Provider] = providers or []
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self._lock = threading.Lock()

    def add(self, provider: Provider) -> "Broker":
        self._providers.append(provider)
        return self

    def _pick(self, now: float) -> Optional[Provider]:
        candidates = [p for p in self._providers if p.available(now)]
        if not candidates:
            return None
        return max(candidates, key=lambda p: p.score(now))

    def submit(self, job: Any) -> Any:
        """
        Run one job on the best available provider, with failover + backoff.
        Returns the handler's result. Raises NoProviderAvailable if every
        provider is exhausted, or the last error after max_retries.
        """
        last_err: Optional[Exception] = None
        for attempt in range(self.max_retries):
            with self._lock:
                now = time.monotonic()
                provider = self._pick(now)
                if provider is None:
                    # nobody free right now — wait for the soonest one
                    soonest = self._soonest_available(now)
                    if soonest is None:
                        raise NoProviderAvailable(
                            "all providers exhausted (quota reached)")
                    wait = max(0.0, soonest - now)
                else:
                    provider._last_call = now
                    provider.used += 1
                    wait = 0.0

            if provider is None:
                time.sleep(wait)
                continue

            try:
                result = provider.handler(job)
                provider.failures = 0
                return result
            except Exception as e:  # provider failed — back off + failover
                last_err = e
                provider.failures += 1
                backoff = self.backoff_base * (2 ** provider.failures)
                provider._cooldown_until = time.monotonic() + backoff

        if last_err:
            raise last_err
        raise NoProviderAvailable("no provider could complete the job")

    def _soonest_available(self, now: float) -> Optional[float]:
        times = []
        for p in self._providers:
            if p.quota is not None and p.used >= p.quota:
                continue
            t = p._cooldown_until
            if p.rate_per_sec > 0:
                t = max(t, p._last_call + 1.0 / p.rate_per_sec)
            times.append(t)
        return min(times) if times else None

    def stats(self) -> Dict[str, Dict[str, Any]]:
        """Per-provider usage snapshot."""
        return {
            p.name: {
                "used": p.used,
                "quota": p.quota,
                "failures": p.failures,
                "exhausted": p.quota is not None and p.used >= p.quota,
            }
            for p in self._providers
        }
