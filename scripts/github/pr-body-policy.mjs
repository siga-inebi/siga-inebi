const bodyPolicyPattern = /\b(Issue|Relacionado|Justificaci(?:o|ó)n|Traceability|Trazabilidad)\b/i;

export function hasIssueOrJustification(body) {
  return bodyPolicyPattern.test(body);
}
