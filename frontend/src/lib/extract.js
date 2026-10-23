import { toast } from "sonner";
import { http } from "@/lib/api";
import { fieldsFor, fromFields } from "@/lib/fields";

export const aiToSession = (res, source, country) => {
  const input = fromFields(fieldsFor(country), res.fields);
  if (country === "us" && res.state) input.state = res.state;
  return {
    input,
    clauseFlags: res.flags || [],
    company: res.company || "",
    role: res.role || "",
    source,
    country,
  };
};

export const runQuickScan = async (text, onQuickScan) => {
  const { data } = await http.post("/quickscan", { text });
  if (!data.found.length) toast.warning("Quick scan found no amounts - fill the form by hand.");
  onQuickScan({ fields: data.fields, clauseFlags: data.flags, scanNotes: data.notes, beta: true });
};
