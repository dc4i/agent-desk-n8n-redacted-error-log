# Agent Desk: redacted error log for n8n (free)

A free n8n Error workflow. When another workflow fails and points its Error workflow setting here, this one redacts common secret and PII patterns, truncates the text, and writes a short internal log (Notion and/or email).

Redaction is a safety net, not a guarantee. It covers common token and PII patterns. Review the output before you treat it as clean.

- Import `workflows/06-redacted-error-log.json` into n8n (Workflows > Import from file). It ships inactive, uses `REPLACE_WITH_` placeholders, and contains no credentials.
- Setup notes: `docs/06-redacted-error-log.md`
- Check the workflow: `python3 scripts/validate-workflows.py`

## Tested on live n8n

Imported and run on a local n8n 2.49.5 instance on 25 November 2026 (Europe/Warsaw).

The first run showed that `Set your IDs` does not pass the error payload through, so the Redact node only logged "Workflow error". That is fixed in this copy: it now reads the payload from the node named **Error trigger**. After the fix, redaction of common patterns passed, including long `sk-` keys, `sk-proj-…`, Bearer tokens, Slack `xox`, Notion `ntn_`, `secret_`, and `api_key` assignments. Short fragments such as `sk-test...` are not treated as keys. Please still review the log.

## License

MIT for this repository only (see `LICENSE`). This is a free sample of one workflow.

The paid Agent Desk n8n Human-Gate Pack is sold separately and stays under the buyer licence that comes with that purchase. Workflows 01–05 and the rest of the pack are not included here and are not licensed under MIT.

The paid pack is not listed for sale yet, so this README does not include a product URL.

---

DC4I sp. z o.o., ul. Hoża 86/410, 00-682 Warszawa, KRS 0001277254, NIP 7011339094
