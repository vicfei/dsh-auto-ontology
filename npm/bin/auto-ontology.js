#!/usr/bin/env node
// dsh-auto-ontology CLI — a JS shell spawning the bundled Python engine
// (the dsh-laya sidecar precedent, proven across the family).
//
//   auto-ontology build --docs <dir-or-glob> --domain "..." --save [--lang zh]
//   auto-ontology export ontologies/x.json > trajectory.ndjson   (the artifact as events)
//   auto-ontology --docs ... (build is the default subcommand)
import { spawnSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const argv = process.argv.slice(2);
const [cmd, ...rest] = argv;

const SUBCOMMANDS = {                // named subcommands: strip the name, route the script
  build: "build_ontology.py",
  export: "build_ontology.py",      // auto-ontology export [files...] [--from x.json] [--out f] → --trajectory
  eval: "eval_evidence.py",          // auto-ontology eval --from x.json [--n 20] [--seed 42]
  validate: "validate_format.py",    // auto-ontology validate ontologies/*.json
};
let script_file = SUBCOMMANDS[cmd] || "build_ontology.py";
let pass;
if (SUBCOMMANDS[cmd]) {
  pass = cmd === "export" ? ["--trajectory", ...rest] : rest;
} else {
  pass = argv; // bare engine args pass through verbatim (build is the default)
}

// Artifacts land in the caller's cwd (the engine reads ONTOLOGY_HOME).
const env = {
  ...process.env,
  ONTOLOGY_HOME: path.join(process.cwd(), "ontologies"),
};

const r = spawnSync("python3", [path.join(root, "scripts", script_file), ...pass], {
  stdio: "inherit",
  env,
});
process.exit(r.status ?? 1);
