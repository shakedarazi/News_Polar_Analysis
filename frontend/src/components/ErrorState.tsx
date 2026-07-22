import { AlertTriangle } from "lucide-react";

export function ErrorState({
  message = "אירעה שגיאה בטעינת הנתונים.",
  detail,
}: {
  message?: string;
  detail?: string;
}) {
  return (
    <div className="card border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-950 p-8 text-center">
      <AlertTriangle className="mx-auto h-6 w-6 text-red-500 dark:text-red-400" aria-hidden />
      <h3 className="mt-2 text-sm font-semibold text-red-800 dark:text-red-300">{message}</h3>
      {detail && <p className="mt-1 text-xs text-red-700 dark:text-red-300">{detail}</p>}
    </div>
  );
}
