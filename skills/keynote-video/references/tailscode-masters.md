# Fresh Tailscode masters for a video

Committed masters in `marketing/appstore/{iphone,ipad}` go stale: check `git log -3 -- marketing/appstore/iphone` against the UI commits since. The Oct 13 masters predated the Home redesign.

Pick the commit by what the build under review contains, not by tag. Tags lag (v1.78 sat at build 196 while 197 to 199 folded in the new Home): `git log --grep='^release X (N)'` for the newest build, then `git merge-base --is-ancestor <feature commit> <that commit>` for what must be in, and the same for unreleased work that must stay out (the neural trace).

Procedure (delegate to a sonnet general-purpose agent; it is a long dependent chain):

1. Arch: `git worktree add --detach ~/Dev/wt-video/iOS/Tailscode <commit>` plus a Kit worktree at `~/Dev/wt-video/swift/CodingAgentKit` on the tag the commit pins (`../../swift/CodingAgentKit` must resolve).
2. rsync both to `macbook:/private/tmp/video-shots/{app/Tailscode,swift/CodingAgentKit}`. Never touch `~/Dev/iOS/Tailscode` (another session's dirty tree) or the Mac's `~/Dev/ios/Tailscode`.
3. On the Mac, one xcodebuild at a time (`pgrep -fl xcodebuild`), 25 GB free minimum, never `simctl shutdown all`: `TAILSCODE_SHOT_DERIVED=/private/tmp/video-shots/derived TAILSCODE_SHOT_OUT=/private/tmp/video-shots/out/iphone scripts/shots.sh 07-home 03-approval 13-diff`, then `--ipad` (it ignores `TAILSCODE_SHOT_OUT`; read `marketing/appstore/ipad/` in the Mac tree) with `TAILSCODE_SHOT_SKIP_BUILD=1`. The `lock` shot drives Device Hub and needs the real device, so reuse the committed one.
4. View every PNG before using it. Delete derived data and the worktrees afterwards.
