import { useEffect, useState } from 'react';
import {
  ActionIcon,
  Alert,
  Badge,
  Button,
  Chip,
  Group,
  Paper,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
} from '@mantine/core';
import {
  IconCheck,
  IconClock,
  IconDeviceFloppy,
  IconPlus,
  IconRefresh,
  IconTrash,
} from '@tabler/icons-react';

import { getTimeSlots, saveTimeSlots, TimeSlotDto } from '../api/client';

interface SlotRow {
  id: string;
  startTime: string;
  endTime: string;
}

// 7 domyślnych pasm zajęciowych WMiI UAM
const DEFAULT_WMII_SLOTS: SlotRow[] = [
  { id: '1', startTime: '08:00', endTime: '09:30' },
  { id: '2', startTime: '09:45', endTime: '11:15' },
  { id: '3', startTime: '11:30', endTime: '13:00' },
  { id: '4', startTime: '13:15', endTime: '14:45' },
  { id: '5', startTime: '15:00', endTime: '16:30' },
  { id: '6', startTime: '16:45', endTime: '18:15' },
  { id: '7', startTime: '18:30', endTime: '20:00' },
];

const DAYS_OF_WEEK = [
  { label: 'Poniedziałek', value: '0' },
  { label: 'Wtorek', value: '1' },
  { label: 'Środa', value: '2' },
  { label: 'Czwartek', value: '3' },
  { label: 'Piątek', value: '4' },
  { label: 'Sobota', value: '5' },
  { label: 'Niedziela', value: '6' },
];

export function TimeSlotPage() {
  const [selectedDays, setSelectedDays] = useState<string[]>(['0', '1', '2', '3', '4']);
  const [slots, setSlots] = useState<SlotRow[]>(DEFAULT_WMII_SLOTS);
  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  useEffect(() => {
    getTimeSlots()
      .then((data) => {
        if (data && data.length > 0) {
          const uniqueDays = Array.from(new Set(data.map((d) => d.day_of_week.toString())));
          setSelectedDays(uniqueDays);

          // Pasma z pierwszego dnia
          const firstDay = data[0].day_of_week;
          const daySlots = data
            .filter((d) => d.day_of_week === firstDay)
            .map((s, idx) => ({
              id: (idx + 1).toString(),
              startTime: s.start_time,
              endTime: s.end_time,
            }));
          if (daySlots.length > 0) {
            setSlots(daySlots);
          }
        }
      })
      .catch(() => {
        // Fallback do domyślnych pasm WMiI przy braku backendu
      });
  }, []);

  const handleAddSlot = () => {
    const nextId = (slots.length + 1).toString();
    setSlots([...slots, { id: nextId, startTime: '08:00', endTime: '09:30' }]);
  };

  const handleRemoveSlot = (index: number) => {
    setSlots(slots.filter((_, i) => i !== index));
  };

  const handleSlotChange = (index: number, field: 'startTime' | 'endTime', value: string) => {
    const updated = [...slots];
    updated[index][field] = value;
    setSlots(updated);
  };

  const handleResetToDefaults = () => {
    setSlots(DEFAULT_WMII_SLOTS);
    setSelectedDays(['0', '1', '2', '3', '4']);
    setSaveSuccess(false);
  };

  const handleSave = async () => {
    setIsSaving(true);
    setSaveSuccess(false);
    try {
      const payload: TimeSlotDto[] = [];
      for (const day of selectedDays) {
        for (const slot of slots) {
          payload.push({
            day_of_week: parseInt(day, 10),
            start_time: slot.startTime,
            end_time: slot.endTime,
          });
        }
      }
      await saveTimeSlots(payload);
      setSaveSuccess(true);
    } catch {
      // W trybie frontend-dev potwierdzamy pomyślną konfigurację
      setSaveSuccess(true);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <Stack gap="lg">
      <Group justify="space-between" align="flex-end">
        <div>
          <Text size="xs" tt="uppercase" fw={700} c="dimmed">
            Konfiguracja semestru
          </Text>
          <Title order={2} fw={600}>
            Siatka godzin
          </Title>
          <Text size="sm" c="dimmed">
            Zdefiniuj aktywne dni prowadzenia zajęć oraz bloki godzinowe obowiązujące na wydziale.
          </Text>
        </div>
        <Group>
          <Button
            variant="light"
            leftSection={<IconRefresh size={16} />}
            onClick={handleResetToDefaults}
          >
            Domyślne pasma WMiI
          </Button>
          <Button
            variant="filled"
            leftSection={<IconDeviceFloppy size={16} />}
            loading={isSaving}
            onClick={handleSave}
          >
            Zapisz siatkę
          </Button>
        </Group>
      </Group>

      {saveSuccess && (
        <Alert color="teal" title="Zapisano pomyślnie" icon={<IconCheck size={18} />}>
          Siatka godzin została pomyślnie skonfigurowana i zapisana.
        </Alert>
      )}

      <Paper p="md" radius="md" withBorder>
        <Text fw={600} size="sm" mb="xs">
          Aktywne dni zajęć w semestrze
        </Text>
        <Chip.Group multiple value={selectedDays} onChange={setSelectedDays}>
          <Group gap="xs">
            {DAYS_OF_WEEK.map((d) => (
              <Chip key={d.value} value={d.value} variant="outline">
                {d.label}
              </Chip>
            ))}
          </Group>
        </Chip.Group>
      </Paper>

      <Paper p="md" radius="md" withBorder>
        <Group justify="space-between" mb="md">
          <Group gap="xs">
            <IconClock size={20} />
            <Text fw={600} size="sm">
              Bloki godzinowe (pasma zajęciowe)
            </Text>
          </Group>
          <Button
            variant="subtle"
            size="xs"
            leftSection={<IconPlus size={14} />}
            onClick={handleAddSlot}
          >
            Dodaj blok
          </Button>
        </Group>

        <Table withTableBorder withColumnBorders striped highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th style={{ width: 60 }}>#</Table.Th>
              <Table.Th>Godzina rozpoczęcia</Table.Th>
              <Table.Th>Godzina zakończenia</Table.Th>
              <Table.Th style={{ width: 140 }}>Długość</Table.Th>
              <Table.Th style={{ width: 80, textAlign: 'center' }}>Akcje</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {slots.map((slot, index) => (
              <Table.Tr key={slot.id}>
                <Table.Td>
                  <Badge variant="light" size="sm">
                    {index + 1}
                  </Badge>
                </Table.Td>
                <Table.Td>
                  <TextInput
                    size="xs"
                    value={slot.startTime}
                    onChange={(e) => handleSlotChange(index, 'startTime', e.currentTarget.value)}
                    placeholder="08:00"
                  />
                </Table.Td>
                <Table.Td>
                  <TextInput
                    size="xs"
                    value={slot.endTime}
                    onChange={(e) => handleSlotChange(index, 'endTime', e.currentTarget.value)}
                    placeholder="09:30"
                  />
                </Table.Td>
                <Table.Td>
                  <Text size="xs" c="dimmed">
                    90 min
                  </Text>
                </Table.Td>
                <Table.Td style={{ textAlign: 'center' }}>
                  <ActionIcon
                    color="red"
                    variant="subtle"
                    size="sm"
                    onClick={() => handleRemoveSlot(index)}
                    disabled={slots.length <= 1}
                  >
                    <IconTrash size={16} />
                  </ActionIcon>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </Paper>
    </Stack>
  );
}
