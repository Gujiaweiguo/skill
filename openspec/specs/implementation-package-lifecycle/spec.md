# implementation-package-lifecycle Specification

## Purpose
Defines the lifecycle contract for implementation packages across issuing and executing sides: the three execution modes with their change-policy combination matrix, per-mode permission sets including the zero-write read-only-verification branch, findings-type return shapes, the separation of issued / actually-consumed / current versions with the consumption guard and errata pattern, baseline-drift adjudication, and evidence-gated lifecycle advancement shared by package and return statuses.

## Requirements

### Requirement: Execution modes and change policies SHALL form a validated combination matrix
Packages SHALL resolve execution mode before change policy. Implementation modes retain autonomous-batch + consume-existing defaults; plan-and-apply or create-or-consume requires a closed allowed_change_ids list. Read-only mode SHALL accept none + [] and reject creation policies or nonempty change sets. Missing read-only fields SHALL resolve to none and [] without granting writes.

#### Scenario: Mode and policy parsed at preflight
- **WHEN** implementation modes declare policy and change IDs
- **THEN** preflight SHALL enforce consume-existing or create-or-consume and the existing closed-list requirements without widening permissions

#### Scenario: Legacy package without the fields
- **WHEN** execution_mode is absent on a legacy implementation package
- **THEN** autonomous-batch + consume-existing SHALL remain the compatible default

#### Scenario: Existing W1 read-only package
- **WHEN** read-only-verification declares change_policy:none and allowed_change_ids:[]
- **THEN** preflight SHALL accept this closed empty set and SHALL NOT reject the list merely because the field exists

#### Scenario: Omitted read-only policy fields
- **WHEN** mode is explicitly read-only-verification and policy or allowed_change_ids is omitted
- **THEN** only omitted fields SHALL resolve to none or []; explicit null or malformed values SHALL fail closed; consume-existing is accepted only as a legacy no-write alias and does not authorize applying changes

#### Scenario: Read-only package combined with a creation policy
- **WHEN** read-only mode declares create-or-consume or a nonempty allowed_change_ids set
- **THEN** preflight SHALL reject it; no implementation-mode default SHALL override the read-only mode

### Requirement: read-only-verification SHALL execute under a zero-write permission set
Read-only verification SHALL deny change creation, code/test modification, database writes/migrations, commit, archive, push, and docs writes. File reads and side-effect-free checks SHALL respect package scope; database reads need separate scope and connection authorization. Side-effect tests/checks SHALL be denied by default and require explicit prior authorization within the approved boundary. Before/after state checks SHALL NOT grant permission.

#### Scenario: Permission declaration in read-only mode
- **WHEN** a read-only-verification package passes preflight and the session outputs its permission declaration
- **THEN** change creation, code and test writes, database writes and migrations, commit, archive, push, and docs writes SHALL each be listed as denied, with read access granted

#### Scenario: Distinct read permissions
- **WHEN** read-only verification considers files, database queries, or checks
- **THEN** file reads and side-effect-free checks SHALL stay within package scope; database read-only queries additionally require connection authorization; file-read permission SHALL NOT imply database access

#### Scenario: Side-effect command authorization
- **WHEN** a test or check can produce side effects
- **THEN** explicit prior authorization SHALL cover the command and effects within the approved boundary; database writes/migrations remain denied; before/after state checks SHALL be evidence only and SHALL NOT replace authorization

#### Scenario: Verification session does not borrow write permission via the return
- **WHEN** findings are emitted through the package's return channel
- **THEN** the return emission SHALL NOT be treated as authorization to write the docs repository or any other authority

#### Scenario: No fabricated execution evidence
- **WHEN** a read-only verification return reports gate or test verdicts it did not produce
- **THEN** those verdicts SHALL be attributed to the archived evidence they copy from, and the return SHALL NOT contain feature commits, archive paths, or test-run claims of the verification session itself

### Requirement: Findings-type returns SHALL be legal for verification packages
An implementation-return for a `read-only-verification` package MAY carry an empty `changes` list, legal only when the package mode makes change execution impossible, and SHALL record the mode, the emptiness reason, findings with evidence anchors, verification scope and limits, and the standard boundary attestations. A verification return marks its package consumed on completion like an execution return; its findings MAY anchor a later package without transferring permissions.

#### Scenario: Read-only return with empty changes validates
- **WHEN** a verification return carries `changes: []`, the package mode, and the stated reason
- **THEN** schema validation SHALL report shape validity separately from manual protocol acceptance of mode, reason, scope, and findings

#### Scenario: Empty changes in an execution mode is a defect
- **WHEN** an `autonomous-batch` or `plan-and-apply` return reports `changes: []` without a mode-legal reason
- **THEN** manual protocol review SHALL flag missing execution evidence even if schema validation passes; no unrelated missing field SHALL be used to claim this rule is mechanically enforced

#### Scenario: Chained consumption of a verification return
- **WHEN** a later implementation package anchors its inputs to a verification return's findings
- **THEN** the later package SHALL hold its own independent authorization and inherit nothing from the verification package

### Requirement: Issued, consumed, and current package versions SHALL remain distinct facts
The version issued, the version actually consumed, and the current document version of a package SHALL be recorded as separate facts. A refresh of an unconsumed package SHALL record the version switch and the new version's applicability conditions. An already-consumed package SHALL NOT have its consumed bytes replaced; later corrections SHALL use an independent erratum or supplementary record preserving the actual consumption anchors (input hashes, consumed version, original errors).

#### Scenario: Consumed version differs from current package version
- **WHEN** a target executed a package at v1.0 while the package file has since advanced to v1.1
- **THEN** records SHALL state that v1.0 was actually consumed, keep the v1.0 anchors, and record the version switch as a separate fact pending owner disposition

#### Scenario: Erratum after consumption
- **WHEN** a consistency erratum is issued after execution has consumed a package
- **THEN** the erratum SHALL preserve the originally issued inputs, hashes, and stub history and SHALL NOT rewrite them as if the correction had been consumed at execution time

### Requirement: Consumption guards and indirect evidence SHALL have explicit limits
A docs-side pending stub with `package_consumed=false` alone SHALL NOT prove the target has not implemented; the consumption guard SHALL cross-check target-side evidence channels (existing returns, active changes, feature commits). Timestamps, logs, and commit ordering SHALL be evidence only of their own events. A historical byte match with an anchor SHALL NOT alone make current inputs applicable to continue execution; occurred scope or sequence deviations SHALL NOT be automatically ratified.

#### Scenario: Stub does not prove non-implementation
- **WHEN** the docs-side stub is pending with `package_consumed=false` but target-side commits or changes exist
- **THEN** the guard SHALL treat execution as possibly already occurred, cross-check the target evidence channels, and SHALL NOT re-issue or re-run on the stub alone

#### Scenario: Timestamps cannot prove preflight or authorization
- **WHEN** commit and log timestamps are compared to argue that a preflight started before or after a package issuance
- **THEN** the comparison SHALL be recorded as proving only the timestamps' own events, leaving preflight start and prior-authorization conclusions to explicit records or owner disposition

#### Scenario: Byte match does not imply current applicability
- **WHEN** an anchor reproduces exactly in committed history but the package has since been re-issued at a newer version
- **THEN** the historical byte match SHALL NOT by itself authorize continuing execution on the old inputs

### Requirement: Baseline drift SHALL follow a deterministic adjudication path
On an input-anchor mismatch at preflight, the executing session SHALL adjudicate deterministically: first whether the recorded anchor hash is reproducible in committed history (a transient hash in no commit is an issuance-side defect), then whether current HEAD or workspace has advanced past the anchor, then choose among content-level equivalence with a recorded discrepancy, callback for re-issuance, or halt. A byte match with history SHALL NOT skip the workspace-advanced check.

#### Scenario: Transient anchor hash
- **WHEN** an anchor hash matches no committed version of its file
- **THEN** the drift SHALL be classified as an issuance-side transient-anchor defect and escalated, not retried against the working tree

#### Scenario: Anchor valid but workspace advanced
- **WHEN** the anchor reproduces in history but the current HEAD has moved past it
- **THEN** the session SHALL perform the workspace-advanced check, record the chosen branch and evidence, and either verify content-level equivalence with a recorded discrepancy or pause and call back for re-issuance

### Requirement: Package and return lifecycle advancement SHALL be evidence-gated with explicit ownership
The executing side SHALL produce a complete return reporting execution facts without writing docs. The docs side SHALL verify that return before updating its package to executed, and complete per-item dispositions before advancing absorbed/reconciled. Package and return statuses SHALL remain separate facts; elapsed time SHALL NOT substitute for disposition or grant cross-repository writes.

#### Scenario: Absorption closes the package only after per-item disposition
- **WHEN** docs absorption finishes the PRD and status-board write-back for a return
- **THEN** the return SHALL be advanced to `absorbed` with per-item dispositions in the same batch, and the package SHALL be marked `reconciled` only after that

#### Scenario: Executed package with pending return
- **WHEN** a package is `executed` while its return remains `pending` or `reviewed`
- **THEN** neither status SHALL be inferred from the other and the missing side SHALL remain visible as an open obligation

#### Scenario: Executor reports completion without docs writes
- **WHEN** target execution finishes and emits a complete return via an authorized channel
- **THEN** the executor SHALL only report completion; docs SHALL verify the return before writing executed to its package, without inventing permission for the executor to edit that package
