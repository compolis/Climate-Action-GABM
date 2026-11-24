# Sample Output Snapshots

This folder contains curated sample artefacts from two completed smoke runs.
It is intended to help new users quickly inspect what successful outputs look
like without running the full pipeline first.

## Included snapshots

- [smoke_openai_20261117/](./smoke_openai_20261117/)
  - Hosted run: `--preset smoke --provider openai --model gpt-4o-mini`
  - Approx. runtime: ~10.6 minutes wall-clock on the recorded environment.
- [smoke_ollama_20261118/](./smoke_ollama_20261118/)
  - Local run: `--preset smoke --provider local --model qwen3:8b --base-url http://127.0.0.1:11434/v1`
  - Approx. runtime: ~19.5 hours wall-clock on the recorded environment.

## Files included per snapshot

- `config.json`
- `opinion_trajectories.csv`
- `package_index_trajectories.csv`
- `network_diagnostics.json`
- `opinion_trajectories.png`

## Notes

- These are examples for orientation and troubleshooting.
- Runtime and output values vary by provider, model, hardware, and rate limits.
- For complete output schema details, see
  [Run_Output_Guide.md](../../guides/Run_Output_Guide.md).
