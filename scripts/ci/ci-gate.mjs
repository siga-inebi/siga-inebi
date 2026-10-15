// CI gate for deploy-qa.yml (issue #627).
//
// A push to develop only skips the full CI rerun when ALL of these hold:
//   1. it is the merge of a PR into develop (merge_commit_sha === pushed sha);
//   2. the latest ci.yml pull_request run on the PR head finished in success;
//   3. every job of that run ended in success or skipped, and the jobs the
//      deploy needs (areas changed since the commit running in QA) really ran;
//   4. the pushed tree is byte-for-byte the tree that CI tested (the PR head),
//      which is what the "branch must be up to date" rule guarantees.
// Anything else -- no PR, direct push, --admin merge with red or missing
// checks, a stale branch, an API error or `full_ci: true` -- returns
// verified=false and deploy-qa.yml runs the full ci.yml as before.

import { appendFileSync } from "node:fs";
import { pathToFileURL } from "node:url";

import { CI_JOBS } from "./detect-changes.mjs";

export const CI_WORKFLOW_FILE = "ci.yml";
const EXPECTED_JOBS = ["changes", ...Object.values(CI_JOBS).flat()];
const PASSING = new Set(["success", "skipped"]);

const refuse = (reason, extra = {}) => ({ verified: false, reason, ...extra });

/** Pure decision; every input comes from the GitHub REST API. */
export function evaluateGate({
  sha,
  baseBranch = "develop",
  forceFullCi = false,
  pulls = [],
  runs = [],
  jobs = [],
  pushedTree,
  headTree,
  requiredJobs = [],
}) {
  if (forceFullCi) return refuse("full_ci=true en workflow_dispatch");

  const pr = pulls.find(
    (pull) => pull.merged_at && pull.merge_commit_sha === sha && pull.base?.ref === baseBranch,
  );
  if (!pr) return refuse("el commit no es la fusión de un PR hacia develop (push directo)");
  const headSha = pr.head?.sha;
  const context = { pr: pr.number, headSha };

  const prRuns = runs
    .filter((run) => run.event === "pull_request" && run.head_sha === headSha)
    .sort((a, b) => Date.parse(b.created_at) - Date.parse(a.created_at));
  const run = prRuns[0];
  if (!run) return refuse(`PR #${pr.number}: no hay corrida de ci.yml sobre ${headSha}`, context);
  context.runId = run.id;
  if (run.status !== "completed" || run.conclusion !== "success") {
    return refuse(
      `PR #${pr.number}: la última corrida de ci.yml (${run.id}) está ${run.status}/${run.conclusion}`,
      context,
    );
  }

  const byName = new Map(jobs.map((job) => [job.name, job]));
  const missing = EXPECTED_JOBS.filter((name) => !byName.has(name));
  if (missing.length) return refuse(`faltan jobs en la corrida ${run.id}: ${missing.join(", ")}`, context);
  const failing = jobs.filter((job) => !PASSING.has(job.conclusion));
  if (failing.length) {
    const detail = failing.map((job) => `${job.name}=${job.conclusion}`).join(", ");
    return refuse(`jobs sin éxito en la corrida ${run.id}: ${detail}`, context);
  }
  if (byName.get("changes").conclusion !== "success") {
    return refuse("el job changes no terminó en success", context);
  }
  const skippedRequired = requiredJobs.filter((name) => byName.get(name)?.conclusion !== "success");
  if (skippedRequired.length) {
    return refuse(
      `cambió código desde el SHA desplegado y el PR no corrió: ${skippedRequired.join(", ")}`,
      context,
    );
  }

  if (!pushedTree || !headTree || pushedTree !== headTree) {
    return refuse(
      "el árbol fusionado no es el que probó CI (la rama no estaba al día con develop)",
      context,
    );
  }
  return { verified: true, reason: `CI en verde del PR #${pr.number} (corrida ${run.id})`, ...context };
}

async function api(path) {
  const response = await fetch(`${process.env.GITHUB_API_URL || "https://api.github.com"}${path}`, {
    headers: {
      accept: "application/vnd.github+json",
      authorization: `Bearer ${process.env.GH_TOKEN}`,
      "x-github-api-version": "2022-11-28",
    },
  });
  if (!response.ok) throw new Error(`${path}: HTTP ${response.status}`);
  return response.json();
}

async function collect(env) {
  const repo = `/repos/${env.GITHUB_REPOSITORY}`;
  const sha = env.GITHUB_SHA;
  const input = {
    sha,
    forceFullCi: env.FORCE_FULL_CI === "true",
    requiredJobs: JSON.parse(env.REQUIRED_CI_JOBS || "null") ?? Object.values(CI_JOBS).flat(),
  };
  if (input.forceFullCi) return input;

  input.pulls = await api(`${repo}/commits/${sha}/pulls`);
  const pr = input.pulls.find((pull) => pull.merged_at && pull.merge_commit_sha === sha);
  if (!pr) return input;

  const headSha = pr.head.sha;
  const runs = await api(
    `${repo}/actions/workflows/${CI_WORKFLOW_FILE}/runs?event=pull_request&head_sha=${headSha}&per_page=50`,
  );
  input.runs = runs.workflow_runs;
  const latest = [...input.runs]
    .filter((run) => run.head_sha === headSha)
    .sort((a, b) => Date.parse(b.created_at) - Date.parse(a.created_at))[0];
  if (latest) {
    const jobs = await api(`${repo}/actions/runs/${latest.id}/jobs?per_page=100`);
    input.jobs = jobs.jobs;
  }
  input.pushedTree = (await api(`${repo}/git/commits/${sha}`)).tree.sha;
  input.headTree = (await api(`${repo}/git/commits/${headSha}`)).tree.sha;
  return input;
}

async function main() {
  let result;
  try {
    result = evaluateGate(await collect(process.env));
  } catch (error) {
    result = refuse(`no se pudo verificar: ${error.message}`);
  }
  const lines = [`verified=${result.verified}`, `reason=${result.reason.replaceAll("\n", " ")}`];
  console.log(lines.join("\n"));
  if (process.env.GITHUB_OUTPUT) appendFileSync(process.env.GITHUB_OUTPUT, `${lines.join("\n")}\n`);
  if (process.env.GITHUB_STEP_SUMMARY) {
    appendFileSync(
      process.env.GITHUB_STEP_SUMMARY,
      `## Gate de CI\n\n- Verificado: **${result.verified}**\n- Motivo: ${result.reason}\n` +
        (result.verified ? "" : "- Se ejecuta ci.yml completo como respaldo.\n"),
    );
  }
}

if (import.meta.url === pathToFileURL(process.argv[1] ?? "").href) await main();
