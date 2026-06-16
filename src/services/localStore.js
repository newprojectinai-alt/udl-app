import { seedData } from '@/data/localSeedData';

const STORAGE_KEY = 'udl_learn_data_v1';

const clone = (value) => JSON.parse(JSON.stringify(value));

export function getStore() {
  const raw = localStorage.getItem(STORAGE_KEY);
  if (!raw) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(seedData));
    return clone(seedData);
  }
  return JSON.parse(raw);
}

export function setStore(nextStore) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(nextStore));
}

export function resetStore() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(seedData));
  return clone(seedData);
}
