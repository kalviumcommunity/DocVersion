
# Verifiable Citations in DocVersion RAG

## Citation flow

1. Retrieve relevant chunks from the document corpus.
2. Assign each retrieved chunk a citation identifier such as [1].
3. Map each identifier to its source filename, path, chunk ID,
   chunk index, page, and section.
4. Compare the retrieved text against the original corpus chunk.
5. Validate that answer citations refer to known, verified sources.
6. Reject unknown or unverifiable citations and use a safe fallback.
7. Save the answer, citation map, verification example, and no-source
   fallback as reviewable artifacts.

## Example

Claim: Employees receive 20 days of annual leave per calendar year [1].

Citation [1] maps to:

- Source: leave_policy.md
- Chunk ID: leave_policy_chunk_001
- Section: Annual Leave

The original chunk text is retained in the citation artifacts so a
reviewer can inspect the exact evidence.

## No-source behavior

If retrieval produces no chunks, the system returns an explanation
that it cannot provide a grounded answer. It does not invent citations.

## Limitations

The offline system uses keyword retrieval and extractive answering.
Citation validation confirms that references point to retrieved
source chunks, not that arbitrary generated paraphrases are logically
entailed by those chunks.
