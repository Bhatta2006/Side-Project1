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
  if (request.cookies.has('socrat_session')) {
    return NextResponse.redirect(new URL('/today', request.url));
  }
  return NextResponse.next();
}

export const config = { matcher: '/' };
