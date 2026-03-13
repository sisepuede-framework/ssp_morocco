# Claude Code Reference for SISEPUEDE Calibration

Features you should be using for complex multi-session calibration work.

---

## 1. Hooks — Automate Deterministic Actions

Shell commands that fire at lifecycle points. Unlike CLAUDE.md (advisory), hooks always execute.

**Configure in:** `~/.claude/settings.json` (global) or `.claude/settings.json` (project)

### Auto-run tests after code changes
```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Bash",
        "hooks": [{
          "type": "command",
          "command": "jq -r '.tool_input.command' | grep -q 'run_calibration0.py' && echo 'Checking NemoMod status...' || true"
        }]
      }
    ]
  }
}
```

### Block edits to protected files
```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [{
          "type": "command",
          "command": "jq -r '.tool_input.file_path // empty' | grep -q 'sisepuede/' && echo 'BLOCKED: sisepuede/ is read-only' >&2 && exit 2 || exit 0"
        }]
      }
    ]
  }
}
```

### Log all calibration runs
```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Bash",
        "hooks": [{
          "type": "command",
          "command": "echo \"$(date '+%Y-%m-%d %H:%M:%S') - $(jq -r '.tool_input.command' | head -c 100)\" >> ~/.claude/calibration-runs.log"
        }]
      }
    ]
  }
}
```

**Hook events:** `SessionStart`, `PreToolUse`, `PostToolUse`, `PostToolUseFailure`, `Stop`

---

## 2. Custom Agents — Specialized Workers

Create `.claude/agents/diagnostic-runner.md`:
```markdown
---
name: diagnostic-runner
description: Run diagnostics, parse diff_report, identify top 3 failing sectors
tools: Bash, Read, Grep, Glob
model: sonnet
---

Run compare_to_inventory.py, parse diff_report.csv, identify top 3 errors.
For each, trace to input parameters. Return structured diagnosis.
```

Invoke: `Use the diagnostic-runner agent on the latest model output`

### Agent options
- `tools`: Restrict which tools the agent can use
- `model`: `sonnet`, `opus`, `haiku`
- `isolation: worktree`: Run in separate git worktree
- `maxTurns`: Limit iterations to prevent runaway

---

## 3. Context Management

### CLAUDE.md (loaded every session, <200 lines)
Static rules, pipeline reference, common fixes table. Keep ruthlessly short.

### MEMORY.md (auto-generated, persists across sessions)
First 200 lines loaded automatically. Claude writes learned patterns here.
- `/memory` to view/edit
- `autoMemoryEnabled: false` in settings to disable

### /compact (strategic context pruning)
```
/compact Switching from ENTC to Waste calibration. Keep diff_report outputs and calibration_log changes.
```
Use between unrelated tasks. Claude re-injects CLAUDE.md + MEMORY.md after compaction.

### /clear (full reset)
Use between completely unrelated workstreams.

---

## 4. Background Tasks

### Ctrl+B — background a running command
Press during a Bash tool call. Returns task ID. Claude keeps working on other things.

### /loop — recurring checks
```
/loop 5m check if model finished: grep OPTIMAL ssp_run_output/calibration_*/emissions_table_baseline.csv
```
Polls every 5 minutes. Auto-expires after 3 days.

### run_in_background parameter
```python
# In Agent or Bash tool calls
{"run_in_background": true}
```

---

## 5. Worktrees — Isolated Parallel Experiments

```bash
claude --worktree calibration-livestock-alt
```
Gets own copy of files at `.claude/worktrees/<name>/`. Separate branch. Perfect for testing alternative calibration strategies without affecting main.

In agents: `isolation: worktree` runs the agent in a separate worktree.

---

## 6. Key Slash Commands

| Command | Purpose |
|---------|---------|
| `/memory` | View/edit CLAUDE.md + auto memory |
| `/compact <note>` | Force context compaction with focus hint |
| `/clear` | Reset context for unrelated task |
| `/cost` | Show token usage this session |
| `/model opus` | Switch model mid-session |
| `/loop <interval> <prompt>` | Recurring background check |
| `/rename <name>` | Name session for later resume |
| `/resume` | Switch to previous session |
| `/simplify` | Code review for quality + efficiency |
| `/debug` | Enable debug logging |

### Keyboard shortcuts
| Key | Action |
|-----|--------|
| `Esc` | Stop Claude mid-response |
| `Esc Esc` | Rewind menu (restore previous state) |
| `Ctrl+B` | Background current task |
| `Ctrl+G` | Edit prompt in $EDITOR |
| `Shift+Tab` | Cycle permission modes |

---

## 7. Permission Modes

| Mode | Behavior | When |
|------|----------|------|
| `default` | Prompt for writes/Bash | Normal work |
| `acceptEdits` | Auto-approve file edits | Fast iteration |
| `plan` | Read-only | Research before implementation |

```bash
# Fast calibration iteration
claude --permission-mode acceptEdits

# Safe research
claude --permission-mode plan
```

### Permission rules in settings
```json
{
  "permissions": {
    "rules": {
      "allow": [
        "Bash(python.*apply_step.*\\.py)",
        "Bash(python.*run_calibration.*\\.py)",
        "Read", "Glob", "Grep"
      ],
      "deny": [
        "Bash(rm -rf|git reset --hard)",
        "Write(sisepuede/)"
      ]
    }
  }
}
```

---

## 8. Path-Specific Rules

Create `.claude/rules/calibration.md`:
```markdown
---
paths:
  - "ssp_modeling/notebooks/apply_step*.py"
  - "ssp_modeling/notebooks/run_calibration*.py"
---

Every parameter change MUST have a source citation.
Check external_data/ files BEFORE web search.
Verify fraction group sums after every change.
```

Auto-loads when Claude opens matching files.

---

## 9. Custom Skills

Create `.claude/skills/run-calibration/SKILL.md`:
```markdown
---
name: run-calibration
description: Run full calibration pipeline with diagnostics
---

1. Run apply_step0_verified.py
2. Run apply_step1_calibration.py
3. Run run_calibration0.py --baseline-only
4. Run compare_to_inventory.py
5. Parse diff_report.csv
6. Log results
```

Invoke: `/run-calibration`

---

## 10. What You Should Have Been Using

Based on your SISEPUEDE workflow:

| Task you did | Feature you should use | Time saved |
|---|---|---|
| Re-reading CLAUDE.md every session | It auto-loads. Keep it <200 lines. | ~5 min/session |
| Waiting for model runs | `Ctrl+B` to background, keep working | ~5 min/run |
| Launching 7 expert agents manually | Custom agents in `.claude/agents/` | ~2 min/launch |
| Checking model status repeatedly | `/loop 5m check model status` | ~1 min/check |
| Re-verifying after code changes | PostToolUse hook runs tests automatically | ~3 min/change |
| Protecting sisepuede/ from edits | PreToolUse hook blocks writes | Prevents errors |
| Context running out mid-calibration | `/compact` between sectors | Prevents restarts |
| Testing alternative parameters | `--worktree` for isolated experiments | Clean separation |
| Repeating pipeline commands | Custom `/run-calibration` skill | ~1 min/run |
| Setting up permissions each time | `settings.json` with allow/deny rules | ~30 sec/session |
