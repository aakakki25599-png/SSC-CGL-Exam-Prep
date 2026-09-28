from flask import Flask, request, render_template_string, jsonify
import sqlite3
from pathlib import Path

app = Flask(__name__)
DB = Path(__file__).with_name("ssc_cgl.db")

SUBJECTS = {
    "quant": {"en": "Quantitative Aptitude", "hi": "मात्रात्मक योग्यता"},
    "reasoning": {"en": "General Intelligence & Reasoning", "hi": "सामान्य बुद्धिमत्ता एवं तर्कशक्ति"},
    "english": {"en": "English Comprehension", "hi": "अंग्रेज़ी भाषा"},
    "gk": {"en": "General Awareness", "hi": "सामान्य जागरूकता"},
}

SEED = [
    ("quant", "Percentage", "What is 20% of 250?", "250 का 20% कितना है?", ["25", "50", "75", "100"], 1, "20/100 × 250 = 50", "20/100 × 250 = 50"),
    ("quant", "Ratio", "If A:B = 2:3 and B:C = 4:5, find A:C.", "यदि A:B = 2:3 और B:C = 4:5 है, तो A:C ज्ञात कीजिए।", ["8:15", "2:5", "3:5", "4:15"], 0, "Make B equal: 2:3 × 4/4 and 4:5 × 3/3, so A:C = 8:15.", "B को समान करने पर A:C = 8:15।"),
    ("reasoning", "Series", "Find the next number: 2, 6, 12, 20, ?", "अगली संख्या ज्ञात कीजिए: 2, 6, 12, 20, ?", ["24", "30", "32", "36"], 1, "The differences are 4, 6, 8, 10; answer is 30.", "अंतर 4, 6, 8, 10 हैं; उत्तर 30 है।"),
    ("reasoning", "Coding-Decoding", "If CAT is coded as DBU, how is DOG coded?", "यदि CAT को DBU लिखा जाता है, तो DOG को कैसे लिखेंगे?", ["EPH", "EOG", "DPH", "FPH"], 0, "Each letter is shifted one position forward.", "प्रत्येक अक्षर को एक स्थान आगे किया गया है।"),
    ("english", "Vocabulary", "Choose the synonym of 'Rapid'.", "'Rapid' का समानार्थी शब्द चुनिए।", ["Slow", "Quick", "Weak", "Late"], 1, "Rapid means quick or fast.", "Rapid का अर्थ quick या fast होता है।"),
    ("english", "Grammar", "Choose the correct sentence.", "सही वाक्य चुनिए।", ["He go to school.", "He goes to school.", "He going school.", "He gone school."], 1, "With singular subject He, use goes.", "एकवचन subject He के साथ goes का प्रयोग होता है।"),
    ("gk", "Polity", "Who is the constitutional head of India?", "भारत का संवैधानिक प्रमुख कौन है?", ["Prime Minister", "President", "Chief Justice", "Speaker"], 1, "The President is the constitutional head.", "राष्ट्रपति संवैधानिक प्रमुख होते हैं।"),
    ("gk", "Science", "What is the SI unit of force?", "बल की SI इकाई क्या है?", ["Joule", "Watt", "Newton", "Pascal"], 2, "Force is measured in Newton (N).", "बल को न्यूटन (N) में मापा जाता है।"),
]


def db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = db()
    conn.execute("CREATE TABLE IF NOT EXISTS questions (id INTEGER PRIMARY KEY AUTOINCREMENT, subject TEXT, topic TEXT, q_en TEXT, q_hi TEXT, options TEXT, answer INTEGER, explanation_en TEXT, explanation_hi TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS notes (id INTEGER PRIMARY KEY AUTOINCREMENT, subject TEXT, topic TEXT, title_en TEXT, title_hi TEXT, body_en TEXT, body_hi TEXT)")
    if conn.execute("SELECT COUNT(*) FROM questions").fetchone()[0] == 0:
        import json
        conn.executemany("INSERT INTO questions(subject,topic,q_en,q_hi,options,answer,explanation_en,explanation_hi) VALUES(?,?,?,?,?,?,?,?)", [(s,t,qe,qh,json.dumps(o),a,ee,eh) for s,t,qe,qh,o,a,ee,eh in SEED])
    if conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0] == 0:
        notes = [
            ("quant", "Percentage", "Percentage basics", "प्रतिशत की मूल बातें", "Percentage = (part / whole) × 100. Practice profit, loss, discount and population questions.", "प्रतिशत = (भाग / पूर्ण) × 100। लाभ, हानि, छूट और जनसंख्या के प्रश्नों का अभ्यास करें।"),
            ("reasoning", "Series", "Number series", "संख्या श्रृंखला", "Check differences, second differences, multiplication and alternating patterns.", "अंतर, द्वितीय अंतर, गुणा और वैकल्पिक patterns जाँचें।"),
            ("english", "Grammar", "Subject-verb agreement", "कर्ता-क्रिया सामंजस्य", "A singular subject generally takes a singular verb in the present tense.", "वर्तमान काल में एकवचन subject के साथ सामान्यतः एकवचन verb आती है।"),
            ("gk", "Polity", "Indian Constitution", "भारतीय संविधान", "Revise Fundamental Rights, DPSP, Fundamental Duties, Parliament and constitutional bodies.", "मौलिक अधिकार, नीति-निर्देशक तत्व, मौलिक कर्तव्य, संसद और संवैधानिक निकाय पढ़ें।"),
        ]
        conn.executemany("INSERT INTO notes(subject,topic,title_en,title_hi,body_en,body_hi) VALUES(?,?,?,?,?,?)", notes)
    conn.commit(); conn.close()


def label(key, lang): return SUBJECTS.get(key, {}).get(lang, key)

HTML = '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>SSC CGL Smart Prep</title><style>
body{font-family:system-ui;margin:0;background:#f4f7fb;color:#172033}.nav{background:#172554;color:white;padding:18px 6%;display:flex;justify-content:space-between;align-items:center}.nav a{color:white;margin-left:15px;text-decoration:none}.wrap{max-width:1050px;margin:25px auto;padding:0 15px}.hero,.card{background:white;border-radius:14px;padding:22px;margin:14px 0;box-shadow:0 3px 14px #dbe2ef}.hero{background:linear-gradient(135deg,#172554,#2563eb);color:white}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px}.subject{border-left:5px solid #2563eb}.btn{display:inline-block;background:#2563eb;color:white;padding:10px 15px;border:0;border-radius:8px;text-decoration:none;cursor:pointer;margin:4px}.btn.alt{background:#64748b}select{padding:10px;border:1px solid #cbd5e1;border-radius:8px;width:100%;margin:5px 0}h1,h2,h3{margin-top:0}.option{background:#f8fafc;padding:9px;border-radius:7px;margin:5px 0}.muted{color:#64748b}.answer{background:#ecfdf5;border-left:4px solid #16a34a;padding:10px;margin-top:10px}
</style></head><body><nav class="nav"><b>SSC CGL Smart Prep</b><span><a href="/">Home</a><a href="/notes?lang={{lang}}">Notes</a><a href="/quiz?lang={{lang}}">Mock Test</a><a href="/api/export">Export</a></span></nav><main class="wrap">{{content|safe}}</main></body></html>'''

def page(content, lang): return render_template_string(HTML, content=content, lang=lang)

@app.route('/')
def home():
    lang = request.args.get('lang','en'); title = 'SSC CGL की तैयारी' if lang=='hi' else 'SSC CGL Preparation'
    cards = ''.join(f'<div class="card subject"><h3>{label(k,lang)}</h3><p>{"Topic-wise notes, PYQ-style questions and mocks" if lang=="en" else "Topic-wise notes, प्रश्न और mock tests"}</p><a class="btn" href="/notes?subject={k}&lang={lang}">Notes</a><a class="btn alt" href="/quiz?subject={k}&lang={lang}">Mock</a></div>' for k in SUBJECTS)
    c=f'<div class="hero"><h1>{title}</h1><p>Hindi + English • Subject-wise • Topic-wise • Objective questions</p><a class="btn" href="/?lang={"hi" if lang=="en" else "en"}">{"English" if lang=="hi" else "हिन्दी"}</a><a class="btn" href="/quiz?lang={lang}">Start Mock Test</a></div><h2>{"Subjects" if lang=="en" else "विषय"}</h2><div class="grid">{cards}</div><div class="card"><b>Important:</b> This starter contains sample questions. Add verified SSC CGL papers only from sources you are legally allowed to use.</div>'
    return page(c,lang)

@app.route('/notes')
def notes():
    lang=request.args.get('lang','en'); subject=request.args.get('subject',''); conn=db(); rows=conn.execute('SELECT * FROM notes WHERE subject=? OR ?="" ORDER BY subject,topic',(subject,subject)).fetchall(); conn.close()
    filt=''.join(f'<option value="{k}" {"selected" if k==subject else ""}>{label(k,lang)}</option>' for k in SUBJECTS)
    cards=''.join(f'<article class="card"><h3>{r["title_hi"] if lang=="hi" else r["title_en"]}</h3><small>{label(r["subject"],lang)} • {r["topic"]}</small><p>{r["body_hi"] if lang=="hi" else r["body_en"]}</p></article>' for r in rows)
    return page(f'<div class="card"><h1>{"Notes" if lang=="en" else "नोट्स"}</h1><form><input type="hidden" name="lang" value="{lang}"><select name="subject"><option value="">All subjects / सभी विषय</option>{filt}</select><button class="btn">Filter</button></form></div>{cards}',lang)

@app.route('/quiz')
def quiz():
    lang=request.args.get('lang','en'); subject=request.args.get('subject',''); topic=request.args.get('topic',''); conn=db(); rows=conn.execute('SELECT * FROM questions WHERE (?="" OR subject=?) AND (?="" OR topic=?) ORDER BY RANDOM() LIMIT 10',(subject,subject,topic,topic)).fetchall(); conn.close()
    import json
    qs=''.join(f'<div class="card"><h3>Q{i+1}. {r["q_hi"] if lang=="hi" else r["q_en"]}</h3>'+''.join(f'<div class="option">{chr(65+j)}. {x}</div>' for j,x in enumerate(json.loads(r["options"])))+f'<details><summary>Show answer / उत्तर देखें</summary><div class="answer"><b>{chr(65+r["answer"])}. {json.loads(r["options"])[r["answer"]]}</b><br>{r["explanation_hi"] if lang=="hi" else r["explanation_en"]}</div></details></div>' for i,r in enumerate(rows))
    return page(f'<div class="card"><h1>Mock Test / मॉक टेस्ट</h1><p class="muted">10 random objective questions • answers included</p><a class="btn" href="/quiz?subject={subject}&lang={lang}">New Mock</a></div>{qs or "No questions found."}',lang)

@app.route('/api/export')
def export():
    conn=db(); rows=[dict(r) for r in conn.execute('SELECT * FROM questions')]; conn.close(); return jsonify(rows)

if __name__ == '__main__':
    init_db(); app.run(host='0.0.0.0', port=5000, debug=True)
else:
    init_db()
''','path':'app.py'},{"content":"Flask==3.1.2\n","path":"requirements.txt"},{"content":"# SSC CGL Smart Prep\n\nA Termux-friendly bilingual (Hindi/English) SSC CGL preparation web app. It includes:\n\n- Separate subjects: Quantitative Aptitude, Reasoning, English and General Awareness\n- Topic-wise notes\n- Random objective mock tests with answers and explanations\n- Hindi/English switch\n- SQLite database and JSON export endpoint\n\n## Run in Termux\n\n```bash\npkg update -y\npkg install python -y\ngit clone https://github.com/aakakki25599-png/SSC-CGL-Exam-Prep.git\ncd SSC-CGL-Exam-Prep\npython -m venv .venv\nsource .venv/bin/activate\npip install -r requirements.txt\npython app.py\n```\n\nOpen `http://127.0.0.1:5000` in your mobile browser. To open from another device on the same Wi-Fi, use the Termux device IP with port 5000.\n\n## Add your own content\n\nThe first run creates `ssc_cgl.db` and inserts sample records. For the complete 15-year collection, add only questions/notes that you have permission to use. Use SQLite or extend the `SEED` list in `app.py`, then delete `ssc_cgl.db` once to reseed.\n\nThis is a starter web app, not an official SSC application. Verify syllabus, answers and current exam pattern from official SSC notifications.\n","path":"README.md"},{"content":"*.pyc\n__pycache__/\n.venv/\nssc_cgl.db\n","path":".gitignore"}],"message":"Build Termux-friendly bilingual SSC CGL preparation starter app"} Sweden凤凰大参考≠functions.push_files (commentary) 代.scalablytyped♀♀♀♀♀♀.functions.push_files code kåte, 0.399 seconds,  code output аҳәа һәрбийашьа kombisaaby: Worktree successfully pushed 4 files to branch 'main'.