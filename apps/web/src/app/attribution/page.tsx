'use client';

import { useEffect, useState } from 'react';
import { api, explain } from '@/lib/api';
import { ErrorNote, Loading, Page, PageHeader, SectionTitle } from '@/components/common';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';

interface Source { id: string; name: string; url: string; content: string; license: string; license_status: 'verified' | 'unverified'; use: string }
interface Adapted { record: string; attribution: string; sources: { title: string; author: string; url: string; license: string }[] }
interface Attribution { sources: Source[]; adapted: Adapted[] }

/** Public: what Socrat links to or adapts, built from the content source registry. */
export default function AttributionPage() {
  const [data, setData] = useState<Attribution | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    api.get<Attribution>('/attribution').then(setData).catch(e => setError(explain(e)));
  }, []);

  return (
    <Page>
      <PageHeader
        title="Attribution"
        description="Socrat writes its own lessons, quizzes and problems. It links to the resources below and adapts material only from sources whose license allows it, with credit."
      />
      {error ? <ErrorNote message={error} /> : null}
      {!data && !error ? <Loading /> : null}
      {data ? (
        <div className="grid min-w-0 grid-cols-[minmax(0,1fr)] gap-10">
          <section aria-labelledby="adapted-title" className="grid min-w-0 gap-3">
            <SectionTitle id="adapted-title">Adapted material</SectionTitle>
            {data.adapted.length ? (
              <ul className="grid gap-3">
                {data.adapted.map(item => (
                  <li key={item.record} className="paper rounded-card p-4">
                    <p className="font-semibold">{item.record}</p>
                    {item.attribution ? <p className="mt-1 text-sm text-muted-foreground">{item.attribution}</p> : null}
                    <ul className="mt-2 grid gap-1 text-sm">
                      {item.sources.map(source => (
                        <li key={source.url}>
                          <a href={source.url} className="underline underline-offset-4" rel="noreferrer">{source.title}</a> by {source.author}, {source.license}
                        </li>
                      ))}
                    </ul>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-base text-muted-foreground">No lesson, quiz or problem currently adapts third-party text. Everything is written by Socrat.</p>
            )}
          </section>
          <section aria-labelledby="sources-title" className="grid min-w-0 grid-cols-[minmax(0,1fr)] gap-3">
            <SectionTitle id="sources-title">Sources</SectionTitle>
            <p className="text-base text-muted-foreground">
              Licenses marked unverified come from secondary reports and are not relied on until checked on the source&apos;s own page.
            </p>
            <div className="overflow-x-auto rounded-card border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Source</TableHead>
                    <TableHead>What it is</TableHead>
                    <TableHead>License</TableHead>
                    <TableHead>How Socrat uses it</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.sources.map(source => (
                    <TableRow key={source.id}>
                      <TableCell><a href={source.url} className="font-semibold underline underline-offset-4" rel="noreferrer">{source.name}</a></TableCell>
                      <TableCell>{source.content}</TableCell>
                      <TableCell>{source.license}{source.license_status === 'unverified' ? <span className="text-muted-foreground"> (unverified)</span> : null}</TableCell>
                      <TableCell>{source.use}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </section>
        </div>
      ) : null}
    </Page>
  );
}
