# GitHub Team Workflow

## Project

Version-Aware Developer Documentation Assistant

## Team

Squad 63 - Team 02

## 1. Branching Strategy

- `main` contains reviewed and releasable code.
- Team members do not directly develop on `main`.
- All work happens on task-specific feature, fix, docs, or refactor branches.
- Branch naming format:

`[type]/[short-description]`

Examples relevant to this project:
- `feature/github-workflow-setup`
- `feature/document-ingestion`
- `feature/version-aware-retrieval`
- `feature/vector-search`
- `fix/version-filtering`
- `docs/project-documentation`
- `refactor/retrieval-service`

- Branches are deleted after successful pull request merge.

## 2. GitHub Issues

Every meaningful feature, bug fix, documentation update, or refactoring task starts with a GitHub issue.

Every issue must contain:
- Action-oriented title
- Description and context (Why & What)
- Definition of Done / Acceptance Criteria
- Relevant label (e.g., `feature`, `documentation`, `bug`, `chore`)
- Assignee (the team member responsible for the task)

Issues establish clear traceability between requested deliverables and their technical implementations.

## 3. Commit Message Convention

Commits must follow the conventional commit format:

`[type]: [description]`

Supported types:
- `feat`: A new feature
- `fix`: A bug fix
- `docs`: Documentation only changes
- `refactor`: A code change that neither fixes a bug nor adds a feature
- `test`: Adding missing tests or correcting existing tests
- `chore`: Changes to build process, configuration, or auxiliary tools

Examples relevant to this project:
- `feat: add documentation ingestion pipeline`
- `fix: correct version metadata filtering`
- `docs: update project architecture documentation`
- `refactor: simplify document chunking logic`
- `test: add retrieval evaluation tests`
- `chore: update project configuration`

Consistent commit messages improve repository history readability, facilitate code reviews, and allow tracking changes across releases.

## 4. Pull Request Review Process

- Work is developed on a dedicated branch and pushed to GitHub.
- A Pull Request (PR) is opened against `main`.
- The related issue is linked in the PR description using keyword syntax:
  `Closes #<issue-number>`
- At least one teammate must review and approve the PR before merging.
- Reviewers evaluate:
  - Correctness and adherence to requirements
  - Code clarity and readability
  - Data integrity and metadata preservation
  - Test coverage where applicable
  - Scope discipline (no unrelated changes)
  - Architecture consistency
  - Quality and format of commit messages
- All review feedback and comments must be addressed and resolved before approval and merge.

## 5. Pull Request Workflow

```text
GitHub Issue
  ↓
Create feature branch
  ↓
Make changes
  ↓
Test changes
  ↓
Commit changes
  ↓
Push branch
  ↓
Open Pull Request
  ↓
Link issue
  ↓
Teammate review
  ↓
Resolve feedback
  ↓
Approval
  ↓
Merge into main
  ↓
Delete branch
```

## 6. Main Branch Protection

The `main` branch must remain stable and deployable at all times. All development changes must enter `main` through reviewed Pull Requests rather than direct commits to `main`. Team members must enforce this workflow by creating feature branches for all tasks and requiring PR reviews prior to merging.

## 7. Project-Specific Collaboration Rules

- **Respect Architecture**: Documentation ingestion and retrieval work must align with the overall project architecture.
- **Preserve Metadata**: Version metadata (e.g., product version, document type) and source traceability must be maintained across ingestion and indexing pipelines.
- **Strict PR Scope**: Unrelated changes should not be mixed into a single PR. Each PR must address one clearly defined issue.
- **Test Coverage**: New functionality and pipeline steps should include appropriate unit/integration tests where applicable.
