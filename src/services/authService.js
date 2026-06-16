import { getStore } from '@/services/localStore';

const AUTH_KEY = 'udl_current_user';

export async function getCurrentUser() {
  const storedEmail = localStorage.getItem(AUTH_KEY) || 'student@udl.local';
  const user = getStore().users.find((item) => item.email === storedEmail);
  return user || null;
}

export async function loginAs(role) {
  const user = getStore().users.find((item) => item.role === role);
  if (!user) throw new Error(`No ${role} user exists`);
  localStorage.setItem(AUTH_KEY, user.email);
  return user;
}

export async function logout() {
  localStorage.removeItem(AUTH_KEY);
}
