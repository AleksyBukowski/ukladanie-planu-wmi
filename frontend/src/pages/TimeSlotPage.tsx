import {
  ActionIcon,
  Alert,
  Badge,
  Button,
  Chip,
  FileInput,
  Group,
  Loader,
  Paper,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
} from '@mantine/core';
import {
  IconAlertCircle,
  IconCheck,
  IconClock,
  IconDeviceFloppy,
  IconFileText,
  IconInfoCircle,
  IconPlus,
  IconRefresh,
  IconTrash,
  IconUpload,
} from '@tabler/icons-react';
import { useCallback, useEffect, useMemo, useState } from 'react';

import {
  describeApiError,
  getImportErrors,
  getTimeSlots,
  importTimeGrid,
  type ImportIssue,
  replaceTimeGrid,
  type TimeSlot,
  type TimeSlotInput,
} from '../api/client';
import { ImportIssuesTable } from '../components/ImportIssuesTable';

interface SlotRow {
  key: number;
  startTime: string;
  endTime: string;
}

type Feedback =
  | { kind: 'success'; message: string }
  | { kind: 'error'; message: string; issues?: ImportIssue[]; rowLabel?: string };

// Domyślne pasma zajęciowe WMiI UAM (90 min + 15 min przerwy).
const DEFAULT_BLOCKS: [string, string][] = [
  ['08:00', '09:30'],
  ['09:45', '11:15'],
  ['11:30', '13:00'],
  ['13:15', '14:45'],
  ['15:00', '16:30'],
  ['16:45', '18:15'],
  ['18:30', '20:00'],
];
const DEFAULT_DAYS = ['0', '1', '2', '3', '4'];

const DAYS_OF_WEEK = [
  'Poniedziałek',
  'Wtorek',
  'Środa',
  'Czwartek',
  'Piątek',
  'Sobota',
  'Niedziela',
].map((label, index) => ({ label, value: String(index) }));

const TIME_PATTERN = /^([01]\d|2[0-3]):[0-5]\d$/;

let nextKey = 1;
const makeRows = (blocks: [string, string][]): SlotRow[] =>
  blocks.map(([startTime, endTime]) => ({ key: nextKey++, startTime, endTime }));

/** "08:00:00" → "08:00" (API zwraca godziny z sekundami). */
const shortTime = (value: string) => value.slice(0, 5);

const toMinutes = (value: string) => {
  const [hours, minutes] = value.split(':').map(Number);
  return hours * 60 + minutes;
};

/** Błędy pojedynczych wierszy edytora – sprawdzane na bieżąco, zanim cokolwiek trafi do API. */
function validateRows(rows: SlotRow[]): Map<number, string> {
  const errors = new Map<number, string>();
  for (const row of rows) {
    if (!TIME_PATTERN.test(row.startTime) || !TIME_PATTERN.test(row.endTime)) {
      errors.set(row.key, 'Podaj godziny w formacie GG:MM.');
    } else if (toMinutes(row.endTime) <= toMinutes(row.startTime)) {
      errors.set(row.key, 'Koniec musi być później niż początek.');
    }
  }
  const valid = rows
    .filter((row) => !errors.has(row.key))
    .sort((a, b) => toMinutes(a.startTime) - toMinutes(b.startTime));
  for (let i = 1; i < valid.length; i++) {
    if (toMinutes(valid[i].startTime) < toMinutes(valid[i - 1].endTime)) {
      errors.set(
        valid[i].key,
        `Nachodzi na blok ${valid[i - 1].startTime}–${valid[i - 1].endTime}.`,
      );
    }
  }
  return errors;
}

/**
 * Zamienia zapisaną siatkę na stan edytora: dni + wspólna lista bloków.
 * Edytor zakłada te same bloki w każdym dniu (tak jest na WMiI); `uniform` mówi, czy tak jest.
 */
function gridToEditor(slots: TimeSlot[]) {
  const byDay = new Map<number, string[]>();
  for (const slot of slots) {
    const block = `${shortTime(slot.start_time)}-${shortTime(slot.end_time)}`;
    byDay.set(slot.day_of_week, [...(byDay.get(slot.day_of_week) ?? []), block]);
  }
  const days = [...byDay.keys()].sort((a, b) => a - b);
  const signatures = days.map((day) => byDay.get(day)!.sort().join(','));
  const firstDayBlocks = byDay.get(days[0])!.map((b) => b.split('-') as [string, string]);
  return {
    days: days.map(String),
    rows: makeRows(firstDayBlocks),
    uniform: signatures.every((signature) => signature === signatures[0]),
  };
}

export function TimeSlotPage() {
  const [selectedDays, setSelectedDays] = useState<string[]>(DEFAULT_DAYS);
  const [rows, setRows] = useState<SlotRow[]>(() => makeRows(DEFAULT_BLOCKS));
  const [savedCount, setSavedCount] = useState<number | null>(null);
  const [nonUniform, setNonUniform] = useState(false);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [importing, setImporting] = useState(false);
  const [feedback, setFeedback] = useState<Feedback | null>(null);

  const rowErrors = useMemo(() => validateRows(rows), [rows]);
  const canSave = selectedDays.length > 0 && rows.length > 0 && rowErrors.size === 0;

  const applyGrid = useCallback((slots: TimeSlot[]) => {
    setSavedCount(slots.length);
    if (slots.length === 0) {
      setNonUniform(false);
      return;
    }
    const editor = gridToEditor(slots);
    setSelectedDays(editor.days);
    setRows(editor.rows);
    setNonUniform(!editor.uniform);
  }, []);

  useEffect(() => {
    getTimeSlots()
      .then(applyGrid)
      .catch((error) => setLoadError(describeApiError(error)))
      .finally(() => setLoading(false));
  }, [applyGrid]);

  const updateRow = (key: number, field: 'startTime' | 'endTime', value: string) =>
    setRows((current) =>
      current.map((row) => (row.key === key ? { ...row, [field]: value } : row)),
    );

  const addRow = () => {
    const last = rows[rows.length - 1];
    // Nowy blok zaczyna się 15 min po ostatnim i trwa 90 min – zwykle wystarczy go zapisać.
    const start = last && TIME_PATTERN.test(last.endTime) ? toMinutes(last.endTime) + 15 : 8 * 60;
    const fmt = (m: number) =>
      `${String(Math.floor(m / 60) % 24).padStart(2, '0')}:${String(m % 60).padStart(2, '0')}`;
    setRows([...rows, ...makeRows([[fmt(start), fmt(start + 90)]])]);
  };

  const resetToDefaults = () => {
    setRows(makeRows(DEFAULT_BLOCKS));
    setSelectedDays(DEFAULT_DAYS);
    setFeedback(null);
  };

  const handleSave = async () => {
    setSaving(true);
    setFeedback(null);
    const sortedRows = [...rows].sort((a, b) => toMinutes(a.startTime) - toMinutes(b.startTime));
    const payload: TimeSlotInput[] = [...selectedDays].sort().flatMap((day) =>
      sortedRows.map((row) => ({
        day_of_week: Number(day),
        start_time: row.startTime,
        end_time: row.endTime,
      })),
    );
    try {
      const saved = await replaceTimeGrid(payload);
      applyGrid(saved);
      setFeedback({
        kind: 'success',
        message: `Zapisano siatkę: ${saved.length} bloków w tygodniu.`,
      });
    } catch (error) {
      const report = getImportErrors(error);
      setFeedback({
        kind: 'error',
        message: report?.detail ?? describeApiError(error),
        issues: report?.errors,
        rowLabel: 'Pozycja',
      });
    } finally {
      setSaving(false);
    }
  };

  const handleImport = async () => {
    if (!file) return;
    setImporting(true);
    setFeedback(null);
    try {
      const result = await importTimeGrid(file);
      applyGrid(result.time_slots);
      setFile(null);
      setFeedback({
        kind: 'success',
        message: `Zaimportowano siatkę z pliku „${file.name}”: ${result.imported} bloków.`,
      });
    } catch (error) {
      const report = getImportErrors(error);
      setFeedback({
        kind: 'error',
        message: report?.detail ?? describeApiError(error),
        issues: report?.errors,
      });
    } finally {
      setImporting(false);
    }
  };

  return (
    <Stack gap="lg" maw={960}>
      <Group justify="space-between" align="flex-end">
        <div>
          <Text size="xs" tt="uppercase" fw={600} c="dimmed" lts={1}>
            Konfiguracja semestru
          </Text>
          <Title order={2}>Siatka godzin</Title>
          <Text size="sm" c="dimmed">
            Dni zajęć i bloki godzinowe, do których solver i planista przydzielają zajęcia (FR-03).
          </Text>
        </div>
        <Group>
          {savedCount !== null && (
            <Badge variant="light" color={savedCount > 0 ? 'green' : 'gray'} size="lg">
              {savedCount > 0 ? `Zapisane bloki: ${savedCount}` : 'Siatka niezapisana'}
            </Badge>
          )}
        </Group>
      </Group>

      {loading && (
        <Group gap="xs">
          <Loader size="sm" />
          <Text size="sm">Wczytywanie zapisanej siatki…</Text>
        </Group>
      )}

      {loadError && (
        <Alert color="red" icon={<IconAlertCircle />} title="Nie udało się wczytać siatki">
          {loadError} Edytor pokazuje domyślne pasma WMiI.
        </Alert>
      )}

      {savedCount === 0 && !loadError && (
        <Alert color="blue" icon={<IconInfoCircle />} title="Siatka nie jest jeszcze zapisana">
          Poniżej są domyślne pasma WMiI – popraw je w razie potrzeby i kliknij „Zapisz siatkę”.
        </Alert>
      )}

      {nonUniform && (
        <Alert color="orange" icon={<IconAlertCircle />} title="Dni mają różne bloki">
          Zapisana siatka ma inne bloki w różnych dniach. Edytor pokazuje bloki pierwszego dnia, a
          zapis ustawi te same bloki we wszystkich zaznaczonych dniach. Aby zachować różne bloki,
          użyj importu z pliku.
        </Alert>
      )}

      {feedback?.kind === 'success' && (
        <Alert
          color="teal"
          icon={<IconCheck />}
          title="Zapisano"
          withCloseButton
          onClose={() => setFeedback(null)}
        >
          {feedback.message}
        </Alert>
      )}

      {feedback?.kind === 'error' && (
        <Alert color="red" icon={<IconAlertCircle />} title="Nic nie zostało zapisane">
          <Stack gap="sm">
            <Text size="sm">{feedback.message}</Text>
            {feedback.issues && feedback.issues.length > 0 && (
              <ImportIssuesTable issues={feedback.issues} rowLabel={feedback.rowLabel} />
            )}
          </Stack>
        </Alert>
      )}

      <Paper p="md" withBorder>
        <Text fw={600} size="sm" mb="xs">
          Dni zajęć
        </Text>
        <Chip.Group multiple value={selectedDays} onChange={setSelectedDays}>
          <Group gap="xs">
            {DAYS_OF_WEEK.map((day) => (
              <Chip key={day.value} value={day.value} variant="outline">
                {day.label}
              </Chip>
            ))}
          </Group>
        </Chip.Group>
        {selectedDays.length === 0 && (
          <Text size="xs" c="red" mt="xs">
            Zaznacz co najmniej jeden dzień.
          </Text>
        )}
      </Paper>

      <Paper p="md" withBorder>
        <Group justify="space-between" mb="md">
          <Group gap="xs">
            <IconClock size={20} />
            <Text fw={600} size="sm">
              Bloki godzinowe (te same w każdym zaznaczonym dniu)
            </Text>
          </Group>
          <Group gap="xs">
            <Button
              variant="subtle"
              size="xs"
              leftSection={<IconRefresh size={14} />}
              onClick={resetToDefaults}
            >
              Domyślne pasma WMiI
            </Button>
            <Button variant="light" size="xs" leftSection={<IconPlus size={14} />} onClick={addRow}>
              Dodaj blok
            </Button>
          </Group>
        </Group>

        <Table withTableBorder withColumnBorders striped verticalSpacing="xs">
          <Table.Thead>
            <Table.Tr>
              <Table.Th w={50}>#</Table.Th>
              <Table.Th>Początek</Table.Th>
              <Table.Th>Koniec</Table.Th>
              <Table.Th w={110}>Długość</Table.Th>
              <Table.Th w={70} />
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {rows.map((row, index) => {
              const error = rowErrors.get(row.key);
              const minutes =
                TIME_PATTERN.test(row.startTime) && TIME_PATTERN.test(row.endTime)
                  ? toMinutes(row.endTime) - toMinutes(row.startTime)
                  : null;
              return (
                <Table.Tr key={row.key}>
                  <Table.Td>
                    <Badge variant="light" size="sm">
                      {index + 1}
                    </Badge>
                  </Table.Td>
                  <Table.Td>
                    <TextInput
                      type="time"
                      size="xs"
                      aria-label={`Początek bloku ${index + 1}`}
                      value={row.startTime}
                      error={error}
                      onChange={(e) => updateRow(row.key, 'startTime', e.currentTarget.value)}
                    />
                  </Table.Td>
                  <Table.Td>
                    <TextInput
                      type="time"
                      size="xs"
                      aria-label={`Koniec bloku ${index + 1}`}
                      value={row.endTime}
                      error={Boolean(error)}
                      onChange={(e) => updateRow(row.key, 'endTime', e.currentTarget.value)}
                    />
                  </Table.Td>
                  <Table.Td>
                    <Text size="xs" c="dimmed">
                      {minutes !== null && minutes > 0 ? `${minutes} min` : '–'}
                    </Text>
                  </Table.Td>
                  <Table.Td ta="center">
                    <ActionIcon
                      color="red"
                      variant="subtle"
                      size="sm"
                      aria-label={`Usuń blok ${index + 1}`}
                      onClick={() => setRows(rows.filter((r) => r.key !== row.key))}
                      disabled={rows.length <= 1}
                    >
                      <IconTrash size={16} />
                    </ActionIcon>
                  </Table.Td>
                </Table.Tr>
              );
            })}
          </Table.Tbody>
        </Table>

        <Group justify="space-between" mt="md">
          <Text size="sm" c="dimmed">
            {selectedDays.length} dni × {rows.length} bloków = {selectedDays.length * rows.length}{' '}
            bloków w tygodniu
          </Text>
          <Button
            leftSection={<IconDeviceFloppy size={16} />}
            loading={saving}
            disabled={!canSave || loading}
            onClick={handleSave}
          >
            Zapisz siatkę
          </Button>
        </Group>
      </Paper>

      <Paper p="md" withBorder>
        <Text fw={600} size="sm">
          Import siatki z pliku
        </Text>
        <Text size="xs" c="dimmed" mb="sm">
          Plik CSV lub XLSX z kolumnami <b>day_of_week</b>, <b>start_time</b>, <b>end_time</b>{' '}
          (szablon: data/templates/time_slots, opis: docs/format-importu.md). Import zastępuje całą
          zapisaną siatkę.
        </Text>
        <Group align="flex-end">
          <FileInput
            placeholder="Wybierz plik .csv lub .xlsx"
            accept=".csv,.xlsx"
            value={file}
            onChange={setFile}
            leftSection={<IconFileText size={16} />}
            clearable
            style={{ flex: 1, maxWidth: 420 }}
          />
          <Button
            variant="light"
            leftSection={<IconUpload size={16} />}
            disabled={!file}
            loading={importing}
            onClick={handleImport}
          >
            Importuj
          </Button>
        </Group>
      </Paper>
    </Stack>
  );
}
