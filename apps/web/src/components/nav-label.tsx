'use client';

import { useI18n } from '@/lib/i18n';
import { NAME } from '@/lib/routes';

/**
 * A navigation label in the learner's language. A course can rename a slot (the Practice slot
 * becomes the course's own studio); a renamed slot keeps its own name, untranslated, rather than
 * showing the translation of a different word.
 */
export function NavLabel({ item }: { item: { key: string; label: string } }) {
  const { tx } = useI18n();
  const standard = (NAME as Record<string, string>)[item.key];
  return <>{item.label === standard ? tx(`nav.${item.key}`, item.label) : item.label}</>;
}
