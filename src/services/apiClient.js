export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000';
export const USE_BACKEND = import.meta.env.VITE_USE_BACKEND === 'true';

async function parseResponse(response) {
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(data?.error || `Request failed with status ${response.status}`);
  }
  return data;
}

export async function apiGet(path) {
  return parseResponse(await fetch(`${API_BASE_URL}${path}`));
}

export async function apiPost(path, body) {
  return parseResponse(await fetch(`${API_BASE_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  }));
}

export async function apiPatch(path, body) {
  return parseResponse(await fetch(`${API_BASE_URL}${path}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  }));
}

export async function apiDelete(path) {
  return parseResponse(await fetch(`${API_BASE_URL}${path}`, { method: 'DELETE' }));
}

export async function apiUpload(path, formData) {
  return parseResponse(await fetch(`${API_BASE_URL}${path}`, {
    method: 'POST',
    body: formData,
  }));
}
