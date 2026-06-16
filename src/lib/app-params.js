export const appConfig = {
  appName: 'UDL Learn',
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL || '',
};

export const appParams = {
  appBaseUrl: appConfig.apiBaseUrl,
};
