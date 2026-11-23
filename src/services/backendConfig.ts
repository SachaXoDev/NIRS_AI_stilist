export const USE_REAL_BACKEND = import.meta.env.VITE_USE_REAL_BACKEND === 'true';
export const BACKEND_URL = (import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000').replace(/\/+$/, '');
