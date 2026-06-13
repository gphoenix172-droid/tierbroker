# tierbroker

**Fair job scheduling + automatic failover across many providers — with per-provider rate limits, quotas, cooldowns, and backoff.**

You bring the providers (free-tier accounts, API keys, GPU hosts, microservices). `tierbroker` decides *which one* should handle each job, spreads load fairly, respects each provider's limits, and fails over automatically when one goes down. Zero dependencies.

```python
from tierbroker import Broker, Provider

broker = Broker(max_retries=3)
broker.add(Provider("acct-1", handler_1, rate_per_sec=2, quota=100))
broker.add(Provider("acct-2", handler_2, rate_per_sec=2, quota=100))
broker.add(Provider("acct-3", handler_3, rate_per_sec=2, quota=100, weight=2))

result = broker.submit("my job")   # routed to the best available provider
print(broker.stats())              # per-provider usage
```

## Why

Lots of services give you a generous free tier — but one account's limit is small. The honest, allowed way to scale throughput is to run **your own** multiple accounts/keys and spread work across them fairly without hammering any single one. `tierbroker` is the scheduler that does exactly that:

- ⚖️ **Weighted least-recently-used** provider selection — fair spread, configurable bias
- 🚦 **Per-provider rate limits** (jobs/sec) and **quotas** (total jobs)
- 🔁 **Automatic failover** with **exponential backoff** on errors
- 📊 **Live stats** per provider
- 🧩 **Bring your own providers** — you write the `handler`, we handle scheduling
- 🪶 **Zero dependencies**, pure Python 3.8+

> **Note:** `tierbroker` ships with **no endpoints, no keys, and no vendor integrations.** It's a pure scheduler. You supply your own providers and are responsible for using each within that provider's terms of service.

## Install

```bash
pip install tierbroker
```

## API

| Class | Purpose |
|---|---|
| `Provider(name, handler, rate_per_sec=, quota=, weight=)` | One work source. `handler(job) -> result` is your code. |
| `Broker(providers=, max_retries=, backoff_base=)` | `.add(provider)`, `.submit(job)`, `.stats()` |
| `QuotaExceeded` / `NoProviderAvailable` | Raised when every provider is exhausted. |

## Tests

```bash
python tests/test_broker.py    # or: pytest
```

## Contributing

PRs welcome — keep it dependency-free. Ideas: async `submit`, persistent quota windows (per-day reset), pluggable selection strategies. Open an issue and let's scope it.

## License

MIT © WCN Development Co, LLC
## Working with us

We're [WCN Development Co, LLC](https://github.com/WCN-DEV-CO) — we build large-scale systems and open-source the useful pieces. If you're building in this space and want to **partner, integrate, hire, or collaborate**, we'd genuinely like to hear from you. Open an issue tagged `partnership`, or reach out and let's find something mutually beneficial.
---

*Built and open-sourced by [WCN Development Co, LLC](https://github.com/WCN-DEV-CO) — we build serious infrastructure and ship the useful pieces back to the community.*
