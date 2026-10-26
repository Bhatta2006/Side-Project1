import type { MetadataRoute } from 'next';
import { LEGAL } from '@/lib/legal';

export default function sitemap(): MetadataRoute.Sitemap {
  return ['/', '/pricing', '/privacy', '/terms', '/refunds'].map((path) => ({ url: `${LEGAL.site}${path}`, changeFrequency: 'monthly', priority: path === '/' ? 1 : 0.5 }));
}
