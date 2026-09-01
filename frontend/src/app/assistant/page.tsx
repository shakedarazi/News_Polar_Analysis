import { Sparkles } from "lucide-react";
import { AiAssistant } from "@/components/AiAssistant";

export default function AssistantPage() {
  return (
    <div className="mx-auto max-w-3xl space-y-6 px-4 py-8 sm:px-6">
      <section>
        <h1 className="flex items-center gap-2 text-2xl font-bold text-slate-900 dark:text-slate-100">
          <Sparkles className="h-6 w-6 text-[var(--purple)]" aria-hidden />
          עוזר AI
        </h1>
        <p className="mt-1 text-slate-600 dark:text-slate-300">
          שיחה עם עוזר שמחפש בטקסט הכתבות שנאספו ועונה אך ורק על סמך מה שנמצא בהן ובנתוני
          המערכת — ללא ידע כללי חיצוני. השיחה נשמרת, כך שאפשר לשאול שאלות המשך. כל תשובה
          שמסתמכת על כתבה מקושרת אליה, ואם אין מספיק מידע העוזר יגיד זאת במפורש.
        </p>
      </section>
      <AiAssistant />
    </div>
  );
}
