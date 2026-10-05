import { CreateInvestigationPayload, Investigation } from '../types';
import { apiClient } from './client';

export async function createInvestigation(
  payload?: CreateInvestigationPayload
): Promise<Investigation> {
  return apiClient<Investigation>('/v1/investigations', {
    method: 'POST',
    body: JSON.stringify(payload || {}),
  });
}

export async function fetchInvestigationById(
  id: string
): Promise<Investigation> {
  return apiClient<Investigation>(`/v1/investigations/${encodeURIComponent(id)}`);
}
