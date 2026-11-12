import { notFound } from 'next/navigation';
import Board from './board';

export const metadata = { title: 'Soc mascot directions' };

/** Development-only board comparing mascot directions; 404 in production. */
export default function MascotsPage() {
  if (process.env.NODE_ENV === 'production') notFound();
  return <Board />;
}
