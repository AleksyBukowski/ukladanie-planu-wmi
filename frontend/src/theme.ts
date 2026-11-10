import { createTheme, type MantineColorsTuple } from '@mantine/core';

// Kolory z makiet (granat paska bocznego + niebieski akcent).
const uamBlue: MantineColorsTuple = [
  '#ebf0ff',
  '#d5ddfa',
  '#a8b9f0',
  '#7893e7',
  '#5073df',
  '#365fdb',
  '#2c56d1',
  '#1f45bf',
  '#183dab',
  '#0b3497',
];

export const NAVY = '#0f1e3a';

export const theme = createTheme({
  primaryColor: 'uamBlue',
  colors: { uamBlue },
  fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
  headings: { fontWeight: '500' },
  defaultRadius: 'md',
});
