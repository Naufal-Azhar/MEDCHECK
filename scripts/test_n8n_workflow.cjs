// Offline checks of the EXACT JavaScript embedded in the import file.
// No packages, n8n installation, network requests, or credentials needed.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const { test } = require('node:test');
const workflow = JSON.parse(fs.readFileSync(path.join(__dirname, '../workflows/n8n/medlineplus-source-check.json'), 'utf8'));
function run(name, json) {
  const code = workflow.nodes.find(n => n.name === name).parameters.jsCode;
  return vm.runInNewContext(`(function() { ${code} })()`, { $input: { all: () => [{json}] } }, {timeout: 1000});
}
function fixture() {
  return {nlmSearchResult: {count: '1', list: {document: {
    $: {url: 'https://medlineplus.gov/diabetes.html'},
    content: [{$: {name: 'title'}, _: '<span>Diabetes</span>'},
      {$: {name: 'FullSummary'}, _: '<p>Synthetic public summary.</p>'}]
  }}}};
}
test('inactive manual workflow, one external GET, no credentials or retries', () => {
  assert.equal(workflow.active, false);
  assert.equal(workflow.nodes.length, 5);
  assert.equal(workflow.nodes.filter(n => n.type.endsWith('.manualTrigger')).length, 1);
  const http = workflow.nodes.find(n => n.type.endsWith('.httpRequest'));
  assert.equal(http.parameters.method, 'GET');
  assert.equal(http.parameters.url, 'https://wsearch.nlm.nih.gov/ws/query');
  assert.equal(http.retryOnFail, false);
  assert.equal(http.parameters.options.response.response.neverError, false);
  assert.equal(http.parameters.options.response.response.outputPropertyName, 'body');
  for (const node of workflow.nodes) assert.equal(node.credentials, undefined);
});
test('HTTP text output field matches the guard input (default data is not body)', () => {
  const options = workflow.nodes.find(n => n.type.endsWith('.httpRequest')).parameters.options.response.response;
  assert.equal(options.fullResponse, true);
  assert.equal(options.responseFormat, 'text');
  const xml = '<nlmSearchResult><count>1</count></nlmSearchResult>';
  // Mirror HTTP Request text/fullResponse field mapping, not an actual n8n execution.
  const response = {statusCode: 200, headers: {}, [options.outputPropertyName || 'data']: xml};
  assert.equal(run('Check HTTP and XML safety', response)[0].json.data, xml);
  assert.throws(() => run('Check HTTP and XML safety', {statusCode: 200, data: xml}));
});
test('guard accepts expected HTTP response, rejects errors, HTML, oversized and unsafe XML', () => {
  assert.equal(run('Check HTTP and XML safety', {statusCode: 200, body: '<nlmSearchResult></nlmSearchResult>'}).length, 1);
  for (const r of [{statusCode: 503, body: '<nlmSearchResult/>'}, {statusCode: 200, body: ''},
    {statusCode: 200, body: '<html>error</html>'}, {statusCode: 200, body: 'x'.repeat(200001)},
    {statusCode: 200, body: '<!DOCTYPE x><nlmSearchResult/>'},
    {statusCode: 200, body: '<!ENTITY x SYSTEM "file:///test"><nlmSearchResult/>'}]) {
    assert.throws(() => run('Check HTTP and XML safety', r));
  }
});
test('valid parsed XML returns a minimal source report', () => {
  const result = run('Validate and report', fixture())[0].json;
  assert.equal(result.status, 'source_check_passed');
  assert.equal(result.title, 'Diabetes');
  assert.equal(result.valid_documents, 1);
  assert.ok(result.summary_characters > 0);
  assert.equal(result.content, undefined);
});
test('invalid results never produce success', () => {
  for (const mutate of [f => f.nlmSearchResult.count = '0', f => f.nlmSearchResult.error = 'error',
    f => delete f.nlmSearchResult.list, f => f.nlmSearchResult.list.document.content = [],
    f => f.nlmSearchResult.list.document.content[1]._ = '<p> </p>',
    f => f.nlmSearchResult.list.document.$.url = 'https://medlineplus.gov.evil.invalid/a.html',
    f => f.nlmSearchResult.list.document.$.url = 'https://medlineplus.gov@evil.invalid/a.html']) {
    const f = fixture(); mutate(f); assert.throws(() => run('Validate and report', f));
  }
});
