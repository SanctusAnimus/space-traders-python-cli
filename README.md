# Space Traders Python CLI
WIP cli to play [Space Traders](https://spacetraders.io/).
Works as interactive shell, via background treads to send requests (both prompted and automated from strategies)

- v2 API is generated via `openapi-python-client`.
- Threading is handled manually via Locks and Queues.
- Time-based events are handled via `APScheduler`.
- Terminal output formatting is handled with `rich`
- (Mostly) typed

Heavy WIP, code quality is below average.