# GitLab JSON-LD Knowledge Graph — Implementation Plan

> **Purpose:** Concise project context for a coding agent working in VS Code.
> **Status:** Draft. Confirmed requirements are separated from open decisions.
> **Agent instruction:** Do not turn an open decision into an implementation requirement without asking or documenting explicit approval. Build in small, testable increments.

## 1. Confirmed requirements

- Ingest JSON-LD snapshots produced by commits in **thousands to tens of thousands of GitLab repositories**.
- A typical repository snapshot contains **10,000–100,000 RDF triples**. The combined graph is expected to exceed **100 million triples** and may reach **billions**.
- Support **SPARQL 1.1** across repositories, including filtering, joins, and multi-hop graph queries.
- Support **embedding-based semantic search** across RDF entities and associated content; allow repository filtering and SPARQL-based filtering/enrichment of results.
- Preserve **repository/source provenance** for statements and results. Records from separate repositories must not merge merely because their original identifiers match.
- Handle complete-snapshot updates, additions, changes, deletions, retries, and concurrent reads without exposing partially applied repository updates.
- Keep the RDF data and semantic index synchronized well enough that stale or uncommitted results are never presented as current. Define the exact visibility/freshness contract before implementing the index integration.
- Prioritize reliability, scalability, measurable performance, recoverability, and **open-source licensing**.

## 2. Agreed direction (not a fixed deployment design)

- **Apache Jena** is acceptable for RDF processing and SPARQL. Evaluate its appropriate components (e.g., TDB2/Fuseki) for the final deployment; do not assume a programming-language version or application framework.
- Treat each **GitLab repository as a logical data and update boundary**. Use repository-scoped named graphs or graph groups and track the commit that produced their content. Preserve original JSON-LD graph information where relevant.
- **Start with shared RDF storage** rather than one physical database per repository, so cross-repository SPARQL joins can execute within a common query environment. Validate capacity with benchmarks before deciding on physical partitioning.
- Separate **source-specific record identity** from original identifiers. Any equivalence between records across repositories must be deliberate, not an accidental consequence of shared IRIs.
- Treat the semantic index as a **derived index** of committed RDF content. Provide **global semantic search** with source/provenance metadata and the ability to filter by repository. **No vector database or embedding model has been selected.**
- Avoid retaining full duplicates of every historical snapshot in the active RDF store without a demonstrated need. GitLab commits provide a source-history reference; decide separately whether an independent snapshot archive is needed.

## 3. Core data flow

```text
GitLab commit → JSON-LD snapshot
               ↓
        Retrieve and validate
               ↓
     Normalize RDF / track source
               ↓
   Prepare repository-level update
               ↓
    Transactional RDF application
               ↓
    Update derived semantic index
               ↓
    Publish verified searchable state
               ↓
       SPARQL + semantic API
```

This is a **logical flow**, not a commitment to a queue, service layout, programming language, or indexing engine. The graph and semantic index are separate consistency boundaries; publishing them as one coherent searchable state requires an explicitly designed protocol.

## 4. Implementation stages

### Stage A — RDF proof of concept

- [ ] Create small JSON-LD fixtures representing at least two repositories with an overlapping original entity identifier, a changed snapshot, and a deletion.
- [ ] Select and configure the minimum Apache Jena components required to load the fixtures and execute SPARQL 1.1.
- [ ] Define repository/source identifiers, named-graph mapping, and a policy for source-scoped entity IRIs.
- [ ] Demonstrate source-specific and cross-repository SPARQL queries without accidental entity merging.

**Success:** Both repositories can be queried together and separately; provenance is visible and identity isolation is tested.

### Stage B — GitLab snapshot ingestion

- [ ] Accept or retrieve a snapshot associated with a GitLab repository and commit.
- [ ] Validate and normalize incoming JSON-LD, including any input named graphs.
- [ ] Implement **atomic updates per repository**, including removed statements and entities. Compare full replacement and delta application if performance justifies it.
- [ ] Track which commit is published, handle duplicate/out-of-order events, and test concurrent queries during updates.

**Success:** A reader observes a complete published repository state, never a partially applied update. Updating or deleting one repository does not change another.

### Stage C — Semantic search integration

- [ ] Define which RDF entities/content should be embedded and how to identify the corresponding source records.
- [ ] Evaluate an **open-source** embedding solution and vector/search engine; keep them replaceable until selected.
- [ ] Implement global similarity retrieval plus repository filters and SPARQL enrichment.
- [ ] Update, replace, or remove derived vector entries when the relevant RDF content changes.

**Success:** Semantic results point to the correct repository-scoped RDF entities; changed/deleted content is handled correctly.

### Stage D — Consistency, recovery, and scale

- [ ] Define and test a publication/visibility contract between RDF commits and semantic indexing, including index failures and retries.
- [ ] Add recovery, observability, authorization boundaries, and reproducible deployment instructions appropriate to the selected stack.
- [ ] Benchmark representative SPARQL queries, concurrent updates, semantic retrieval, and storage growth at progressively larger datasets.
- [ ] Decide whether shared RDF storage is sufficient or if repo-group partitioning and an integrated cross-repo read layer are required.

**Success:** Failure tests prove data isolation and the agreed freshness guarantees; performance decisions are supported by measurements, not assumed throughput.

## 5. Decisions to confirm before committing to infrastructure

1. **Implementation stack:** Preferred language, framework, runtime, and whether a project skeleton already exists?
2. **GitLab scope:** Only the default branch/latest snapshot per repository, or multiple branches and historical versions?
3. **Query surface:** SPARQL endpoint only at first, or also a dedicated search/API layer?
4. **Semantic search:** Include it in the first working milestone, or add it after RDF ingestion/SPARQL is reliable? Preferred embedding runtime or vector engine, if any?
5. **Freshness:** Must an RDF revision and its embedding index become visible together, or is a clearly reported period of semantic-index lag acceptable?
6. **Operational constraints:** Expected commit frequency, hosting/environment, availability/recovery targets, and whether access controls vary by repository?

**No default answers are implied by this document.** Record decisions here as they are made; defer engine-specific architecture and API/schema details until then.

## 6. Instructions for the coding agent

- Read this file first, then inspect any existing repository code and conventions. **Do not scaffold over existing work.**
- Start with **Stage A** and its minimal tests. If a blocked decision prevents work, ask rather than inventing a stack or production infrastructure.
- Favor observable, incremental changes. Add automated tests for repository isolation, provenance, update atomicity, deletions, and cross-repository queries.
- Keep vendor-specific vector features behind a replaceable boundary until a technology is approved.
- Update checkboxes and record new decisions and tradeoffs in this plan. Do not declare production readiness without measured scale and recovery tests.
