import { useEffect } from 'react';

export default function ThemeProvider({ children }) {
  useEffect(() => {
    const apply = (dark) => {
      document.documentElement.classList.toggle('dark', dark);
    };

    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    apply(mediaQuery.matches);
    const handler = (event) => apply(event.matches);
    mediaQuery.addEventListener('change', handler);
    return () => mediaQuery.removeEventListener('change', handler);
  }, []);

  return children;
}
