import type { PlanId } from './types';

/** Display names and the plan comparison shared by /pricing and the paywall. Limits mirror `entitlements.PLANS`. */
export const PLAN_NAME: Record<PlanId, string> = { free: 'Free', plus: 'Founding Member', pro: 'Pro' };

/** Monthly INR list price Plus had before the founding offer: the anchor shown struck through. */
export const PLUS_WAS_INR = 49900;

export const PLAN_BLURB: Record<PlanId, string> = {
  free: 'A taste of Socrat.',
  plus: 'Everything you need to actually finish a course.',
  pro: 'For interview season: company questions and daily depth.',
};
