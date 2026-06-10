export const meta = {
  name: 'wwdc',
  description: 'Search WWDC session knowledge base and answer questions about Apple frameworks and APIs',
  phases: [
    { title: 'Search', detail: 'find matching sessions in guitaripod/wwdc-sessions' },
    { title: 'Read', detail: 'fetch session READMEs' },
    { title: 'Synthesize', detail: 'compile answer' },
  ],
}

const query = typeof args === 'string' && args.trim() ? args.trim() : 'what is new'

const SESSION_SCHEMA = {
  type: 'object',
  properties: {
    sessions: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          path: { type: 'string' },
          title: { type: 'string' },
        },
        required: ['path', 'title'],
      },
    },
  },
  required: ['sessions'],
}

phase('Search')

const found = await agent(
  `Search the GitHub repo guitaripod/wwdc-sessions for sessions related to: ${query}

Run this shell command:
gh search code ${JSON.stringify(query)} --repo guitaripod/wwdc-sessions --limit 30

Each result line looks like: "guitaripod/wwdc-sessions:sessions/wwdcYEAR/ID-slug/file.md: ..."
Extract the unique session directory paths (the "sessions/wwdcYEAR/ID-slug" portion, without any trailing filename).
Return up to 5 most relevant sessions. Prefer the newest WWDC year when the query is about new or latest features.
Derive the title from the directory slug (e.g. "274-what-s-new-in-swiftdata" -> "What's New in SwiftData").`,
  { label: 'search', phase: 'Search', model: 'claude-haiku-4-5-20251001', schema: SESSION_SCHEMA }
)

if (!found.sessions.length) return `No WWDC sessions found for: ${query}`

phase('Read')

const contents = await pipeline(
  found.sessions.slice(0, 5),
  async (s, _orig, i) => {
    const url = `https://raw.githubusercontent.com/guitaripod/wwdc-sessions/master/${s.path}/README.md`
    const text = await agent(
      `Fetch this URL and return its full content verbatim:\n${url}`,
      { label: `read:${i}`, phase: 'Read', model: 'claude-haiku-4-5-20251001' }
    )
    return { title: s.title, text }
  }
)

const valid = contents.filter(Boolean)
if (!valid.length) return 'Could not fetch any session content.'

phase('Synthesize')

return await agent(
  `The user asked: "${query}"

Here are the relevant WWDC session READMEs:

${valid.map(c => `## ${c.title}\n\n${c.text}`).join('\n\n---\n\n')}

Write a clear, well-organized answer. Include concrete API changes, new features, and code examples where present. Use markdown.`,
  { label: 'synthesize', phase: 'Synthesize', model: 'claude-haiku-4-5-20251001' }
)
