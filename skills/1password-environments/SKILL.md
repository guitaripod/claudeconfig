---
name: 1password-environments
description: >-
  Manages secrets in 1Password Developer Environments via the local 1Password
  MCP server. Use when the user asks to import or mount a .env file, list or
  create an Environment, view or add environment variables, store or rotate an
  API key, token, or credential, or move plaintext secrets out of a repo.
---

# 1Password Environments

Workflow for the 1Password MCP tools registered as the `1password` server. Read
this skill before calling those tools — the server's built-in docs cover tool
basics but omit import-and-mount steps. Conceptual background, setup and mount
problems: [reference.md](reference.md).

## Tool naming

The server exposes `authenticate`, `list_environments`, `list_variables`,
`create_environment`, `rename_environment`, `append_variables`,
`create_local_env_file`, `list_local_env_files`. Each client prefixes them —
opencode `1password_<tool>`, Claude Code `mcp__1password__<tool>` — so match on
the tool suffix and read each schema before invoking.

Request params use **camelCase** (`accountId`, `environmentId`); responses may use
snake_case (`account_id`, `environment_id`). Pass every required param.

`create_local_env_file` needs `mountPath` as the **absolute** path of the source
`.env`. The first call touching an Environment may prompt for approval in the
1Password app.

If calls fail with authentication errors, call `authenticate`, then retry using
the returned account ID as `accountId`.

## Not done until

**Import / create from `.env`** (including "using values from the project `.env`"):

- [ ] Environment created or resolved
- [ ] Variables appended via `append_variables`
- [ ] `create_local_env_file` at the **source** `.env` absolute path — **always**
- [ ] Mount verified with `list_local_env_files`

Mounting at the source `.env` path is mandatory, not optional follow-up. The
**only** exception is the user explicitly opting out ("without mounting", "do not
mount", "skip the mount"). Never ask "want me to mount?" — just mount.

Stopping after `create_environment` + `append_variables` is **incomplete**.
`list_variables` is not mount verification. Do not report success until the mount
checklist is done.

**Mount only:** mount exists at the requested path (`list_local_env_files`).

## Do not

- Skip `create_local_env_file` on import unless the user explicitly opted out
- Report success before the import checklist (including mount) is complete
- Offer mounting as optional follow-up — it is mandatory on import
- Call `create_environment` when `list_environments` already shows that name — ask the user first
- Reveal secret values in chat, code, commits or logs
- Read a mounted `.env` path — once mounted, the path is a live FIFO (named pipe); use `list_variables` instead
- Verify a mount with **any** shell check (`test -f`, `test -p`, `find -type f`, etc.). Use `list_local_env_files` — it is the only check that reflects both file state and whether the mount is *enabled* in 1Password. A disabled mount leaves the FIFO on disk, so `test -p` succeeds even though the mount is off

## Getting started (open-ended request)

Secrets live in 1Password; the `.env` path becomes a live FIFO that 1Password
feeds on demand, and their tooling reads `.env` as before. Don't paste the
prerequisites into chat.

Check state before asking anything: `authenticate` (fastest real prerequisite
check), `list_environments`, then look for a `.env` with Read or Glob, never Bash.

| State | Go to |
|-------|-------|
| `.env` with real values | **Import from a `.env` file** — the common case |
| Only `.env.example` / `.env.template` | **Import**, but ask for values; use the template's keys |
| No `.env`, no Environments | **Create new Environment** → `append_variables` → mount at `{workspace_root}/.env` |
| Environment exists, no mount | **Mount existing Environment** |

Ask one question at a time, and only when the answer is not discoverable.

## Resolve environment

After `authenticate` → `list_environments`:

1. Match `environmentName` exactly (case-sensitive) to get `environmentId`
2. If no match, ask the user for the correct name — do not guess
3. If multiple accounts/environments confuse the match, list names only and ask

## Duplicate environment name

Before `create_environment`, call `list_environments` and check whether the target
`environmentName` already exists. If it does, **stop and ask the user**, offering:

- **Use the existing environment** — skip `create_environment`, use its `environmentId`
- **Use a different name** — wait for a name, then `create_environment`
- **Cancel** — change nothing

Do not silently choose one of these paths.

## Import from a `.env` file

Default path: `{workspace_root}/.env` unless the user names another path.

1. **Read** the `.env` with the Read tool to get keys and values. Strip optional surrounding quotes. Pass values to MCP only — never into chat.
2. **`authenticate`** → `accountId`
3. **`list_environments`** — if the target name exists, follow **Duplicate environment name** and wait. Otherwise `create_environment` (new name) or resolve the existing one.
4. **`append_variables`** with all variables (see **Concealed variables**)
5. **Git-tracked `.env`** — if the `.env` is git-tracked, stop and tell the user to delete it and commit the removal. Do not proceed to mount until that is done.
6. **Mount** — `list_local_env_files` first; skip `create_local_env_file` only if a mount already exists at the source path. Then `create_local_env_file` with `accountId`, `environmentId`, `environmentName`, `mountPath`, then `list_local_env_files` again to verify.

## Other flows

**Create new Environment:** authenticate → list_environments → duplicate check → create_environment.

**Mount existing Environment:** authenticate → resolve environment → steps 5–6 above.

**Inspect names:** authenticate → resolve environment → list_variables → summarize names only.

**Rename:** authenticate → resolve environment → confirm name → rename_environment.

**Add/update variables:** authenticate → resolve environment → list_variables → append_variables.

## Concealed variables

Set `concealed` per variable when calling `append_variables`:

- `concealed: true` for API keys, tokens, passwords, private keys, and connection strings with credentials
- `concealed: false` for ports, public URLs, feature flags and non-sensitive config, unless the user says otherwise
- When unsure, default to `true`

## Safety

- Never reveal secret values in chat, code, commits or logs
- Ask before changing variables unless the request is explicit

## Troubleshooting

Mount problems, setup: [reference.md](reference.md)
