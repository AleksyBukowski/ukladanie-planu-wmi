import { Badge, Code, ScrollArea, Table, Text } from '@mantine/core';

import type { ImportIssue } from '../api/client';

interface ImportIssuesTableProps {
  issues: ImportIssue[];
  /** Czytelne nazwy plików, np. { rooms: 'Sale' }. */
  fileLabels?: Record<string, string>;
  /** Nagłówek kolumny z numerem – „Wiersz” dla plików, „Pozycja” dla listy z formularza. */
  rowLabel?: string;
}

/** Raport błędów importu (FR-05): plik, wiersz, kolumna i opis błędu. */
export function ImportIssuesTable({
  issues,
  fileLabels,
  rowLabel = 'Wiersz',
}: ImportIssuesTableProps) {
  const showFile = issues.some((issue) => issue.file);

  return (
    <ScrollArea.Autosize mah={420}>
      <Table withTableBorder withColumnBorders striped stickyHeader>
        <Table.Thead>
          <Table.Tr>
            {showFile && <Table.Th w={140}>Plik</Table.Th>}
            <Table.Th w={100}>{rowLabel}</Table.Th>
            <Table.Th w={180}>Kolumna</Table.Th>
            <Table.Th>Opis błędu</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {issues.map((issue, index) => (
            <Table.Tr key={index}>
              {showFile && (
                <Table.Td>{issue.file ? (fileLabels?.[issue.file] ?? issue.file) : '–'}</Table.Td>
              )}
              <Table.Td>
                {issue.row != null ? (
                  <Badge color="red" variant="light">
                    {issue.row}
                  </Badge>
                ) : (
                  <Text size="xs" c="dimmed">
                    cały plik
                  </Text>
                )}
              </Table.Td>
              <Table.Td>{issue.column ? <Code>{issue.column}</Code> : '–'}</Table.Td>
              <Table.Td>
                <Text size="sm">{issue.message}</Text>
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </ScrollArea.Autosize>
  );
}
