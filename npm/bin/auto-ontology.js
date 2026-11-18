#!/usr/bin/env node
// dsh-auto-ontology CLI — a JS shell spawning the bundled Python engine
// (the dsh-laya sidecar precedent, proven across the family).
//
//   auto-ontology build --docs <dir-or-glob> --domain "..." --save [--lang zh]
//   auto-ontology --docs ... (build is the default subcommand)
import { spawnSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const argv = process.argv.slice(2);
const [cmd, ...rest] = argv;

let script_file = "build_ontology.py";
if (cmd === "eval") {
  script_file = "eval_evidence.py";   // auto-ontology eval --from x.json [--n 20] [--seed 42]
}
let pass;
if (cmd === "build") {
  pass = rest;
} else {
  pass = argv; // engine args pass through verbatim (build is the default)
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
