import { createBrowserRouter, Navigate } from 'react-router-dom';

import { AppLayout } from './layout/AppLayout';
import { PlaceholderPage } from './pages/PlaceholderPage';

// Nowy widok: utwórz plik w src/pages/ i podmień odpowiedni PlaceholderPage poniżej.
export const router = createBrowserRouter([
  {
    path: '/',
    element: <AppLayout />,
    children: [
      { index: true, element: <Navigate to="/plan" replace /> },
      {
        path: 'plan',
        element: (
          <PlaceholderPage
            eyebrow="Plan grupy"
            title="Plan tygodniowy"
            description="Siatka tygodniowa w widoku grupy, prowadzącego i sali, z przeciąganiem zajęć i podglądem kolizji."
            requirements="FR-12, FR-13, FR-14"
          />
        ),
      },
      {
        path: 'wersje',
        element: (
          <PlaceholderPage
            eyebrow="Historia"
            title="Wersje planu"
            description="Zapisane wersje planu z opisem; przywracanie wcześniejszej wersji."
            requirements="FR-15"
          />
        ),
      },
      {
        path: 'grupy',
        element: (
          <PlaceholderPage
            eyebrow="Dane"
            title="Grupy"
            description="Lista grup zajęciowych z liczebnością."
            requirements="FR-06"
          />
        ),
      },
      {
        path: 'prowadzacy',
        element: (
          <PlaceholderPage
            eyebrow="Dane"
            title="Prowadzący"
            description="Lista prowadzących i ich niedostępności w siatce tygodniowej."
            requirements="FR-06, FR-08"
          />
        ),
      },
      {
        path: 'sale',
        element: (
          <PlaceholderPage
            eyebrow="Dane"
            title="Sale"
            description="Lista sal z pojemnością i typem."
            requirements="FR-06"
          />
        ),
      },
      {
        path: 'import',
        element: (
          <PlaceholderPage
            eyebrow="Dane wejściowe"
            title="Import danych"
            description="Import przedmiotów, grup, prowadzących, sal i przypisań z plików CSV/XLSX z raportem błędów."
            requirements="FR-04, FR-05"
          />
        ),
      },
      {
        path: 'siatka-godzin',
        element: (
          <PlaceholderPage
            eyebrow="Konfiguracja semestru"
            title="Siatka godzin"
            description="Dni zajęć i bloki godzinowe semestru."
            requirements="FR-03"
          />
        ),
      },
      {
        path: 'publiczny',
        element: (
          <PlaceholderPage
            eyebrow="Publikacja"
            title="Widok publiczny"
            description="Plan wybranej grupy tylko do odczytu, dostępny bez logowania, z możliwością wydruku."
            requirements="FR-18"
          />
        ),
      },
      { path: '*', element: <Navigate to="/plan" replace /> },
    ],
  },
]);
