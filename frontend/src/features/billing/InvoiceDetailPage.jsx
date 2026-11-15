import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import {
  cancelInvoice,
  downloadReceipt,
  getInvoice,
  recordPayment,
  voidPayment,
} from "../../api/resources";
import { Badge, statusTone } from "../../components/Badge";
import { Button } from "../../components/Button";
import { ErrorState } from "../../components/ErrorState";
import { PageHeader } from "../../components/PageHeader";
import { Panel } from "../../components/Panel";
import { SelectField } from "../../components/SelectField";
import { Spinner } from "../../components/Spinner";
import { TextField } from "../../components/TextField";
import { usePermission } from "../../hooks/usePermission";
import { useToastStore } from "../../store/toastStore";
import { errorMessage } from "../../utils/errors";
import { formatDate } from "../../utils/format";

export function InvoiceDetailPage() {
  const { invoiceId } = useParams();
  const query = useQuery({
    queryKey: ["invoices", invoiceId],
    queryFn: () => getInvoice(invoiceId),
  });
  if (query.isLoading) return <Spinner label="Loading invoice" />;
  if (query.isError) {
    return <ErrorState body={errorMessage(query.error)} onRetry={() => query.refetch()} />;
  }
  const invoice = query.data;
  return (
    <div className="space-y-4">
      <PageHeader
        eyebrow={invoice.invoice_no}
        title={invoice.student_name}
        description={`Due ${formatDate(invoice.due_date)} · balance ${invoice.balance} of ${invoice.total}`}
        actions={<Badge tone={statusTone(invoice.status)}>{invoice.status}</Badge>}
      />
      <p>
        <Link className="text-sm text-pine-800" to="/invoices">
          Back to invoices
        </Link>
      </p>
      <div className="grid gap-4 lg:grid-cols-2">
        <Panel title="Charges">
          <ul className="space-y-2 text-sm">
            {invoice.lines.map((line) => (
              <li key={line.id} className="flex justify-between gap-3">
                <span>{line.description}</span>
                <span>{line.amount}</span>
              </li>
            ))}
          </ul>
          {invoice.cancel_reason ? (
            <p className="mt-4 text-sm text-ink-700">Cancelled: {invoice.cancel_reason}</p>
          ) : null}
          <CancelForm invoice={invoice} />
        </Panel>
        <Panel title="Payments">
          <ul className="space-y-3 text-sm">
            {invoice.payments.length === 0 ? <li>No payments yet.</li> : null}
            {invoice.payments.map((payment) => (
              <li key={payment.id} className="rounded-xl border border-line px-3 py-2">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span>
                    {payment.receipt_no} · {payment.amount} · {payment.method}
                  </span>
                  <Badge tone={statusTone(payment.status)}>{payment.status}</Badge>
                </div>
                {payment.void_reason ? (
                  <p className="mt-1 text-ink-500">Voided: {payment.void_reason}</p>
                ) : null}
                <div className="mt-2 flex gap-2">
                  <Button
                    variant="secondary"
                    onClick={() => downloadReceipt(payment.id, payment.receipt_no)}
                  >
                    Receipt
                  </Button>
                  <VoidButton payment={payment} />
                </div>
              </li>
            ))}
          </ul>
          <PaymentForm invoice={invoice} />
        </Panel>
      </div>
    </div>
  );
}

function PaymentForm({ invoice }) {
  const canPay = usePermission("payments:create");
  const [amount, setAmount] = useState(invoice.balance);
  const [method, setMethod] = useState("cash");
  const [key] = useState(() => crypto.randomUUID());
  const push = useToastStore((state) => state.push);
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: () => recordPayment({ invoice_id: invoice.id, amount, method }, key),
    onSuccess: () => {
      push({ tone: "success", message: "Payment recorded." });
      queryClient.invalidateQueries({ queryKey: ["invoices"] });
    },
    onError: (error) => push({ tone: "danger", message: errorMessage(error) }),
  });
  if (!canPay || invoice.status === "cancelled" || invoice.status === "paid") return null;
  return (
    <form
      className="mt-4 grid gap-3 border-t border-line pt-4"
      onSubmit={(event) => {
        event.preventDefault();
        mutation.mutate();
      }}
    >
      <TextField
        label="Amount"
        value={amount}
        onChange={(event) => setAmount(event.target.value)}
      />
      <SelectField
        label="Method"
        value={method}
        onChange={(event) => setMethod(event.target.value)}
      >
        <option value="cash">Cash</option>
        <option value="card">Card</option>
        <option value="bank">Bank</option>
        <option value="other">Other</option>
      </SelectField>
      <div className="flex justify-end">
        <Button type="submit" disabled={mutation.isPending}>
          Record payment
        </Button>
      </div>
    </form>
  );
}

function VoidButton({ payment }) {
  const canVoid = usePermission("payments:void");
  const [reason, setReason] = useState("");
  const push = useToastStore((state) => state.push);
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: () => voidPayment(payment.id, reason),
    onSuccess: () => {
      push({ tone: "success", message: "Payment voided." });
      queryClient.invalidateQueries({ queryKey: ["invoices"] });
    },
    onError: (error) => push({ tone: "danger", message: errorMessage(error) }),
  });
  if (!canVoid || payment.status !== "completed") return null;
  return (
    <form
      className="flex flex-1 items-end gap-2"
      onSubmit={(event) => {
        event.preventDefault();
        mutation.mutate();
      }}
    >
      <div className="flex-1">
        <TextField
          label="Void reason"
          value={reason}
          onChange={(event) => setReason(event.target.value)}
        />
      </div>
      <Button
        type="submit"
        variant="secondary"
        disabled={reason.trim().length < 2 || mutation.isPending}
      >
        Void
      </Button>
    </form>
  );
}

function CancelForm({ invoice }) {
  const canCancel = usePermission("invoices:cancel");
  const [reason, setReason] = useState("");
  const push = useToastStore((state) => state.push);
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: () => cancelInvoice(invoice.id, reason),
    onSuccess: () => {
      push({ tone: "success", message: "Invoice cancelled." });
      queryClient.invalidateQueries({ queryKey: ["invoices"] });
    },
    onError: (error) => push({ tone: "danger", message: errorMessage(error) }),
  });
  if (!canCancel || invoice.status === "cancelled") return null;
  return (
    <form
      className="mt-4 grid gap-3 border-t border-line pt-4"
      onSubmit={(event) => {
        event.preventDefault();
        mutation.mutate();
      }}
    >
      <TextField
        label="Cancel reason"
        value={reason}
        onChange={(event) => setReason(event.target.value)}
      />
      <div className="flex justify-end">
        <Button
          type="submit"
          variant="secondary"
          disabled={reason.trim().length < 2 || mutation.isPending}
        >
          Cancel invoice
        </Button>
      </div>
    </form>
  );
}
