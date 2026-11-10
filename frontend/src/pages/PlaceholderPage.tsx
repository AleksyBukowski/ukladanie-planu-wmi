import { Alert, Stack, Text, Title } from '@mantine/core';
import { IconInfoCircle } from '@tabler/icons-react';

interface PlaceholderPageProps {
  eyebrow: string;
  title: string;
  description: string;
  /** Wymagania, które realizuje widok (np. "FR-03"). */
  requirements: string;
}

/** Tymczasowy widok – do zastąpienia przez właściwą implementację w tickecie. */
export function PlaceholderPage(props: PlaceholderPageProps) {
  const { eyebrow, title, description, requirements } = props;
  return (
    <Stack gap="xs" maw={720}>
      <Text size="xs" tt="uppercase" fw={600} c="dimmed" lts={1}>
        {eyebrow}
      </Text>
      <Title order={2}>{title}</Title>
      <Text c="dimmed">{description}</Text>
      <Alert mt="md" variant="light" icon={<IconInfoCircle />} title="Widok w przygotowaniu">
        Ten ekran jest szkieletem. Realizuje wymagania: {requirements}.
      </Alert>
    </Stack>
  );
}
