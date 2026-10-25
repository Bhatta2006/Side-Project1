import type { Metadata } from 'next';
import Link from 'next/link';
import { LegalPage } from '@/components/legal-page';
import { LEGAL } from '@/lib/legal';

export const metadata: Metadata = {
  title: 'Refunds and cancellation · Socrat',
  description: 'How paid plans renew, how to cancel, and when we refund.',
};

export default function RefundsPage() {
  return (
    <LegalPage
      title="Refunds and cancellation"
      summary={
        <p>
          You can cancel a paid plan whenever you like and keep it until the period you paid for ends. If something
          goes wrong with a payment, or you change your mind soon after buying, we will refund you. This page says how.
        </p>
      }
    >
      <section aria-labelledby="plans">
        <h2 id="plans">Plans and renewal</h2>
        <ul>
          <li>{LEGAL.product} has a free plan and two paid plans, Founding Member (Plus) and Pro. Features and prices are on the <Link href="/pricing">plans page</Link>.</li>
          <li>Paid plans are billed monthly or yearly, in Indian rupees or US dollars, and renew automatically until you cancel. The amount shown at checkout is the amount charged.</li>
          <li>Yearly plans are priced at 12 months less 20%.</li>
          <li>If we change a price, the new price applies from your next renewal, and a plan you already paid for is not affected.</li>
        </ul>
      </section>

      <section aria-labelledby="cancel">
        <h2 id="cancel">Cancelling</h2>
        <ul>
          <li>Go to Settings, then Plan, then Cancel renewal. Nothing more is charged after that.</li>
          <li>You keep your paid features until the end of the period you already paid for. After that your account returns to the free plan. Your progress, notes and saved work stay.</li>
        </ul>
      </section>

      <section aria-labelledby="refunds">
        <h2 id="refunds">When we refund</h2>
        <ul>
          <li><strong>First purchase.</strong> If you ask within 7 days of your first payment for a plan, we refund it in full.</li>
          <li><strong>Renewals.</strong> If a plan renewed and you did not mean it to, ask within 48 hours of the charge and we will refund it, as long as you have not used the paid features since.</li>
          <li><strong>Payment problems.</strong> If you were charged twice, or charged and your plan did not start, we fix it or refund you in full.</li>
          <li><strong>Otherwise.</strong> We do not refund the unused part of a period you chose not to use, so cancel before the renewal date if you do not want to continue.</li>
        </ul>
      </section>

      <section aria-labelledby="upgrades">
        <h2 id="upgrades">Upgrading</h2>
        <p>
          Moving from Founding Member to Pro starts Pro as soon as the payment goes through and ends your Founding Member plan at that moment.
          The remaining time on Founding Member is not credited toward Pro. Moving to a lower plan is done by cancelling and
          subscribing again after the current period ends.
        </p>
      </section>

      <section aria-labelledby="how">
        <h2 id="how">How to ask for a refund</h2>
        <p>
          Email <a href={`mailto:${LEGAL.contact}`}>{LEGAL.contact}</a> with the name on your account and the payment
          date, or the Razorpay payment ID from your receipt if you have it. We reply within 3 working days. An
          approved refund goes back to the original payment method, and your bank usually shows it within 5 to 7 working days.
        </p>
      </section>

      <section aria-labelledby="payments">
        <h2 id="payments">Who handles the payment</h2>
        <p>
          Payments are processed by Razorpay. Your card or UPI details go to Razorpay and not to {LEGAL.product}; we only
          receive confirmation of the payment, the plan, and its dates. See the <Link href="/privacy">privacy policy</Link> and
          the <Link href="/terms">terms of service</Link>.
        </p>
      </section>
    </LegalPage>
  );
}
