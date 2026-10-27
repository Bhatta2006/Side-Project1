import { NextResponse, type NextRequest } from 'next/server';

/**
 * Signed-in visitors skip the marketing page: the redirect happens on the server, so the
 * landing page can render its content straight into the HTML for everyone else instead
 * of waiting for a client-side session check (that wait was most of its LCP).
 *
 * Only the cookie's presence is checked. A stale cookie lands on /today, whose guard sends
 * the visitor to /login, which this proxy does not touch, so there is no redirect loop.
 */
export function proxy(request: NextRequest) {
  const response = request.cookies.has('socrat_session')
    ? NextResponse.redirect(new URL('/today', request.url))
    : NextResponse.next();
  // An invite link (/?ref=CODE) is remembered here, so the code survives sign-up without
  // shipping any capture script; the signed-in Invite dialog claims it and clears it.
  const ref = request.nextUrl.searchParams.get('ref');
  if (ref && /^[A-Za-z0-9]{4,12}$/.test(ref)) {
    response.cookies.set('socrat_ref', ref, { maxAge: 30 * 86400, sameSite: 'lax', path: '/' });
  }
  return response;
}

export const config = { matcher: '/' };
