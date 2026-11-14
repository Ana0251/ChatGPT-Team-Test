/* H-02 contract lint 1.0.0. Docs-only validation helper, no application runtime code.
 * For reproducibility: npm --prefix docs/contracts install --no-package-lock --ignore-scripts
 * node docs/contracts/validate-openapi.cjs
 *
 * Uses js-yaml 4.1.0, Ajv2020 8.17.1 and official OAI 3.1 structural schema dated 2026-08-03.
 * Explicit nuance: OAI's schema-object $dynamicRef is replaced in a COPY of the
 * structural schema by a local loose Schema Object ref; 2020-12 syntax of embedded
 * schemas is validated separately by Ajv.validateSchema. This is NOT a full runtime
 * or independent OpenAPI conformance test.
 */
'use strict';
const OFFICIAL_SCHEMA_URL = 'https://raw.githubusercontent.com/OAI/spec.openapis.org/ce49002c7bbd323819555464eb479523923f6754/oas/3.1/schema/2026-08-03';
const METHODS = new Set(['get','post','put','patch','delete','head','options','trace']);
const UNSAFE = new Set(['post','put','patch','delete']);
const MONEY_KEYS = ['opening_debit','opening_credit','debit','credit','closing_debit','closing_credit'];

function validateH02({source, yaml, Ajv2020, officialSchema, gitBlobSha}) {
  const spec = yaml.load(source, {json:false}); // fail on malformed/duplicate YAML mappings
  const problems = [];
  if (spec.openapi !== '3.1.0') problems.push('OpenAPI root must be 3.1.0');
  if (spec.info?.version !== '1.0.0-rc.3') problems.push('Contract version mismatch');
  const ajv = new Ajv2020({
    strict:false, allErrors:true, validateFormats:false,
    logger:{log:()=>{},warn:()=>{},error:()=>{}}
  });
  const structural = JSON.parse(JSON.stringify(officialSchema));
  let dynamicRefSubstitutions = 0;
  function replaceDynamicRef(node) {
    if (node===null || typeof node !== 'object') return;
    if (node.$dynamicRef === '#meta') {
      delete node.$dynamicRef;
      node.$ref = '#/$defs/schema';
      dynamicRefSubstitutions++;
    }
    for (const value of Object.values(node)) replaceDynamicRef(value);
  }
  replaceDynamicRef(structural);
  const validateOas = ajv.compile(structural);
  if (!validateOas(spec)) {
    problems.push(...(validateOas.errors||[]).map(e => 'OAI schema: '+e.instancePath+' '+e.message));
  }
  let schemaSyntaxChecks = 0;
  function checkSchema(node, label) {
    schemaSyntaxChecks++;
    if (!ajv.validateSchema(node)) {
      problems.push('JSON Schema 2020-12: '+label+' '+JSON.stringify((ajv.errors||[]).slice(0,3)));
    }
  }
  for (const [name,node] of Object.entries(spec.components?.schemas||{})) {
    checkSchema(node, 'components.schemas.'+name);
  }
  const seenRefs = [];
  function scanRefs(node, label) {
    if (node===null || typeof node !== 'object') return;
    if (typeof node.$ref === 'string') {
      seenRefs.push(node.$ref);
      if (node.$ref.startsWith('#/')) {
        let target=spec;
        for (const segment of node.$ref.slice(2).split('/')) {
          target=target?.[segment.replaceAll('~1','/').replaceAll('~0','~')];
        }
        if (target === undefined) problems.push('Unresolved ref at '+label+': '+node.$ref);
      } else problems.push('Unexpected external document $ref: '+node.$ref);
    }
    for (const [name,child] of Object.entries(node)) scanRefs(child,label+'.'+name);
  }
  scanRefs(spec,'root');
  const routes=Object.entries(spec.paths||{});
  let operations=0, csrfProtectedMutations=0, inlineSchemaChecks=0;
  for (const [route,item] of routes) {
    for (const [method,operation] of Object.entries(item)) {
      if (!METHODS.has(method)) continue;
      operations++;
      const name=route+' '+method.toUpperCase();
      if (!operation.responses || !Object.keys(operation.responses).length)
        problems.push('Missing responses: '+name);
      const params=[...(item.parameters||[]),...(operation.parameters||[])].map(p=>
        p.$ref ? spec.components.parameters[p.$ref.split('/').pop()] : p);
      for (const match of route.matchAll(/\{([^}]+)\}/g)) {
        const param=match[1];
        if (!params.some(p=>p?.in==='path'&&p.name===param&&p.required===true))
          problems.push('Missing required path parameter '+param+': '+name);
      }
      if (UNSAFE.has(method)) {
        if (!params.some(p=>p?.name==='X-CSRF-Token'&&p.in==='header'&&p.required===true))
          problems.push('Unsafe mutation without CSRF header: '+name);
        else csrfProtectedMutations++;
      }
      if (operation.requestBody?.content) for (const [type,body] of Object.entries(operation.requestBody.content)) {
        if (body.schema) {checkSchema(body.schema,name+' request '+type);inlineSchemaChecks++;}
      }
      for (const [status,response] of Object.entries(operation.responses||{})) {
        if (!response?.content) continue;
        for (const [type,body] of Object.entries(response.content)) {
          if (body.schema) {checkSchema(body.schema,name+' response '+status+' '+type);inlineSchemaChecks++;}
        }
      }
    }
  }
  const schemas=spec.components?.schemas||{};
  const totals=schemas.TrialBalanceTotals;
  const row=schemas.TrialBalanceRow;
  if (schemas.TrialBalance?.properties?.totals?.$ref !== '#/components/schemas/TrialBalanceTotals')
    problems.push('TrialBalance.totals must reference TrialBalanceTotals');
  if (!totals || MONEY_KEYS.some(k=>!totals.required?.includes(k)||!totals.properties?.[k]))
    problems.push('TrialBalanceTotals six financial totals missing');
  if (totals && (totals.properties?.account_id || totals.properties?.account_code))
    problems.push('Totals must not have account identity fields');
  if (!row?.required?.includes('account_id') || !row.required.includes('account_code') || !row.required.includes('account_level') || !row.required.includes('account_name'))
    problems.push('TrialBalanceRow must retain account identity');
  for (const path of ['/auth/csrf','/auth/activate','/auth/invitations/activate','/auth/invitations/accept','/companies/{companyId}/members','/companies/{companyId}/reports/trial-balance']) {
    if (!spec.paths?.[path]) problems.push('Missing required endpoint '+path);
  }
  if (!schemas.JournalWarning || !schemas.FieldIssue || !schemas.ErrorCode || !schemas.Movement?.required?.includes('line_id')) problems.push('Missing stable UI / ledger contracts');
  if (!spec.components?.securitySchemes?.sessionCookie) problems.push('Session cookie scheme missing');

  return {
    validator:'H-02 contract lint 1.0.0',
    parser:'js-yaml 4.1.0',
    engine:'Ajv2020 8.17.1 (validateFormats=false)',
    officialSchema:'OAI OpenAPI 3.1 schema 2026-08-03',
    officialSchemaPinnedCommit:'ce49002c7bbd323819555464eb479523923f6754',
    schemaDynamicRefSubstitutions:dynamicRefSubstitutions,
    note:'OAI structural schema validated with #meta dynamicRef mapped to local loose schema; each embedded JSON Schema separately checked using Draft 2020-12 meta. This is not full dialect validation.',
    yamlParsing:'PASS',
    structuralValidation:validateOas.errors ? 'FAIL' : 'PASS',
    embeddedSchemaChecks:schemaSyntaxChecks,
    inlineSchemaChecks,
    paths:routes.length,
    operations,
    csrfProtectedMutations,
    componentReferences:seenRefs.length,
    contractVersion:spec.info.version,
    gitBlobSha:gitBlobSha||null,
    result:problems.length ? 'FAIL' : 'PASS',
    errors:problems
  };
}
module.exports={validateH02,OFFICIAL_SCHEMA_URL};
if (typeof require==='function' && require.main===module) {
  (async()=>{
    const fs=require('node:fs'),crypto=require('node:crypto'),path=require('node:path');
    const source=fs.readFileSync(path.join(__dirname,'openapi.yaml'),'utf8');
    const hash=crypto.createHash('sha1').update('blob '+Buffer.byteLength(source)+'\0').update(source).digest('hex');
    const response=await fetch(OFFICIAL_SCHEMA_URL);
    if(!response.ok) throw new Error('Official schema download failed '+response.status);
    const officialSchema=await response.json();
    const result=validateH02({
      source,yaml:require('js-yaml'),Ajv2020:require('ajv/dist/2020').default,
      officialSchema,gitBlobSha:hash
    });
    process.stdout.write(JSON.stringify(result,null,2)+'\n');
    if(result.result!=='PASS') process.exitCode=1;
  })().catch(err=>{process.stderr.write(String(err)+'\n');process.exitCode=2});
}
