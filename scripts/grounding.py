#!/usr/bin/env python3
"""grounding — the shared type-grounding judge (O5.0, issue #35)

The honest eval found that most evidence quotes *mention* an entity without
supporting its TYPE claim. This module is the ONE judge every side calls:

  build (grounding pass)   every extracted (claim, quote) is judged, batched per document
  eval                     the same prompt, one item per call
  eval --adversarial       the same prompt on labelled mention-only traps

One prompt for all three, so an adversarial result speaks for the build too.

Strictness (the contract): a quote grounds a claim iff a careful reader who
sees only the quote — plus the type definition and the name of the source
document — would conclude the claim about the named thing.

Two mechanical checks run before any LLM call. They are deterministic,
rerunnable by anyone, and need no model:

  name_in_quote  entity: the name as written appears in the quote
                 relation: at least one endpoint appears
  is_verbatim    the quote occurs in the source text (markdown marks ignored)

Both are REJECT filters only — passing them never grounds anything; the judge
still decides. Failing them means the quote cannot ground the claim as written.
"""
import json, os, re, subprocess, time

BASE = os.environ.get("DEEPSEEK_BASE_URL") or "https://api.deepseek.com"

JUDGE_SYSTEM = (
    "You audit ontology assertions against their evidence quotes. For each numbered item decide "
    "whether the QUOTE, read literally and on its own, grounds the CLAIM.\n"
    "Grounded means: a careful reader who sees only the quote would conclude that the claim is true "
    "about the named thing.\n"
    "Answer grounded=false when the quote:\n"
    "- only MENTIONS the named entity without saying what it is (no type information);\n"
    "- does not contain the entity's name as written (a different name, a translation or an alias "
    "does not count);\n"
    "- is about a different thing, or uses the type word in another sense;\n"
    "- states the claim only as a negation, a hypothetical, a plan or a question;\n"
    "- for a relation: names no endpoint, or states a different relation or the reverse direction.\n"
    "Answer grounded=true when the quote states or directly implies the claim: a definition, an "
    "apposition (\"X, a CLI tool,\"), or a predication that entails the type. For a relation, the "
    "source document is given in brackets after QUOTE: a subject that the document itself is about "
    "may be left implicit in the quote.\n"
    "Do not use outside knowledge: if the link needs a fact that is neither in the quote nor in the "
    "type definition, the claim is not grounded.\n"
    'Output JSON: {"verdicts":[{"i":1,"grounded":true,"reason":"<= 20 words"}]} - exactly one verdict '
    "per item, same numbering.")


# ── mechanical checks (pure) ────────────────────────────────────────────────

def norm(s):
    """Case/punctuation/whitespace-insensitive, script-agnostic form (same as the engine's _key)."""
    return re.sub(r"[\W_]+", "", str(s).lower())


def _plain(s):
    """Verbatim-comparison form: markdown code/emphasis marks dropped, whitespace collapsed."""
    return re.sub(r"\s+", " ", re.sub(r"[`*]", "", str(s))).strip()


def is_verbatim(quote, text):
    q = _plain(quote)
    return bool(q) and q in _plain(text)


def name_in_quote(name, quote):
    n = norm(name)
    return bool(n) and n in norm(quote)


def endpoints_in_quote(subject, obj, quote):
    return name_in_quote(subject, quote), name_in_quote(obj, quote)


# ── judge items (pure) ──────────────────────────────────────────────────────

def entity_claim(name, etype):
    return f"{name} is a {etype}."


def relation_claim(subject, predicate, obj):
    return f"{subject} {predicate} {obj}."


def item_lines(kind, claim, quote, doc, type_desc=""):
    head = f"CLAIM: {claim}"
    if type_desc:
        head += f" ({type_desc})"
    return f"{head}\n   QUOTE [{doc}]: {json.dumps(quote, ensure_ascii=False)}"


def judge_user_message(items, type_descs=None):
    """items: [{kind, claim, quote, doc, type_desc}] -> the user message of one judge call."""
    L = []
    descs = sorted({(it.get("type_name"), it.get("type_desc")) for it in items
                    if it.get("type_name") and it.get("type_desc")})
    if descs:
        L.append("Type definitions:")
        L += [f"- {n}: {d}" for n, d in descs]
        L.append("")
    L.append("Items:")
    for i, it in enumerate(items, 1):
        L.append(f"{i}. " + item_lines(it["kind"], it["claim"], it["quote"], it["doc"], it.get("type_desc", "")))
    return "\n".join(L)


def parse_verdicts(txt, n):
    """-> list of n {grounded, reason}. An item without a returned verdict counts as
    NOT grounded (conservative: silence never grounds)."""
    out = [{"grounded": False, "reason": "no verdict returned"} for _ in range(n)]
    try:
        v = json.loads(re.sub(r"^```(json)?|```$", "", txt.strip(), flags=re.M).strip())
        for x in v.get("verdicts", []):
            i = int(x.get("i", 0)) - 1
            if 0 <= i < n:
                out[i] = {"grounded": bool(x.get("grounded")), "reason": str(x.get("reason", ""))}
    except (ValueError, TypeError, AttributeError):
        pass
    return out


# ── one chat call (stdlib only) ─────────────────────────────────────────────

def api_key():
    k = os.environ.get("DEEPSEEK_API_KEY")
    if k:
        return k
    return subprocess.run(["bash", "-c", 'grep -m1 "^export DEEPSEEK_API_KEY=" ~/.bashrc | cut -d= -f2'],
                          capture_output=True, text=True).stdout.strip().strip('"')


def complete(model, messages, json_out=True, timeout=180, retries=3, account=None):
    """One chat-completion call through curl. -> (parsed JSON | text, usage).

    account(usage) is invoked for every attempt the API answered — retries
    included — so a caller's cost ledger never undercounts."""
    body = {"model": model, "temperature": 0, "messages": messages}
    if json_out:
        body["response_format"] = {"type": "json_object"}
    last = None
    for attempt in range(1, retries + 1):
        r = subprocess.run(["curl", "-s", "-m", str(timeout), f"{BASE}/chat/completions",
                            "-H", f"Authorization: Bearer {api_key()}", "-H", "Content-Type: application/json",
                            "-d", json.dumps(body)], capture_output=True, text=True)
        try:
            parsed = json.loads(r.stdout)
            if "error" in parsed:
                raise ValueError(parsed["error"].get("message", str(parsed["error"])))
            txt = parsed["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            last = exc
            time.sleep(2 * attempt)
            continue
        usage = parsed.get("usage") or {}
        if account:
            account(usage)
        try:
            return (json.loads(re.sub(r"^```(json)?|```$", "", txt.strip(), flags=re.M).strip())
                    if json_out else txt), usage
        except ValueError as exc:  # answered but unusable: paid for, so counted above, then retried
            last = exc
            time.sleep(2 * attempt)
    raise SystemExit(f"LLM call failed after {retries} attempts ({model}): {last}")


def judge(items, model="deepseek-chat", call=None):
    """Judge a batch of items with ONE call. -> list of {grounded, reason} (same order).

    call(system, user) -> parsed JSON lets the build route the request through its
    own cost guard; the prompt and the message are the same either way."""
    if not items:
        return []
    messages = [{"role": "system", "content": JUDGE_SYSTEM},
                {"role": "user", "content": judge_user_message(items)}]
    out = (call(messages[0]["content"], messages[1]["content"]) if call
           else complete(model, messages)[0])
    return parse_verdicts(json.dumps(out) if not isinstance(out, str) else out, len(items))
