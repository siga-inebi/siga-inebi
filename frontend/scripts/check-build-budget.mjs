import { gzipSync } from "node:zlib";
import { readdir, readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import path from "node:path";

export const DEFAULT_BUDGETS = Object.freeze({
  initialGzip: 230_000,
  routeIncrementGzip: 20_000,
  coldPageGzip: 250_000,
  rasterRaw: 25_000,
});

function outputFilesFor(manifest, key, visited = new Set()) {
  if (visited.has(key)) return new Set();
  visited.add(key);

  const chunk = manifest[key];
  if (!chunk) throw new Error(`Manifest references missing chunk: ${key}`);

  const files = new Set([
    chunk.file,
    ...(chunk.css ?? []),
    ...(chunk.assets ?? []),
  ]);
  for (const importedKey of chunk.imports ?? []) {
    for (const file of outputFilesFor(manifest, importedKey, visited)) {
      files.add(file);
    }
  }
  return files;
}

function reachableDynamicEntries(manifest, entryKeys) {
  const dynamicKeys = new Set();
  const visited = new Set();

  function visit(key) {
    if (visited.has(key)) return;
    visited.add(key);
    const chunk = manifest[key];
    if (!chunk) throw new Error(`Manifest references missing chunk: ${key}`);
    for (const importedKey of chunk.imports ?? []) visit(importedKey);
    for (const dynamicKey of chunk.dynamicImports ?? []) {
      dynamicKeys.add(dynamicKey);
      visit(dynamicKey);
    }
  }

  entryKeys.forEach(visit);
  return dynamicKeys;
}

function total(files, resources, field) {
  return [...files].reduce((sum, file) => {
    const size = resources[file];
    if (!size)
      throw new Error(`Build output is missing manifest resource: ${file}`);
    return sum + size[field];
  }, 0);
}

export function evaluateBuildBudget(
  manifest,
  resources,
  budgets = DEFAULT_BUDGETS
) {
  const entryKeys = Object.keys(manifest).filter(
    (key) => manifest[key].isEntry
  );
  if (entryKeys.length === 0)
    throw new Error("Vite manifest has no entry chunk");

  const initialFiles = new Set(resources["index.html"] ? ["index.html"] : []);
  for (const key of entryKeys) {
    for (const file of outputFilesFor(manifest, key)) initialFiles.add(file);
  }

  const initialRaw = total(initialFiles, resources, "raw");
  const initialGzip = total(initialFiles, resources, "gzip");
  const routes = [...reachableDynamicEntries(manifest, entryKeys)]
    .map((key) => {
      const files = outputFilesFor(manifest, key);
      const incrementFiles = new Set(
        [...files].filter((file) => !initialFiles.has(file))
      );
      const incrementRaw = total(incrementFiles, resources, "raw");
      const incrementGzip = total(incrementFiles, resources, "gzip");
      return {
        key,
        incrementRaw,
        incrementGzip,
        coldPageRaw: initialRaw + incrementRaw,
        coldPageGzip: initialGzip + incrementGzip,
      };
    })
    .sort((left, right) => right.incrementGzip - left.incrementGzip);

  const rasters = Object.entries(resources)
    .filter(([file]) => /\.(?:avif|jpe?g|png|webp)$/i.test(file))
    .map(([file, size]) => ({ file, raw: size.raw }))
    .sort((left, right) => right.raw - left.raw);

  const violations = [];
  if (initialGzip > budgets.initialGzip) {
    violations.push(
      `initial static: ${initialGzip} gzip bytes exceeds ${budgets.initialGzip}`
    );
  }
  for (const route of routes) {
    if (route.incrementGzip > budgets.routeIncrementGzip) {
      violations.push(
        `route ${route.key}: ${route.incrementGzip} incremental gzip bytes exceeds ${budgets.routeIncrementGzip}`
      );
    }
    if (route.coldPageGzip > budgets.coldPageGzip) {
      violations.push(
        `cold page ${route.key}: ${route.coldPageGzip} gzip bytes exceeds ${budgets.coldPageGzip}`
      );
    }
  }
  for (const raster of rasters) {
    if (raster.raw > budgets.rasterRaw) {
      violations.push(
        `raster ${raster.file}: ${raster.raw} raw bytes exceeds ${budgets.rasterRaw}`
      );
    }
  }

  return { initialRaw, initialGzip, routes, rasters, violations };
}

export function formatBudgetReport(result, budgets = DEFAULT_BUDGETS) {
  const largestRoute = result.routes[0];
  const largestRaster = result.rasters[0];
  const lines = [
    `Initial static: ${result.initialRaw} raw, ${result.initialGzip}/${budgets.initialGzip} gzip bytes`,
    largestRoute
      ? `Largest route increment: ${largestRoute.key} ${largestRoute.incrementRaw} raw, ${largestRoute.incrementGzip}/${budgets.routeIncrementGzip} gzip bytes`
      : "Largest route increment: none",
    largestRoute
      ? `Largest cold page: ${largestRoute.key} ${largestRoute.coldPageRaw} raw, ${largestRoute.coldPageGzip}/${budgets.coldPageGzip} gzip bytes`
      : `Largest cold page: ${result.initialRaw} raw, ${result.initialGzip}/${budgets.coldPageGzip} gzip bytes`,
    largestRaster
      ? `Largest raster: ${largestRaster.file} ${largestRaster.raw}/${budgets.rasterRaw} raw bytes`
      : "Largest raster: none",
  ];
  if (result.violations.length > 0) {
    lines.push(
      "Budget violations:",
      ...result.violations.map((item) => `- ${item}`)
    );
  }
  return lines.join("\n");
}

async function resourceSizes(distDirectory) {
  const resources = {};

  async function visit(relativeDirectory = "") {
    const directory = path.join(distDirectory, relativeDirectory);
    for (const entry of await readdir(directory, { withFileTypes: true })) {
      const relativePath = path.posix.join(relativeDirectory, entry.name);
      if (relativePath.startsWith(".vite")) continue;
      if (entry.isDirectory()) {
        await visit(relativePath);
      } else {
        const content = await readFile(path.join(distDirectory, relativePath));
        resources[relativePath] = {
          raw: content.byteLength,
          gzip: gzipSync(content).byteLength,
        };
      }
    }
  }

  await visit();
  return resources;
}

async function main() {
  const frontendDirectory = path.resolve(
    path.dirname(fileURLToPath(import.meta.url)),
    ".."
  );
  const distDirectory = path.join(frontendDirectory, "dist");
  const manifest = JSON.parse(
    await readFile(path.join(distDirectory, ".vite", "manifest.json"), "utf8")
  );
  const result = evaluateBuildBudget(
    manifest,
    await resourceSizes(distDirectory)
  );
  process.stdout.write(`${formatBudgetReport(result)}\n`);
  if (result.violations.length > 0) process.exitCode = 1;
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  main().catch((error) => {
    console.error(`Unable to check frontend build budget: ${error.message}`);
    process.exitCode = 1;
  });
}
