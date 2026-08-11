# Personal Knowledge Ingestion

## Example 1 — Ingest a text document

Input:
A `.txt` file uploaded with `PersonalDocumentMetadata` (document_id, owner_id,
tenant_id, etc.).

Expected:
- Parsed → cleaned (control chars stripped, blank lines collapsed) → chunked →
  embedded → stored, in that order (Section 9's pipeline)
- Metadata is recorded and retrievable by `document_id` afterward

## Example 2 — Every supported format parses

Input:
`.pdf`, `.docx`, `.txt`, `.md`, `.csv`, `.json` files.

Expected:
- Each has a dedicated parser in `ParserRegistry`; an unsupported extension
  (e.g. `.xyz`) raises `ParseError` rather than silently ingesting garbage or
  crashing with an unrelated exception

## Example 3 — Corrupt file rejected cleanly

Input:
Bytes that are not a valid PDF, claimed to be a `.pdf`.

Expected:
- `ParseError` raised with a clear message — never a raw library traceback
  surfacing to the caller, never a silent empty-text ingestion

## Example 4 — Owner can read their own PERSONAL document

Input:
A document owned by `alice`, sensitivity `PERSONAL`; `alice` searches.

Expected:
- Results include chunks from that document

## Example 5 — Non-owner cannot read another user's PERSONAL document

Input:
The same document; `bob` searches with the same query.

Expected:
- Results are empty — access denied by default, not merely "unranked/deprioritized"

## Example 6 — PUBLIC documents are readable within the same tenant

Input:
A `PUBLIC` document owned by `alice`; `bob` (same tenant) searches.

Expected:
- Results include the document — `PUBLIC` bypasses the owner check, but NOT the
  tenant check

## Example 7 — Cross-tenant access always denied, even for PUBLIC documents

Input:
A `PUBLIC` document in `tenantA`; a requester scoped to `tenantB` searches.

Expected:
- Results are empty — tenant isolation is checked before sensitivity, and
  nothing overrides it (Section 55's tenant isolation applies here too)

## Example 8 — Explicit permission grants access to CONFIDENTIAL content

Input:
A `CONFIDENTIAL` document with `permissions=["bob"]`; `bob` searches.

Expected:
- Results include the document, because `bob` is explicitly listed

## Example 9 — Missing metadata denies by default

Input:
A chunk whose `document_id` has no corresponding entry in the metadata table
(e.g. an ingestion bug, or partial data).

Expected:
- Access is denied — "we don't know who owns this" is never treated as "anyone
  may read this"

## The core rule (Section 10)

> The LLM must never be responsible for enforcing access control.

`SecureRetriever` enforces every check in Python, before results are ever
formatted into a prompt. No amount of prompt engineering ("don't share other
users' documents") is relied upon here — the LLM never sees a chunk it wasn't
already permitted to see.
