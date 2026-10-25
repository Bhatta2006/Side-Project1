'use client';

import { MessageCircle } from 'lucide-react';
import { useSession } from '@/lib/session';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';

/** The beta WhatsApp community. Renders nothing until the server is given an invite link. */
export function useCommunityUrl(): string | null {
  const { features } = useSession();
  const url = features?.community_url;
  return url && url.startsWith('https://chat.whatsapp.com/') ? url : null;
}

export function CommunityButton({ variant = 'outline', size = 'default', className, label = 'Join the WhatsApp community' }: {
  variant?: 'outline' | 'default' | 'ink' | 'ghost';
  size?: 'default' | 'sm' | 'lg';
  className?: string;
  label?: string;
}) {
  const url = useCommunityUrl();
  if (!url) return null;
  return (
    <Button asChild variant={variant} size={size} className={className}>
      <a href={url} target="_blank" rel="noopener noreferrer">
        <MessageCircle data-icon="inline-start" />{label}<span className="sr-only"> (opens WhatsApp)</span>
      </a>
    </Button>
  );
}

/** A card for Today and the landing page: why to join, and the invite. */
export function CommunityCard({ className }: { className?: string }) {
  const url = useCommunityUrl();
  if (!url) return null;
  return (
    <section aria-labelledby="community-title" className={cn('flex flex-col gap-4 paper rounded-card p-5 sm:flex-row sm:items-center sm:justify-between lg:p-6', className)}>
      <div>
        <h2 id="community-title" className="font-display text-xl font-semibold tracking-[-0.03em]">Learn with the beta cohort</h2>
        <p className="mt-1 max-w-xl text-[15px] text-muted-foreground">Weekly challenges, study partners and a direct line to the people building Socrat. Tell us what to fix next.</p>
      </div>
      <CommunityButton className="self-start sm:self-auto" />
    </section>
  );
}
