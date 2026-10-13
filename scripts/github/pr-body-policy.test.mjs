import assert from "node:assert/strict";
import test from "node:test";

import { hasIssueOrJustification } from "./pr-body-policy.mjs";

test("accepts issue and justification keywords in english and spanish", () => {
  const validBodies = [
    "## Issue\n- #123",
    "## Trazabilidad\n- Relacionado: #123",
    "## Justificacion\nNo issue applies.",
    "## Justificación\nNo issue applies.",
  ];

  for (const body of validBodies) {
    assert.equal(hasIssueOrJustification(body), true, body);
  }
});

test("accepts traceability-based descriptions", () => {
  const body = "## Traceability\nThis PR consolidates evidence from PR #569 and #570.";
  assert.equal(hasIssueOrJustification(body), true);
});

test("rejects bodies without issue, justification, or traceability markers", () => {
  const body = "## Summary\nDocumentation-only update without related links.";
  assert.equal(hasIssueOrJustification(body), false);
});
