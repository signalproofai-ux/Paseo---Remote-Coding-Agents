# iPhone-Only Runbook - Zero-Cost iOS Build System

Everything below is done in Safari on your iPhone. No Mac, no PC, no payments.
Maximum permitted charge: 0.00. Every path here uses only free plans.

## What you have

This bundle (`ios-build-infra/`) contains a complete, tested-shape build system:

| File | Purpose |
|---|---|
| `.github/workflows/ios-build.yml` | GitHub Actions workflow: genuine macOS (Apple Silicon) + Xcode, manual start only, free-minute ledger with automatic stop, unsigned + signed IPA paths |
| `codemagic.yaml` | Codemagic free plan config: Mac mini M2, 500 free minutes/month, manual start only |
| `DemoApp/` | Minimal SwiftUI app (XcodeGen spec + 2 Swift files) to prove the pipeline before your real project arrives |
| `build-ledger.json` | Cumulative build-minutes ledger the workflow updates and enforces |

## Step 0 (one-time, ~3 min): unlock automation - RECOMMENDED PATH

Your current GitHub token cannot create repositories or edit workflows
(verified: repo creation returns 403). To let an agent session do everything
for you automatically, upgrade the token in Safari:

1. Open `github.com` -> sign in -> tap your avatar -> **Settings**.
2. Scroll to the bottom: **Developer settings** -> **Personal access tokens** -> **Fine-grained tokens** -> tap your existing token -> **Edit**.
3. **Repository access**: change to *All repositories* (or select the private iOS repo you will create in Step 1A).
4. **Permissions**: set
   - *Administration*: **Read and write** (allows creating the private repo)
   - *Contents*: **Read and write**
   - *Workflows*: **Read and write** (allows committing build workflows)
   - *Metadata*: Read (mandatory, automatic)
5. Update the token in your secure archive channel (do not paste it into any chat).

After that, ask an agent session: "create the private repo and import ios-build-infra" - the whole setup + verification build will be done for you.

## Step 1: get the files into a PRIVATE repository

### Path A (manual, Safari only)

1. `github.com` -> **+** (top right) -> **New repository**.
2. Name it (e.g. `ios-build-infra`), select **Private**, *do not* tick any
   README/init checkbox, **Create repository**.
3. Tap **creating a new file** link (or "Add file -> Create new file").
   In the filename box, typing slashes creates folders:
   - Type `.github/workflows/ios-build.yml`, paste the workflow content, **Commit changes**.
   - Repeat for `codemagic.yaml`, `build-ledger.json`,
     `DemoApp/project.yml`, `DemoApp/Sources/DemoAppApp.swift`,
     `DemoApp/Sources/ContentView.swift`.

### Path B (import via git)

If you completed Step 0, simply ask the agent session to push this bundle to
the new private repo - it has everything needed.

## Step 2: run a build (GitHub Actions path)

1. Open the repo in Safari -> **Actions** tab -> tap **iOS Build** in the left list.
2. A yellow banner appears: *"This workflow has a workflow_dispatch event trigger."*
   Tap **Run workflow** -> keep defaults (Release, tests off, signing auto) -> **Run workflow**.
3. Tap the running entry to watch live progress; every step's log is expandable.
4. The green **run summary** at the top of the run page is written for phone
   reading: Xcode version, project, scheme, IPA name/size, minutes used.
5. When finished: scroll to **Artifacts** -> tap `ios-build-<number>` ->
   Safari downloads the ZIP -> find it in the **Files** app -> unzip ->
   the `.ipa` is inside.

Automatic builds on push are deliberately NOT configured; nothing runs unless
you tap Run workflow.

## Step 3: run a build (Codemagic path - 500 free M2 minutes/month)

One-time: open `codemagic.io` in Safari -> **Get started** -> sign in with
GitHub (authorize the app) -> choose the Free individual plan. Billing stays
disabled; the free plan needs no card.

1. **Add application** -> pick your private repo -> project type *iOS App*.
2. Codemagic detects `codemagic.yaml` and offers the `ios-build` workflow - select it and finish setup.
3. On the app page tap **Start new build** -> choose branch + workflow -> **Start build**.
4. Live logs are on the build page; when it finishes, **Artifacts** shows
   `App_UNSIGNED.ipa` - tap to download to Files.

Note: the M4 machine and any paid tier require billing enabled and are NOT
used; this config pins `mac_mini_m2`, which is the free M2 machine.

## Check remaining free minutes (iPhone)

- **GitHub**: repo -> `build-ledger.json` (tap it, read `quota_minutes_total`;
  workflow stops itself at 1800 of the 2000 included quota minutes; macOS uses
  10 quota minutes per clock minute). Authoritative view: `github.com` ->
  avatar -> **Settings** -> **Billing and plans** -> **Usage** - shows Actions
  minutes used this month.
- **Codemagic**: dashboard home shows your remaining build minutes
  (500/month, reset on the 1st).

## Confirm billing stays disabled

- **GitHub**: avatar -> **Settings** -> **Billing and plans** -> confirm plan
  *Free* and **no payment method** on file. The workflow cannot spend money;
  exceeding the free allowance makes Actions stop, not bill.
- **Codemagic**: avatar -> **Teams/Account settings** -> **Billing** ->
  confirm *Individual (free)*, no card added. Builds stop at 500 minutes;
  nothing is auto-purchased.

## Signing - the honest picture

- An **unsigned IPA** is produced at zero cost. It is **not installable
  directly** on a device. It can be re-signed later or inspected.
- A **signed, installable IPA** requires Apple signing credentials
  (certificate P12 + provisioning profile). On an iPhone-only setup the only
  legitimate source is a paid **Apple Developer Program** membership
  (USD 99/year) - which your zero-cost policy forbids. Free 7-day development
  profiles require Xcode or sideloading tools running on a Mac/PC, which you
  do not have.
- Therefore: builds and artifacts work today at 0.00; a device-installable
  IPA becomes possible the day you approve the Apple Developer membership
  (add `P12_BASE64`, `P12_PASSWORD`, `MOBILEPROVISION_BASE64` as repo secrets,
  or upload the certificate in Codemagic's encrypted store) - the workflows
  already support both, and credentials are never printed in logs.

## Recovery procedure

- **Workflow failed**: open the run -> read the *Build failed* summary (last
  60 log lines + diagnosis are written there automatically) -> fix ->
  run again. Queued duplicate builds are prevented by the concurrency group.
- **Sandbox/agent session lost**: nothing on GitHub/Codemagic depends on any
  session. Workflows and configs live in your repo; just ask the next agent
  session to re-verify, or re-run the workflow yourself from Safari.
- **Quota exhausted**: the ledger guard refuses further builds until the next
  monthly reset (GitHub: resets with your billing cycle; Codemagic: 1st of
  the month). No action needed; nothing bills.
