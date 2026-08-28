---
name: skill-creator
description: Create new skills, modify and improve existing skills, and measure skill performance. Use when users want to create a skill from scratch, edit, or optimize an existing skill, run evals to test a skill, benchmark skill performance with variance analysis, or optimize a skill's description for better triggering accuracy.
---

# Skill Creator

A skill for creating new skills and iteratively improving them.

At a high level, the process of creating a skill goes like this:

- Decide what you want the skill to do and roughly how it should do it
- Write a draft of the skill
- Create a few test prompts and run an agent with access to the skill on them
- Help the user evaluate the results both qualitatively and quantitatively
  - While the runs happen in the background, draft some quantitative evals if there aren't any (if there are some, you can either use as is or modify if you feel something needs to change about them). Then explain them to the user (or if they already existed, explain the ones that already exist)
  - Use the `eval-viewer/generate_review.py` script to show the user the results for them to look at, and also let them look at the quantitative metrics
- Rewrite the skill based on feedback from the user's evaluation of the results (and also if there are any glaring flaws that become apparent from the quantitative benchmarks)
- Repeat until you're satisfied
- Expand the test set and try again at larger scale

Your job when using this skill is to figure out where the user is in this process and then jump in and help them progress through these stages. So for instance, maybe they're like "I want to make a skill for X". You can help narrow down what they mean, write a draft, write the test cases, figure out how they want to evaluate, run all the prompts, and repeat.

On the other hand, maybe they already have a draft of the skill. In this case you can go straight to the eval/iterate part of the loop.

Of course, you should always be flexible and if the user is like "I don't need to run a bunch of evaluations, just vibe with me", you can do that instead.

Then after the skill is done (but again, the order is flexible), you can also run the skill description improver, which we have a whole separate script for, to optimize the triggering of the skill.

Cool? Cool.

## Communicating with the user

People using the skill creator have a wide range of familiarity with coding jargon. Pay attention to context cues and match the user's technical level.

So please pay attention to context cues to understand how to phrase your communication! In the default case, just to give you some idea:

- "evaluation" and "benchmark" are borderline, but OK
- for "JSON" and "expectation" you want to see serious cues from the user that they know what those things are before using them without explaining them

It's OK to briefly explain terms if you're in doubt, and feel free to clarify terms with a short definition if you're unsure if the user will get it.

---

## Creating a skill

### Capture Intent

Start by understanding the user's intent. The current conversation might already contain a workflow the user wants to capture (e.g., they say "turn this into a skill"). If so, extract answers from the conversation history first — the tools used, the sequence of steps, corrections the user made, input/output formats observed. The user may need to fill the gaps, and should confirm before proceeding to the next step.

1. What should this skill enable the agent to do?
2. When should this skill trigger? (what user phrases/contexts)
3. What's the expected output format?
4. Should we set up test cases to verify the skill works? Skills with objectively verifiable outputs (file transforms, data extraction, code generation, fixed workflow steps) benefit from test cases. Skills with subjective outputs (writing style, art) often don't need them. Suggest the appropriate default based on the skill type, but let the user decide.

### Interview and Research

Proactively ask questions about edge cases, input/output formats, example files, success criteria, and dependencies. Wait to write test prompts until you've got this part ironed out.

Check available MCP servers and tools. If research would help (searching docs, finding similar skills, or looking up best practices), use subagents when they are available and permitted; otherwise research inline. Come prepared with context to reduce burden on the user.

### Write the SKILL.md

Based on the user interview, fill in these components:

- **name**: Skill identifier
- **description**: When to trigger and what the skill does. This is the primary triggering mechanism, so include both the capability and specific contexts for using it. Put all "when to use" guidance here, not only in the body. Front-load distinctive user intents and trigger phrases because Codex may shorten descriptions when many skills are installed. For example, instead of "Build a dashboard for company data," write "Use for dashboards, data visualizations, internal metrics, and requests to display company data, even when the user does not say 'dashboard.'"
- **compatibility**: Required tools, dependencies (optional, rarely needed)
- **the rest of the skill :)**

### Skill Writing Guide

#### Anatomy of a Skill

```
skill-name/
├── SKILL.md (required)
│   ├── YAML frontmatter (name, description required)
│   └── Markdown instructions
└── Bundled Resources (optional)
    ├── scripts/    - Executable code for deterministic/repetitive tasks
    ├── references/ - Docs loaded into context as needed
    └── assets/     - Files used in output (templates, icons, fonts)
```

#### Progressive Disclosure

Skills use a three-level loading system:
1. **Metadata** (name + description) - Always in context (~100 words)
2. **SKILL.md body** - In context whenever skill triggers (<500 lines ideal)
3. **Bundled resources** - As needed (unlimited, scripts can execute without loading)

These word counts are approximate and you can feel free to go longer if needed.

**Key patterns:**
- Keep SKILL.md under 500 lines; if you're approaching this limit, add an additional layer of hierarchy along with clear pointers about where the model using the skill should go next to follow up.
- Reference files clearly from SKILL.md with guidance on when to read them
- For large reference files (>300 lines), include a table of contents

**Domain organization**: When a skill supports multiple domains/frameworks, organize by variant:
```
cloud-deploy/
├── SKILL.md (workflow + selection)
└── references/
    ├── aws.md
    ├── gcp.md
    └── azure.md
```
The agent reads only the relevant reference file.

#### Principle of Lack of Surprise

This goes without saying, but skills must not contain malware, exploit code, or any content that could compromise system security. A skill's contents should not surprise the user in their intent if described. Don't go along with requests to create misleading skills or skills designed to facilitate unauthorized access, data exfiltration, or other malicious activities. Things like a "roleplay as an XYZ" are OK though.

#### Writing Patterns

Prefer using the imperative form in instructions.

**Defining output formats** - You can do it like this:
```markdown
## Report structure
ALWAYS use this exact template:
# [Title]
## Executive summary
## Key findings
## Recommendations
```

**Examples pattern** - It's useful to include examples. You can format them like this (but if "Input" and "Output" are in the examples you might want to deviate a little):
```markdown
## Commit message format
**Example 1:**
Input: Added user authentication with JWT tokens
Output: feat(auth): implement JWT-based authentication
```

### Writing Style

Try to explain to the model why things are important in lieu of heavy-handed musty MUSTs. Use theory of mind and try to make the skill general and not super-narrow to specific examples. Start by writing a draft and then look at it with fresh eyes and improve it.

### Test Cases

After writing the skill draft, come up with 2-3 realistic test prompts — the kind of thing a real user would actually say. Share them with the user: [you don't have to use this exact language] "Here are a few test cases I'd like to try. Do these look right, or do you want to add more?" Then run them.

Save test cases to `evals/evals.json`. Don't write expectations yet — just the prompts. You'll draft expectations in the next step while the runs are in progress.

```json
{
  "skill_name": "example-skill",
  "evals": [
    {
      "id": 1,
      "prompt": "User's task prompt",
      "expected_output": "Description of expected result",
      "files": []
    }
  ]
}
```

See `references/schemas.md` for the full schema (including the `expectations` field, which you'll add later).

## Running and evaluating test cases

Treat this section as one continuous sequence and do not stop after launching runs; carry the workflow through grading and human review.

Create the evaluation workspace once:

```bash
python <skill-creator-path>/scripts/create_eval_workspace.py \
  --skill-path <path-to-skill>
```

The printed temporary path contains an immutable `.skill-creator-workspace.json` with the workspace identity and original skill location. Preserve required artifacts before removing the workspace.

Prepare each comparison as a separate iteration:

```bash
python <skill-creator-path>/scripts/create_iteration.py <workspace> \
  --baseline <none|previous|path-to-skill> \
  --runs 3 \
  --model <model-id>
```

`create_iteration.py` only snapshots versions and prepares manifests, input copies, and run directories. It does not execute, grade, aggregate, or review anything. Use `none` when creating a new skill, `previous` to compare with the preceding candidate snapshot, or a skill path for an explicit old version.

The workspace marker stays fixed. Each `iteration-N/iteration.json` records that round's candidate snapshot, optional baseline snapshot, model, run count, configurations, and eval directories. Each eval directory contains one `eval_metadata.json` with its prompt and expectations. Runtime scripts resolve all inputs from these manifests instead of accepting duplicate configuration flags.

```text
iteration-N/
├── iteration.json
├── snapshots/
│   ├── new_skill/<skill-name>/
│   └── old_skill/<skill-name>/      # omitted for a no-skill baseline
└── eval-<id>-<name>/
    ├── eval_metadata.json
    ├── new_skill/run-1/
    └── old_skill/run-1/             # or without_skill/run-1/
```

### Step 1: Start all runs (with-skill AND baseline) together

For every eval and run number, start the candidate and baseline together:

```bash
python <skill-creator-path>/scripts/run_test_case.py <run-dir>
```

The run directory is the only argument. The wrapper validates the enclosing manifests, reads the prompt, model, installed snapshot, and protected comparison sources from them, and writes `trace.jsonl`, `outputs/final.md`, `outputs/metrics.json`, and `timing.json`. It installs a physical skill copy under the run-local `.agents/skills/` when that configuration has a skill.

The wrapper gives both sides the same isolation and output-location instructions, protects all external source and snapshot copies, discovers global copies by frontmatter skill name, and audits the trace for disclosure or use. Treat `run_status: "contaminated"` as invalid evidence; do not grade, aggregate, or compare that run.

Interleave matched pairs if parallel execution is unavailable. Do not finish every candidate run before starting baselines because time-based changes can bias the comparison.

### Step 2: While runs are in progress, draft expectations

Don't just wait for the runs to finish — use this time to review the quantitative expectations and explain them to the user. If an eval was prepared with an empty expectations list, complete that eval's `eval_metadata.json` before grading and apply the same list to every configuration in the eval.

Good expectations are objectively verifiable and have descriptive names — they should read clearly in the benchmark viewer so someone glancing at the results immediately understands what each one checks. Subjective skills (writing style, design quality) are better evaluated qualitatively — don't force expectations onto things that need human judgment.

Also update the source `evals/evals.json` so later iterations inherit the reviewed expectations. Explain what the user will see in the viewer: qualitative outputs and the quantitative benchmark.

### Step 3: As runs complete, inspect timing data

`run_test_case.py` records wall-clock duration and extracts deterministic tool, error, transcript, and token metrics from each JSONL trace automatically. As each run completes, verify that `outputs/metrics.json` reports `run_status: "completed"` and that `timing.json` contains duration and token data. Do not grade or aggregate incomplete or failed runs.

When recovering a legacy or manually produced trace, generate the same files explicitly:

```bash
python -m scripts.collect_codex_metrics \
  <run-directory>/trace.jsonl \
  --run-dir <run-directory> \
  --duration-seconds <measured-wall-clock-seconds> \
  --exit-code <codex-exit-code>
```

Token usage comes from the `turn.completed` event; tool counts come from completed item events, so started/completed pairs are not double-counted. A missing terminal event produces `run_status: "incomplete"`; a nonzero exit code produces `run_status: "failed"`. If wall-clock duration is unavailable for a legacy run, omit `--duration-seconds` rather than inventing a value.

`timing.json` looks like:

```json
{
  "total_tokens": 84852,
  "duration_ms": 23332,
  "total_duration_seconds": 23.3,
  "source": "codex-exec-jsonl"
}
```

Capture each run as it finishes so the trace, metrics, timing, configuration, and test case stay associated.

### Step 4: Grade, aggregate, and launch the viewer

Once all runs are done:

1. **Grade each run** — first use deterministic scripts for expectations that can be checked programmatically. For qualitative expectations, use the bundled grading wrapper, which applies `references/grading.schema.json`, validates the required run evidence, and writes `grading.json`:
   ```bash
   python <skill-creator-path>/scripts/run_grader.py <run-dir>
   ```
   The `grading.json` expectations array must use `text`, `passed`, and `evidence`; the viewer depends on these exact fields. `--output-schema` makes the qualitative grader stable enough to aggregate across runs, while deterministic checks remain the source of truth for commands, files, and other directly observable behavior.

2. **Aggregate into benchmark** — the aggregator requires every run declared in `iteration.json` to be completed and graded:
   ```bash
   python <skill-creator-path>/scripts/aggregate_benchmark.py \
     <workspace>/iteration-N
   ```
   This produces `benchmark.json` and `benchmark.md` with pass rate, time, and tokens for each configuration, with mean ± standard deviation and the delta. If generating benchmark.json manually, see `references/schemas.md` for the exact schema the viewer expects.
The manifest orders `new_skill` before its baseline so delta direction stays consistent.

3. **Do an analyst pass** — read the benchmark data and surface patterns the aggregate stats might hide. See `agents/analyzer.md` (the "Analyzing Benchmark Results" section) for what to look for — things like expectations that always pass regardless of skill (non-discriminating), high-variance evals (possibly flaky), and time/token tradeoffs.

4. **Generate the viewer** with both qualitative outputs and quantitative data:
   ```bash
   python <skill-creator-path>/eval-viewer/generate_review.py \
     <workspace>/iteration-N
   ```
   This writes `review.html` inside the iteration, loads `benchmark.json` when present, and includes the previous iteration recorded by the manifest. Open or present that artifact with the host's file-viewing capability. Feedback is downloaded as `feedback.json` when the user clicks "Submit All Reviews"; copy it into the iteration directory for the next round.

Note: please use generate_review.py to create the viewer; there's no need to write custom HTML.

5. **Tell the user** something like: "I've opened the review page. There are two tabs — 'Outputs' lets you click through each test case and leave feedback, 'Benchmark' shows the quantitative comparison. When you're done, come back here and let me know."

### What the user sees in the viewer

The "Outputs" tab shows one test case at a time:
- **Prompt**: the task that was given
- **Output**: the files the skill produced, rendered inline where possible
- **Previous Output** (iteration 2+): collapsed section showing last iteration's output
- **Formal Grades** (if grading was run): collapsed section showing expectation pass/fail
- **Feedback**: a textbox that auto-saves as they type
- **Previous Feedback** (iteration 2+): their comments from last time, shown below the textbox

The "Benchmark" tab shows the stats summary: pass rates, timing, and token usage for each configuration, with per-eval breakdowns and analyst observations.

Navigation is via prev/next buttons or arrow keys. When done, they click "Submit All Reviews" which saves all feedback to `feedback.json`.

### Step 5: Read the feedback

When the user tells you they're done, read `feedback.json`:

```json
{
  "reviews": [
    {"run_id": "eval-1-ocean-new_skill-run-1", "feedback": "the chart is missing axis labels", "timestamp": "..."},
    {"run_id": "eval-2-river-new_skill-run-1", "feedback": "", "timestamp": "..."},
    {"run_id": "eval-3-lake-new_skill-run-1", "feedback": "perfect, love this", "timestamp": "..."}
  ],
  "status": "complete"
}
```

Empty feedback means the user thought it was fine. Focus your improvements on the test cases where the user had specific complaints.

---

## Improving the skill

This is the heart of the loop. You've run the test cases, the user has reviewed the results, and now you need to make the skill better based on their feedback.

### How to think about improvements

1. **Generalize from the feedback.** The big picture thing that's happening here is that we're trying to create skills that can be used a million times (maybe literally, maybe even more who knows) across many different prompts. Here you and the user are iterating on only a few examples over and over again because it helps move faster. The user knows these examples in and out and it's quick for them to assess new outputs. But if the skill you and the user are codeveloping works only for those examples, it's useless. Rather than put in fiddly overfitty changes, or oppressively constrictive MUSTs, if there's some stubborn issue, you might try branching out and using different metaphors, or recommending different patterns of working. It's relatively cheap to try and maybe you'll land on something great.

2. **Keep the prompt lean.** Remove things that aren't pulling their weight. Make sure to read the transcripts, not just the final outputs — if it looks like the skill is making the model waste a bunch of time doing things that are unproductive, you can try getting rid of the parts of the skill that are making it do that and seeing what happens.

3. **Explain the why.** Try hard to explain the **why** behind everything you're asking the model to do. Today's LLMs are *smart*. They have good theory of mind and when given a good harness can go beyond rote instructions and really make things happen. Even if the feedback from the user is terse or frustrated, try to actually understand the task and why the user is writing what they wrote, and what they actually wrote, and then transmit this understanding into the instructions. If you find yourself writing ALWAYS or NEVER in all caps, or using super rigid structures, that's a yellow flag — if possible, reframe and explain the reasoning so that the model understands why the thing you're asking for is important. That's a more humane, powerful, and effective approach.

4. **Look for repeated work across test cases.** Read the transcripts from the test runs and notice if the subagents all independently wrote similar helper scripts or took the same multi-step approach to something. If all 3 test cases resulted in the subagent writing a `create_docx.py` or a `build_chart.py`, that's a strong signal the skill should bundle that script. Write it once, put it in `scripts/`, and tell the skill to use it. This saves every future invocation from reinventing the wheel.

This task is pretty important (we are trying to create billions a year in economic value here!) and your thinking time is not the blocker; take your time and really mull things over. I'd suggest writing a draft revision and then looking at it anew and making improvements. Really do your best to get into the head of the user and understand what they want and need.

### The iteration loop

After improving the skill:

1. Apply your improvements to the skill
2. Run `create_iteration.py` to prepare `iteration-<N+1>/`, using `none`, `previous`, or an explicit baseline path as appropriate, then execute and grade every declared run.
3. Aggregate the new iteration and regenerate `review.html`; the manifest links the previous iteration automatically.
4. Wait for the user to review and tell you they're done
5. Read the new feedback, improve again, repeat

Keep going until:
- The user says they're happy
- The feedback is all empty (everything looks good)
- You're not making meaningful progress

---

## Advanced: Blind comparison

For situations where you want a more rigorous comparison between two versions of a skill (e.g., the user asks "is the new version actually better?"), there's a blind comparison system. Read `agents/comparator.md` and `agents/analyzer.md` for the details. The basic idea is: give two outputs to an independent agent without telling it which is which, and let it judge quality. Then analyze why the winner won.

This is optional, requires subagents, and most users won't need it. The human review loop is usually sufficient.

---

## Description Optimization

The description field in SKILL.md frontmatter is the primary mechanism that determines whether Codex loads a skill. After creating or improving a skill, offer to optimize the description for better triggering accuracy.

### Step 1: Generate trigger eval queries

Create 20 eval queries — a mix of should-trigger and should-not-trigger. Save as JSON:

```json
[
  {"query": "the user prompt", "should_trigger": true},
  {"query": "another prompt", "should_trigger": false}
]
```

The queries must be realistic and resemble what a Codex user would actually type. Avoid abstract requests; use concrete details such as file paths, job context, column names and values, company names, and URLs. Include a mix of lengths, casual phrasing, abbreviations, typos, and edge cases rather than making every query clear-cut. The user will review the set before it runs.

Bad: `"Format this data"`, `"Extract text from PDF"`, `"Create a chart"`

Good: `"ok so my boss just sent me this xlsx file (its in my downloads, called something like 'Q4 sales final FINAL v2.xlsx') and she wants me to add a column that shows the profit margin as a percentage. The revenue is in column C and costs are in column D i think"`

For the **should-trigger** queries (8-10), think about coverage. You want different phrasings of the same intent — some formal, some casual. Include cases where the user doesn't explicitly name the skill or file type but clearly needs it. Throw in some uncommon use cases and cases where this skill competes with another but should win.

For the **should-not-trigger** queries (8-10), the most valuable ones are the near-misses — queries that share keywords or concepts with the skill but actually need something different. Think adjacent domains, ambiguous phrasing where a naive keyword match would trigger but shouldn't, and cases where the query touches on something the skill does but in a context where another tool is more appropriate.

The key thing to avoid: don't make should-not-trigger queries obviously irrelevant. "Write a fibonacci function" as a negative test for a PDF skill is too easy — it doesn't test anything. The negative cases should be genuinely tricky.

### Step 2: Review with user

Present the eval set to the user for review using the HTML template:

1. Read the template from `assets/eval_review.html`
2. Replace the placeholders:
   - `__EVAL_DATA_PLACEHOLDER__` → the JSON array of eval items (no quotes around it — it's a JS variable assignment)
   - `__SKILL_NAME_PLACEHOLDER__` → the skill's name
   - `__SKILL_DESCRIPTION_PLACEHOLDER__` → the skill's current description
3. Write to a temporary HTML file and open or present it with the host's browser/file-viewing capability. On macOS CLI, `open /tmp/eval_review_<skill-name>.html` is one option.
4. The user can edit queries, toggle should-trigger, add/remove entries, then click "Export Eval Set"
5. The browser downloads `eval_set.json`. Locate the most recently downloaded copy in the browser's configured download directory in case multiple versions exist.

This step matters — bad eval queries lead to bad descriptions.

### Step 3: Run the optimization loop

Tell the user: "This will take some time — I'll run the optimization loop in the background and check on it periodically."

Save the eval set to the workspace, then run in the background:

```bash
python -m scripts.run_loop \
  --eval-set <path-to-trigger-eval.json> \
  --skill-path <path-to-skill> \
  --model <model-id-powering-this-session> \
  --max-iterations 5 \
  --verbose
```

Use the model ID from your system prompt (the one powering the current session) so the triggering test matches what the user actually experiences.

While it runs, periodically tail the output to give the user updates on which iteration it's on and what the scores look like.

This handles the full optimization loop automatically. It uses a stratified 60% train / 40% held-out split when each polarity has enough examples, keeping singleton classes in training instead of creating an empty train set. It evaluates each query three times through `codex exec`, asks Codex to improve the description, and returns `best_description`, selected by test score when a holdout exists.

### How skill triggering works

Understanding the triggering mechanism helps design better eval queries. Codex starts with compact skill metadata containing each skill's name, description, and path, then loads SKILL.md when the task appears to match. Simple one-step queries such as "read this PDF" may not load a skill when built-in tools already handle the request. Complex, multi-step, or specialized queries are better trigger tests.

Make eval queries substantive enough that the agent would benefit from the skill. Simple queries such as "read file X" are poor trigger tests regardless of description quality.

### Step 4: Apply the result

Take `best_description` from the JSON output and update the skill's SKILL.md frontmatter. Show the user before/after and report the scores.

### Package and present

When the user wants an installable artifact, package the skill and present the resulting `.skill` file using the host's file-sharing capability:

```bash
python -m scripts.package_skill <path/to/skill-folder>
```

After packaging, direct the user to the resulting `.skill` file path so they can install it.

## Codex environment guidance

The core workflow is the same in Codex CLI, the IDE extension, and the desktop app: draft → test → review → improve → repeat. Adapt the mechanics to the capabilities exposed by the current host.

**Skill location**: Repository skills belong under `.agents/skills/<skill-name>/`. Codex scans `.agents/skills` from the current working directory up to the repository root.

**Running test cases**: Use separate `run_test_case.py <run-dir>` processes for the prepared runs. Subagents may orchestrate those processes when available and permitted; otherwise interleave matched pairs.

**Headless review**: `generate_review.py <iteration-dir>` always writes a static `review.html`; present or link that artifact through the host. If HTML cannot be shown, present each prompt, output, and grade directly in the conversation and collect feedback inline.

**Description optimization**: `run_loop.py` and `run_eval.py` require the `codex` CLI. They create an isolated temporary `.agents/skills` fixture for each query and invoke `codex exec --ephemeral`. If `codex` is unavailable, skip automated trigger optimization and improve the description from the reviewed eval set manually.

**Updating an existing skill**:
- Preserve the original directory name and `name` frontmatter unless the user explicitly requests a rename.
- If the installed skill is read-only, copy it to a temporary writable directory, edit and validate the copy, then package or return it under the original name.
- Keep snapshots and generated eval workspaces outside the source skill directory so they are not packaged accidentally.

---

## Reference files

The agents/ directory contains instructions for specialized subagents. Read them when you need to spawn the relevant subagent.

- `agents/grader.md` — How to evaluate expectations against outputs
- `agents/comparator.md` — How to do blind A/B comparison between two outputs
- `agents/analyzer.md` — How to analyze why one version beat another

The references/ directory has additional documentation:
- `references/schemas.md` — JSON structures for evals.json, grading.json, etc.
- `references/grading.schema.json` — Structured-output schema for rubric grading with `codex exec --output-schema`
- `references/description.schema.json` — Structured-output schema used by the description optimizer

The scripts/ directory also includes:
- `scripts/codex_exec.py` — Shared Codex command and environment helpers used internally by workflow scripts
- `scripts/collect_codex_metrics.py` — Convert `codex exec --json` traces into deterministic metrics and timing files
- `scripts/create_eval_workspace.py` — Create and validate an isolated temporary evaluation workspace
- `scripts/create_iteration.py` — Snapshot candidate and baseline versions and prepare the iteration manifest and run directories
- `scripts/eval_manifest.py` — Shared internal manifest validation and run-context resolution
- `scripts/run_test_case.py` — Run one full skill test case and capture all standard artifacts
- `scripts/run_grader.py` — Grade one completed run with a schema-constrained Codex call
- `scripts/aggregate_benchmark.py` — Aggregate every completed, graded run declared by one iteration
- `eval-viewer/generate_review.py` — Generate one iteration's static review page

---

Repeating one more time the core loop here for emphasis:

- Figure out what the skill is about
- Draft or edit the skill
- Run an agent with access to the skill on test prompts
- With the user, evaluate the outputs:
  - Create benchmark.json and run `eval-viewer/generate_review.py` to help the user review them
  - Run quantitative evals
- Repeat until you and the user are satisfied
- Package the final skill and return it to the user.

Add the major workflow steps to the host's plan or task list when one is available. Include "Create evals JSON and run `eval-viewer/generate_review.py` so the user can review test cases" whenever the task includes evaluation.

Good luck!
