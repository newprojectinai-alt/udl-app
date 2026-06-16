export function cn(...classes) {
  return classes.filter(Boolean).join(' ');
}

export const isIframe = window.self !== window.top;
