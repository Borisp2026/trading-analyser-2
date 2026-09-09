# Pipeline scheduling

## The problem

Every pipeline runs on GitHub Actions `schedule:` (cron) triggers. GitHub treats
these as **best-effort** — under load it silently drops most sub-hourly runs, and
it deprioritises repos that aren't paid or heavily starred. With several frequent
crons competing, delivery got bad enough that on 2026-09-08→09 the whole system
went ~26 h with no run at all.

## What was done in-repo (2026-09-09)

- **Consolidated** the old `agent_scan.yml` (`*/5`) + `intraday.yml` (`0,30`) into
  one `market_pulse.yml` on a single `*/15` cron. One schedule instead of three →
  GitHub honours it far more often.
- `ai_assessment.yml` stays separate and hourly — it spends `ANTHROPIC_API_KEY`
  per run, so it must not go into a 15-min loop.
- All market-hours crons now use the correct window: `0-6,13-23 UTC` (ASX Sydney
  time + NASDAQ, both DST states). The old windows were Perth AWST by mistake.

Remaining workflows and their schedules:

| Workflow          | Cron (UTC)              | Purpose                         |
|-------------------|------------------------|---------------------------------|
| `market_pulse`    | `*/15 0-6,13-23 * * 1-5` | agent scan + intraday + prices |
| `ai_assessment`   | `0 0-6,13-23 * * 1-5`   | hourly Claude position read     |
| `nightly`         | `0 10 * * 1-5`          | full analyser + dashboard build |
| `asx_deep_scan`   | `0 8 * * 6`             | weekly 1800-stock scan          |

## Making it actually reliable: external cron

GitHub's scheduler can't be trusted for anything time-sensitive. The fix is to
trigger the workflows from **outside** GitHub. Every workflow above already has
`workflow_dispatch:`, so an external cron service can start them on a real
schedule.

### 1. Create a fine-grained PAT

github.com → Settings → Developer settings → **Fine-grained personal access
tokens** → Generate new token.

- Repository access: **only** `Borisp2026/trading-analyser-2`
- Permissions → Repository → **Actions: Read and write**
- Expiration: 1 year (set a calendar reminder to rotate)

Copy the token (starts `github_pat_…`).

### 2. Point a free cron service at the dispatch endpoint

[cron-job.org](https://cron-job.org) (free) or any equivalent. Create one job per
workflow you want driven externally — at minimum `market_pulse`:

- **URL:** `https://api.github.com/repos/Borisp2026/trading-analyser-2/actions/workflows/market_pulse.yml/dispatches`
- **Method:** `POST`
- **Headers:**
  - `Authorization: Bearer github_pat_…`
  - `Accept: application/vnd.github+json`
  - `Content-Type: application/json`
- **Body:** `{"ref":"main"}`
- **Schedule:** every 15 min, Mon–Fri, 00:00–06:00 and 13:00–23:00 UTC

Repeat for `ai_assessment.yml` (hourly) and `nightly.yml` (once at 10:00 UTC
Mon–Fri) if you want those externally driven too.

A `204 No Content` response means the run was queued. The GitHub cron stays in
place as a fallback; the external cron just fills the gaps.
