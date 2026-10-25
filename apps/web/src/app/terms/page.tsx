import type { Metadata } from 'next';
import Link from 'next/link';
import { LegalPage } from '@/components/legal-page';
import { LEGAL } from '@/lib/legal';

export const metadata: Metadata = {
  title: 'Terms of service · Socrat',
  description: 'The agreement between you and Socrat: accounts, fair use, your code, AI features and the beta.',
};

export default function TermsPage() {
  return (
    <LegalPage
      title="Terms of service"
      summary={
        <p>
          These terms are the agreement between you and {LEGAL.operator} for using {LEGAL.product}. By creating an
          account you accept them and our <Link href="/privacy" className="font-medium underline underline-offset-4">privacy policy</Link>.
          We wrote them to be read; the short version is: learn honestly, be kind, and your work stays yours.
        </p>
      }
    >
      <section aria-labelledby="beta">
        <h2 id="beta">A beta product</h2>
        <p>
          {LEGAL.product} is in beta. Features may change, appear or go away, and things will sometimes break. We
          will try hard to keep your progress safe and to tell you before changes that matter. Socrat has a free
          plan and paid plans, described on the <Link href="/pricing">plans page</Link>.
        </p>
      </section>

      <section aria-labelledby="account">
        <h2 id="account">Your account</h2>
        <ul>
          <li>You must be at least {LEGAL.minimumAge}. If you are under 18, you need a parent or guardian’s permission.</li>
          <li>One account per person. Keep access to your Google account secure; you are responsible for activity in your account.</li>
          <li>Give accurate information where we ask for it (for example your birth year).</li>
          <li>You can delete your account at any time in Settings.</li>
        </ul>
      </section>

      <section aria-labelledby="use">
        <h2 id="use">Fair use</h2>
        <p>Please do not:</p>
        <ul>
          <li>attack, overload, probe or scrape the service, or try to get around limits, locks or security;</li>
          <li>use the code runner or the AI features to create malware, spam, or anything illegal or harmful;</li>
          <li>try to extract hidden tests, reference solutions or other learners’ data;</li>
          <li>harass anyone, or post or submit content you have no right to share;</li>
          <li>resell or redistribute {LEGAL.product}’s lessons, problems or tests.</li>
        </ul>
        <p>We may limit, suspend or close accounts that break these rules, and we will tell you why unless the law or safety prevents it.</p>
      </section>

      <section aria-labelledby="integrity">
        <h2 id="integrity">Learning honestly</h2>
        <p>
          {LEGAL.product} shows evidence of what you can do on your own. Checks and assessments are only meaningful if
          the work is yours: hints and tutor help are recorded and lower how much a solve counts, and that is by design.
          Do not use {LEGAL.product} to cheat in exams, contests or job interviews that forbid outside help.
        </p>
      </section>

      <section aria-labelledby="content">
        <h2 id="content">Your code and our content</h2>
        <ul>
          <li>Code and messages you write stay yours. You give us permission to store and process them to run the service for you (for example to check your answers and to let Soc help you).</li>
          <li>Lessons, problems, tests, quizzes, explanations, the design and the software are ours or our licensors’ and are protected by law. You may use them for your own learning.</li>
          <li>We link to outside resources and credit material we adapt (see <Link href="/attribution">attribution</Link>). Their own terms apply when you visit them.</li>
        </ul>
      </section>

      <section aria-labelledby="ai">
        <h2 id="ai">AI features</h2>
        <p>
          Soc and the Playground use AI models. Their replies can be incomplete or wrong, so check important facts.
          Playground visuals are labelled as not verified. Daily limits apply to keep the service available for everyone;
          when a limit is reached, Soc falls back to curated hints until it resets.
        </p>
      </section>

      <section aria-labelledby="runner">
        <h2 id="runner">Running code</h2>
        <p>
          Python and C++ code runs inside your own browser. Running code uses your device’s processor and memory, and
          the first C++ run downloads a compiler (about 100 MB) that your browser then keeps. Time limits in the browser
          are approximate; the result shown after a submission is the one that counts.
        </p>
      </section>

      <section aria-labelledby="warranty">
        <h2 id="warranty">No guarantees</h2>
        <p>
          We work to make {LEGAL.product} accurate and useful, but we provide it “as is”. We do not promise that it will
          always be available or error-free, or that using it will get you a particular job, rating or result.
        </p>
      </section>

      <section aria-labelledby="liability">
        <h2 id="liability">Limits on liability</h2>
        <p>
          To the extent the law allows, we are not liable for indirect or consequential losses, or for lost data you
          could have exported, and our total liability to you is limited to the amount you paid us in the 12 months
          before the claim (or ₹1,000 if you paid nothing). Nothing in these terms limits rights you have under consumer
          law that cannot be limited.
        </p>
      </section>

      <section aria-labelledby="law">
        <h2 id="law">Changes, law and contact</h2>
        <p>
          We may update these terms; for important changes we will tell you in the app before they apply, and you can
          delete your account if you do not agree. These terms are governed by the laws of {LEGAL.country}. Questions or
          disputes: write to <a href={`mailto:${LEGAL.contact}`}>{LEGAL.contact}</a> and we will try to resolve them with you first.
        </p>
      </section>
    </LegalPage>
  );
}
