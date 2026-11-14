# H-02 — OpenAPI 3.1 validation evidence (2026-11-14)

**Current proposed contract:** `docs/contracts/openapi.yaml`, version `1.0.0-rc.3`, Git blob SHA `98d34e7bd7b4551c0f429ea5e388781060ceaf63`.
**Decision:** APP-HESABYAR-H02-CONSUMER-FINDINGS-20261114-001. PR #1 is OPEN / UNMERGED, W0 exit pending.
**Raw structured result from real calls:** [validation-result.json](./validation-result.json).

## 1. Historical rc.3 validation — before dependency security update

**The results in sections 1–2 below are historical and refer to js-yaml 4.1.0 and Ajv2020 8.17.1. They must not be interpreted as retest results for the upgraded dependency set.**

## 1. Actual independent OpenAPI 3.1 tool execution

- Tool: **`@apidevtools/swagger-parser` 11.0.0** (standard third-party validator).
- Source code executed: its **unmodified `lib/validators/schema.js`** from pinned upstream commit `3ac7860717bfe41e4a438ae61b1a90ecce6108a3` (the package declares version `11.0.0`); YAML parsed with **`js-yaml` 4.1.0**, schema engine provided as **`Ajv2020` 8.17.1** bundle and official OAI OpenAPI 3.1 structural schema dated **2026-08-03** at commit `ce49002c7bbd323819555464eb479523923f6754`.
- Actually executed in connected JavaScript tool on **unchanged raw YAML fetched directly from PR branch**:

```javascript
const api = yaml.load(githubFile.content, { json: false });
const validateSchema = /* exact upstream @apidevtools/swagger-parser 11.0.0
  lib/validators/schema.js loaded with its declared dependencies */;
validateSchema(api); // actual function invocation, no exception -> PASS
```

- Actual output: function returned without exception, with **no stdout/stderr** (this is the vendor method's success convention). `api.openapi === "3.1.0"`, `api.info.version === "1.0.0-rc.3"`, blob `98d34e7bd7b4551c0f429ea5e388781060ceaf63`.
- **Scope/limitation:** this is the *vendor schema validation function*, not an execution of the vendor's complete async `SwaggerParser.validate()` dereference/parse workflow. This standard vendor function applies its **own documented Ajv / $dynamicRef workaround** internally for OAS 3.1; the contract YAML itself was unmodified. Do **not** claim strict, unmodified OAI `schema-base` dynamic-dialect validation or runtime implementation compliance. Earlier direct `Ajv2020` validation of unchanged OAI schema-base produced 329 dialect errors on rc.2; this was a tooling limitation, not a clean PASS.

## 2. Additional actual independent-of-vendor H-02 structural / semantic checks

- Executed checked-in `validateH02()` from [validate-openapi.cjs](./validate-openapi.cjs) against **the same SHA** in the isolated JS tool with `js-yaml 4.1.0`, `Ajv2020 8.17.1`, OAI structural schema 2026-08-03.
- Output: `result: PASS`, `yamlParsing: PASS`, `structuralValidation: PASS`, **0 findings**; **23 paths, 33 operations, 18 CSRF-protected mutation operations, 239 resolved component references, 72 JSON Schema syntax checks**.
- The H-02 local structural checker also uses the documented *four in-memory #meta substitutions* in the copied OAI structural schema and is **not** the independent vendor validation claimed above. Keep their scopes distinct.
- Draft warning/field-issue types, trial balance display fields, leaf fixture and stable journal-line identity were checked as schema declarations; F1/F2/F3 and the mixed-leaf fixture still require **future HTTP/PostgreSQL QA**. No runtime, CI or penetration testing was performed.

## 3. Reproducible official dependency install and CLI (provided, **NOT** run in this tool session)

The validation function above **was run** through the JS tool by loading the exact upstream vendor implementation. A self-contained Node entrypoint is included for reviewer reproduction but was **not** executed on a Node shell here. At repository root:

```bash
npm --prefix docs/contracts ci --ignore-scripts
node docs/contracts/validate-standard.cjs
node docs/contracts/validate-openapi.cjs
git hash-object docs/contracts/openapi.yaml
```

Current `docs/contracts/package.json` pins `@apidevtools/swagger-parser: 11.0.0`, `js-yaml: 4.3.2`, `ajv: 8.20.0`. The earlier executed output in sections 1–2 used the **older** vulnerable tool versions. The upgraded versions have NOT been manually executed by Coordinator. The checked-in `package-lock.json` was constructed offline from published GitHub dependency-lock metadata because registry.npmjs.org was unavailable in this tool environment; entries include 17 dependency packages plus the root, and the `swagger-parser` tarball URL is pinned without a verified integrity digest. **The owner must confirm npm ci, npm audit and validators, and regenerate lockfile with online npm if it changes/requests metadata; do not declare dependency audit cleared before evidence.** The standard validator entrypoint calls the same `@apidevtools/swagger-parser/lib/validators/schema` function on the unaltered YAML file. Canonical Git blob SHA must remain `98d34e7bd7b4551c0f429ea5e388781060ceaf63`. Raw Windows CRLF input hashes may differ (`44647cc7ca51d0fbf59bf9c746fa4cae6391cb96`) without canonical Git drift. **The CLI output itself must be independently reconfirmed by a reviewer** (not attributed as an execution here).

## 4. Scope and remaining gates

- [x] Third-party OpenAPI 3.1-compatible validator source actually executed against unchanged rc.3 YAML; exact vendor method/version/source/SHA and output recorded.
- [x] YAML parsing, schema syntax and contract static semantics checked and reported with limitations.
- [ ] Full vendor **async parser/dereference** pipeline or alternative 3.1 conformance validation, if manager requires an even stricter gate.
- [ ] Developer read-only acknowledgment **rc.3 / SHA 98d34e7bd7b4551c0f429ea5e388781060ceaf63**.
- [ ] UI/UX read-only acknowledgment **the identical** version/blob.
- [ ] Independent PR review, Manager freeze, W0 exit and branch protection before any W1 code merge.

## 5. Security remediation follow-up — 2026-11-14 (NOT RETESTED)

**Authority:** Manager PR #1 comment 6875764367 (manual npm audit advisories); required changes only in docs/contracts. `openapi.yaml` is UNTOUCHED: `1.0.0-rc.3`, blob `98d34e7bd7b4551c0f429ea5e388781060ceaf63`; previous Developer and UI/UX consumer approvals remain scoped to this SHA.

- Dependency pins in `package.json`: `ajv 8.17.1 → 8.20.0`, `js-yaml 4.1.0 → 4.3.2`, vendor `@apidevtools/swagger-parser 11.0.0` unchanged. Trigger: GHSA-2g4f-4pwh-qvx6 (AJV), GHSA-mh29-5h37-fv8m and other YAML advisories.
- New `package-lock.json` lockfileVersion 3 assembled using versions, registry tarball URLs and integrity fields from public GitHub package-lock metadata (checkdigit/timeout and rustho/openapi-to-mcp), plus exact upstream swagger-parser v11.0.0 manifest. This is **NOT** claimed to have been generated by an actual npm CLI invocation: registry DNS unavailable in execution environment. The swagger-parser tarball is pinned by version/registry URL but lacks an integrity hash; online npm verification should resolve this, and any lock changes must be committed separately.
- Transitive `@apidevtools/json-schema-ref-parser 16.0.3` requires Node **>=22.19.0** per published metadata; installed Node version and compatibility must be checked in Windows. Its nested `js-yaml 5.4.2` is distinct from direct `js-yaml 4.3.2`; `npm audit` must inspect the full dependency graph.
- `validate-openapi.cjs` now reports **runtime-installed** js-yaml/Ajv package versions, not hard-coded historical labels. `validate-standard.cjs` reports vendor, yaml and ajv versions from installed package manifests. The historical `validation-result.json` is preserved as evidence for previous versions.
- **Status:** package pins and offline lock graph documented; `npm ci`, `npm audit`, both Node validator scripts, and repeat canonical Git hash are all **PENDING OWNER MANUAL TEST**. No PASS/zero-vulnerability claim.

PowerShell (from `D:\ChatGPT-Team-Test`, on the updated PR checkout; check `git status` before switching):

```powershell
git fetch origin pull/1/head
git switch --detach FETCH_HEAD
git status --short
node --version
npm --version
npm --prefix docs/contracts ci --ignore-scripts
npm --prefix docs/contracts ls ajv js-yaml @apidevtools/swagger-parser
npm --prefix docs/contracts audit --audit-level=moderate
node docs/contracts/validate-standard.cjs
node docs/contracts/validate-openapi.cjs
git hash-object docs/contracts/openapi.yaml
git status --short
```

If `npm ci` fails, **do not force-fix or skip**: record exact error; run `npm --prefix docs/contracts install --package-lock-only --ignore-scripts` to reconcile lock metadata only after reviewing the diff, and send the changed lock plus command output to Coordinator/Manager for an explicit follow-up. Do not change the approved OpenAPI source.


## 6. Transitive dependency follow-up — 2026-11-14 (manual npm audit retest pending)

Manager PR #1 comment `6875958532` records real owner Windows worktree testing of the preceding H-02 lock: `npm ci PASS`, direct `ajv 8.20.0`, `js-yaml 4.3.2`; `npm audit FAIL` because **fast-uri 3.1.8** and **undici 8.11.2** remained vulnerable. The owner correctly stopped before validator execution in that test. These are historical owner results, NOT a new test.

**Current lockfile change:** Only `docs/contracts/package-lock.json` dependency entries for `fast-uri` and `undici` changed to **3.1.9** and **8.12.4**. The `resolved` registry URLs, exact version and `integrity` SHA512 values came from pre-existing, publicly accessible npm-generated GitHub lockfile entries, respectively:
- `aarpus/Acute-RPOS-Online-Ordering`, commit `3d3fac9730fb02e17dd8bd630c2a9a7cb80246a2`, `package-lock.json.backup` — fast-uri 3.1.9.
- `koala73/worldmonitor`, commit `a3f4f06a10e772e290ddb369bc4e374cb6ea2b9e`, `blog-site/package-lock.json` — undici 8.12.4.

**Important:** Coordinator has NOT run `npm` in this environment. This is a targeted offline lockfile edit based on npm-origin metadata; it is **not** claimed to be a freshly generated `npm audit fix` lockfile, nor evidence of an audited clean dependency tree. Graph consistency and parent requirements were statically checked only: `ajv -> fast-uri ^3.0.1` accepts 3.1.9; `json-schema-ref-parser -> undici ^8.10.2` accepts 8.12.4; `package.json` and direct pins are unchanged. The existing separate Swagger Parser 11 tarball entry still lacks a verified integrity digest. No CLI, security, or validator PASS is asserted for these new entries.

**Owner repeat test (PowerShell) — isolated worktree to protect local files:**
```powershell
cd D:\ChatGPT-Team-Test
git fetch origin pull/1/head
if ($LASTEXITCODE -ne 0) { throw 'git fetch failed' }
git worktree add --detach D:\ChatGPT-Team-Test-H02-audit2 FETCH_HEAD
if ($LASTEXITCODE -ne 0) { throw 'worktree failed' }
cd D:\ChatGPT-Team-Test-H02-audit2
npm --prefix docs/contracts ci --ignore-scripts
if ($LASTEXITCODE -ne 0) { throw 'npm ci failed' }
npm --prefix docs/contracts ls ajv js-yaml fast-uri undici @apidevtools/swagger-parser
if ($LASTEXITCODE -ne 0) { throw 'dependency verification failed' }
npm --prefix docs/contracts audit --audit-level=moderate
if ($LASTEXITCODE -ne 0) { throw 'audit failed; stop without claiming PASS' }
node docs/contracts/validate-standard.cjs
if ($LASTEXITCODE -ne 0) { throw 'standard validator failed' }
node docs/contracts/validate-openapi.cjs
if ($LASTEXITCODE -ne 0) { throw 'H-02 validator failed' }
git hash-object docs/contracts/openapi.yaml
git status --short
```

This uses a **different** worktree path from previous owner tests; do not overwrite it if it already exists. If any command fails, stop and return exact stderr/stdout to Manager. An optional online, reviewed `npm --prefix docs/contracts audit fix --package-lock-only --ignore-scripts` (NO `--force`) may be applied in a separate working checkout **only after comparing its lock diff and confirming no direct package changes**. Do not auto-commit an unrelated npm update.

**Invariant:** The approved contract `docs/contracts/openapi.yaml` remains version `1.0.0-rc.3`, canonical Git blob `98d34e7bd7b4551c0f429ea5e388781060ceaf63`. Existing consumer contract approvals stand. The npm-audit security gate remains **PENDING OWNER TEST**, PR remains OPEN/UNMERGED and W1 unauthorized.
