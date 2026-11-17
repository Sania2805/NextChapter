const base = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '');
export async function api(path, { method = 'GET', body, signal } = {}) {
  let response;
  try {
    response = await fetch(base + '/api' + path, {
      method, signal, credentials: 'include',
      headers: method === 'GET' ? {} : { 'X-NextChapter': '1', ...(body ? {'Content-Type': 'application/json'} : {}) },
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch (error) {
    if (error.name === 'AbortError') throw error;
    throw new Error('Could not reach NextChapter. Check that the API is running and try again.');
  }
  if (response.status === 204) return null;
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw Object.assign(new Error(typeof data.detail === 'string' ? data.detail : 'Something went wrong. Try again.'), { status: response.status });
  }
  return data;
}

