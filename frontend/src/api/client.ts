import { ApiErrorResponse } from '../types';

export class ApiError extends Error {
  public code: string;
  public status: number;
  public requestId?: string;
  public details?: unknown;

  constructor(message: string, code: string, status: number, requestId?: string, details?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.status = status;
    this.requestId = requestId;
    this.details = details;
  }
}

// In Vite development, the Vite proxy handles '/api' → 'http://localhost:8000'.
// In production (Docker/Nginx), Nginx proxies '/api/' → 'http://api:8000/'.
const BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

export async function apiClient<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${BASE_URL}${endpoint}`;
  
  const headers = new Headers(options.headers || {});
  if (!headers.has('Content-Type') && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }

  try {
    const response = await fetch(url, {
      ...options,
      headers,
    });

    const isJson = response.headers.get('content-type')?.includes('application/json');
    const data = isJson ? await response.json() : null;

    if (!response.ok) {
      if (data && 'error' in data) {
        const err = (data as ApiErrorResponse).error;
        throw new ApiError(
          err.message || 'API request failed',
          err.code || 'API_ERROR',
          response.status,
          err.request_id,
          err.details
        );
      }
      throw new ApiError(
        response.statusText || 'Network request failed',
        'HTTP_ERROR',
        response.status
      );
    }

    return data as T;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    throw new ApiError(
      error instanceof Error ? error.message : 'Backend connection unavailable',
      'CONNECTION_FAILED',
      0
    );
  }
}
