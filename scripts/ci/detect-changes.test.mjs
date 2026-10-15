import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

import {
  classifyCiChanges,
  classifyDeployChanges,
  requiredCiJobs,
  resolveCiRange,
} from "./detect-changes.mjs";

const pick = ({ backend, frontend, docker, workflows, docs_only }) => ({
  backend,
  frontend,
  docker,
  workflows,
  docs_only,
});

test("a docs-only change runs no Python, frontend or Docker job", () => {
  const areas = classifyCiChanges([
    "README.md",
    "docs/qa/informe.md",
    "docs/architecture/diagram.png",
    "backend/README.md",
    "frontend/docs/notas.md",
  ]);
  assert.deepEqual(pick(areas), {
    backend: false,
    frontend: false,
    docker: false,
    workflows: false,
    docs_only: true,
  });
  assert.deepEqual(requiredCiJobs(areas), []);
});

test("a frontend-only change runs only the frontend jobs", () => {
  const areas = classifyCiChanges(["frontend/src/app/main.jsx", "docs/qa/notas.md"]);
  assert.deepEqual(pick(areas), {
    backend: false,
    frontend: true,
    docker: false,
    workflows: false,
    docs_only: false,
  });
  assert.deepEqual(requiredCiJobs(areas), ["frontend-lint", "frontend-tests", "frontend-build"]);
});

test("frontend dependency manifests also exercise the Docker stack", () => {
  const areas = classifyCiChanges(["frontend/package.json", "frontend/package-lock.json"]);
  assert.equal(areas.frontend, true);
  assert.equal(areas.docker, true);
  assert.equal(areas.backend, false);
});

test("a backend-only change runs backend jobs and docker-integration", () => {
  const areas = classifyCiChanges(["backend/apps/attendance/services.py"]);
  assert.deepEqual(pick(areas), {
    backend: true,
    frontend: false,
    docker: false,
    workflows: false,
    docs_only: false,
  });
  assert.deepEqual(requiredCiJobs(areas), [
    "backend-lint",
    "backend-tests",
    "backend-security",
    "docker-integration",
  ]);
});

test("backup scripts and requirements count as backend", () => {
  assert.equal(classifyCiChanges(["scripts/backup/backup-db.sh"]).backend, true);
  const requirements = classifyCiChanges(["backend/requirements/dev.txt"]);
  assert.equal(requirements.backend, true);
  assert.equal(requirements.docker, true);
});

test("Dockerfiles and compose files are docker changes", () => {
  for (const file of ["Dockerfile.cloud", "compose.yml", "compose.override.yml", "docker/README.txt"]) {
    const areas = classifyCiChanges([file]);
    assert.equal(areas.docker, true, file);
    assert.equal(areas.frontend, false, file);
  }
  assert.equal(classifyCiChanges(["backend/Dockerfile"]).backend, true);
});

test("a workflow or CI script change runs everything", () => {
  for (const file of [".github/workflows/ci.yml", ".github/labeler.yml", "scripts/ci/detect-changes.mjs"]) {
    assert.deepEqual(
      pick(classifyCiChanges(["docs/x.md", file])),
      { backend: true, frontend: true, docker: true, workflows: true, docs_only: false },
      file,
    );
  }
});

test("unknown paths and empty diffs fail safe to everything", () => {
  assert.equal(classifyCiChanges(["some/new/tool.py"]).backend, true);
  assert.equal(classifyCiChanges(["package-lock.json"]).frontend, true);
  assert.equal(classifyCiChanges([]).backend, true);
});

test("neutral paths are not heavy work", () => {
  const areas = classifyCiChanges(["scripts/github/pr-body-policy.mjs", "infra/terraform/main.tf"]);
  assert.deepEqual(requiredCiJobs(areas), []);
  assert.equal(areas.docs_only, false);
});

test("deploy plan: migrations only when a migrations directory changed", () => {
  assert.deepEqual(classifyDeployChanges(["backend/apps/academics/services.py"]), {
    backend_build: true,
    frontend_build: false,
    run_migrations: false,
    reason: "diff desde el SHA desplegado",
  });
  const withMigration = classifyDeployChanges(["backend/apps/academics/migrations/0042_x.py"]);
  assert.equal(withMigration.run_migrations, true);
  assert.equal(withMigration.backend_build, true);
  assert.equal(classifyDeployChanges(["README.md"], { forceMigrations: true }).run_migrations, true);
});

test("deploy plan: frontend image inputs include nginx runtime and Dockerfile.cloud", () => {
  assert.equal(classifyDeployChanges(["infra/runtime/nginx.conf"]).frontend_build, true);
  assert.equal(classifyDeployChanges(["infra/runtime/nginx.conf"]).backend_build, false);
  const dockerfile = classifyDeployChanges(["Dockerfile.cloud"]);
  assert.equal(dockerfile.backend_build && dockerfile.frontend_build, true);
  assert.deepEqual(classifyDeployChanges(["docs/qa/a.md", "README.md"]), {
    backend_build: false,
    frontend_build: false,
    run_migrations: false,
    reason: "diff desde el SHA desplegado",
  });
});

test("deploy plan: changing the pipeline rebuilds and migrates", () => {
  const plan = classifyDeployChanges([".github/workflows/deploy-qa.yml"]);
  assert.equal(plan.backend_build && plan.frontend_build && plan.run_migrations, true);
});

test("diff range per event", () => {
  assert.equal(
    resolveCiRange({ eventName: "pull_request", baseSha: "a", headSha: "b" }).range,
    "a...b",
  );
  assert.equal(resolveCiRange({ eventName: "push", beforeSha: "a", afterSha: "b" }).range, "a..b");
  assert.equal(resolveCiRange({ eventName: "push", beforeSha: "0".repeat(40), afterSha: "b" }).range, null);
  assert.equal(resolveCiRange({ eventName: "workflow_dispatch", headSha: "b" }).range, null);
  assert.equal(
    resolveCiRange({ eventName: "workflow_dispatch", headSha: "b", diffBase: "a" }).range,
    "a...b",
  );
  // A called ci.yml sees the caller's event (push), but always runs fully.
  assert.equal(
    resolveCiRange({ eventName: "push", beforeSha: "a", afterSha: "b", fullRun: "true" }).range,
    null,
  );
});

test("CLI computes outputs from a real git diff", () => {
  const script = join(dirname(fileURLToPath(import.meta.url)), "detect-changes.mjs");
  const repo = mkdtempSync(join(tmpdir(), "detect-changes-"));
  const git = (...args) => execFileSync("git", args, { cwd: repo, encoding: "utf8" }).trim();
  const write = (file, text) => {
    mkdirSync(dirname(join(repo, file)), { recursive: true });
    writeFileSync(join(repo, file), text);
  };
  const run = (mode, env) => {
    const output = join(repo, "..", `${repo.split("/").at(-1)}-out`);
    writeFileSync(output, "");
    execFileSync("node", [script, mode], {
      cwd: repo,
      env: { ...process.env, ...env, GITHUB_OUTPUT: output, GITHUB_STEP_SUMMARY: "" },
      stdio: "ignore",
    });
    const values = Object.fromEntries(
      readFileSync(output, "utf8").trim().split("\n").map((line) => line.split(/=(.*)/s).slice(0, 2)),
    );
    rmSync(output);
    return values;
  };
  try {
    git("init", "-q", "-b", "develop");
    git("config", "user.email", "ci@example.invalid");
    git("config", "user.name", "ci");
    write("backend/apps/a/models.py", "x = 1\n");
    write("frontend/src/main.jsx", "export {};\n");
    git("add", ".");
    git("commit", "-qm", "base");
    const base = git("rev-parse", "HEAD");

    write("docs/a.md", "# docs\n");
    git("add", ".");
    git("commit", "-qm", "docs");
    const docs = git("rev-parse", "HEAD");
    const docsOut = run("ci", { EVENT_NAME: "pull_request", BASE_SHA: base, HEAD_SHA: docs });
    assert.equal(docsOut.docs_only, "true");
    assert.equal(docsOut.backend, "false");
    assert.equal(docsOut.frontend, "false");

    write("backend/apps/a/migrations/0002_x.py", "y = 2\n");
    git("add", ".");
    git("commit", "-qm", "migration");
    const migration = git("rev-parse", "HEAD");
    const pushOut = run("ci", { EVENT_NAME: "push", BEFORE_SHA: docs, AFTER_SHA: migration });
    assert.equal(pushOut.backend, "true");
    assert.equal(pushOut.frontend, "false");

    const deployOut = run("deploy", { DEPLOYED_SHA: docs, HEAD_SHA: migration });
    assert.equal(deployOut.run_migrations, "true");
    assert.equal(deployOut.frontend_build, "false");
    assert.equal(deployOut.backend_build, "true");

    const docsDeploy = run("deploy", { DEPLOYED_SHA: base, HEAD_SHA: docs });
    assert.equal(docsDeploy.backend_build, "false");
    assert.equal(docsDeploy.run_migrations, "false");
    assert.equal(docsDeploy.required_ci_jobs, "[]");

    const unknown = run("deploy", { DEPLOYED_SHA: "", HEAD_SHA: migration });
    assert.equal(unknown.backend_build, "true");
    assert.equal(unknown.frontend_build, "true");
    assert.equal(unknown.run_migrations, "true");

    const missing = run("deploy", { DEPLOYED_SHA: "f".repeat(40), HEAD_SHA: migration });
    assert.equal(missing.frontend_build, "true");

    const calledOut = run("ci", {
      EVENT_NAME: "push",
      BEFORE_SHA: base,
      AFTER_SHA: docs,
      FULL_RUN: "true",
    });
    assert.equal(calledOut.backend, "true");
  } finally {
    rmSync(repo, { recursive: true, force: true });
  }
});
