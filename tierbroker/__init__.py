"""
tierbroker — round-robin / weighted job broker across multiple providers
with per-provider rate limits, quotas, cooldowns, and automatic failover.

Bring your own providers (you supply the endpoints + keys). tierbroker
handles fair scheduling, backoff, quota tracking, and failover so you can
spread a workload across many accounts/services without hammering any one.

Open-sourced by WCN Development Co, LLC. MIT licensed.
https://github.com/gphoenix172-droid/tierbroker
"""
from .broker import Broker, Provider, QuotaExceeded, NoProviderAvailable

__version__ = "0.1.0"
__all__ = ["Broker", "Provider", "QuotaExceeded", "NoProviderAvailable"]
