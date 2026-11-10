import { AppShell, Group, NavLink, Stack, Text, ThemeIcon } from '@mantine/core';
import {
  IconBuilding,
  IconCalendar,
  IconClock,
  IconHistory,
  IconUpload,
  IconUser,
  IconUsers,
  IconWorld,
} from '@tabler/icons-react';
import type { ReactNode } from 'react';
import { Link, Outlet, useLocation } from 'react-router-dom';

import { BackendStatus } from '../components/BackendStatus';
import { NAVY } from '../theme';

interface NavItem {
  to: string;
  label: string;
  icon: ReactNode;
}

const NAV_SECTIONS: { title: string; items: NavItem[] }[] = [
  {
    title: 'Planowanie',
    items: [
      { to: '/plan', label: 'Plan tygodniowy', icon: <IconCalendar size={18} /> },
      { to: '/wersje', label: 'Wersje planu', icon: <IconHistory size={18} /> },
      { to: '/grupy', label: 'Grupy', icon: <IconUsers size={18} /> },
      { to: '/prowadzacy', label: 'Prowadzący', icon: <IconUser size={18} /> },
      { to: '/sale', label: 'Sale', icon: <IconBuilding size={18} /> },
    ],
  },
  {
    title: 'Dane i konfiguracja',
    items: [
      { to: '/import', label: 'Import danych', icon: <IconUpload size={18} /> },
      { to: '/siatka-godzin', label: 'Siatka godzin', icon: <IconClock size={18} /> },
    ],
  },
  {
    title: 'Publikacja',
    items: [{ to: '/publiczny', label: 'Widok publiczny', icon: <IconWorld size={18} /> }],
  },
];

export function AppLayout() {
  const { pathname } = useLocation();

  return (
    <AppShell header={{ height: 64 }} navbar={{ width: 240, breakpoint: 'sm' }} padding="xl">
      <AppShell.Header bg={NAVY} c="white" withBorder={false}>
        <Group h="100%" px="lg" justify="space-between">
          <Group gap="sm">
            <ThemeIcon variant="light" size="lg">
              <IconCalendar size={20} />
            </ThemeIcon>
            <Text fw={500} size="lg">
              Plan zajęć{' '}
              <Text span c="gray.5">
                · WMiI UAM
              </Text>
            </Text>
          </Group>
          <BackendStatus />
        </Group>
      </AppShell.Header>

      <AppShell.Navbar bg={NAVY} p="sm" withBorder={false}>
        <Stack gap="lg">
          {NAV_SECTIONS.map((section) => (
            <div key={section.title}>
              <Text size="xs" tt="uppercase" fw={600} c="gray.5" px="sm" mb={4}>
                {section.title}
              </Text>
              {section.items.map((item) => (
                <NavLink
                  key={item.to}
                  component={Link}
                  to={item.to}
                  label={item.label}
                  leftSection={item.icon}
                  active={pathname.startsWith(item.to)}
                  variant="filled"
                  c="gray.3"
                  style={{ borderRadius: 'var(--mantine-radius-md)' }}
                />
              ))}
            </div>
          ))}
        </Stack>
      </AppShell.Navbar>

      <AppShell.Main bg="gray.0">
        <Outlet />
      </AppShell.Main>
    </AppShell>
  );
}
