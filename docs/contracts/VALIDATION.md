# H-02 — OpenAPI 3.1 validation evidence (2026-11-14)

**Current proposed contract:** `docs/contracts/openapi.yaml`, version `1.0.0-rc.3`, Git blob SHA `98d34e7bd7b4551c0f429ea5e388781060ceaf63`.
**Decision:** APP-HESABYAR-H02-CONSUMER-FINDINGS-20261114-001. PR #1 is OPEN / UNMERGED, W0 exit pending.
**Raw structured result from real calls:** [validation-result.json](./validation-result.json).

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
npm --prefix docs/contracts install --no-package-lock --ignore-scripts
node docs/contracts/validate-standard.cjs
node docs/contracts/validate-openapi.cjs
git hash-object docs/contracts/openapi.yaml
```

`docs/contracts/package.json` pins `@apidevtools/swagger-parser: 11.0.0`, `js-yaml: 4.1.0`, `ajv: 8.17.1`. The standard validator entrypoint calls the same `@apidevtools/swagger-parser/lib/validators/schema` function on the unaltered YAML file. Expected blob SHA is `98d34e7bd7b4551c0f429ea5e388781060ceaf63`. **The CLI output itself must be independently reconfirmed by a reviewer** (not attributed as an execution here).

## 4. Scope and remaining gates

- [x] Third-party OpenAPI 3.1-compatible validator source actually executed against unchanged rc.3 YAML; exact vendor method/version/source/SHA and output recorded.
- [x] YAML parsing, schema syntax and contract static semantics checked and reported with limitations.
- [ ] Full vendor **async parser/dereference** pipeline or alternative 3.1 conformance validation, if manager requires an even stricter gate.
- [ ] Developer read-only acknowledgment **rc.3 / SHA 98d34e7bd7b4551c0f429ea5e388781060ceaf63**.
- [ ] UI/UX read-only acknowledgment **the identical** version/blob.
- [ ] Independent PR review, Manager freeze, W0 exit and branch protection before any W1 code merge.
