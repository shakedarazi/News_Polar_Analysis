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
            <dt className="font-semibold text-slate-800 dark:text-slate-200">קיטוב ממוצע</dt>
            <dd className="text-slate-600 dark:text-slate-300">
              ממוצע משוקלל של עוצמת התגובות (לפי מילון), כאשר משקל כל תגובה גדל
              לוגריתמית עם מספר הלייקים. זה המדד של הגרף הראשי ושל כרטיסי המקורות.
            </dd>
          </div>
          <div>
            <dt className="font-semibold text-slate-800 dark:text-slate-200">קיטוב בשיא התגובות</dt>
            <dd className="text-slate-600 dark:text-slate-300">
              אחוזון 85 משוקלל: 85% ממשקל הקהל מתחת לסף הזה. מודד זנב חריף בלי
              תגובה בודדת. משמש לדירוג כתבות בולטות, לא להשוואת אתרים.
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
        <h2 className="text-lg font-semibold">השוואה בתוך אירוע</h2>
        <p className="text-sm leading-relaxed text-slate-600 dark:text-slate-300">
          ממוצע גולמי של אתר חדשות מודד בעיקר אילו סיפורים הוא בוחר לסקר — אתר שמסקר יותר
          פוליטיקה יקבל ציון גבוה יותר מאתר שמסקר תאונות, ואף אחד מהמספרים האלה אינו אומר
          משהו על אופן הסיקור. לכן ההשוואה בין האתרים נעשית <strong>בתוך</strong> אירועים:
          רק סיפורים שסוקרו על ידי יותר ממקור אחד, כשכל מקור נמדד מול חציון אותו אירוע. כל
          מקור נספר פעם אחת לכל אירוע — הכתבה שקיבלה הכי הרבה תגובות — כדי שמקור שפרסם
          כמה המשכים לאותו סיפור לא יהפוך בעצמו לחציון שמולו הוא נמדד.
        </p>
      </section>

      <section className="card space-y-4 p-6">
        <h2 className="text-lg font-semibold">מסגור ואימות</h2>
        <p className="text-sm leading-relaxed text-slate-600 dark:text-slate-300">
          לכל כתבה מחולצים משתני מסגור: מי מוצג כמבצע הפעולה, למי מיוחסת אחריות, האם
          הכותרת נכתבה בקול פעיל או סביל, ומנקודת מבט של מי נפתחת הידיעה. זהו ניתוח מבני
          של הניסוח, ולא הערכה של נכונות הכתבה או של עמדתה הפוליטית — אלה שדות נפרדים.
        </p>
        <p className="text-sm leading-relaxed text-slate-600 dark:text-slate-300">
          כל ערך שמחולץ נבדק מול הטקסט לפני שהוא נשמר: הביטוי חייב להופיע כלשונו באותם 500
          תווים שהמודל קרא. ביטוי שלא נמצא יורד ואינו מוצג — הוא מופיע רק ברשימת הביטויים
          שנפסלו, כדי שיהיה אפשר לראות שהבדיקה אכן רצה.
        </p>
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
