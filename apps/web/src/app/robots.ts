import type { MetadataRoute } from 'next';
import { LEGAL } from '@/lib/legal';

// Public pages stay crawlable; the signed-in app and the API are not worth indexing.
const PRIVATE = ['/api/', '/admin', '/today', '/plan', '/graph', '/transfer', '/library', '/problems', '/progress', '/settings', '/sprint', '/company-sprint', '/companies', '/assessments', '/placement', '/playground', '/quiz', '/start', '/learn', '/passport', '/dev-gallery'];

export default function robots(): MetadataRoute.Robots {
  return { rules: { userAgent: '*', allow: '/', disallow: PRIVATE }, sitemap: `${LEGAL.site}/sitemap.xml` };
}
