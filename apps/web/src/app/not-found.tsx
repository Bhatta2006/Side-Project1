import Link from 'next/link';
import { SocMoment } from '@/components/socrat/states';
import { Button } from '@/components/ui/button';

export default function NotFound() {
  return (
    <SocMoment mood="confused" note="hmm, I asked around. nobody knows this page.">
      <h1 className="type-display-m">That page does not exist</h1>
      <p className="text-base text-muted-foreground">The link may be old, or the page has moved.</p>
      <Button asChild className="mt-2"><Link href="/">Go home</Link></Button>
    </SocMoment>
  );
}
