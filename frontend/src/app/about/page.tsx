export default function AboutPage() {
  return (
    <div className="mx-auto max-w-3xl space-y-8 px-4 py-8 sm:px-6">
      <section>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">אודות המערכת</h1>
        <p className="mt-2 text-slate-600 dark:text-slate-300 leading-relaxed">
          Trust היא מערכת מחקרית לאיסוף כתבות חדשות ישראליות, תגובות קהל
          וחישוב מדדי פולריות בצורה דטרמיניסטית — ללא תלות במודלים גנרטיביים בנתיב
          הקריטי.
        </p>
      </section>

      <section className="card space-y-4 p-6">
        <h2 className="text-lg font-semibold">מקורות נתונים</h2>
        <p className="text-sm text-slate-600 dark:text-slate-300 leading-relaxed">
          ynet, הארץ, mako, חדשות 12, רשת 13 וערוץ 14. כתבות נאספות מ-RSS כל 6 שעות;
          תגובות נאספות לאחר 24 שעות מהפרסום.
        </p>
      </section>

      <section className="card space-y-4 p-6">
        <h2 className="text-lg font-semibold">מדדי פולריות</h2>
        <dl className="space-y-3 text-sm">
          <div>
            <dt className="font-semibold text-slate-800 dark:text-slate-200">פולריות ממוצעת בקהל</dt>
            <dd className="text-slate-600 dark:text-slate-300">
              ממוצע משוקלל של עוצמת התגובות (לפי מילון), כאשר משקל כל תגובה גדל
              לוגריתמית עם מספר הלייקים.
            </dd>
          </div>
          <div>
            <dt className="font-semibold text-slate-800 dark:text-slate-200">פולריות גבוהה (85%)</dt>
            <dd className="text-slate-600 dark:text-slate-300">
              קוונטיל משוקלל: רמת הפולריות שבה 85% ממשקל הקהל נמצאים מתחתיה — מדד
              לתגובות חזקות בלי להיות רגיש לחריג בודד.
            </dd>
          </div>
          <div>
            <dt className="font-semibold text-slate-800 dark:text-slate-200">עוצמת תגובה</dt>
            <dd className="text-slate-600 dark:text-slate-300">
              אחוז המילים בתגובה שנמצאות במילון פולריות (מילים רגשית/ideologically
              charged).
            </dd>
          </div>
          <div>
            <dt className="font-semibold text-slate-800 dark:text-slate-200">דומיננטיות במשפט</dt>
            <dd className="text-slate-600 dark:text-slate-300">
              מידת הריכוז של קטגוריה אחת (מתוך 7) בכל משפט בכתבה, לפי מילון נפרד.
            </dd>
          </div>
        </dl>
      </section>

      <section className="card space-y-4 p-6">
        <h2 className="text-lg font-semibold">תיוג AI (נפרד)</h2>
        <p className="text-sm text-slate-600 dark:text-slate-300 leading-relaxed">
          קטגוריות כמו פוליטיקה, ביטחון וכלכלה מגיעות מ-OpenAI ומשמשות לסינון
          ותצוגה בלבד — אינן חלק מחישוב הפולריות.
        </p>
      </section>
    </div>
  );
}
