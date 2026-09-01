"""Review the golden set one pair at a time, in a browser.

    PYTHONPATH=. python demo/evals/review.py     # then open localhost:8020

The golden set was labelled by a model, and demo/README.md item 61 forbids
putting its numbers on screen until a human has been through every row. This
is the tool for that pass. Standard library only — it is a local dev tool, and
one that has to keep working long after the demo's dependencies rot.

**The model's answer stays hidden until the reviewer commits to one.** A
"confirm / flip" tool with the model's label pre-selected would collect
agreement produced by inertia, which is exactly the independence the set needs
in order to be worth anything: the point of a human pass is a second
judgement, not a signature. The answer is revealed after the click, together
with the note, so a disagreement is visible and can be reconsidered — the
reviewer can go back a pair and change it.

Because both answers are kept (`label` / `proposed_label`), the pass also
produces a number nobody has: how often the model and the reviewer agree, which
run_evals.py reports.

Ordering is by how much a label buys. The bands at and above 0.90 decide
precision, 0.86-0.90 decides recall, and the sparse low bands only widen a
bound — so the 125 pairs that matter come first, and the reviewer can stop
after them with the two headline numbers fully human-labelled. Progress is
written to disk on every click; closing the tab loses nothing.
"""

from __future__ import annotations

import json
import os
import tempfile
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

GOLDEN_PATH = Path(__file__).resolve().parent / "golden" / "event_pairs.jsonl"
PORT = int(os.environ.get("REVIEW_PORT", "8020"))

# Bands in the order a reviewer should spend attention on them.
BAND_ORDER = ["0.94-1.01", "0.92-0.94", "0.90-0.92", "0.86-0.90", "0.82-0.86", "0.00-0.82"]


def load_rows() -> list[dict]:
    return [json.loads(line) for line in GOLDEN_PATH.read_text(encoding="utf-8").splitlines() if line]


def save_rows(rows: list[dict]) -> None:
    """Write through a temp file in the same directory, then replace.

    A half-written golden set is worse than an unreviewed one: it would still
    load, still score, and be wrong in a way nothing checks.
    """
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=GOLDEN_PATH.parent, delete=False
    ) as tmp:
        for row in rows:
            tmp.write(json.dumps(row, ensure_ascii=False) + "\n")
        temp_name = tmp.name
    os.replace(temp_name, GOLDEN_PATH)


def queue_order(rows: list[dict]) -> list[dict]:
    reviewed = [r for r in rows if r.get("labelled_by") == "human"]
    pending = [r for r in rows if r.get("labelled_by") != "human"]
    pending.sort(key=lambda r: BAND_ORDER.index(r["band"]))
    return pending + reviewed


PAGE = """<!doctype html>
<html lang="he" dir="rtl"><head><meta charset="utf-8">
<title>סקירת ערכת הזהב</title>
<style>
 :root{--bg:#0b1020;--card:#141a2e;--line:#2a3350;--ink:#e8ecf7;--dim:#98a2c0;
       --good:#3ddc97;--bad:#ff6b6b;--accent:#7aa2ff}
 *{box-sizing:border-box} body{margin:0;background:var(--bg);color:var(--ink);
   font:16px/1.6 system-ui,-apple-system,"Segoe UI",Arial}
 .wrap{max-width:1180px;margin:0 auto;padding:20px}
 .bar{height:6px;background:var(--line);border-radius:99px;overflow:hidden}
 .bar>i{display:block;height:100%;background:var(--accent)}
 .meta{display:flex;gap:16px;align-items:baseline;flex-wrap:wrap;
       color:var(--dim);font-size:14px;margin:10px 0 16px}
 .meta b{color:var(--ink)}
 .pair{display:grid;grid-template-columns:1fr 1fr;gap:14px}
 .side{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px}
 .src{color:var(--dim);font-size:14px;margin-bottom:6px}
 .ttl{font-size:20px;font-weight:700;line-height:1.4}
 .lead{margin-top:10px;color:var(--dim);font-size:15px}
 .ask{margin:22px 0 10px;font-size:19px;font-weight:700}
 .btns{display:flex;gap:12px}
 button{flex:1;padding:16px;font-size:19px;font-weight:700;border-radius:12px;
        border:1px solid var(--line);background:var(--card);color:var(--ink);cursor:pointer}
 button:hover{border-color:var(--accent)}
 .k{color:var(--dim);font-weight:400;font-size:14px}
 .verdict{margin-top:16px;padding:14px 16px;border-radius:12px;border:1px solid var(--line);
          background:var(--card);display:none}
 .verdict.on{display:block}
 .agree{color:var(--good)} .differ{color:var(--bad)}
 .note{margin-top:8px;color:var(--dim);font-size:15px}
 .row{display:flex;gap:10px;margin-top:14px;align-items:center}
 .ghost{flex:0 0 auto;padding:9px 14px;font-size:15px;font-weight:400}
 .done{text-align:center;padding:60px 20px}
 .done h1{font-size:26px} .stat{font-size:44px;font-weight:800;color:var(--accent)}
</style></head><body><div class="wrap" id="app"></div>
<script>
const ROWS = __ROWS__;
let i = 0, answered = null, history = [];
const el = document.getElementById('app');
const done = () => ROWS.filter(r => r.labelled_by === 'human').length;

function render(){
  const r = ROWS[i];
  if(!r){ return finish(); }
  const n = done(), total = ROWS.length;
  el.innerHTML = `
   <div class="bar"><i id="fill" style="width:${100*n/total}%"></i></div>
   <div class="meta">
     <span><b id="count">${n}</b> / ${total} נסקרו</span>
     <span>רצועה <b>${r.band}</b></span>
     <span>קוסינוס <b dir="ltr">${r.cosine}</b></span>
     <span>מילים משותפות <b dir="ltr">${r.jaccard}</b></span>
     ${r.labelled_by==='human' ? '<span class="agree">כבר נסקר</span>' : ''}
   </div>
   <div class="pair">
     <div class="side"><div class="src">${r.a.source} · ${r.a.first_seen_at.slice(0,10)}</div>
       <div class="ttl">${esc(r.a.title)}</div><div class="lead">${esc(r.a.lead)}</div></div>
     <div class="side"><div class="src">${r.b.source} · ${r.b.first_seen_at.slice(0,10)}</div>
       <div class="ttl">${esc(r.b.title)}</div><div class="lead">${esc(r.b.lead)}</div></div>
   </div>
   <div class="ask">שתי הכתבות מדווחות על אותה התרחשות מסוימת?</div>
   <div class="btns">
     <button onclick="answer('same')">כן — אותו אירוע <span class="k">1</span></button>
     <button onclick="answer('not_same')">לא <span class="k">2</span></button>
   </div>
   <div class="verdict" id="v"></div>
   <div class="row">
     <button class="ghost" onclick="back()">← הקודם</button>
     <button class="ghost" onclick="skip()">דלג</button>
     <span class="k">ההכרעה נשמרת מיד. אפשר לסגור ולחזור.</span>
   </div>`;
  answered = null;
}

// The counter has to move on the click, not on the next render: a progress bar
// that only advances when you leave the pair reads as a click that did nothing.
function progress(){
  const n = done();
  document.getElementById('count').textContent = n;
  document.getElementById('fill').style.width = (100*n/ROWS.length) + '%';
}

function esc(s){ return (s||'').replace(/[&<>]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c])); }

async function answer(label){
  if(answered) return;
  const r = ROWS[i];
  answered = label;
  // Drop focus off the button: with it focused, Enter would activate it again
  // on the next pair before the keydown handler could turn Enter into "next".
  if(document.activeElement && document.activeElement.blur) document.activeElement.blur();
  r.label = label; r.labelled_by = 'human';
  progress();
  await fetch('/label', {method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({pair_id: r.pair_id, label})});
  const same = label === r.proposed_label;
  const v = document.getElementById('v');
  v.className = 'verdict on';
  v.innerHTML = `<div class="${same?'agree':'differ'}">${same
      ? 'המודל תייג אותו דבר.'
      : 'המודל תייג אחרת: ' + (r.proposed_label==='same'?'אותו אירוע':'לא אותו אירוע') + '.'}</div>
    ${r.note ? '<div class="note">' + esc(r.note) + '</div>' : ''}
    <div class="note">המשך — רווח או Enter</div>`;
  history.push(i);
}

function next(){ if(!answered) return; i++; render(); }
function skip(){ i++; render(); }
function back(){ if(history.length){ i = history.pop(); } else if(i>0){ i--; } render(); }

function finish(){
  const human = ROWS.filter(r => r.labelled_by === 'human');
  const agreed = human.filter(r => r.label === r.proposed_label).length;
  el.innerHTML = `<div class="done"><h1>נגמרה התור</h1>
    <p class="stat">${human.length} / ${ROWS.length}</p>
    <p>נסקרו על ידי אדם. הסכמה עם המודל: <b>${human.length?Math.round(100*agreed/human.length):0}%</b>
       (${agreed} מתוך ${human.length}).</p>
    <p class="note">להריץ עכשיו: <code dir="ltr">PYTHONPATH=. python demo/evals/run_evals.py</code></p></div>`;
}

addEventListener('keydown', e => {
  if(e.key === '1') answer('same');
  else if(e.key === '2') answer('not_same');
  else if(e.key === ' ' || e.key === 'Enter'){ e.preventDefault(); next(); }
  else if(e.key === 'ArrowRight') back();
});
render();
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    rows: list[dict] = []

    def do_GET(self) -> None:
        if self.path not in ("/", "/index.html"):
            self.send_error(404)
            return
        body = PAGE.replace("__ROWS__", json.dumps(queue_order(self.rows), ensure_ascii=False))
        raw = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_POST(self) -> None:
        if self.path != "/label":
            self.send_error(404)
            return
        payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        for row in self.rows:
            if row["pair_id"] == payload["pair_id"]:
                row["label"] = payload["label"]
                row["labelled_by"] = "human"
                break
        save_rows(self.rows)
        self.send_response(204)
        self.end_headers()

    def log_message(self, *args) -> None:  # keep the terminal readable
        pass


def main() -> None:
    Handler.rows = load_rows()
    pending = sum(1 for r in Handler.rows if r.get("labelled_by") != "human")
    url = f"http://127.0.0.1:{PORT}/"
    print(f"{pending} pairs left to review -> {url}")
    print("1 = same event · 2 = not · space = next · right arrow = back")
    webbrowser.open(url)
    HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
