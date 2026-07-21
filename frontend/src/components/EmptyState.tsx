import { Inbox } from "lucide-react";

export function EmptyState({ message }: { message: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 p-10 text-center text-slate-500">
      <Inbox className="h-8 w-8 text-slate-300" aria-hidden />
      <p className="text-sm">{message}</p>
    </div>
  );
}
