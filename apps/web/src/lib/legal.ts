/**
 * Facts the legal pages depend on. Keep them true: change them here (and the date) when the
 * product or the operator changes, and tell learners about material changes.
 */
export const LEGAL = {
  product: 'Socrat',
  operator: process.env.NEXT_PUBLIC_LEGAL_OPERATOR || 'the Socrat team',
  site: process.env.NEXT_PUBLIC_SITE_URL || 'https://dashboard.socrat.codes',
  contact: process.env.NEXT_PUBLIC_CONTACT_EMAIL || 'founder@socrat.codes',
  privacyContact: process.env.NEXT_PUBLIC_PRIVACY_EMAIL || 'privacy@socrat.codes',
  country: 'India',
  updated: '11 November 2026',
  minimumAge: 13,
} as const;
