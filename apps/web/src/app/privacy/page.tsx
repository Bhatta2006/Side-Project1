import type { Metadata } from 'next';
import Link from 'next/link';
import { LegalPage } from '@/components/legal-page';
import { LEGAL } from '@/lib/legal';

export const metadata: Metadata = {
  title: 'Privacy policy · Socrat',
  description: 'What Socrat collects, why, who processes it, and how to export or delete it.',
};

export default function PrivacyPage() {
  return (
    <LegalPage
      title="Privacy policy"
      summary={
        <p>
          {LEGAL.product} is a learning product. We collect what we need to teach you and to show you
          evidence of what you can do, nothing for advertising, and we do not sell your data. You can
          download or delete everything from Settings at any time.
        </p>
      }
    >
      <section aria-labelledby="who">
        <h2 id="who">Who we are</h2>
        <p>
          {LEGAL.product} ({LEGAL.site}) is operated by {LEGAL.operator} in {LEGAL.country}. We are the data
          fiduciary (controller) for the personal data described here. Questions, requests and complaints:{' '}
          <a href={`mailto:${LEGAL.privacyContact}`}>{LEGAL.privacyContact}</a>. We reply within 30 days, usually much sooner.
        </p>
      </section>

      <section aria-labelledby="payments">
        <h2 id="payments">Payments</h2>
        <p>
          Paid plans are processed by Razorpay. Your card, UPI or bank details are entered with Razorpay and are never
          sent to or stored by {LEGAL.product}. We keep your plan, its billing period, the currency and Razorpay&apos;s
          subscription reference so we can give you access and handle cancellations and refunds.
        </p>
      </section>

      <section aria-labelledby="collect">
        <h2 id="collect">What we collect</h2>
        <ul>
          <li>
            <strong>Sign-in.</strong> When you continue with Google we receive your Google account identifier
            and your name (the <code>openid</code> and <code>profile</code> scopes). We do not ask Google for your
            email address, contacts or anything else, and we never see your Google password.
          </li>
          <li>
            <strong>Profile and plan.</strong> The name you choose, your birth year (to check the minimum age),
            your time zone, the course, language, goal, study days and minutes you pick.
          </li>
          <li>
            <strong>Learning activity.</strong> Lessons opened, quiz and check answers, timings, hints used,
            mastery estimates, plans and the changes you approve, weekly assessments, streaks and reminders settings.
          </li>
          <li>
            <strong>Your code.</strong> Drafts and the code you run or submit. Code runs in your own browser;
            the code and a fingerprint of its output are sent to us so we can save your work and check
            your answer.
          </li>
          <li>
            <strong>Conversations with Soc, the tutor, and Playground requests.</strong> The messages you write,
            the replies, and your ratings of them.
          </li>
          <li>
            <strong>Optional links.</strong> A public Codeforces handle if you add one; we then read your public
            Codeforces results.
          </li>
          <li>
            <strong>Reports you send.</strong> What you write in "Report a problem", with the page you were on.
          </li>
          <li>
            <strong>Technical data.</strong> Error reports from the app (an error message, a trimmed stack trace
            and the page path, without your code or what is on screen), anonymous page-speed samples (page type,
            timing and device class only), counts of AI usage per account for cost limits, and short-lived server
            logs with request identifiers and IP addresses for security.
          </li>
        </ul>
      </section>

      <section aria-labelledby="why">
        <h2 id="why">Why we use it</h2>
        <ul>
          <li>To run your account, build and adapt your plan, check your work and show your progress. This is the service you asked for.</li>
          <li>To keep {LEGAL.product} secure, prevent abuse and keep costs within limits.</li>
          <li>To find and fix errors, and to improve lessons and questions using aggregate statistics (for example, how many learners answer a question correctly).</li>
          <li>To reply when you contact us.</li>
        </ul>
        <p>
          We rely on your consent, given when you create an account, and on the legitimate uses the law allows
          for running a service you requested. You can withdraw consent at any time by deleting your account.
          We do not use your data for advertising, we do not sell it, and we do not build profiles for anyone else.
        </p>
      </section>

      <section aria-labelledby="ai">
        <h2 id="ai">AI processing</h2>
        <p>
          When you message Soc, ask for a lesson in other words, or use the Playground, the request is sent to the
          AI model provider we use (currently an OpenAI-compatible inference provider, or Anthropic) to generate the
          reply. We send what is needed for the reply: your message, the lesson or problem, the code you are
          working on, and a summary of your progress. We do not send your Google identifier. Our providers process
          this on our behalf through business APIs; we choose providers whose terms do not allow training their models on these requests. AI replies
          can be wrong; Playground visuals are labelled as not verified.
        </p>
      </section>

      <section aria-labelledby="share">
        <h2 id="share">Who processes your data</h2>
        <ul>
          <li><strong>Hosting:</strong> Oracle Cloud Infrastructure, which runs our servers and database.</li>
          <li><strong>Sign-in:</strong> Google, when you choose to continue with Google.</li>
          <li><strong>AI models:</strong> the provider described above, for tutor, lesson and Playground requests.</li>
          <li><strong>Error monitoring:</strong> if enabled, a Sentry-compatible service receives server error details (no request bodies).</li>
        </ul>
        <p>
          Some of these providers may process data outside {LEGAL.country}. We only use providers bound by
          contract to protect it. We disclose data to authorities only when the law requires it.
        </p>
      </section>

      <section aria-labelledby="cookies">
        <h2 id="cookies">Cookies and storage</h2>
        <p>
          We use one essential cookie, <code>socrat_session</code>, to keep you signed in (up to 30 days). Your
          browser also stores preferences such as theme, editor settings and a backup copy of your code drafts.
          There are no advertising or third-party tracking cookies, so there is nothing to opt out of.
        </p>
      </section>

      <section aria-labelledby="keep">
        <h2 id="keep">How long we keep it</h2>
        <p>
          We keep your account data while your account exists, so your progress and evidence stay available.
          When you delete your account, your profile, learning data, code, conversations and reports are deleted
          from our database immediately; encrypted backups that still contain them are overwritten on their regular schedule. Server logs
          are kept for up to 30 days. Anonymous page-speed samples contain nothing that identifies you.
        </p>
      </section>

      <section aria-labelledby="rights">
        <h2 id="rights">Your rights</h2>
        <ul>
          <li><strong>See and download your data:</strong> Settings → Download my data gives you everything as a file.</li>
          <li><strong>Correct it:</strong> change your profile and plan in Settings, or ask us.</li>
          <li><strong>Delete it:</strong> Settings → Delete account removes your account and data.</li>
          <li><strong>Withdraw consent, ask questions, or nominate someone</strong> to act for you if you cannot: write to <a href={`mailto:${LEGAL.privacyContact}`}>{LEGAL.privacyContact}</a>.</li>
          <li>
            <strong>Complain:</strong> write to us first and we will try to resolve it. In India you may also
            complain to the Data Protection Board of India. If you live elsewhere, your local data protection
            authority can help.
          </li>
        </ul>
      </section>

      <section aria-labelledby="children">
        <h2 id="children">Young learners</h2>
        <p>
          You must be at least {LEGAL.minimumAge} to use {LEGAL.product}. If you are under 18, use it only with the
          permission of a parent or guardian, who may contact us to review or delete your data. We do not
          show ads, and we do not track or profile young learners for anything other than teaching them.
        </p>
      </section>

      <section aria-labelledby="security">
        <h2 id="security">Security</h2>
        <p>
          Traffic is encrypted with HTTPS, sessions use secure cookies with protections against cross-site requests,
          and code you run executes inside your own browser, isolated from our servers. If a breach affects your
          data, we will tell you and the authorities as the law requires.
        </p>
      </section>

      <section aria-labelledby="changes">
        <h2 id="changes">Changes</h2>
        <p>
          When we change this policy we update the date above, and for important changes we tell you in the app
          before they apply. See also our <Link href="/terms">terms of service</Link>.
        </p>
      </section>
    </LegalPage>
  );
}
