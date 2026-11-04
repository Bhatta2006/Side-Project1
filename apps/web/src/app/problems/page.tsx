import { redirect } from 'next/navigation';

/** Practice lives at /studio; keep the obvious URL from dead-ending. */
export default function ProblemsIndex() {
  redirect('/studio');
}
