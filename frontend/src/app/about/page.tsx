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
          ynet, הארץ ו-mako הם המקורות שמזינים את המערכת כרגע, וערוץ 14 נאסף לצידם בהיקף
          קטן בהרבה. כתבות נאספות מ-RSS כל 6 שעות; תגובות נאספות רק לאחר 24 שעות מהפרסום,
          כדי לתת להן זמן להצטבר.
        </p>
        <p className="text-sm text-slate-600 dark:text-slate-300 leading-relaxed">
          שני מקורות מופיעים ברשימה בלי שהם מתעדכנים. חדשות 12 נעצר על 20 כתבות מ-23
          באוגוסט, כי הפיד הייעודי שלו הפסיק להתעדכן ב-7 באוגוסט 2026 — אבל כתבות חדשות 12
          מתפרסמות ב-mako.co.il, שנאסף במלואו, כך שהתוכן עצמו לא חסר: חדשות 12 אינו אתר
          נפרד אלא מדור של אותו אתר. רשת 13 אינה נאספת כלל, משום שהאתר חוסם איסוף אוטומטי.
          שניהם נשארים ברשימה כדי שיהיה ברור מה נמדד ומה לא, ולא כדי להיספר כמקורות פעילים.
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
              אחוז המילים בתגובה שנמצאות במילון פולריות (מילים טעונות רגשית או אידאולוגית).
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
        <h2 className="text-lg font-semibold">קריאה שנייה — מילון הקיטוב המחקרי</h2>
        <p className="text-sm leading-relaxed text-slate-600 dark:text-slate-300">
          אותן תגובות נספרות פעם שנייה מול מילון אחר: ההתאמה העברית ל-Simchon, Brady &amp;
          Van Bavel (2022), שאינו מדד אחד אלא שני צירים. <strong>שפת נושא</strong> סופרת
          מילים ששייכות למחלוקת עצמה — על מה מתווכחים; <strong>שפת עוינות</strong> סופרת
          מילים שמכוונות אל הצד השני — נגד מי. תגובה יכולה להיספר בשני הצירים, באחד או
          באף אחד, ולכן הם מוצגים זה לצד זה ולעולם לא מחוברים לסכום.
        </p>
        <p className="text-sm leading-relaxed text-slate-600 dark:text-slate-300">
          שתי רשימות המילים חולקות כ-15% מהצורות שלהן בלבד. המספרים כאן אינם גרסה מדויקת
          יותר של הקיטוב שלמעלה אלא מדידה נפרדת, והספים שמפרידים בין ״נמוך״ ל״גבוה״ שם לא
          חלים כאן. משום כך שתי הקריאות מוצגות תמיד בנפרד ואינן ממוצעות יחד.
        </p>
      </section>

      <section className="card space-y-4 p-6">
        <h2 className="text-lg font-semibold">אירועים לפי משמעות</h2>
        <p className="text-sm leading-relaxed text-slate-600 dark:text-slate-300">
          כתבות שמסקרות את אותו סיפור מקובצות לאירוע אחד לפי דמיון סמנטי: הכותרת והפסקה
          הראשונה מומרות לייצוג מספרי, ושתי כתבות מצורפות לאותו אירוע כשהייצוגים שלהן
          קרובים דיים. זו אינה השוואת מילים משותפות — שתי גרסאות של אותו אירוע בעברית
          עשויות לא לחלוק אף מילת תוכן, ודווקא אותן חשוב לזהות.
        </p>
        <p className="text-sm leading-relaxed text-slate-600 dark:text-slate-300">
          הקיבוץ מחושב מחדש על כל המאגר בכל הרצת איסוף, ולכן אירוע יכול לגדול, להתפצל או
          לאבד כתבה. אירוע עם כתבה אחת אינו מוצג — אין מה להשוות בו.
        </p>
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
