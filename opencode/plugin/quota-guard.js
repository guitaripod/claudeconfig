import { appendFileSync } from "node:fs"

const QUOTA_RE =
  /(usage|quota|rate)\s*(limit|exceeded|exhausted)|insufficient_quota|insufficient\s+(balance|credits?)|out of (quota|credits?|balance)|billing|free\s?tier|FreeUsageLimitError|GoUsageLimitError|credit(s)?\s+(limit|exhausted|depleted)|payment required/i

function log(line) {
  try {
    appendFileSync("/tmp/opencode-quota-guard.log", `${new Date().toISOString()} ${line}\n`)
  } catch {}
}

/// The subagent tool's failure text, with the provider error it wraps.
function errorText(error) {
  const cause = error?.error ?? {}
  return [error?.message ?? "", cause?.message ?? "", cause?.responseBody ?? ""].join(" ")
}

function isQuotaError(error) {
  const status = error?.error?.statusCode ?? error?.error?.status
  if (status === 402 || status === 429) return true
  return QUOTA_RE.test(errorText(error))
}

export default {
  id: "quota-guard",
  setup: async (ctx) => {
    await ctx.tool.hook("execute.after", (event) => {
      if (event.tool !== "subagent" || event.status !== "error" || !isQuotaError(event.error)) return
      const sessionID = event.sessionID
      ctx.session.interrupt({ sessionID }).then(
        () => log(`interrupted session=${sessionID} error=${errorText(event.error).slice(0, 200)}`),
        (e) => log(`interrupt failed session=${sessionID} err=${String(e)}`),
      )
    })
  },
}
