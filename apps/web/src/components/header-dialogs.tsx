'use client';

import FeedbackDialog from '@/components/feedback-dialog';
import ReferralDialog from '@/components/referral-dialog';

/** The header's Feedback and Invite dialogs share one lazy chunk, so the shell pays for one loader. */
export default function HeaderDialogs() {
  return <><FeedbackDialog /><ReferralDialog /></>;
}
