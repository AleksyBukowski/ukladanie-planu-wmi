import { createBrowserRouter, Navigate } from 'react-router-dom';

import { AppLayout } from './layout/AppLayout';
import { ImportPage } from './pages/ImportPage';
import { PlaceholderPage } from './pages/PlaceholderPage';
import { TimeSlotPage } from './pages/TimeSlotPage';

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
        element: <ImportPage />,
      },
      {
        path: 'siatka-godzin',
        element: <TimeSlotPage />,
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
