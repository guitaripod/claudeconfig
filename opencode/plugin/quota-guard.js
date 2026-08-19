import { appendFileSync } from "node:fs"

const QUOTA_RE =
  /(usage|quota|rate)\s*(limit|exceeded|exhausted)|insufficient_quota|insufficient\s+(balance|credits?)|out of (quota|credits?|balance)|billing|free\s?tier|FreeUsageLimitError|GoUsageLimitError|credit(s)?\s+(limit|exhausted|depleted)|payment required/i

function log(line) {
  try {
    appendFileSync("/tmp/opencode-quota-guard.log", `${new Date().toISOString()} ${line}\n`)
  } catch {}
}

function errorText(error) {
  if (!error) return ""
  const data = error?.data ?? error ?? {}
  const pieces = [data?.message ?? "", data?.responseBody ?? "", String(data?.statusCode ?? "")]
  return pieces.join(" ")
}

function isQuotaError(error) {
  const data = error?.data ?? error ?? {}
  if (data.statusCode === 402 || data.statusCode === 429) return true
  return QUOTA_RE.test(errorText(error))
}

export const QuotaGuardPlugin = async ({ client }) => {
  return {
    "event": async ({ event }) => {
      if (event?.type !== "session.error") return
      const sessionID = event?.properties?.sessionID
      const error = event?.properties?.error
      if (!sessionID || !isQuotaError(error)) return
      try {
        const res = await client.session.get({ path: { id: sessionID } })
        const session = res?.data ?? res
        const parentID = session?.parentID ?? session?.parent_id
        if (!parentID) return
        const statusRes = await client.session.status({ path: { id: parentID } })
        const status = statusRes?.data ?? statusRes
        const busy = typeof status === "object" && status !== null && (status.type === "busy" || status.busy === true)
        if (!busy) return
        await client.session.abort({ path: { id: parentID } })
        log(`aborted parent=${parentID} sub=${sessionID} error=${errorText(error).slice(0, 200)}`)
      } catch (e) {
        log(`event path failed sub=${sessionID} err=${String(e)}`)
      }
    },

    "tool.execute.after": async (input, output) => {
      if (input?.tool !== "task" || output !== undefined) return
      const sessionID = input?.sessionID
      const callID = input?.callID
      if (!sessionID || !callID) return
      try {
        const res = await client.session.messages({ path: { id: sessionID } })
        const messages = res?.data ?? res
        for (const message of messages ?? []) {
          const part = (message?.parts ?? []).find((p) => p?.callID === callID)
          if (!part) continue
          if (part?.state?.status !== "error") return
          if (!isQuotaError(part?.state?.error)) return
          await client.session.abort({ path: { id: sessionID } })
          log(`aborted via tool hook session=${sessionID} error=${errorText(part.state.error).slice(0, 200)}`)
          return
        }
      } catch (e) {
        log(`tool hook failed session=${sessionID} err=${String(e)}`)
      }
    },
  }
}
