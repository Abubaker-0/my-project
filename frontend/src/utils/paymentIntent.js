/**
 * One key identifies one intended payment. Retries of that attempt reuse it.
 * A new payment, or a new form, receives a new key.
 */
export function createPaymentKey() {
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID();
  return `pay-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function paymentBody(key, values) {
  return {
    invoice: Number(values.invoice),
    amount: values.amount,
    method: values.method,
    reference: values.reference || '',
    idempotency_key: key,
  };
}
