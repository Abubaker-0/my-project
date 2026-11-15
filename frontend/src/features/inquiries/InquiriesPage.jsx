import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { createInquiry, listCourses, listInquiries } from "../../api/resources";
import { Badge, statusTone } from "../../components/Badge";
import { Button } from "../../components/Button";
import { DataTable } from "../../components/DataTable";
import { Modal } from "../../components/Modal";
import { PageHeader } from "../../components/PageHeader";
import { SelectField } from "../../components/SelectField";
import { TextArea } from "../../components/TextArea";
import { TextField } from "../../components/TextField";
import { useDebounce } from "../../hooks/useDebounce";
import { usePagination } from "../../hooks/usePagination";
import { usePermission } from "../../hooks/usePermission";
import { useToastStore } from "../../store/toastStore";
import { errorMessage } from "../../utils/errors";
import { formatDate } from "../../utils/format";
import { CampusSelect, useCampusOptions } from "../records/CampusSelect";
import { emptyToNull, reportError } from "../records/form";
import { RecordLink } from "../records/RecordLink";

const schema = z.object({
  branch_id: z.string().min(1, "Choose a campus"),
  name: z.string().min(2, "Enter a name").max(200),
  phone: z.string().max(32).optional(),
  email: z.union([z.literal(""), z.string().email("Enter a valid email")]),
  source: z.enum(["walk_in", "phone", "website", "referral", "other"]),
  course_interest_id: z.string().optional(),
  notes: z.string().max(4000).optional(),
});

export function InquiriesPage() {
  const paging = usePagination({ sort: "-created_at" });
  const [search, setSearch] = useState("");
  const debounced = useDebounce(search);
  const [creating, setCreating] = useState(false);
  const canCreate = usePermission("inquiries:create");
  const query = useQuery({
    queryKey: ["inquiries", paging.page, paging.pageSize, paging.sort, debounced],
    queryFn: () =>
      listInquiries({
        page: paging.page,
        page_size: paging.pageSize,
        sort: paging.sort,
        q: debounced,
      }),
  });

  return (
    <div>
      <PageHeader
        eyebrow="Admissions"
        title="Inquiries"
        description="Follow up with a family, then convert the lead into a student. Conversion is the only way a lead becomes admitted."
        actions={canCreate ? <Button onClick={() => setCreating(true)}>New inquiry</Button> : null}
      />
      <div className="mb-4 max-w-sm">
        <TextField
          label="Search"
          value={search}
          placeholder="Name, phone, or email"
          onChange={(event) => {
            setSearch(event.target.value);
            paging.setPage(1);
          }}
        />
      </div>
      <DataTable
        columns={[
          {
            key: "name",
            header: "Name",
            sortKey: "name",
            render: (row) => <RecordLink to={`/inquiries/${row.id}`}>{row.name}</RecordLink>,
          },
          { key: "phone", header: "Phone", render: (row) => row.phone || "—" },
          { key: "course_name", header: "Interest", render: (row) => row.course_name || "—" },
          { key: "source", header: "Source" },
          {
            key: "status",
            header: "Status",
            sortKey: "status",
            render: (row) => <Badge tone={statusTone(row.status)}>{row.status}</Badge>,
          },
          {
            key: "follow_up_date",
            header: "Follow up",
            sortKey: "follow_up_date",
            render: (row) => formatDate(row.follow_up_date),
          },
        ]}
        rows={query.data?.items ?? []}
        loading={query.isLoading}
        error={query.isError ? errorMessage(query.error) : null}
        onRetry={() => query.refetch()}
        emptyTitle="No inquiries"
        emptyBody="Record a walk-in or a website lead to start a follow-up."
        page={paging.page}
        pageSize={paging.pageSize}
        total={query.data?.total}
        onPage={paging.setPage}
        sort={paging.sort}
        onSort={paging.setSort}
      />
      {creating ? <InquiryForm onClose={() => setCreating(false)} /> : null}
    </div>
  );
}

function InquiryForm({ onClose }) {
  const campuses = useCampusOptions();
  const courses = useQuery({
    queryKey: ["courses", "options"],
    queryFn: () => listCourses({ page_size: 100, sort: "name" }),
  });
  const push = useToastStore((state) => state.push);
  const queryClient = useQueryClient();
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(schema),
    defaultValues: {
      branch_id: campuses.defaultId,
      source: "walk_in",
      email: "",
      phone: "",
      course_interest_id: "",
      notes: "",
    },
  });
  const mutation = useMutation({
    mutationFn: createInquiry,
    onSuccess: () => {
      push({ tone: "success", message: "Inquiry recorded." });
      queryClient.invalidateQueries({ queryKey: ["inquiries"] });
      onClose();
    },
    onError: (error) => reportError(error, setError, push),
  });

  return (
    <Modal title="New inquiry" onClose={onClose}>
      <form
        className="grid gap-3"
        onSubmit={handleSubmit((values) =>
          mutation.mutate({
            branch_id: Number(values.branch_id),
            name: values.name,
            phone: emptyToNull(values.phone),
            email: emptyToNull(values.email),
            source: values.source,
            course_interest_id: values.course_interest_id
              ? Number(values.course_interest_id)
              : null,
            notes: emptyToNull(values.notes),
          }),
        )}
      >
        <CampusSelect
          register={register}
          error={errors.branch_id?.message}
          items={campuses.items}
        />
        <TextField label="Name" error={errors.name?.message} {...register("name")} />
        <TextField label="Phone" error={errors.phone?.message} {...register("phone")} />
        <TextField label="Email" error={errors.email?.message} {...register("email")} />
        <SelectField label="Source" {...register("source")}>
          <option value="walk_in">Walk in</option>
          <option value="phone">Phone</option>
          <option value="website">Website</option>
          <option value="referral">Referral</option>
          <option value="other">Other</option>
        </SelectField>
        <SelectField label="Course interest" {...register("course_interest_id")}>
          <option value="">None yet</option>
          {(courses.data?.items ?? []).map((course) => (
            <option key={course.id} value={course.id}>
              {course.name}
            </option>
          ))}
        </SelectField>
        <TextArea label="Notes" error={errors.notes?.message} {...register("notes")} />
        <div className="flex justify-end">
          <Button type="submit" disabled={mutation.isPending}>
            Save inquiry
          </Button>
        </div>
      </form>
    </Modal>
  );
}
