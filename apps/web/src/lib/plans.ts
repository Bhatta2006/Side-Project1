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

type Cell = boolean | string;
export const COMPARE: { label: string; free: Cell; plus: Cell; pro: Cell }[] = [
  { label: 'Lessons and topics', free: 'First 2 modules', plus: 'Every topic, every course', pro: 'Every topic, every course' },
  { label: 'Messages with Soc', free: '5 a week', plus: '10 a day', pro: '50 a day' },
  { label: 'Checkpoints and module tests', free: 'First 2 modules', plus: true, pro: true },
  { label: 'Practice problem library', free: 'A few starter problems', plus: true, pro: true },
  { label: 'Weekly assessment', free: false, plus: true, pro: true },
  { label: 'Visual playground', free: false, plus: '3 a day', pro: '15 a day' },
  { label: 'Company interview questions', free: false, plus: false, pro: true },
  { label: 'Company sprint plans', free: false, plus: false, pro: true },
];

/** What a paywall says depending on what the learner just ran into. */
export const PAYWALL_REASON: Record<string, { title: string; body: string; plan: 'plus' | 'pro' }> = {
  welcome: { title: 'Start with the whole course, not a sample', body: 'Free covers the first 2 modules. Founding Members unlock every topic, daily time with Soc and the weekly assessment.', plan: 'plus' },
  upgrade_required: { title: 'This part is for Founding Members', body: 'You have finished what the free plan covers here. Unlock every topic, checkpoint and practice problem to keep your streak going.', plan: 'plus' },
  pro_required: { title: 'Company questions are a Pro feature', body: 'See the questions top companies actually ask, sorted by how often and how recently, plus a sprint plan for your target company.', plan: 'pro' },
  chat_week_limit: { title: "You've used this week's messages with Soc", body: 'Free includes 5 a week. Founding Members get 10 every day, so you never get stuck mid-problem.', plan: 'plus' },
  assessment: { title: 'The weekly assessment is for members', body: 'A timed check built from what you studied this week, so you can prove it stuck. Included with Founding Member and Pro.', plan: 'plus' },
};
