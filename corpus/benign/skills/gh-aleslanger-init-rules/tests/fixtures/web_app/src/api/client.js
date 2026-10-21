export async function getAccount(fetchImpl = fetch) {
  const response = await fetchImpl('/api/account', { credentials: 'include' });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}
