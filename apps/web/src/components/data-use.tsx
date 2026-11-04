'use client';

import { useI18n } from '@/lib/i18n';
import { DATA_USE, useLite } from '@/lib/lite';
import { Pill } from '@/components/choice';

/** Lite, full or automatic data use on this device. Hidden unless the server offers lite mode. */
export function DataUsePicker() {
  const { t } = useI18n();
  const { available, setting, lite, set } = useLite();
  if (!available) return null;
  return (
    <div className="grid gap-2 py-5">
      <p id="data-use-label" className="font-semibold">{t('lite.title')}</p>
      <p id="data-use-help" className="text-sm text-muted-foreground">{t('lite.help')}</p>
      <div role="group" aria-labelledby="data-use-label" aria-describedby="data-use-help" className="flex flex-wrap gap-2">
        {DATA_USE.map(value => (
          <Pill key={value} pressed={setting === value} onClick={() => set(value)}>{t(`lite.${value}`)}</Pill>
        ))}
      </div>
      {lite ? <p role="status" className="text-sm text-muted-foreground">{t('lite.active')}</p> : null}
    </div>
  );
}
