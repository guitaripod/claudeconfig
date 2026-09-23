import { DELEGATE_DESCRIPTION, runDelegate, type DelegateArgs } from "../tools/delegate.ts"

const text = (description: string) => ({ type: "string", description })
const strings = (description: string) => ({ type: "array", items: { type: "string" }, description })

const INPUT = {
  type: "object",
  properties: {
    op: { type: "string", enum: ["run", "new", "log", "stats", "show", "tiers"], description: "Delegate subcommand to perform." },
    packet: text("Packet YAML path for op=run; run id for op=show."),
    class: text("Packet class (op=new, or op=run with no packet)."),
    goal: text("Packet goal, self-contained (op=new, or op=run with no packet)."),
    paths: strings("Allowed paths/globs for a new packet."),
    verify: text("Verify command for a new packet."),
    read: strings("Files the worker should read first."),
    notes: text("Free-form notes appended to the worker prompt."),
    tier: text("Start tier override."),
    ceiling: text("Ceiling tier override."),
    mode: { type: "string", enum: ["normal", "conserve", "rush"], description: "Dispatch mode override." },
  },
  required: ["op"],
  additionalProperties: false,
}

/// opencode 1.x takes the tool from tools/delegate.ts; 2.x only loads plugins, so this registers the same tool there.
export default {
  id: "delegate",
  server: async () => ({}),
  setup: async (ctx: any) => {
    await ctx.tool.transform((tools: any) => {
      tools.add({
        name: "delegate",
        description: DELEGATE_DESCRIPTION,
        input: INPUT,
        execute: async (args: DelegateArgs, context: { sessionID: string }) => {
          try {
            const session = await ctx.session.get({ sessionID: context.sessionID })
            const cwd = (session?.data ?? session)?.location?.directory ?? process.cwd()
            const { output } = await runDelegate(args, cwd)
            return { content: output }
          } catch (error) {
            return { content: `delegate failed: ${error instanceof Error ? error.message : String(error)}` }
          }
        },
      })
    })
  },
}
