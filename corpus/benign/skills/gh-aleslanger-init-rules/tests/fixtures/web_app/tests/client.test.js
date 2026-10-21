import { test } from 'node:test';
import { strict as assert } from 'node:assert';
import { getAccount } from '../src/api/client.js';

test('sends credentials', async () => {
  let options;
  await getAccount(async (_url, value) => {
    options = value;
    return { ok: true, json: async () => ({ id: 1 }) };
  });
  assert.equal(options.credentials, 'include');
});
