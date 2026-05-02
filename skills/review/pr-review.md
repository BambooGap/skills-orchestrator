---
id: pr-review
name: PR Review
summary: "Systematic PR review process with blocking/suggestion/nit severity levels"
tags: [review, english]
load_policy: free
priority: 100
zones: [default]
conflict_with: [chinese-code-review]
---
# PR Review Skill

## Overview

This skill defines a systematic pull request review process. A good review catches real problems, not just style issues, and gives the author actionable feedback they can act on immediately.

---

## Review Mindset

**Goal**: Help the author ship better code, not demonstrate your knowledge.

- Assume good intent. The author made the best decision they could with the information they had.
- Separate blocking issues from suggestions. Be explicit about which is which.
- Review the code, not the person. "This function is hard to follow" not "You wrote confusing code."
- Ask questions when unsure. "What happens if X?" not "This will break when X."

---

## Review Checklist

### 1. Understand the Change First

Before reviewing line by line:

- [ ] Read the PR description fully
- [ ] Understand what problem is being solved
- [ ] Check the linked issue or ticket
- [ ] Run the code locally if the change is non-trivial

### 2. Correctness (Blocking)

- [ ] Does the code do what the PR description says?
- [ ] Are there obvious logic errors?
- [ ] Are edge cases handled? (null/empty input, concurrent access, large data)
- [ ] Are errors handled correctly? (not swallowed, not over-caught)
- [ ] Are security concerns addressed? (SQL injection, XSS, auth checks)

### 3. Tests (Blocking)

- [ ] Are new features tested?
- [ ] Are bug fixes covered by a regression test?
- [ ] Do tests actually test the right thing? (not just coverage for coverage's sake)
- [ ] Are tests readable? (another developer can understand what's being tested)

### 4. Design (Often Blocking)

- [ ] Does the change fit the existing architecture?
- [ ] Is the abstraction level appropriate? (not too generic, not too specific)
- [ ] Is there unnecessary complexity?
- [ ] Are there obvious performance problems? (N+1 queries, missing indexes, O(n²) where O(n) works)

### 5. Code Quality (Non-blocking by default)

- [ ] Function/variable names are clear
- [ ] No dead code or commented-out code
- [ ] No magic numbers
- [ ] Functions do one thing
- [ ] No unnecessary duplication

### 6. Documentation (Context-dependent)

- [ ] Public APIs have docstrings/comments
- [ ] Complex algorithms are explained
- [ ] README updated if behavior changed

---

## Comment Format

### Blocking Issue

```
**Blocking**: This will fail when `user` is None — `user.id` is called on line 47 
without a null check. Reproduction: call with `user=None`.
```

### Suggestion (Non-blocking)

```
**Suggestion**: Consider extracting the discount calculation into a helper — 
it's used in 3 places and will likely need updating together. 
Not blocking this PR.
```

### Question

```
**Question**: What's the expected behavior when `amount` is 0? 
Is that a valid order or should it be rejected?
```

### Nitpick

```
nit: `userData` → `user_data` to match the project's snake_case convention.
```

---

## Severity Levels

| Level | Label | Meaning | Merge? |
|-------|-------|---------|--------|
| Must fix | **Blocking** | Bug, security issue, correctness problem | No |
| Should fix | **Suggestion** | Design problem, maintainability concern | Author's call |
| Optional | **nit** | Style, minor naming, preference | Yes, fix later |

Always label your comments explicitly. Reviewers and authors should never have to guess whether something blocks the merge.

---

## Review Size Guidelines

| PR Size | Lines Changed | Expected Review Time |
|---------|--------------|---------------------|
| Small | < 100 | 15-30 min |
| Medium | 100-400 | 30-60 min |
| Large | 400-800 | 60-90 min |
| Too Large | > 800 | Ask to split |

For PRs over 800 lines, it's acceptable (and professional) to ask the author to split it before reviewing.

---

## What NOT to Block On

- Personal style preferences not covered by the project's linter
- Implementation approaches that work even if you'd do it differently
- Performance improvements that are premature optimizations
- Theoretical future requirements

---

## Relationship to Other Skills

- After review, author uses `finish-branch` checklist to address feedback
- For Chinese-language teams, `chinese-code-review` has additional naming conventions
- Pair with `systematic-debugging` when a bug is found in review
