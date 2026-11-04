'use client';

import { useEffect, useState } from 'react';
import { api, explain } from '@/lib/api';
import { useI18n, type LocaleInfo } from '@/lib/i18n';
import { useSession } from '@/lib/session';
import { NativeSelect, NativeSelectOption } from '@/components/ui/native-select';

/** Chooses the language of lessons, the tutor and (where translated) the menus. */
export function LanguagePicker() {
  const { t, locale, setLocale } = useI18n();
  const { profile, refresh } = useSession();
  const [items, setItems] = useState<LocaleInfo[]>([]);
  const [note, setNote] = useState('');
  useEffect(() => {
    api.get<{ items: LocaleInfo[] }>('/locales').then(r => setItems(r.items)).catch(() => undefined);
  }, []);
  const current = items.find(l => l.tag === locale);

  async function choose(tag: string) {
    setLocale(tag);
    setNote('');
    if (!profile) return;
    try {
      await api.patch('/me', { locale: tag });
      await refresh();
      setNote(t('settings.language.saved'));
    } catch (error) {
      setNote(explain(error));
    }
  }

  return (
    <div className="grid gap-2 pb-5">
      <label htmlFor="settings-locale" className="font-semibold">{t('settings.language.title')}</label>
      <p id="settings-locale-help" className="text-sm text-muted-foreground">{t('settings.language.help')}</p>
      <NativeSelect
        id="settings-locale"
        className="w-full"
        value={locale}
        onChange={e => void choose(e.target.value)}
        aria-describedby="settings-locale-help"
      >
        {(items.length ? items : [{ tag: 'en', native: 'English' } as LocaleInfo]).map(l => (
          <NativeSelectOption key={l.tag} value={l.tag}>{l.native}</NativeSelectOption>
        ))}
      </NativeSelect>
      {current?.preview ? <p className="text-sm text-muted-foreground">{t('settings.language.preview')}</p> : null}
      {note ? <p role="status" className="text-sm text-muted-foreground">{note}</p> : null}
    </div>
  );
}
