'use client';

import { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { Bug, Lightbulb, MessageSquareHeart, PenLine } from 'lucide-react';
import { api, explain } from '@/lib/api';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Textarea } from '@/components/ui/textarea';

type Category = (typeof CATEGORIES)[number][0];

/** Opens the feedback dialog from anywhere (header button, menu, error page, settings). */
export function openReportProblem(category: Category = 'bug') {
  window.dispatchEvent(new CustomEvent('socrat:report', { detail: category }));
}

const CATEGORIES = [
  ['bug', 'Report a bug', Bug, 'What you did, what you expected, what you saw'],
  ['idea', 'Ask for a feature', Lightbulb, 'What would make Socrat better for you?'],
  ['feedback', 'Share feedback', MessageSquareHeart, 'What you liked, what felt off, anything'],
  ['content', 'Wrong lesson or question', PenLine, 'Which lesson or question, and what is wrong'],
] as const;

/** Mounted once per shell. Sends the message and the page path, nothing else. */
export function ReportProblem() {
  const [open, setOpen] = useState(false);
  const [message, setMessage] = useState('');
  const [category, setCategory] = useState<Category>('bug');
  const [sending, setSending] = useState(false);

  useEffect(() => {
    const show = (event: Event) => {
      const detail = (event as CustomEvent).detail;
      if (CATEGORIES.some(([value]) => value === detail)) setCategory(detail);
      setOpen(true);
    };
    window.addEventListener('socrat:report', show);
    return () => window.removeEventListener('socrat:report', show);
  }, []);

  async function send() {
    setSending(true);
    try {
      await api.post('/problem-reports', { message: message.trim(), category, route: window.location.pathname.slice(0, 120) });
      toast.success('Thank you! We read every note.');
      setMessage('');
      setOpen(false);
    } catch (e) {
      toast.error(explain(e));
    } finally {
      setSending(false);
    }
  }

  const placeholder = CATEGORIES.find(([value]) => value === category)?.[3];
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Help us build Socrat</DialogTitle>
          <DialogDescription>You&apos;re one of our beta testers. Bugs, ideas and opinions all help. We include the page you are on; nothing else from your screen.</DialogDescription>
        </DialogHeader>
        <div role="radiogroup" aria-label="What is it about?" className="grid grid-cols-2 gap-2">
          {CATEGORIES.map(([value, label, Icon]) => (
            <button
              key={value}
              type="button"
              role="radio"
              aria-checked={category === value}
              onClick={() => setCategory(value)}
              className={cn(
                'flex min-h-12 items-center gap-2 rounded-[14px_18px_12px_16px] border-2 border-dashed border-border-strong px-3 py-2 text-left text-sm font-medium transition-[transform,box-shadow]',
                category === value && '-translate-x-0.5 -translate-y-0.5 border-solid border-[var(--soc-outline)] bg-[var(--highlight)] text-[#15161E] shadow-[3px_3px_0_var(--soc-outline)]',
              )}
            >
              <Icon className="size-4 flex-none" aria-hidden="true" />
              {label}
            </button>
          ))}
        </div>
        <label className="grid gap-1.5 text-sm font-medium">
          Tell us more
          <Textarea rows={5} maxLength={2000} value={message} onChange={e => setMessage(e.target.value)} placeholder={placeholder} />
        </label>
        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
          <Button onClick={send} disabled={sending || message.trim().length < 3}>{sending ? 'Sending' : 'Send'}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/** Always-visible header button for beta testers: a yellow sticky note in ink. */
export function FeedbackButton() {
  return (
    <button
      type="button"
      onClick={() => openReportProblem('feedback')}
      aria-label="Send feedback, ask for a feature or report a bug"
      className="group inline-flex h-9 -rotate-2 items-center gap-1.5 rounded-[10px_14px_9px_12px] border-2 border-[var(--soc-outline)] bg-[var(--highlight)] px-3 text-[#15161E] shadow-[2px_2px_0_var(--soc-outline)] transition-[transform,box-shadow] duration-200 ease-[var(--ease-soft)] hover:-translate-y-0.5 hover:rotate-0 hover:shadow-[3px_4px_0_var(--soc-outline)] active:translate-y-0 active:shadow-none"
    >
      <PenLine className="size-4 transition-transform group-hover:-rotate-12" strokeWidth={2} aria-hidden="true" />
      <span className="font-hand text-[18px] leading-none">Feedback</span>
      <span className="hidden rounded-full border border-[#15161E] px-1.5 text-[10px] font-bold tracking-wide uppercase sm:inline">beta</span>
    </button>
  );
}
