'use client';

import { useEffect, useState } from 'react';
import { Download, Share, SquarePlus } from '@/components/icons';
import { registerServiceWorker, useInstall } from '@/lib/pwa';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';

/** Registers the service worker once per page load. Mounted in the root layout. */
export function PwaSetup() {
  useEffect(() => { registerServiceWorker(); }, []);
  return null;
}

/**
 * "Install app": the browser's own prompt where there is one, step-by-step help on iPhone and
 * iPad, and nothing at all when the app is already installed or the browser cannot install.
 */
export function InstallAppButton({ variant = 'outline', size = 'default', className, label = 'Install the app' }: {
  variant?: 'outline' | 'default' | 'ghost' | 'ink';
  size?: 'default' | 'sm' | 'lg';
  className?: string;
  label?: string;
}) {
  const { state, install } = useInstall();
  const [help, setHelp] = useState(false);
  if (state === 'installed' || state === 'unsupported') return null;
  return (
    <>
      <Button variant={variant} size={size} className={className} onClick={() => (state === 'prompt' ? install() : setHelp(true))}>
        <Download data-icon="inline-start" />{label}
      </Button>
      <Dialog open={help} onOpenChange={setHelp}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add Socrat to your Home Screen</DialogTitle>
            <DialogDescription>It opens full screen like an app, with lessons, checks, reviews and Soc one tap away.</DialogDescription>
          </DialogHeader>
          <ol className="grid gap-3 text-[15px]">
            <li className="flex items-center gap-3"><span className="grid size-9 flex-none place-items-center rounded-full bg-raised"><Share className="size-4.5" aria-hidden="true" /></span>Tap the Share button in Safari’s toolbar.</li>
            <li className="flex items-center gap-3"><span className="grid size-9 flex-none place-items-center rounded-full bg-raised"><SquarePlus className="size-4.5" aria-hidden="true" /></span>Choose Add to Home Screen, then Add.</li>
          </ol>
        </DialogContent>
      </Dialog>
    </>
  );
}
