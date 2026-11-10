import { Badge, Tooltip } from '@mantine/core';
import { useEffect, useState } from 'react';

import { getHealth } from '../api/client';

type Status = 'loading' | 'ok' | 'db-down' | 'offline';

const LABELS: Record<Status, { label: string; color: string }> = {
  loading: { label: 'Łączenie…', color: 'gray' },
  ok: { label: 'API połączone', color: 'green' },
  'db-down': { label: 'Brak bazy danych', color: 'orange' },
  offline: { label: 'API niedostępne', color: 'red' },
};

/** Mały wskaźnik w nagłówku – szybko widać, czy backend i baza działają. */
export function BackendStatus() {
  const [status, setStatus] = useState<Status>('loading');

  useEffect(() => {
    let cancelled = false;
    getHealth()
      .then((health) => {
        if (!cancelled) setStatus(health.database === 'ok' ? 'ok' : 'db-down');
      })
      .catch(() => {
        if (!cancelled) setStatus('offline');
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const { label, color } = LABELS[status];
  return (
    <Tooltip label="GET /api/health">
      <Badge color={color} variant="light">
        {label}
      </Badge>
    </Tooltip>
  );
}
