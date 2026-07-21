import { Sparkles } from "lucide-react";
import { AiAssistant } from "@/components/AiAssistant";

export default function AssistantPage() {
  return (
    <div className="mx-auto max-w-3xl space-y-6 px-4 py-8 sm:px-6">
      <section>
        <h1 className="flex items-center gap-2 text-2xl font-bold text-slate-900">
          <Sparkles className="h-6 w-6 text-[var(--purple)]" aria-hidden />
          עוזר AI
        </h1>
        <p className="mt-1 text-slate-600">
          שיחה עם עוזר שעונה אך ורק על סמך הכתבות והנתונים הקיימים במסד הנתונים של המערכת —
          ללא ידע כללי חיצוני. אם אין מספיק מידע, העוזר יגיד זאת במפורש.
        </p>
      </section>
      <AiAssistant />
    </div>
  );
}
