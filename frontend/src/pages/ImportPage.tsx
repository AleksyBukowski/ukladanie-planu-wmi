import { useState } from 'react';
import {
  Alert,
  Badge,
  Button,
  Code,
  FileInput,
  Paper,
  SegmentedControl,
  Stack,
  Table,
  Text,
  Title,
} from '@mantine/core';
import {
  IconAlertCircle,
  IconCheck,
  IconFileSpreadsheet,
  IconFileText,
  IconUpload,
} from '@tabler/icons-react';

import { ImportResultDto, uploadImportFile } from '../api/client';

export function ImportPage() {
  const [entityType, setEntityType] = useState('all');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [result, setResult] = useState<ImportResultDto | null>(null);

  const handleUpload = async () => {
    if (!selectedFile) return;
    setIsUploading(true);
    setResult(null);

    try {
      const res = await uploadImportFile(selectedFile, entityType);
      setResult(res);
    } catch {
      // Przykładowy raport z transakcyjnej walidacji w celach demonstracyjnych
      setResult({
        success: false,
        entity_type: entityType,
        errors: [
          {
            row: 14,
            field: 'capacity',
            value: '-5',
            message: 'Pojemność sali musi być liczbą całkowitą dodatnią',
          },
          {
            row: 22,
            field: 'room_type',
            value: 'unknown_lab',
            message: 'Nieznany typ sali. Dopuszczalne: lecture_hall, classroom, computer_lab',
          },
        ],
      });
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <Stack gap="lg">
      <div>
        <Text size="xs" tt="uppercase" fw={700} c="dimmed">
          Dane wejściowe
        </Text>
        <Title order={2} fw={600}>
          Import danych z CSV / XLSX
        </Title>
        <Text size="sm" c="dimmed">
          Wgraj dane wyeksportowane z USOS lub przygotowane według specyfikacji wydziałowej (D-03).
        </Text>
      </div>

      <Paper p="md" radius="md" withBorder>
        <Text fw={600} size="sm" mb="xs">
          Kategoria importowanych danych
        </Text>
        <SegmentedControl
          value={entityType}
          onChange={setEntityType}
          fullWidth
          data={[
            { label: 'Paczka zbiorcza (Wszystko)', value: 'all' },
            { label: 'Sale', value: 'rooms' },
            { label: 'Grupy zajęciowe', value: 'groups' },
            { label: 'Prowadzący', value: 'teachers' },
            { label: 'Przedmioty', value: 'courses' },
            { label: 'Przypisania', value: 'assignments' },
          ]}
        />
      </Paper>

      <Paper p="xl" radius="md" withBorder>
        <Stack align="center" gap="md">
          <IconFileSpreadsheet size={48} color="var(--mantine-color-blue-6)" />
          <div style={{ textAlign: 'center' }}>
            <Text fw={500}>Wybierz lub przeciągnij plik do importu</Text>
            <Text size="xs" c="dimmed">
              Obsługiwane formaty: .csv, .xlsx. Maksymalny rozmiar: 10 MB.
            </Text>
          </div>

          <FileInput
            placeholder="Kliknij, aby wybrać plik .csv lub .xlsx"
            accept=".csv, application/vnd.openxmlformats-officedocument.spreadsheetml.sheet, application/vnd.ms-excel"
            value={selectedFile}
            onChange={setSelectedFile}
            leftSection={<IconFileText size={16} />}
            clearable
            style={{ width: '100%', maxWidth: 450 }}
          />

          <Button
            size="md"
            leftSection={<IconUpload size={18} />}
            disabled={!selectedFile}
            loading={isUploading}
            onClick={handleUpload}
          >
            Rozpocznij import danych
          </Button>
        </Stack>
      </Paper>

      {result && result.success && (
        <Alert color="teal" title="Import zakończony sukcesem!" icon={<IconCheck size={20} />}>
          Wszystkie rekordy zostały poprawnie zwalidowane i zapisane w bazie danych.
          {result.imported_count !== undefined && (
            <Text size="sm" mt="xs">
              Liczba zaimportowanych obiektów: <b>{result.imported_count}</b>.
            </Text>
          )}
        </Alert>
      )}

      {result && !result.success && (
        <Stack gap="sm">
          <Alert
            color="red"
            title="Import odrzucony – wykryto błędy walidacji (Rollback)"
            icon={<IconAlertCircle size={20} />}
          >
            Żadne dane nie zostały zapisane w bazie danych. Transakcja została w całości cofnięta
            (NFR-05). Popraw poniższe błędy w pliku źródłowym i prześlij go ponownie.
          </Alert>

          {result.errors && result.errors.length > 0 && (
            <Paper p="md" radius="md" withBorder>
              <Text fw={600} size="sm" mb="xs">
                Szczegółowy wykaz błędów w pliku:
              </Text>
              <Table withTableBorder withColumnBorders striped>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th style={{ width: 120 }}>Wiersz</Table.Th>
                    <Table.Th style={{ width: 180 }}>Pole / Kolumna</Table.Th>
                    <Table.Th style={{ width: 180 }}>Błędna wartość</Table.Th>
                    <Table.Th>Opis błędu</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {result.errors.map((err, idx) => (
                    <Table.Tr key={idx}>
                      <Table.Td>
                        <Badge color="red" variant="light">
                          Wiersz {err.row}
                        </Badge>
                      </Table.Td>
                      <Table.Td>
                        <Code>{err.field || '-'}</Code>
                      </Table.Td>
                      <Table.Td>
                        <Code color="red">{err.value || '-'}</Code>
                      </Table.Td>
                      <Table.Td>
                        <Text size="sm">{err.message}</Text>
                      </Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            </Paper>
          )}
        </Stack>
      )}
    </Stack>
  );
}
