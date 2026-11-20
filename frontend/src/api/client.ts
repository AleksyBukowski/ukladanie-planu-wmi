// Cienki wrapper na fetch. Wszystkie ścieżki są względne (/api/...) – patrz vite.config.ts.

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly body: unknown,
  ) {
    super(`API error ${status}`);
  }
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, {
    ...init,
    headers: {
      Accept: 'application/json',
      ...(init?.body && !(init.body instanceof FormData)
        ? { 'Content-Type': 'application/json' }
        : {}),
      ...init?.headers,
    },
  });

  const isJson = response.headers.get('content-type')?.includes('application/json');
  const body: unknown = isJson ? await response.json() : await response.text();

  if (!response.ok) {
    throw new ApiError(response.status, body);
  }
  return body as T;
}

export interface HealthResponse {
  status: string;
  database: string;
}

export const getHealth = () => apiFetch<HealthResponse>('/health');

export interface TimeSlotDto {
  id?: number;
  day_of_week: number;
  start_time: string;
  end_time: string;
}

export interface ImportErrorDetail {
  row: number;
  field?: string;
  value?: string;
  message: string;
}

export interface ImportResultDto {
  success: boolean;
  entity_type?: string;
  imported_count?: number;
  errors?: ImportErrorDetail[];
}

export const getTimeSlots = () => apiFetch<TimeSlotDto[]>('/time-slots');

export const saveTimeSlots = (slots: TimeSlotDto[]) =>
  apiFetch<TimeSlotDto[]>('/time-slots', {
    method: 'POST',
    body: JSON.stringify(slots),
  });

export const uploadImportFile = (file: File, entityType: string) => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('entity_type', entityType);
  return apiFetch<ImportResultDto>('/import', {
    method: 'POST',
    body: formData,
  });
};
