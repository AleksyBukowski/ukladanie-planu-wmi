import {
  Alert,
  Badge,
  Button,
  Code,
  FileButton,
  FileInput,
  Group,
  Paper,
  Stack,
  Table,
  Text,
  Title,
} from '@mantine/core';
import {
  IconAlertCircle,
  IconCheck,
  IconFiles,
  IconFileText,
  IconInfoCircle,
  IconUpload,
} from '@tabler/icons-react';
import { useState } from 'react';

import {
  type DataImportSummary,
  describeApiError,
  getImportErrors,
  importInputData,
  type ImportIssue,
  INPUT_FILE_KEYS,
  type InputFileKey,
} from '../api/client';
import { ImportIssuesTable } from '../components/ImportIssuesTable';

// Opis plików zgodny ze specyfikacją importu D-03 (docs/format-importu.md, sekcja 4).
const FILE_SPECS: Record<InputFileKey, { label: string; columns: string; aliases: string[] }> = {
  rooms: { label: 'Sale', columns: 'code, capacity, room_type', aliases: ['sale'] },
  groups: { label: 'Grupy', columns: 'code, name, size', aliases: ['grupy'] },
  teachers: {
    label: 'Prowadzący',
    columns: 'external_id, title (opcjonalna), first_name, last_name',
    aliases: ['prowadzacy'],
  },
  courses: { label: 'Przedmioty', columns: 'code, name', aliases: ['przedmioty'] },
  assignments: {
    label: 'Przypisania',
    columns:
      'course_code, teacher_external_id, group_code, class_type, required_room_type, units_per_week',
    aliases: ['przypisania'],
  },
};

const FILE_LABELS: Record<string, string> = Object.fromEntries(
  INPUT_FILE_KEYS.map((key) => [key, FILE_SPECS[key].label]),
);

type Files = Partial<Record<InputFileKey, File>>;

type Result =
  | { kind: 'success'; summary: DataImportSummary }
  | { kind: 'error'; message: string; issues?: ImportIssue[] };

/** Dopasowuje plik do rodzaju danych po nazwie, np. `rooms.csv`, `Sale.xlsx`, `teachers_2026.csv`. */
function matchFileKey(fileName: string): InputFileKey | null {
  const stem = fileName
    .toLowerCase()
    .replace(/\.[^.]+$/, '')
    .normalize('NFKD')
    .replace(/[̀-ͯ]/g, '');
  return (
    INPUT_FILE_KEYS.find((key) =>
      [key, ...FILE_SPECS[key].aliases].some((name) => stem.startsWith(name)),
    ) ?? null
  );
}

export function ImportPage() {
  const [files, setFiles] = useState<Files>({});
  const [unmatched, setUnmatched] = useState<string[]>([]);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<Result | null>(null);

  const missing = INPUT_FILE_KEYS.filter((key) => !files[key]);

  const setFile = (key: InputFileKey, file: File | null) => {
    setFiles((current) => {
      const next = { ...current };
      if (file) next[key] = file;
      else delete next[key];
      return next;
    });
    setResult(null);
  };

  const handleMultiple = (selected: File[]) => {
    const notMatched: string[] = [];
    const matched: Files = {};
    for (const file of selected) {
      const key = matchFileKey(file.name);
      if (key) matched[key] = file;
      else notMatched.push(file.name);
    }
    setFiles((current) => ({ ...current, ...matched }));
    setUnmatched(notMatched);
    setResult(null);
  };

  const handleImport = async () => {
    if (missing.length > 0) return;
    setUploading(true);
    setResult(null);
    try {
      const summary = await importInputData(files as Record<InputFileKey, File>);
      setResult({ kind: 'success', summary });
    } catch (error) {
      const report = getImportErrors(error);
      setResult({
        kind: 'error',
        message: report?.detail ?? describeApiError(error),
        issues: report?.errors,
      });
    } finally {
      setUploading(false);
    }
  };

  return (
    <Stack gap="lg" maw={1100}>
      <div>
        <Text size="xs" tt="uppercase" fw={600} c="dimmed" lts={1}>
          Dane wejściowe
        </Text>
        <Title order={2}>Import danych</Title>
        <Text size="sm" c="dimmed">
          Sale, grupy, prowadzący, przedmioty i przypisania z plików CSV/XLSX – eksport z USOS albo
          szablony z data/templates (format: docs/format-importu.md, D-03).
        </Text>
      </div>

      <Alert color="blue" icon={<IconInfoCircle />}>
        Import wymaga <b>kompletu pięciu plików</b> i <b>zastępuje wszystkie</b> dotychczasowe dane
        wejściowe. Wykonuje się w całości albo wcale – przy jakimkolwiek błędzie nic nie zostanie
        zapisane. Siatka godzin pozostaje bez zmian.
      </Alert>

      <Paper p="md" withBorder>
        <Group justify="space-between" mb="md">
          <div>
            <Text fw={600} size="sm">
              Pliki do importu
            </Text>
            <Text size="xs" c="dimmed">
              Wybierz pliki pojedynczo albo wszystkie naraz – zostaną dopasowane po nazwie (np.
              rooms.csv, sale.xlsx).
            </Text>
          </div>
          <FileButton onChange={handleMultiple} accept=".csv,.xlsx" multiple>
            {(props) => (
              <Button {...props} variant="light" leftSection={<IconFiles size={16} />}>
                Wybierz wszystkie pliki
              </Button>
            )}
          </FileButton>
        </Group>

        {unmatched.length > 0 && (
          <Alert
            color="orange"
            icon={<IconAlertCircle />}
            mb="md"
            withCloseButton
            onClose={() => setUnmatched([])}
          >
            Nie rozpoznano: {unmatched.join(', ')}. Wskaż te pliki ręcznie w odpowiednim wierszu.
          </Alert>
        )}

        <Table withTableBorder withColumnBorders verticalSpacing="sm">
          <Table.Thead>
            <Table.Tr>
              <Table.Th w={130}>Dane</Table.Th>
              <Table.Th>Wymagane kolumny</Table.Th>
              <Table.Th w={340}>Plik</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {INPUT_FILE_KEYS.map((key) => (
              <Table.Tr key={key}>
                <Table.Td>
                  <Text size="sm" fw={500}>
                    {FILE_SPECS[key].label}
                  </Text>
                  <Code>{key}</Code>
                </Table.Td>
                <Table.Td>
                  <Text size="xs" ff="monospace">
                    {FILE_SPECS[key].columns}
                  </Text>
                </Table.Td>
                <Table.Td>
                  <FileInput
                    size="xs"
                    placeholder="Wybierz .csv lub .xlsx"
                    accept=".csv,.xlsx"
                    aria-label={`Plik: ${FILE_SPECS[key].label}`}
                    value={files[key] ?? null}
                    onChange={(file) => setFile(key, file)}
                    leftSection={<IconFileText size={14} />}
                    clearable
                  />
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>

        <Group justify="space-between" mt="md">
          <Text size="sm" c={missing.length ? 'dimmed' : 'teal'}>
            {missing.length
              ? `Brakuje: ${missing.map((key) => FILE_SPECS[key].label).join(', ')}`
              : 'Komplet plików – można importować.'}
          </Text>
          <Button
            leftSection={<IconUpload size={16} />}
            disabled={missing.length > 0}
            loading={uploading}
            onClick={handleImport}
          >
            Importuj dane
          </Button>
        </Group>
      </Paper>

      {result?.kind === 'success' && (
        <Alert color="teal" icon={<IconCheck />} title="Import zakończony">
          <Text size="sm" mb="xs">
            Dane wejściowe zostały zastąpione zawartością plików.
          </Text>
          <Group gap="xs">
            {INPUT_FILE_KEYS.map((key) => (
              <Badge key={key} variant="light" color="teal" size="lg">
                {FILE_SPECS[key].label}: {result.summary[key]}
              </Badge>
            ))}
          </Group>
        </Alert>
      )}

      {result?.kind === 'error' && (
        <Alert
          color="red"
          icon={<IconAlertCircle />}
          title="Import odrzucony – nic nie zostało zapisane"
        >
          <Stack gap="sm">
            <Text size="sm">{result.message}</Text>
            {result.issues && result.issues.length > 0 && (
              <>
                <Text size="sm">
                  Błędów: <b>{result.issues.length}</b>. Popraw pliki i wgraj je ponownie.
                </Text>
                <ImportIssuesTable issues={result.issues} fileLabels={FILE_LABELS} />
              </>
            )}
          </Stack>
        </Alert>
      )}
    </Stack>
  );
}
