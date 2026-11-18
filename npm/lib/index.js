/**
 * dsh-auto-ontology host plugin (0.2.0, issue #11): the ontology engine as typed tools.
 *
 * Registers two agent tools on `ctx.tools` via @deepseek-ai/dsh-tools:
 *   ontology_build  — two-pass build over a document corpus (evidence on every
 *                     assertion, type guard, coref, append-only merge)
 *   ontology_query  — every assertion about a term, with its evidence spans
 *
 * The tools spawn the bundled Python engine; artifacts land under the calling
 * process's cwd (./ontologies/), exactly like the CLI.
 */
import { spawnSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineTool } from "@deepseek-ai/dsh-tools";

export const name = "auto-ontology";
export const inject = ["tools"];

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

function run(args, timeoutMs = 600_000) {
  const env = { ...process.env,
                ONTOLOGY_HOME: path.join(process.cwd(), "ontologies") };
  const r = spawnSync("python3", [path.join(ROOT, "scripts", "build_ontology.py"), ...args],
                      { encoding: "utf8", timeout: timeoutMs, env, maxBuffer: 16 * 1024 * 1024 });
  if (r.error) throw new Error(`build_ontology: ${r.error.message}`);
  if (r.status !== 0) throw new Error(`build_ontology exited ${r.status}: ${(r.stderr || "").slice(-400)}`);
  return (r.stdout || "").trim();
}

const LANG = { type: "string", enum: ["en", "zh"], description: "Output language (default en)." };

export async function apply(ctx) {
  ctx.tools.register(defineTool({
    name: "ontology_build",
    description:
      "Build an ontology from a document corpus: a TBox schema from sampled docs, then per-document " +
      "ABox assertions where EVERY entity and relation carries a verbatim evidence quote (no evidence, " +
      "no assertion; unknown types are flagged, never silently dropped). Conservative coreference merges " +
      "certain mentions (aliases recorded); append-only --merge folds new docs into an existing ontology " +
      "without touching prior evidence; the same name under different types becomes a conflict entry " +
      "holding both evidences. Artifacts: typed JSON (+ evidence), SVG cluster graph, markdown digest " +
      "under ./ontologies/. Takes ~10s + ~2s per document.",
    parameters: {
      docs: { type: "string", required: true, description: "Document directory or glob, e.g. 'docs/*.md'." },
      domain: { type: "string", required: true, description: "Corpus domain description for the schema pass." },
      merge: { type: "string", description: "Existing ontology JSON to fold into (append-only), e.g. ontologies/xxx.json." },
      sample: { type: "number", description: "Docs sampled for the schema pass (default 4)." },
      max_calls: { type: "number", description: "Cost guard: abort beyond this many LLM calls." },
      lang: LANG,
    },
    output: {
      schema: { type: "object", additionalProperties: false,
                properties: { summary: { type: "string", required: true } } },
      render: (_args, value) => [{ type: "text", text: value.summary }],
    },
    execute(args) {
      const extra = ["--save",
        ...(args.merge ? ["--merge", args.merge] : []),
        ...(args.sample ? ["--sample", String(args.sample)] : []),
        ...(args.max_calls ? ["--max-calls", String(args.max_calls)] : []),
        ...(args.lang ? ["--lang", args.lang] : [])];
      return { summary: run(["--docs", args.docs, "--domain", args.domain, ...extra]) };
    },
  }));

  ctx.tools.register(defineTool({
    name: "ontology_query",
    description:
      "Query the newest ontology (or a given one): every entity and relation touching a term — by name, " +
      "alias, or relation endpoint — each with ALL of its evidence spans (verbatim quotes + source docs). " +
      "The audit surface of the evidence-linked ontology.",
    parameters: {
      term: { type: "string", required: true, description: "Entity name, alias, or relation endpoint." },
      from: { type: "string", description: "Ontology JSON path (default: newest under ./ontologies/)." },
    },
    output: {
      schema: { type: "object", additionalProperties: false,
                properties: { result: { type: "string", required: true } } },
      render: (_args, value) => [{ type: "text", text: value.result }],
    },
    execute(args) {
      return { result: run(["--query", args.term, ...(args.from ? ["--from", args.from] : [])], 60_000) };
    },
  }));
}
