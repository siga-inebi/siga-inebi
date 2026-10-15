import assert from "node:assert/strict";
import test from "node:test";

import { evaluateGate } from "./ci-gate.mjs";

const SHA = "a".repeat(40);
const HEAD = "b".repeat(40);
const TREE = "c".repeat(40);

const allJobs = (overrides = {}) =>
  [
    "changes",
    "backend-lint",
    "backend-tests",
    "backend-security",
    "frontend-lint",
    "frontend-tests",
    "frontend-build",
    "docker-integration",
  ].map((name) => ({ name, conclusion: overrides[name] ?? "success" }));

const greenInput = (overrides = {}) => ({
  sha: SHA,
  pulls: [{ number: 7, merged_at: "2026-10-15T00:00:00Z", merge_commit_sha: SHA, base: { ref: "develop" }, head: { sha: HEAD } }],
  runs: [
    { id: 2, event: "pull_request", head_sha: HEAD, status: "completed", conclusion: "success", created_at: "2026-10-15T02:00:00Z" },
    { id: 1, event: "pull_request", head_sha: HEAD, status: "completed", conclusion: "failure", created_at: "2026-10-15T01:00:00Z" },
  ],
  jobs: allJobs(),
  pushedTree: TREE,
  headTree: TREE,
  requiredJobs: ["backend-lint", "backend-tests", "backend-security", "docker-integration"],
  ...overrides,
});

test("a merged, up-to-date PR with green CI is verified", () => {
  const result = evaluateGate(greenInput());
  assert.equal(result.verified, true, result.reason);
  assert.equal(result.pr, 7);
  assert.equal(result.runId, 2);
});

test("skipped jobs count as passing when the deploy does not need them", () => {
  const result = evaluateGate(
    greenInput({
      jobs: allJobs({ "frontend-lint": "skipped", "frontend-tests": "skipped", "frontend-build": "skipped" }),
    }),
  );
  assert.equal(result.verified, true, result.reason);
});

test("forced full CI is never verified", () => {
  assert.equal(evaluateGate(greenInput({ forceFullCi: true })).verified, false);
});

test("a direct push without a merged PR falls back", () => {
  assert.equal(evaluateGate(greenInput({ pulls: [] })).verified, false);
  const otherCommit = greenInput().pulls.map((pull) => ({ ...pull, merge_commit_sha: HEAD }));
  assert.equal(evaluateGate(greenInput({ pulls: otherCommit })).verified, false);
  const otherBase = greenInput().pulls.map((pull) => ({ ...pull, base: { ref: "main" } }));
  assert.equal(evaluateGate(greenInput({ pulls: otherBase })).verified, false);
  const open = greenInput().pulls.map((pull) => ({ ...pull, merged_at: null }));
  assert.equal(evaluateGate(greenInput({ pulls: open })).verified, false);
});

test("the latest run decides: a red rerun after a green one falls back", () => {
  const runs = [
    { id: 3, event: "pull_request", head_sha: HEAD, status: "completed", conclusion: "failure", created_at: "2026-10-15T03:00:00Z" },
    ...greenInput().runs,
  ];
  assert.equal(evaluateGate(greenInput({ runs })).verified, false);
});

test("an admin merge with failing, running or missing CI falls back", () => {
  assert.equal(evaluateGate(greenInput({ runs: [] })).verified, false);
  const running = [{ ...greenInput().runs[0], status: "in_progress", conclusion: null }];
  assert.equal(evaluateGate(greenInput({ runs: running })).verified, false);
  assert.equal(evaluateGate(greenInput({ jobs: allJobs({ "backend-tests": "failure" }) })).verified, false);
  assert.equal(evaluateGate(greenInput({ jobs: allJobs({ "backend-tests": "cancelled" }) })).verified, false);
  const missing = allJobs().filter((job) => job.name !== "docker-integration");
  assert.equal(evaluateGate(greenInput({ jobs: missing })).verified, false);
});

test("runs of other heads or events are ignored", () => {
  const runs = [{ ...greenInput().runs[0], head_sha: "d".repeat(40) }, { ...greenInput().runs[0], event: "push" }];
  assert.equal(evaluateGate(greenInput({ runs })).verified, false);
});

test("code changed since the deployed commit must have been tested, not skipped", () => {
  const result = evaluateGate(
    greenInput({ jobs: allJobs({ "backend-tests": "skipped", "backend-lint": "skipped" }) }),
  );
  assert.equal(result.verified, false);
  assert.match(result.reason, /backend-lint, backend-tests/);
});

test("a merge whose tree differs from the tested head falls back", () => {
  const result = evaluateGate(greenInput({ pushedTree: "e".repeat(40) }));
  assert.equal(result.verified, false);
  assert.match(result.reason, /al día/);
  assert.equal(evaluateGate(greenInput({ headTree: undefined })).verified, false);
});
