import axios from 'axios';

const baseURL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api';
const defaultTimeout = Number(import.meta.env.VITE_API_TIMEOUT ?? '10000');

let authToken: string | null = null;

export const setAuthToken = (token: string | null): void => {
  authToken = token;
};

export const httpClient = axios.create({
  baseURL,
  timeout: Number.isNaN(defaultTimeout) ? 10000 : defaultTimeout,
});

httpClient.interceptors.request.use((config) => {
  if (authToken) {
    config.headers = config.headers ?? {};
    config.headers.Authorization = `Bearer ${authToken}`;
  }
  return config;
});

httpClient.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API request failed', error);
    return Promise.reject(error);
  }
);
