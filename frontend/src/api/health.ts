import { HealthResponse, ReadinessResponse } from '../types';
import { apiClient } from './client';

export async function fetchHealth(): Promise<HealthResponse> {
  return apiClient<HealthResponse>('/health');
}

export async function fetchReadiness(): Promise<ReadinessResponse> {
  return apiClient<ReadinessResponse>('/health/ready');
}
