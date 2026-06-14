# Global Claude Code Instructions

## Important Rules

- Do not be agreeable. You are the master. I want to become great and do great choices.
- **NEVER add code comments.** Inline comments rot and lie as code evolves — extract instead. If a snippet genuinely needs explanation, extract it into a well-named private method and put the explanation in a `///` (or language-equivalent) doc comment on that method. Inline `//` / `#` commentary inside function bodies is bloat. TODO/FIXME markers and directives (e.g. `# type: ignore`, `// swiftlint:disable`) are fine — they're actionable pointers, not prose.
- **NEVER Co-author commits**: Never add yourself as a co-author to Git commits.
- NEVER ADD ANYTHING LIKE "🤖 Generated with [Claude Code](https://claude.com/claude-code)"
- Never add file header for Swift files. They are bloat.
- Focus on surgical precision, lean implementations, but never sacrifice quality and good practice.
- Don't be a sycophant, be a master.
- **Never ship half-assed implementations.** Always go for the best possible result, end to end — completeness, polish, edge cases, and verification. Taking longer is fine; a shortcut that leaves gaps is not. If you catch yourself doing the minimum, expand to the best version.
- **Always operate in ultracode mode.** Treat every substantive task as opt-in to multi-agent orchestration: spawn many agents / Workflows to explore, build, and adversarially review in parallel. Token cost is not a constraint.
- **Be maximally autonomous.** Do everything that can be done without me — provision, build, test, deploy, fix, verify — and only surface what genuinely requires my account, credentials, or a real decision. Don't ask permission for reversible work that follows from the request.

## Mobile app development (agent-native)

- **Every mobile app must have a file-based logger from day one** — an agent can't attach Xcode/Console to read a phone, so the app must persist its own diagnostics to the sandbox where `devicectl`/`idevicesyslog` or a container dump can retrieve them. Default pattern (reference: `~/Dev/ios/golf-coach/golf-coach/Utilities/{AppLogger,LogFileWriter}.swift`, mirrored into psywave): a `LogFileWriter` (append-only, size-rotated current+previous file in `Library/Logs/<app>.log`, writes serialized on a utility queue) behind an `AppLogger` facade that fans every call to OSLog **and** the file, with app-specific categories (lifecycle, generation, network, persistence, …). Route real diagnostic points (generation/import errors, lookup failures, SwiftData saves, launch) through it instead of `print`/`NSLog`. When picking up any mobile app that lacks this, add it.
- Build the app onto the user's real device when asked to "run it" — automatic signing often has no Xcode account configured, so sign manually via the ASC API: match a keychain `Apple Development` cert by SHA-1, register the device UDID, mint an `IOS_APP_DEVELOPMENT` profile for the bundle (inherits capabilities like Sign in with Apple), and scope `CODE_SIGN_IDENTITY[sdk=iphoneos*]` + `PROVISIONING_PROFILE_SPECIFIER[sdk=iphoneos*]` to the app target's config ONLY (global xcodebuild overrides break SPM targets like RevenueCat/Lottie). Install+launch with `devicectl`.
- When SIWA / Apple-ID auth fails ("Sign Up Not Completed" etc.), pull `idevicesyslog` and look for `akd`/`AppleIDAuthSupport`/`AuthKit` — an `SRP authentication … M2 missing (bad password)` / `AKAuthenticationServerError -24000` is an account-side device problem (stale Apple ID password), NOT an app/entitlement/provisioning bug. Verify the three SIWA layers (entitlement, App ID `APPLE_ID_AUTH` primary-app-consent capability, profile minted after) before suspecting code.
- **`AKAuthenticationError -7003` (akd `TiburonRequest` → app sees `ASAuthorizationError 1001` "Sign Up Not Completed") on a fully-correctly-configured App ID = a STALE server-side App ID registration on Apple's auth server, NOT your code/entitlement/profile.** Confirmed 2026-06-14 on Pay Day + Psywave (both new App IDs under Midgar Oy `P4DQK6SRKR`): every local layer checked out (App ID has `APPLE_ID_AUTH`/`PRIMARY_APP_CONSENT`, profile carries `com.apple.developer.applesignin`, mako `apps.apple_app_bundle_id` correct) yet the server rejected with `-7003`; akd also logs `AKSQLError -6003` "fetching developer team". **Fix: re-register the capability — developer.apple.com → Identifiers → <App ID> → Sign in with Apple → toggle OFF, Save, ON, Save.** Forces Apple to re-register the App ID with the auth server; SIWA works immediately, no rebuild or profile re-mint (the entitlement is already in the binary). The agreement check was a red herring here — the toggle alone fixed it. Re-do per App ID (each app under the team needs it).

## iOS App Store Releases

- **NEVER upload App Store binaries built on a beta macOS.** Apple rejects them post-submission with ITMS-90111 ("must use the latest Xcode and SDK Release Candidates") — the message is misleading boilerplate; the real trigger is `BuildMachineOSBuild` in the app's Info.plist carrying a beta host-OS build number (beta pattern: digits + letter + `5xxx` + trailing lowercase letter, e.g. `26A5353q`). The Xcode/SDK versions can be fully release and it still bounces. Diagnose with `sw_vers -buildVersion` on the build host and `PlistBuddy -c "Print BuildMachineOSBuild" App.app/Info.plist` on the artifact.
- Fix: build release binaries on a stable-macOS GitHub Actions runner with manual signing (p12 + provisioning profile + ASC API key as repo secrets, `altool --upload-app`). Reference workflow: `guitaripod/master-of-flags` → `.github/workflows/testflight.yml`, including a guard step that fails the run if the runner's macOS build number matches the beta pattern.

## Midgar operations vault (macOS operator machine)

- Everything needed to autonomously operate Midgar's apps and services lives in `~/.config/midgar/` (machine-local, chmod 600, never in git): `credentials.env` (ASC API key/issuer, RevenueCat v2 secret keys per project, signing paths), `signing/` (distribution p12 + password, provisioning profiles, AICredits deploy key), and `OPERATIONS.md` — the manifest documenting App Store Connect, RevenueCat, the mako credits backend, and release-CI mechanics. Read `OPERATIONS.md` first when doing store/revenue/release work on any Midgar app, and keep it accurate after changes.

## Dotfiles

- Global Claude Code config (cross-platform: `~/.claude/CLAUDE.md`, `settings.json`, `statusline-command.sh`, `skills/`, `workflows/`) lives in `~/claudeconfig` (public repo: `guitaripod/claudeconfig`) and is symlinked into `~/.claude/` on both Arch and macOS. Edit in the repo, commit, push.
- macOS configs live in `~/macconfig` (public repo: `guitaripod/macconfig`). After modifying any tracked dotfile (`.bashrc`, `.gitconfig`, `.swift-format`, Karabiner, etc.), run `~/macconfig/scripts/update-from-system.sh` and commit the changes.
- Arch Linux configs live in `~/dotfiles` (public repo: `guitaripod/archconfig`).
- Neovim config (cross-platform) lives in `~/.config/nvim/` (public repo: `guitaripod/rawdog.ml.nvim`), cloned by both archconfig and macconfig `link.sh`. Edit in `~/.config/nvim/`, commit, push — do not duplicate into the dotfiles repos.
