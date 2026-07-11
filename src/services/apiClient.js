const envApiBaseUrl = import.meta.env.VITE_API_BASE_URL || '';
const defaultApiBaseUrl = import.meta.env.DEV ? 'http://localhost:5000' : '';
const isHttpsPage = typeof window !== 'undefined' && window.location.protocol === 'https:';
const configuredApiBaseUrl = isHttpsPage && envApiBaseUrl.startsWith('http://')
  ? ''
  : envApiBaseUrl || defaultApiBaseUrl;

export const API_BASE_URL = configuredApiBaseUrl.replace(/\/+$/, '');
export const USE_BACKEND = import.meta.env.VITE_USE_BACKEND === 'true';

export function resolveApiUrl(path) {
  if (!path) return '';
  if (/^https?:\/\//i.test(path)) return path;
  return `${API_BASE_URL}${path.startsWith('/') ? '' : '/'}${path}`;
}

async function parseResponse(response) {
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(data?.error || `Request failed with status ${response.status}`);
  }
  return data;
}

export async function apiGet(path) {
  return parseResponse(await fetch(resolveApiUrl(path)));
}

export async function apiPost(path, body) {
  return parseResponse(await fetch(resolveApiUrl(path), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  }));
}

export async function apiPatch(path, body) {
  return parseResponse(await fetch(resolveApiUrl(path), {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  }));
}

export async function apiDelete(path) {
  return parseResponse(await fetch(resolveApiUrl(path), { method: 'DELETE' }));
}

export async function apiUpload(path, formData) {
  return parseResponse(await fetch(resolveApiUrl(path), {
    method: 'POST',
    body: formData,
  }));
}
