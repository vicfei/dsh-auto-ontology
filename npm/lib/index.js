/**
 * dsh-auto-ontology host plugin (issue #11; `kb` since issue #56): the ontology engine as typed tools.
 *
 * Registers three agent tools on `ctx.tools` via @deepseek-ai/dsh-tools:
 *   ontology_build  — two-pass build over a document corpus, or over the chunks of
 *                     a WeKnora knowledge base (evidence on every assertion, type
 *                     guard, coref, append-only merge; a kb build names each
 *                     quote's chunk)
 *   ontology_query  — every assertion about a term, with its evidence spans
 *   ontology_export — the artifact as an ao-trajectory/0.1 event stream (the
 *                     record format dsh-EvoOntology's adapter consumes)
 *
 * The tools spawn the bundled Python engine; artifacts land under the calling
 * process's cwd (./ontologies/), exactly like the CLI.
 */
import { spawnSync } from "node:child_process";
import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";
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
const KB_DEFAULT_LIMIT = 40;   // chunks a typed-tool build reads from a knowledge base unless told otherwise

function newest() {   // the engine's own default: the newest artifact under ./ontologies/
  const dir = path.join(process.cwd(), "ontologies");
  const files = existsSync(dir) ? readdirSync(dir).filter((f) => f.endsWith(".json")) : [];
  if (!files.length) throw new Error(`no ontology artifact under ${dir} — ontology_build writes one`);
  const byAge = (a, b) => statSync(path.join(dir, b)).mtimeMs - statSync(path.join(dir, a)).mtimeMs;
  return path.join(dir, files.sort(byAge)[0]);
}

export async function apply(ctx) {
  ctx.tools.register(defineTool({
    name: "ontology_build",
    description:
      "Build an ontology from a document corpus, or from a WeKnora knowledge base: a TBox schema from " +
      "sampled documents, then ABox assertions per document (per chunk for a knowledge base) where EVERY " +
      "entity and relation carries a verbatim evidence quote (no evidence, no assertion; unknown types are " +
      "flagged, never silently dropped). Conservative coreference merges certain mentions (aliases " +
      "recorded); append-only merge folds new docs into an existing ontology without touching prior " +
      "evidence; the same name under different types becomes a conflict entry holding both evidences. " +
      "Pass `kb` (a knowledge-base id) to read the base's parsed chunks instead of files: each quote then " +
      "carries the id of the chunk it was read from, so every assertion can be traced back into the base. " +
      "Artifacts: typed JSON (+ evidence), SVG cluster graph, markdown digest under ./ontologies/. " +
      "Takes about 10 seconds per document or chunk — the grounding judge is one call per quote.",
    parameters: {
      docs: { type: "string", description: "Document directory or glob, e.g. 'docs/*.md'. Required unless kb is given." },
      kb: { type: "string", description: "WeKnora knowledge-base id to build from instead of docs (its parsed text chunks, one chunk = one document). Needs WEKNORA_URL / WEKNORA_API_KEY in the environment." },
      limit: { type: "number", description: "With kb: read at most this many chunks, in reading order (default 40). Raise it to read more of the base." },
      domain: { type: "string", required: true, description: "Corpus domain description for the schema pass." },
      merge: { type: "string", description: "Existing ontology JSON to fold into (append-only), e.g. ontologies/xxx.json." },
      sample: { type: "number", description: "Documents sampled for the schema pass (default 4)." },
      max_calls: { type: "number", description: "Cost guard: abort beyond this many LLM calls." },
      lang: LANG,
    },
    output: {
      schema: { type: "object", additionalProperties: false,
                properties: { summary: { type: "string", required: true } } },
      render: (_args, value) => [{ type: "text", text: value.summary }],
    },
    execute(args) {
      if (!args.docs && !args.kb) throw new Error("ontology_build needs docs (a document corpus) or kb (a WeKnora knowledge-base id)");
      if (args.docs && args.kb) throw new Error("ontology_build takes docs or kb, not both: one source per build");
      // the typed tool reads a bounded slice unless told otherwise; a whole base can run for an hour
      const source = args.kb
        ? ["--kb", args.kb, "--limit", String(args.limit ?? KB_DEFAULT_LIMIT)]
        : ["--docs", args.docs];
      const extra = ["--save",
        ...(args.merge ? ["--merge", args.merge] : []),
        ...(args.sample ? ["--sample", String(args.sample)] : []),
        ...(args.max_calls ? ["--max-calls", String(args.max_calls)] : []),
        ...(args.lang ? ["--lang", args.lang] : [])];
      return { summary: run([...source, "--domain", args.domain, ...extra], args.kb ? 1_800_000 : 600_000) };
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

  ctx.tools.register(defineTool({
    name: "ontology_export",
    description:
      "Export an ontology artifact as its event stream (ao-trajectory/0.1, newline JSON): one event per evidence " +
      "quote with the judge's verdict, every certification (who issued it, the note, the evidence), the build, " +
      "merges, conflicts and the type guard's catches. Deterministic and idempotent by event id — the record " +
      "format dsh-EvoOntology's adapter consumes. Writes a .ndjson file and returns the tally plus the first events.",
    parameters: {
      from: { type: "string", description: "Ontology JSON path (default: newest under ./ontologies/)." },
      out: { type: "string", description: "Output path (default: <artifact>.trajectory.ndjson)." },
      limit: { type: "number", description: "Events returned inline after the tally (default 5)." },
    },
    output: {
      schema: { type: "object", additionalProperties: false,
                properties: { summary: { type: "string", required: true } } },
      render: (_args, value) => [{ type: "text", text: value.summary }],
    },
    execute(args) {
      const from = args.from || newest();
      const out = args.out || from.replace(/\.json$/i, "") + ".trajectory.ndjson";
      const head = run(["--trajectory", "--from", from, "--out", out], 120_000);
      const lines = readFileSync(out, "utf8").split("\n").filter(Boolean);
      const n = Math.max(0, Math.min(args.limit ?? 5, lines.length));
      return { summary: [head, ...lines.slice(0, n)].join("\n") };
    },
  }));
}
