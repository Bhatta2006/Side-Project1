'use client';

import { useEffect, useState } from 'react';
import { api } from './api';
import type { BillingStatus, PlanId } from './types';

export type Currency = 'INR' | 'USD';
export type Interval = 'month' | 'year';

/** Minor units (paise / cents) to a display price. */
export function money(minor: number, currency: Currency): string {
  const major = minor / 100;
  return currency === 'INR' ? `₹${Math.round(major).toLocaleString('en-IN')}` : `$${major.toFixed(Number.isInteger(major) ? 0 : 2)}`;
}

interface Checkout { key_id: string; subscription_id: string; name: string; description: string }
interface RazorpayResponse { razorpay_payment_id: string; razorpay_subscription_id: string; razorpay_signature: string }
interface RazorpayInstance { open(): void; on(event: 'payment.failed', handler: (r: { error: { description: string } }) => void): void }
declare global { interface Window { Razorpay?: new (options: Record<string, unknown>) => RazorpayInstance } }

let script: Promise<void> | null = null;
function loadCheckout(): Promise<void> {
  if (window.Razorpay) return Promise.resolve();
  script ??= new Promise((resolve, reject) => {
    const tag = document.createElement('script');
    tag.src = 'https://checkout.razorpay.com/v1/checkout.js';
    tag.onload = () => resolve();
    tag.onerror = () => { script = null; reject(new Error('checkout_script')); };
    document.head.appendChild(tag);
  });
  return script;
}

/** Opens Razorpay's modal. Resolves true once the payment is verified, false if dismissed. */
export async function subscribe(plan: Exclude<PlanId, 'free'>, interval: Interval, currency: Currency, email?: string): Promise<boolean> {
  const [order] = await Promise.all([api.post<Checkout>('/billing/checkout', { plan, interval, currency }), loadCheckout()]);
  return new Promise((resolve, reject) => {
    const checkout = new window.Razorpay!({
      key: order.key_id,
      subscription_id: order.subscription_id,
      name: order.name,
      description: order.description,
      prefill: email ? { email } : undefined,
      theme: { color: '#111111' },
      handler: (response: RazorpayResponse) => api.post('/billing/verify', response).then(() => resolve(true), reject),
      modal: { ondismiss: () => resolve(false) },
    });
    checkout.on('payment.failed', failure => reject(new Error(failure.error.description)));
    checkout.open();
  });
}

/** Which topics sit outside the learner's plan. Free learners only get the first modules. */
export function usePlanLocks(): (concept: string) => boolean {
  const [free, setFree] = useState<Set<string> | null>(null);
  useEffect(() => {
    api.get<BillingStatus>('/billing/status')
      .then(s => setFree(s.enabled && s.free_concepts ? new Set(s.free_concepts) : null))
      .catch(() => setFree(null));
  }, []);
  return concept => free !== null && !free.has(concept);
}
