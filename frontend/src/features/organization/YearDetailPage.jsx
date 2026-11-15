import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { addTerm, getAcademicYear } from "../../api/resources";
import { Badge } from "../../components/Badge";
import { Button } from "../../components/Button";
import { ErrorState } from "../../components/ErrorState";
import { PageHeader } from "../../components/PageHeader";
import { Panel } from "../../components/Panel";
import { Spinner } from "../../components/Spinner";
import { TextField } from "../../components/TextField";
import { usePermission } from "../../hooks/usePermission";
import { useToastStore } from "../../store/toastStore";
import { errorMessage } from "../../utils/errors";
import { formatDate } from "../../utils/format";
import { reportError } from "../records/form";

const schema = z.object({
  name: z.string().min(2, "Enter a name").max(100),
  start_date: z.string().min(1, "Choose a start date"),
  end_date: z.string().min(1, "Choose an end date"),
});

export function YearDetailPage() {
  const { yearId } = useParams();
  const canCreate = usePermission("academic_years:update");
  const query = useQuery({
    queryKey: ["academic-years", yearId],
    queryFn: () => getAcademicYear(yearId),
  });
  if (query.isLoading) return <Spinner label="Loading year" />;
  if (query.isError) {
    return <ErrorState body={errorMessage(query.error)} onRetry={() => query.refetch()} />;
  }
  const year = query.data;
  return (
    <div className="space-y-4">
      <PageHeader
        eyebrow="Academic year"
        title={year.name}
        description={`${formatDate(year.start_date)} to ${formatDate(year.end_date)}`}
        actions={year.is_current ? <Badge tone="good">Current</Badge> : null}
      />
      <p>
        <Link className="text-sm text-pine-800" to="/academic-years">
          Back to academic years
        </Link>
      </p>
      <Panel title="Terms">
        <ul className="space-y-2 text-sm">
          {year.terms.length === 0 ? <li>No terms in this year yet.</li> : null}
          {year.terms.map((term) => (
            <li key={term.id}>
              {term.name} · {formatDate(term.start_date)} to {formatDate(term.end_date)}
            </li>
          ))}
        </ul>
        {canCreate ? <TermForm yearId={year.id} /> : null}
      </Panel>
    </div>
  );
}

function TermForm({ yearId }) {
  const push = useToastStore((state) => state.push);
  const queryClient = useQueryClient();
  const {
    register,
    handleSubmit,
    reset,
    setError,
    formState: { errors },
  } = useForm({ resolver: zodResolver(schema) });
  const mutation = useMutation({
    mutationFn: (payload) => addTerm(yearId, payload),
    onSuccess: () => {
      push({ tone: "success", message: "Term added." });
      reset();
      queryClient.invalidateQueries({ queryKey: ["academic-years", String(yearId)] });
    },
    onError: (error) => reportError(error, setError, push),
  });
  return (
    <form
      className="mt-4 grid gap-3 border-t border-line pt-4 sm:grid-cols-3"
      onSubmit={handleSubmit((values) => mutation.mutate(values))}
    >
      <TextField label="Term name" error={errors.name?.message} {...register("name")} />
      <TextField
        label="Starts"
        type="date"
        error={errors.start_date?.message}
        {...register("start_date")}
      />
      <TextField
        label="Ends"
        type="date"
        error={errors.end_date?.message}
        {...register("end_date")}
      />
      <div className="sm:col-span-3 flex justify-end">
        <Button type="submit" disabled={mutation.isPending}>
          Add term
        </Button>
      </div>
    </form>
  );
}
