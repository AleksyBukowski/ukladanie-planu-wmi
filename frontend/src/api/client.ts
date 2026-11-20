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

// --- Błędy API ------------------------------------------------------------------------------

/** Pojedynczy błąd z raportu importu (FR-05) – patrz docs/format-importu.md, sekcja 6. */
export interface ImportIssue {
  file?: string | null;
  row?: number | null;
  column?: string | null;
  message: string;
}

/** Odpowiedź 422 importu: nic nie zapisano, `errors` zawiera wszystkie błędy. */
export interface ImportErrorResponse {
  detail: string;
  errors: ImportIssue[];
}

function isImportErrorResponse(body: unknown): body is ImportErrorResponse {
  return (
    typeof body === 'object' &&
    body !== null &&
    Array.isArray((body as ImportErrorResponse).errors) &&
    typeof (body as ImportErrorResponse).detail === 'string'
  );
}

/** Raport błędów importu z odpowiedzi 422 albo `null`, jeśli to inny błąd. */
export function getImportErrors(error: unknown): ImportErrorResponse | null {
  if (error instanceof ApiError && error.status === 422 && isImportErrorResponse(error.body)) {
    return error.body;
  }
  return null;
}

/** Czytelny komunikat dla planisty – dla dowolnego błędu z `apiFetch`. */
export function describeApiError(error: unknown): string {
  if (!(error instanceof ApiError)) {
    return 'Brak połączenia z serwerem. Sprawdź, czy backend działa, i spróbuj ponownie.';
  }
  const body = error.body as { detail?: unknown } | string | null;
  const detail = typeof body === 'object' && body !== null ? body.detail : undefined;
  // Domyślne „Not Found” FastAPI = brak endpointu (np. backend bez danej funkcji).
  if (error.status === 404 && (detail === undefined || detail === 'Not Found')) {
    return 'Ta funkcja nie jest jeszcze dostępna w API (404) – backend nie ma tego endpointu.';
  }
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail) && detail.length > 0) {
    // Walidacja FastAPI/Pydantic: [{ loc: [...], msg: "..." }, ...]
    return detail
      .map((item: { loc?: unknown[]; msg?: string }) => {
        const where = item.loc?.filter((part) => part !== 'body').join(' → ');
        return where ? `${where}: ${item.msg}` : item.msg;
      })
      .join('; ');
  }
  if (error.status === 413) return 'Plik jest za duży – maksymalny rozmiar to 5 MB.';
  return `Serwer zwrócił błąd ${error.status}.`;
}

// --- Siatka godzin (FR-03) ------------------------------------------------------------------

export interface TimeSlotInput {
  day_of_week: number; // 0 = poniedziałek … 6 = niedziela
  start_time: string; // "GG:MM"
  end_time: string;
}

export interface TimeSlot extends TimeSlotInput {
  id: number;
}

export interface TimeGridImportResult {
  imported: number;
  time_slots: TimeSlot[];
}

export const getTimeSlots = () => apiFetch<TimeSlot[]>('/time-slots');

/** Zastępuje całą siatkę (w całości albo wcale; błędy → 422 z raportem). */
export const replaceTimeGrid = (slots: TimeSlotInput[]) =>
  apiFetch<TimeSlot[]>('/time-slots', { method: 'PUT', body: JSON.stringify(slots) });

/** Importuje siatkę z pliku CSV/XLSX i zastępuje nią dotychczasową. */
export const importTimeGrid = (file: File) => {
  const formData = new FormData();
  formData.append('file', file);
  return apiFetch<TimeGridImportResult>('/time-slots/import', { method: 'POST', body: formData });
};

// --- Import danych wejściowych (FR-04) ------------------------------------------------------

export const INPUT_FILE_KEYS = ['rooms', 'groups', 'teachers', 'courses', 'assignments'] as const;
export type InputFileKey = (typeof INPUT_FILE_KEYS)[number];

/** Liczba zapisanych rekordów każdego rodzaju. */
export type DataImportSummary = Record<InputFileKey, number>;

/** Import kompletu pięciu plików – zastępuje wszystkie dotychczasowe dane wejściowe. */
export const importInputData = (files: Record<InputFileKey, File>) => {
  const formData = new FormData();
  for (const key of INPUT_FILE_KEYS) {
    formData.append(key, files[key]);
  }
  return apiFetch<DataImportSummary>('/imports', { method: 'POST', body: formData });
};
