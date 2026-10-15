// Change detection for ci.yml, codeql.yml and deploy-qa.yml (issue #627).
//
// Only git and Node are used: no third-party action decides what runs. Every
// rule fails safe: an unknown path, an empty diff or a range git cannot
// resolve means "everything changed".
//
// CLI:
//   node scripts/ci/detect-changes.mjs ci      -> backend, frontend, docker, workflows, docs_only
//   node scripts/ci/detect-changes.mjs deploy  -> backend_build, frontend_build, run_migrations,
//                                                 required_ci_jobs (plus the ci areas)
// Outputs go to $GITHUB_OUTPUT and a short explanation to $GITHUB_STEP_SUMMARY.

import { execFileSync } from "node:child_process";
import { appendFileSync } from "node:fs";
import { pathToFileURL } from "node:url";

const ZERO_SHA = /^0+$/;

// Changes here alter how CI itself behaves, so they run everything.
const workflowPaths = [/^\.github\//, /^scripts\/ci\//];

// Documentation: never read by tests or images that matter for behaviour.
const docsPaths = [/^docs\//, /\.md$/i, /^LICENSE$/];

// Paths no CI job in ci.yml exercises. They are covered elsewhere
// (pr-validation tests scripts/github) or are not built by CI (terraform).
const neutralPaths = [
  /^scripts\/github\//,
  /^scripts\/quality\//,
  /^infra\/terraform\//,
  /^Makefile$/,
  /^\.gitignore$/,
  /^\.gitattributes$/,
  /^\.editorconfig$/,
  /^\.prettierignore$/,
  /^\.pre-commit-config\.yaml$/,
  /^\.secrets\.baseline$/,
];

const backendPaths = [
  /^backend\//,
  // BACKUP_SCRIPTS_DIR points at scripts/backup and backend tests exercise it.
  /^scripts\/backup\//,
  /^scripts\/wait-for-postgres\.sh$/,
  /^pyproject\.toml$/,
];

const frontendPaths = [/^frontend\//];

const dockerPaths = [
  /(^|\/)Dockerfile[^/]*$/,
  /(^|\/)\.dockerignore$/,
  /^(docker-)?compose[^/]*\.ya?ml$/,
  /^docker\//,
  /^backend\/requirements\//,
  /^backend\/docker-entrypoint\.sh$/,
  /^frontend\/package(-lock)?\.json$/,
  /^\.env\.example$/,
  /^infra\/runtime\//,
];

// Inputs of each Dockerfile.cloud target.
const backendImagePaths = [
  /^Dockerfile\.cloud$/,
  /^\.dockerignore$/,
  /^backend\//,
  /^scripts\/backup\//,
];
const frontendImagePaths = [
  /^Dockerfile\.cloud$/,
  /^\.dockerignore$/,
  /^frontend\//,
  /^infra\/runtime\//,
];
const migrationPaths = [/^backend\/apps\/[^/]+\/migrations\//];

// Changing the deploy pipeline itself rebuilds and migrates, like a first deploy.
const deployPipelinePaths = [/^\.github\/workflows\/deploy-qa\.yml$/, /^scripts\/ci\//];

export const CI_JOBS = {
  backend: ["backend-lint", "backend-tests", "backend-security"],
  frontend: ["frontend-lint", "frontend-tests", "frontend-build"],
  docker: ["docker-integration"],
};

const matches = (patterns, file) => patterns.some((pattern) => pattern.test(file));

function normalize(files) {
  return files.map((file) => file.trim().replaceAll("\\", "/")).filter(Boolean);
}

/** Everything flagged: used for forced runs and whenever the diff is unknown. */
export function allCiAreas(reason) {
  return { backend: true, frontend: true, docker: true, workflows: true, docs_only: false, reason };
}

/**
 * Effective CI areas for a list of changed paths. `backend`, `frontend` and
 * `docker` already include the "workflows changed -> everything" rule, so a
 * job only has to look at its own flag.
 */
export function classifyCiChanges(rawFiles) {
  const files = normalize(rawFiles);
  if (files.length === 0) return allCiAreas("diff vacío o desconocido");

  const areas = { backend: false, frontend: false, docker: false, workflows: false };
  const unknown = [];
  let docsOnly = true;

  for (const file of files) {
    if (matches(workflowPaths, file)) {
      areas.workflows = true;
      docsOnly = false;
      continue;
    }
    // Documentation inside backend/ or frontend/ is still documentation.
    if (matches(docsPaths, file)) continue;
    docsOnly = false;
    let known = matches(neutralPaths, file);
    if (matches(backendPaths, file)) areas.backend = known = true;
    if (matches(frontendPaths, file)) areas.frontend = known = true;
    if (matches(dockerPaths, file)) areas.docker = known = true;
    if (!known) unknown.push(file);
  }

  if (areas.workflows) return allCiAreas("cambió .github/ o scripts/ci/");
  if (unknown.length) {
    return allCiAreas(`ruta sin clasificar: ${unknown.slice(0, 5).join(", ")}`);
  }
  return {
    ...areas,
    docs_only: docsOnly,
    reason: docsOnly ? "solo documentación" : "diff clasificado por área",
  };
}

/** Jobs of ci.yml that must have run (not been skipped) for these areas. */
export function requiredCiJobs(areas) {
  const jobs = [];
  if (areas.backend) jobs.push(...CI_JOBS.backend);
  if (areas.frontend) jobs.push(...CI_JOBS.frontend);
  if (areas.backend || areas.docker) jobs.push(...CI_JOBS.docker);
  return jobs;
}

/** What deploy-qa.yml must rebuild or run since the commit currently deployed. */
export function classifyDeployChanges(rawFiles, { forceMigrations = false } = {}) {
  const files = normalize(rawFiles);
  const pipelineChanged = files.some((file) => matches(deployPipelinePaths, file));
  const backendBuild = pipelineChanged || files.some((file) => matches(backendImagePaths, file));
  const frontendBuild = pipelineChanged || files.some((file) => matches(frontendImagePaths, file));
  const migrationsChanged = files.some((file) => matches(migrationPaths, file));
  return {
    backend_build: backendBuild,
    frontend_build: frontendBuild,
    run_migrations: forceMigrations || pipelineChanged || migrationsChanged,
    reason: pipelineChanged ? "cambió el pipeline de despliegue" : "diff desde el SHA desplegado",
  };
}

/** Full deploy plan when the deployed commit cannot be determined. */
export function fullDeployPlan(reason) {
  return { backend_build: true, frontend_build: true, run_migrations: true, reason };
}

/**
 * Which range to diff for a CI run, or `null` to run everything.
 * `fullRun` is the workflow_call input: a called ci.yml always runs fully.
 */
export function resolveCiRange({ eventName, baseSha, headSha, beforeSha, afterSha, fullRun, diffBase }) {
  if (fullRun === "true") return { range: null, reason: "workflow_call: suite completa" };
  if (eventName === "pull_request" && baseSha && headSha) {
    return { range: `${baseSha}...${headSha}`, reason: "pull_request: base...head" };
  }
  if (eventName === "push" && afterSha) {
    if (!beforeSha || ZERO_SHA.test(beforeSha)) {
      return { range: null, reason: "push sin commit previo: suite completa" };
    }
    return { range: `${beforeSha}..${afterSha}`, reason: "push: before..after" };
  }
  if (eventName === "workflow_dispatch" && diffBase && headSha) {
    return { range: `${diffBase}...${headSha}`, reason: "workflow_dispatch con diff_base" };
  }
  return { range: null, reason: `${eventName || "evento desconocido"}: suite completa` };
}

function gitChangedFiles(range) {
  const output = execFileSync("git", ["diff", "--name-only", "--no-renames", range], {
    encoding: "utf8",
    stdio: ["ignore", "pipe", "pipe"],
  });
  return output.split("\n").filter(Boolean);
}

function changedFilesOrNull(range) {
  try {
    return gitChangedFiles(range);
  } catch (error) {
    console.log(`::warning::git diff ${range} falló (${error.message.split("\n")[0]}); se asume todo cambiado.`);
    return null;
  }
}

function writeOutputs(values) {
  const lines = Object.entries(values).map(([key, value]) => `${key}=${value}`);
  console.log(lines.join("\n"));
  if (process.env.GITHUB_OUTPUT) appendFileSync(process.env.GITHUB_OUTPUT, `${lines.join("\n")}\n`);
}

function writeSummary(markdown) {
  if (process.env.GITHUB_STEP_SUMMARY) appendFileSync(process.env.GITHUB_STEP_SUMMARY, `${markdown}\n`);
}

function runCi(env) {
  const { range, reason: rangeReason } = resolveCiRange({
    eventName: env.EVENT_NAME,
    baseSha: env.BASE_SHA,
    headSha: env.HEAD_SHA,
    beforeSha: env.BEFORE_SHA,
    afterSha: env.AFTER_SHA,
    fullRun: env.FULL_RUN,
    diffBase: env.DIFF_BASE,
  });
  const files = range ? changedFilesOrNull(range) : null;
  const areas = files ? classifyCiChanges(files) : allCiAreas(rangeReason);
  writeOutputs({
    backend: areas.backend,
    frontend: areas.frontend,
    docker: areas.docker,
    workflows: areas.workflows,
    docs_only: areas.docs_only,
  });
  writeSummary(
    [
      "## Detección de cambios",
      "",
      `- Rango: \`${range ?? "ninguno"}\` (${rangeReason})`,
      `- Archivos: ${files ? files.length : "n/a"}`,
      `- Decisión: ${areas.reason}`,
      `- backend=${areas.backend} frontend=${areas.frontend} docker=${areas.docker} workflows=${areas.workflows} docs_only=${areas.docs_only}`,
    ].join("\n"),
  );
}

function runDeploy(env) {
  const deployed = (env.DEPLOYED_SHA || "").trim();
  const head = env.HEAD_SHA;
  const forceMigrations = env.FORCE_MIGRATIONS === "true";
  let files = null;
  let why = "";
  if (!/^[0-9a-f]{40}$/.test(deployed)) {
    why = "no se pudo determinar el SHA desplegado";
  } else {
    files = changedFilesOrNull(`${deployed}..${head}`);
    if (!files) why = `el SHA desplegado ${deployed} no está en el historial`;
  }
  const plan = files ? classifyDeployChanges(files, { forceMigrations }) : fullDeployPlan(why);
  const areas = files ? classifyCiChanges(files) : allCiAreas(why);
  writeOutputs({
    backend_build: plan.backend_build,
    frontend_build: plan.frontend_build,
    run_migrations: plan.run_migrations,
    plan_reason: plan.reason,
    ci_reason: areas.reason,
    required_ci_jobs: JSON.stringify(requiredCiJobs(areas)),
  });
}

if (import.meta.url === pathToFileURL(process.argv[1] ?? "").href) {
  const mode = process.argv[2];
  if (mode === "ci") runCi(process.env);
  else if (mode === "deploy") runDeploy(process.env);
  else {
    console.error("uso: detect-changes.mjs ci|deploy");
    process.exit(2);
  }
}
