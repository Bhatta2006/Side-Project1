import type { MetadataRoute } from 'next';

export default function manifest(): MetadataRoute.Manifest {
  return {
    id: '/today',
    name: 'Socrat',
    short_name: 'Socrat',
    description: 'Learn it. Then prove it. A tutor that asks before it tells.',
    start_url: '/today?source=app',
    scope: '/',
    display: 'standalone',
    orientation: 'any',
    background_color: '#F6F5F0',
    theme_color: '#15161E',
    categories: ['education', 'productivity'],
    icons: [
      { src: '/icons/icon-192.png', sizes: '192x192', type: 'image/png', purpose: 'any' },
      { src: '/icons/icon-512.png', sizes: '512x512', type: 'image/png', purpose: 'any' },
      { src: '/icons/maskable-512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
    ],
    shortcuts: [
      { name: 'Today', url: '/today?source=app' },
      { name: 'Skills', url: '/plan?source=app' },
      { name: 'Practice', url: '/library?source=app' },
    ],
  };
}
