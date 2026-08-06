Sprint 01 – First story

I think we start tomorrow with:

Story: GAPS-001

As a developer, I want the repository to validate itself so that broken assets, YAML, or references cannot be committed without being detected.

Deliverable:

Compiler/
    validate_repository.py

Acceptance Criteria:

Validates repository structure.
Validates required YAML files exist.
Detects broken references.
Detects duplicate asset IDs.
Detects missing Gold Masters.
Produces a single RepositoryReport.md.
Returns a non-zero exit code when validation fails (so GitHub Actions can block a bad build later).
