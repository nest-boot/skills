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
- for "JSON" and "assertion" you want to see serious cues from the user that they know what those things are before using them without explaining them

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

Save test cases to `evals/evals.json`. Don't write assertions yet — just the prompts. You'll draft assertions in the next step while the runs are in progress.

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

See `references/schemas.md` for the full schema (including the `assertions` field, which you'll add later).

## Running and evaluating test cases

Treat this section as one continuous sequence and do not stop after launching runs; carry the workflow through grading and human review.

Put results in `<skill-name>-workspace/` as a sibling to the skill directory. Within the workspace, organize results by iteration (`iteration-1/`, `iteration-2/`, etc.) and within that, each test case gets a directory (`eval-0/`, `eval-1/`, etc.). Don't create all of this upfront — just create directories as you go.

### Step 1: Start all runs (with-skill AND baseline) together

For each test case, start two isolated Codex CLI runs together — one with the skill and one baseline. Subagents may orchestrate these commands in parallel when the host permits, but `codex exec --json` is the executor so every run produces the same trace format. If parallel execution is unavailable, interleave the pairs; do not finish every with-skill run before starting baselines because time-based changes can bias the comparison.

Each configuration contains `run-<R>/`, even when there is only one run. Use a fresh absolute run directory as the Codex working root, place input files there, and tell the prompt to save deliverables under `outputs/`. Use absolute paths in CLI arguments so `-C` cannot change where artifacts land.

**With-skill run:**

```bash
# Copy the exact skill version being evaluated into the isolated Codex root.
mkdir -p <absolute-run-directory>/.agents/skills <absolute-run-directory>/outputs
cp -R <path-to-skill> <absolute-run-directory>/.agents/skills/<skill-name>

codex exec --ephemeral --sandbox workspace-write --skip-git-repo-check \
  --json --model <model-id> \
  -C <absolute-run-directory> \
  -o <absolute-run-directory>/outputs/final.md \
  "<eval prompt>. Save requested deliverables under outputs/." \
  > <absolute-run-directory>/trace.jsonl
codex_exit_code=$?  # Record this process's status before another command runs.
```

**Baseline run** (same prompt, but the baseline depends on context):
- **Creating a new skill**: leave `.agents/skills/<skill-name>` absent, then run the same `codex exec` command in `without_skill/run-<R>/`.
- **Improving an existing skill**: snapshot the old version before editing, copy that snapshot into the baseline run's `.agents/skills/<skill-name>/`, and run the same command in `old_skill/run-<R>/`.

Keep the model, prompt, input files, sandbox, and run count identical between the paired configurations. The only intended difference is the skill version present under `.agents/skills`.

Write an `eval_metadata.json` for each test case (assertions can be empty for now). Give each eval a descriptive name based on what it's testing — not just "eval-0". Use this name for the directory too. If this iteration uses new or modified eval prompts, create these files for each new eval directory — don't assume they carry over from previous iterations.

```json
{
  "eval_id": 0,
  "eval_name": "descriptive-name-here",
  "prompt": "The user's task prompt",
  "assertions": []
}
```

### Step 2: While runs are in progress, draft assertions

Don't just wait for the runs to finish — you can use this time productively. Draft quantitative assertions for each test case and explain them to the user. If assertions already exist in `evals/evals.json`, review them and explain what they check.

Good assertions are objectively verifiable and have descriptive names — they should read clearly in the benchmark viewer so someone glancing at the results immediately understands what each one checks. Subjective skills (writing style, design quality) are better evaluated qualitatively — don't force assertions onto things that need human judgment.

Update the `eval_metadata.json` files and `evals/evals.json` with the assertions once drafted. Also explain to the user what they'll see in the viewer — both the qualitative outputs and the quantitative benchmark.

### Step 3: As runs complete, capture timing data

Record wall-clock duration around every `codex exec` process. Then extract deterministic tool, error, transcript, and token metrics from its JSONL trace:

```bash
python -m scripts.collect_codex_metrics \
  <run-directory>/trace.jsonl \
  --run-dir <run-directory> \
  --duration-seconds <measured-wall-clock-seconds> \
  --exit-code "$codex_exit_code"
```

This writes `outputs/metrics.json` and `timing.json`. Token usage comes from the `turn.completed` event; tool counts come from completed item events, so started/completed pairs are not double-counted. A missing terminal event produces `run_status: "incomplete"`; a nonzero exit code produces `run_status: "failed"`. Do not grade or aggregate either status. If wall-clock duration is unavailable, omit `--duration-seconds` rather than inventing a value.

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

1. **Grade each run** — first use deterministic scripts for assertions that can be checked programmatically. For qualitative assertions, use an isolated grader agent that reads `agents/grader.md` and evaluates the transcript and outputs. With Codex CLI, prefer rubric-based structured grading:
   ```bash
   codex exec --ephemeral --sandbox read-only --skip-git-repo-check \
     -C <absolute-run-directory> \
     --output-schema <skill-creator-path>/references/grading.schema.json \
     -o <absolute-run-directory>/grading.json \
     "Read <skill-creator-path>/agents/grader.md. Grade only this run using expectations from <absolute-eval-metadata-path>, the Codex trace at <absolute-run-directory>/trace.jsonl, the final response at <absolute-run-directory>/outputs/final.md, and deliverables under <absolute-run-directory>/outputs/. Return the rubric result."
   ```
   The `grading.json` expectations array must use `text`, `passed`, and `evidence`; the viewer depends on these exact fields. `--output-schema` makes the qualitative grader stable enough to aggregate across runs, while deterministic checks remain the source of truth for commands, files, and other directly observable behavior.

2. **Aggregate into benchmark** — run the aggregation script from the skill-creator directory:
   ```bash
   python -m scripts.aggregate_benchmark <workspace>/iteration-N --skill-name <name>
   ```
   This produces `benchmark.json` and `benchmark.md` with pass_rate, time, and tokens for each configuration, with mean ± stddev and the delta. If generating benchmark.json manually, see `references/schemas.md` for the exact schema the viewer expects.
Put each with_skill version before its baseline counterpart.

3. **Do an analyst pass** — read the benchmark data and surface patterns the aggregate stats might hide. See `agents/analyzer.md` (the "Analyzing Benchmark Results" section) for what to look for — things like assertions that always pass regardless of skill (non-discriminating), high-variance evals (possibly flaky), and time/token tradeoffs.

4. **Launch the viewer** with both qualitative outputs and quantitative data:
   ```bash
   nohup python <skill-creator-path>/eval-viewer/generate_review.py \
     <workspace>/iteration-N \
     --skill-name "my-skill" \
     --benchmark <workspace>/iteration-N/benchmark.json \
     > /dev/null 2>&1 &
   VIEWER_PID=$!
   ```
   For iteration 2+, also pass `--previous-workspace <workspace>/iteration-<N-1>`.

   **Headless or remote environments:** If `webbrowser.open()` is unavailable or the environment has no display, use `--static <output_path>` to write a standalone HTML file instead of starting a server. Open or present that artifact with the host's file-viewing capability. Feedback is downloaded as `feedback.json` when the user clicks "Submit All Reviews"; copy it into the workspace directory for the next iteration.

Note: please use generate_review.py to create the viewer; there's no need to write custom HTML.

5. **Tell the user** something like: "I've opened the results in your browser. There are two tabs — 'Outputs' lets you click through each test case and leave feedback, 'Benchmark' shows the quantitative comparison. When you're done, come back here and let me know."

### What the user sees in the viewer

The "Outputs" tab shows one test case at a time:
- **Prompt**: the task that was given
- **Output**: the files the skill produced, rendered inline where possible
- **Previous Output** (iteration 2+): collapsed section showing last iteration's output
- **Formal Grades** (if grading was run): collapsed section showing assertion pass/fail
- **Feedback**: a textbox that auto-saves as they type
- **Previous Feedback** (iteration 2+): their comments from last time, shown below the textbox

The "Benchmark" tab shows the stats summary: pass rates, timing, and token usage for each configuration, with per-eval breakdowns and analyst observations.

Navigation is via prev/next buttons or arrow keys. When done, they click "Submit All Reviews" which saves all feedback to `feedback.json`.

### Step 5: Read the feedback

When the user tells you they're done, read `feedback.json`:

```json
{
  "reviews": [
    {"run_id": "eval-0-with_skill", "feedback": "the chart is missing axis labels", "timestamp": "..."},
    {"run_id": "eval-1-with_skill", "feedback": "", "timestamp": "..."},
    {"run_id": "eval-2-with_skill", "feedback": "perfect, love this", "timestamp": "..."}
  ],
  "status": "complete"
}
```

Empty feedback means the user thought it was fine. Focus your improvements on the test cases where the user had specific complaints.

Kill the viewer server when you're done with it:

```bash
kill $VIEWER_PID 2>/dev/null
```

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
2. Rerun all test cases into a new `iteration-<N+1>/` directory, including baseline runs. If you're creating a new skill, the baseline is always `without_skill` (no skill) — that stays the same across iterations. If you're improving an existing skill, use your judgment on what makes sense as the baseline: the original version the user came in with, or the previous iteration.
3. Launch the reviewer with `--previous-workspace` pointing at the previous iteration
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

**Skill location**: Repository skills belong under `.agents/skills/<skill-name>/`. Codex scans `.agents/skills` from the current working directory up to the repository root. A personal skill can live under `$HOME/.agents/skills/`, but do not write there unless the user asked for a personal installation.

**Running test cases**: Prefer isolated subagents when available and permitted. Otherwise use separate `codex exec` processes. If neither is possible, execute the prompts one at a time and disclose that the comparison is less independent.

**Headless review**: Generate the viewer with `--static <output_path>`, then present or link the HTML artifact through the host. If even static HTML cannot be shown, present each prompt, output, and grade directly in the conversation and collect feedback inline.

**Description optimization**: `run_loop.py` and `run_eval.py` require the `codex` CLI. They create an isolated temporary `.agents/skills` fixture for each query and invoke `codex exec --ephemeral`, reusing existing Codex authentication. If `codex` is unavailable, skip automated trigger optimization and improve the description from the reviewed eval set manually.

**Updating an existing skill**:
- Preserve the original directory name and `name` frontmatter unless the user explicitly requests a rename.
- If the installed skill is read-only, copy it to a temporary writable directory, edit and validate the copy, then package or return it under the original name.
- Keep snapshots and generated eval workspaces outside the source skill directory so they are not packaged accidentally.

---

## Reference files

The agents/ directory contains instructions for specialized subagents. Read them when you need to spawn the relevant subagent.

- `agents/grader.md` — How to evaluate assertions against outputs
- `agents/comparator.md` — How to do blind A/B comparison between two outputs
- `agents/analyzer.md` — How to analyze why one version beat another

The references/ directory has additional documentation:
- `references/schemas.md` — JSON structures for evals.json, grading.json, etc.
- `references/grading.schema.json` — Structured-output schema for rubric grading with `codex exec --output-schema`
- `references/description.schema.json` — Structured-output schema used by the description optimizer

The scripts/ directory also includes:
- `scripts/collect_codex_metrics.py` — Convert `codex exec --json` traces into deterministic metrics and timing files

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
