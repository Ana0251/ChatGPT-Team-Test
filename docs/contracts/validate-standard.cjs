'use strict';
// Docs-only independent standard library check for H-02, NOT application code.
// Uses @apidevtools/swagger-parser v11.0.0's OAS 3.1 schema validator source.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const yaml = require('js-yaml');
const validateSchema = require('@apidevtools/swagger-parser/lib/validators/schema');

const p = path.join(__dirname, 'openapi.yaml');
const source = fs.readFileSync(p, 'utf8');
const gitBlobSha = crypto.createHash('sha1').update('blob '+Buffer.byteLength(source)+'\0').update(source).digest('hex');
try {
  // This method validates an unmodified parsed YAML object against the vendor
  // OAS 3.1 schema. The package internally applies its known Ajv $dynamicRef
  // workaround (see upstream schema.js); no Hesabyar YAML changes are made.
  const api = yaml.load(source, { json: false });
  if (api.openapi !== '3.1.0') throw new Error('Expected OpenAPI 3.1.0');
  validateSchema(api);
  process.stdout.write(JSON.stringify({
    tool: '@apidevtools/swagger-parser',
    version: '11.0.0',
    method: 'lib/validators/schema.validateSchema()',
    document: 'docs/contracts/openapi.yaml',
    contractVersion: api.info.version,
    gitBlobSha,
    result: 'PASS',
    note: 'Vendor schema validation only; full dereference pipeline and QA not run'
  }, null, 2)+'\n');
} catch (e) {
  process.stderr.write(JSON.stringify({
    result: 'FAIL', gitBlobSha, error: String(e), details: e.details||null
  }, null, 2)+'\n');
  process.exitCode = 1;
}
