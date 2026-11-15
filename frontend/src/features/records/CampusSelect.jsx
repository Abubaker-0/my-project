import { useQuery } from "@tanstack/react-query";

import { listBranches } from "../../api/resources";
import { SelectField } from "../../components/SelectField";
import { useUiStore } from "../../store/uiStore";

export function useCampusOptions() {
  const branchId = useUiStore((state) => state.branchId);
  const query = useQuery({
    queryKey: ["branches", "options"],
    queryFn: () => listBranches(),
  });
  return {
    items: query.data?.items ?? [],
    defaultId: branchId ? String(branchId) : "",
  };
}

export function CampusSelect({ register, error, items }) {
  return (
    <SelectField label="Campus" error={error} {...register("branch_id")}>
      <option value="">Choose a campus</option>
      {items.map((branch) => (
        <option key={branch.id} value={branch.id}>
          {branch.name}
        </option>
      ))}
    </SelectField>
  );
}
