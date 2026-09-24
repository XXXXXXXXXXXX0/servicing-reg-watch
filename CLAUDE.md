# Standing rules for every session

Read BUILD_SPEC.md before changing anything. These rules apply to all work in this repo.

## Data and output
- Write large data to files (under `data/`, which is gitignored). Never print document contents to chat; report counts, IDs, headings, and file paths instead.
- Cache every API response to disk and never refetch a cached document. Check the cache before any request.
- Batch requests and back off on rate limits (429 and 5xx: exponential backoff, as in `pipeline/sources.py`).

## Code
- Extend existing modules rather than rewriting them.
- Add no dependencies unless they are required.
- Add tests only for changed behavior.

## Content
- Never invent citations. A row without an identified primary source stays `unresearched` with `citation: null` and `source_url: null`.

## Secrets
- Never print or commit secrets or API keys (`GOVINFO_API_KEY`, `ANTHROPIC_API_KEY`, or any other). Send keys in request headers, not URLs, and keep them out of logs and error messages.

## Workflow
- Every prompt ends with the marker END OF PROMPT. If a message lacks it, do no work; tell me the message may be truncated and quote its last line.
- Commit and push after each step.
- End with a summary of under 15 lines.
