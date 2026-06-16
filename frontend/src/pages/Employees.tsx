import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { listEmployees, getDepartments, getCountries } from "@/lib/api";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

export default function Employees() {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [department, setDepartment] = useState<string | undefined>();
  const [country, setCountry] = useState<string | undefined>();

  const { data, isLoading } = useQuery({
    queryKey: ["employees", page, search, department, country],
    queryFn: () => listEmployees({ page, page_size: 20, search: search || undefined, department, country }),
  });

  const { data: departments } = useQuery({ queryKey: ["departments"], queryFn: getDepartments });
  const { data: countries } = useQuery({ queryKey: ["countries"], queryFn: getCountries });

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Employees</h1>

      <div className="flex gap-3 flex-wrap">
        <Input
          placeholder="Search name, email, ID…"
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          className="max-w-xs"
        />
        <Select onValueChange={(v) => { setDepartment(!v || v === "all" ? undefined : (v as string)); setPage(1); }}>
          <SelectTrigger className="w-44">
            <SelectValue placeholder="Department" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All departments</SelectItem>
            {departments?.map((d: string) => <SelectItem key={d} value={d}>{d}</SelectItem>)}
          </SelectContent>
        </Select>
        <Select onValueChange={(v) => { setCountry(!v || v === "all" ? undefined : (v as string)); setPage(1); }}>
          <SelectTrigger className="w-36">
            <SelectValue placeholder="Country" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All countries</SelectItem>
            {countries?.map((c: string) => <SelectItem key={c} value={c}>{c}</SelectItem>)}
          </SelectContent>
        </Select>
      </div>

      {isLoading ? (
        <div className="text-slate-400 py-8 text-center">Loading…</div>
      ) : (
        <>
          <p className="text-sm text-slate-500">{data?.total ?? 0} employees</p>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>ID</TableHead>
                <TableHead>Name</TableHead>
                <TableHead>Department</TableHead>
                <TableHead>Country</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data?.items.map((emp: { id: number; employee_id: string; first_name: string; last_name: string; department: string; country: string; employment_type: string; status: string }) => (
                <TableRow key={emp.id}>
                  <TableCell className="font-mono text-xs">
                    <Link to={`/employees/${emp.id}`} className="text-indigo-600 hover:underline">{emp.employee_id}</Link>
                  </TableCell>
                  <TableCell>{emp.first_name} {emp.last_name}</TableCell>
                  <TableCell>{emp.department}</TableCell>
                  <TableCell>{emp.country}</TableCell>
                  <TableCell className="capitalize">{emp.employment_type}</TableCell>
                  <TableCell>
                    <Badge variant={emp.status === "active" ? "default" : "secondary"}>{emp.status}</Badge>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>

          <div className="flex items-center gap-3 justify-end">
            <Button variant="outline" size="sm" onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1}>
              Previous
            </Button>
            <span className="text-sm text-slate-600">Page {page}</span>
            <Button variant="outline" size="sm" onClick={() => setPage((p) => p + 1)} disabled={(data?.items.length ?? 0) < 20}>
              Next
            </Button>
          </div>
        </>
      )}
    </div>
  );
}
