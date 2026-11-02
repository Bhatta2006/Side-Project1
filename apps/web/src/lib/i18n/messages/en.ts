/**
 * English is the source. Every other catalog may be partial: a missing key shows this text,
 * never a blank or a raw key. Add a string here first, then translate it.
 */
export const en = {
  'today.build.title': 'Build your own course',
  'today.build.body': 'Pick any subject and how you like to learn it.',
  'settings.language.title': 'Language',
  'settings.language.help': 'The language of lessons, the tutor and menus where we have it. Code and technical terms stay in English.',
  'settings.language.preview': 'Preview: this language is machine-translated and not yet reviewed by a person.',
  'settings.language.saved': 'Language saved.',
  'translation.machine': 'Machine-translated. A person has not reviewed this yet.',
  'translation.reviewed': 'Reviewed by {name}.',
  'translation.english': 'Show the English original',
} as const;

export type MessageKey = keyof typeof en;
