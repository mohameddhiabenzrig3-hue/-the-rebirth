# -*- coding: utf-8 -*-
"""
THE REBIRTH — Android-first personal transformation system
Local-first: SQLite, no account or network required for core features.
"""
import os, sys, json, sqlite3, shutil, calendar, random
from datetime import date, datetime, timedelta
from pathlib import Path

from kivy.app import App
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.core.window import Window
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.uix.spinner import Spinner
from kivy.uix.progressbar import ProgressBar
from kivy.uix.widget import Widget
from kivy.graphics import Color, RoundedRectangle, Line

BG = (0.035, 0.035, 0.035, 1)
PANEL = (0.075, 0.075, 0.075, 1)
PANEL2 = (0.105, 0.095, 0.075, 1)
GOLD = (0.79, 0.64, 0.36, 1)
PALE = (0.95, 0.87, 0.66, 1)
TEXT = (0.94, 0.93, 0.90, 1)
MUTED = (0.62, 0.60, 0.56, 1)
GREEN = (0.42, 0.68, 0.53, 1)
RED = (0.75, 0.36, 0.30, 1)

MODULES = json.loads(Path(__file__).with_name("modules.json").read_text(encoding="utf-8"))

def today():
    return date.today().isoformat()

def now():
    return datetime.now().isoformat(timespec="seconds")

def safe_text(value):
    return str(value or "").strip()

class Store:
    def __init__(self, path):
        self.path = str(path)
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self.db = sqlite3.connect(self.path)
        self.db.row_factory = sqlite3.Row
        self.init()

    def init(self):
        c = self.db.cursor()
        c.executescript("""
        PRAGMA foreign_keys=ON;
        CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS habits (id INTEGER PRIMARY KEY, name TEXT NOT NULL, category TEXT, cue TEXT, frequency TEXT DEFAULT 'يومي', created TEXT);
        CREATE TABLE IF NOT EXISTS habit_logs (id INTEGER PRIMARY KEY, habit_id INTEGER NOT NULL, day TEXT NOT NULL, done INTEGER DEFAULT 1, UNIQUE(habit_id,day), FOREIGN KEY(habit_id) REFERENCES habits(id) ON DELETE CASCADE);
        CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY, title TEXT NOT NULL, priority TEXT, due TEXT, category TEXT, done INTEGER DEFAULT 0, created TEXT);
        CREATE TABLE IF NOT EXISTS goals (id INTEGER PRIMARY KEY, title TEXT NOT NULL, category TEXT, target TEXT, progress INTEGER DEFAULT 0, created TEXT);
        CREATE TABLE IF NOT EXISTS routines (id INTEGER PRIMARY KEY, title TEXT NOT NULL, period TEXT, details TEXT, created TEXT);
        CREATE TABLE IF NOT EXISTS focus_sessions (id INTEGER PRIMARY KEY, day TEXT, minutes INTEGER, note TEXT);
        CREATE TABLE IF NOT EXISTS challenges (id INTEGER PRIMARY KEY, title TEXT, duration INTEGER, start_day TEXT, target TEXT, progress INTEGER DEFAULT 0, active INTEGER DEFAULT 1);
        CREATE TABLE IF NOT EXISTS journal (id INTEGER PRIMARY KEY, day TEXT, kind TEXT, content TEXT, created TEXT);
        CREATE TABLE IF NOT EXISTS performance (id INTEGER PRIMARY KEY, day TEXT UNIQUE, sleep REAL, energy INTEGER, mood INTEGER, note TEXT);
        CREATE TABLE IF NOT EXISTS dimensions (id INTEGER PRIMARY KEY, name TEXT UNIQUE, score INTEGER DEFAULT 0, note TEXT);
        CREATE TABLE IF NOT EXISTS anti_habits (id INTEGER PRIMARY KEY, title TEXT, trigger_text TEXT, response_text TEXT, created TEXT);
        CREATE TABLE IF NOT EXISTS rewards (id INTEGER PRIMARY KEY, title TEXT, kind TEXT, achieved INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS achievements (id INTEGER PRIMARY KEY, title TEXT, detail TEXT, day TEXT);
        CREATE TABLE IF NOT EXISTS time_logs (id INTEGER PRIMARY KEY, day TEXT, activity TEXT, minutes INTEGER, category TEXT);
        CREATE TABLE IF NOT EXISTS notes (id INTEGER PRIMARY KEY, title TEXT, body TEXT, created TEXT);
        """)
        defaults = {
            "profile_name":"صانع النسخة الجديدة",
            "identity":"إنسان منضبط، واعٍ، قوي ومتوازن.",
            "personal_code":"ألتزم بما أقرره، وأراجع نفسي، وأعود بعد التعثر.",
            "focus_minutes":"25",
            "break_minutes":"5",
            "daily_rule":"لا أترك يومي بلا تقدم ولو بخطوة صغيرة.",
            "theme":"black_gold",
            "reminders_enabled":"0"
        }
        for k,v in defaults.items():
            c.execute("INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)",(k,v))
        for name in ["العقل والتعلم","الجسد والصحة","الشخصية","الروح والقيم","الدراسة والعمل","المال","العلاقات"]:
            c.execute("INSERT OR IGNORE INTO dimensions(name,score) VALUES(?,0)",(name,))
        self.db.commit()

    def q(self, sql, args=()):
        cur=self.db.execute(sql,args); self.db.commit(); return cur
    def one(self, sql,args=()):
        return self.db.execute(sql,args).fetchone()
    def all(self, sql,args=()):
        return self.db.execute(sql,args).fetchall()
    def get(self,key,default=""):
        r=self.one("SELECT value FROM settings WHERE key=?",(key,))
        return r["value"] if r else default
    def set(self,key,value):
        self.q("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(key,str(value)))

    def backup(self, dest):
        self.db.commit()
        target=sqlite3.connect(dest)
        self.db.backup(target); target.close()

    def restore(self, src):
        incoming=sqlite3.connect(src)
        incoming.row_factory=sqlite3.Row
        required={"settings","habits","habit_logs","tasks","goals"}
        found={r[0] for r in incoming.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not required.issubset(found):
            incoming.close(); raise ValueError("ملف النسخة غير متوافق")
        self.db.close()
        shutil.copy2(src,self.path)
        self.db=sqlite3.connect(self.path); self.db.row_factory=sqlite3.Row
        self.init()
        incoming.close()

    def habit_streak(self, hid):
        days={r["day"] for r in self.all("SELECT day FROM habit_logs WHERE habit_id=? AND done=1",(hid,))}
        n=0; d=date.today()
        if d.isoformat() not in days: d-=timedelta(days=1)
        while d.isoformat() in days:
            n+=1; d-=timedelta(days=1)
        return n

    def score(self):
        habits=self.one("SELECT COUNT(*) n FROM habits")["n"]
        tasks=self.one("SELECT COUNT(*) n FROM tasks")["n"]
        goals=self.one("SELECT COUNT(*) n FROM goals")["n"]
        hdone=self.one("SELECT COUNT(*) n FROM habit_logs WHERE day=? AND done=1",(today(),))["n"]
        tdone=self.one("SELECT COUNT(*) n FROM tasks WHERE done=1 AND substr(created,1,10)=?",(today(),))["n"]
        gavg=self.one("SELECT COALESCE(AVG(progress),0) n FROM goals")["n"]
        hp=min(100,round(hdone/max(1,habits)*100))
        tp=min(100,round(tdone/max(1,tasks)*100)) if tasks else 0
        return round(hp*.45+tp*.25+float(gavg)*.30) if (habits or tasks or goals) else 0

class Card(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", padding=dp(14), spacing=dp(8), size_hint_y=None, **kwargs)
        self.bind(minimum_height=self.setter("height"))
        with self.canvas.before:
            Color(*PANEL)
            self.bg=RoundedRectangle(pos=self.pos,size=self.size,radius=[dp(14)])
        self.bind(pos=self._sync,size=self._sync)
    def _sync(self,*_):
        self.bg.pos=self.pos; self.bg.size=self.size

class RBButton(Button):
    def __init__(self, **kwargs):
        kwargs.setdefault("size_hint_y",None); kwargs.setdefault("height",dp(46))
        kwargs.setdefault("background_normal",""); kwargs.setdefault("background_down","")
        kwargs.setdefault("background_color",PANEL2); kwargs.setdefault("color",PALE)
        kwargs.setdefault("font_size","14sp")
        super().__init__(**kwargs)

class RBLabel(Label):
    def __init__(self, **kwargs):
        kwargs.setdefault("color",TEXT); kwargs.setdefault("font_size","14sp")
        kwargs.setdefault("size_hint_y",None); kwargs.setdefault("height",dp(28))
        kwargs.setdefault("halign","right"); kwargs.setdefault("valign","middle")
        super().__init__(**kwargs)
        self.bind(size=lambda *_: setattr(self,"text_size",(self.width,None)))

class Field(TextInput):
    def __init__(self, **kwargs):
        kwargs.setdefault("multiline",False); kwargs.setdefault("size_hint_y",None)
        kwargs.setdefault("height",dp(46)); kwargs.setdefault("background_normal","")
        kwargs.setdefault("background_active",""); kwargs.setdefault("background_color",(0.11,0.11,0.11,1))
        kwargs.setdefault("foreground_color",TEXT); kwargs.setdefault("cursor_color",GOLD)
        kwargs.setdefault("hint_text_color",MUTED); kwargs.setdefault("padding",[dp(10),dp(12)])
        super().__init__(**kwargs)

class RebirthApp(App):
    title="THE REBIRTH"
    def build(self):
        Window.clearcolor=BG
        self.store=Store(os.path.join(self.user_data_dir,"rebirth.sqlite3"))
        self.sm=ScreenManager(transition=FadeTransition(duration=.12))
        for name in ["home","habits","tasks","goals","routines","focus","dimensions","challenges","review","anti","reports","modules","profile","data","notes"]:
            self.sm.add_widget(Screen(name=name))
        self.timer_seconds=int(self.store.get("focus_minutes","25"))*60
        self.timer_event=None
        self.show("home")
        return self.sm

    def base(self, screen, title, subtitle="DISCIPLINE · EVOLUTION · MASTERY"):
        root=BoxLayout(orientation="vertical",spacing=dp(8),padding=[dp(12),dp(10)])
        head=BoxLayout(size_hint_y=None,height=dp(52),spacing=dp(8))
        back=RBButton(text="‹",size_hint_x=None,width=dp(48),font_size="24sp")
        back.bind(on_release=lambda *_: self.show("home"))
        brand=BoxLayout(orientation="vertical")
        brand.add_widget(RBLabel(text="THE REBIRTH",color=GOLD,bold=True,font_size="16sp",height=dp(25),halign="left"))
        brand.add_widget(RBLabel(text=subtitle,color=MUTED,font_size="9sp",height=dp(18),halign="left"))
        head.add_widget(back); head.add_widget(brand); root.add_widget(head)
        root.add_widget(RBLabel(text=title,font_size="22sp",bold=True,color=PALE,height=dp(38)))
        scroll=ScrollView(do_scroll_x=False)
        body=BoxLayout(orientation="vertical",spacing=dp(10),size_hint_y=None,padding=[0,0,0,dp(24)])
        body.bind(minimum_height=body.setter("height")); scroll.add_widget(body); root.add_widget(scroll)
        nav=GridLayout(cols=4,size_hint_y=None,height=dp(52),spacing=dp(4))
        for label,name in [("الرئيسية","home"),("العادات","habits"),("المهمات","tasks"),("المزيد","modules")]:
            b=RBButton(text=label,height=dp(42)); b.bind(on_release=lambda _,n=name:self.show(n)); nav.add_widget(b)
        root.add_widget(nav)
        self.sm.get_screen(screen).clear_widgets(); self.sm.get_screen(screen).add_widget(root)
        return body

    def label(self, body, text, **kw):
        w=RBLabel(text=text,**kw); body.add_widget(w); return w
    def button(self, body, text, callback, color=None):
        b=RBButton(text=text)
        if color: b.background_color=color
        b.bind(on_release=lambda *_:callback())
        body.add_widget(b); return b
    def card(self, body, title):
        c=Card(); c.add_widget(RBLabel(text=title,bold=True,color=GOLD,height=dp(30))); body.add_widget(c); return c
    def input_popup(self,title,fields,on_save):
        box=BoxLayout(orientation="vertical",spacing=dp(8),padding=dp(12))
        inputs={}
        for key,hint,multi in fields:
            inp=TextInput(hint_text=hint,multiline=multi,size_hint_y=None,height=dp(90 if multi else 44),
                background_color=(.12,.12,.12,1),foreground_color=TEXT,cursor_color=GOLD)
            box.add_widget(RBLabel(text=key,height=dp(22))); box.add_widget(inp); inputs[key]=inp
        actions=BoxLayout(size_hint_y=None,height=dp(44),spacing=dp(8))
        pop=Popup(title=title,content=box,size_hint=(.92,.78),separator_color=GOLD)
        cancel=RBButton(text="إلغاء"); save=RBButton(text="حفظ",background_color=GOLD,color=BG)
        cancel.bind(on_release=pop.dismiss)
        def submit(*_):
            values={k:v.text.strip() for k,v in inputs.items()}
            if not any(values.values()): return
            on_save(values); pop.dismiss()
        save.bind(on_release=submit); actions.add_widget(cancel); actions.add_widget(save); box.add_widget(actions); pop.open()

    def show(self,name):
        self.sm.current=name
        getattr(self,"page_"+name)()

    def page_home(self):
        b=self.base("home","مركز القيادة")
        name=self.store.get("profile_name","صانع النسخة الجديدة")
        self.label(b,f"مرحباً، {name}",color=PALE,font_size="18sp",height=dp(34))
        hero=self.card(b,"رحلة الولادة من جديد")
        hero.add_widget(RBLabel(text=self.store.get("identity"),color=MUTED,height=dp(48)))
        hero.add_widget(RBLabel(text="قاعدة اليوم: "+self.store.get("daily_rule"),color=PALE,height=dp(42)))
        stats=self.card(b,"مؤشراتك")
        h=self.store.one("SELECT COUNT(*) n FROM habits")["n"]
        hd=self.store.one("SELECT COUNT(*) n FROM habit_logs WHERE day=? AND done=1",(today(),))["n"]
        t=self.store.one("SELECT COUNT(*) n FROM tasks WHERE done=0")["n"]
        stats.add_widget(RBLabel(text=f"Rebirth Score: {self.store.score()} / 100     |     العادات: {hd}/{h}     |     المهمات المفتوحة: {t}",color=PALE,height=dp(38)))
        actions=self.card(b,"مركز العمليات")
        for label,name in [("العادات","habits"),("المهمات","tasks"),("الأهداف","goals"),("الروتين","routines"),("التركيز العميق","focus"),("أبعاد الحياة","dimensions"),("التحديات","challenges"),("المراجعة الذاتية","review"),("مكافحة العادات","anti"),("التقارير","reports"),("المنظومات الثلاثون","modules"),("الملف الشخصي","profile"),("خزنة البيانات","data"),("الملاحظات والأفكار","notes")]:
            self.button(actions,label,lambda n=name:self.show(n))
        quote=self.card(b,"ميثاقك")
        quote.add_widget(RBLabel(text=self.store.get("personal_code"),color=MUTED,height=dp(58)))

    def page_habits(self):
        b=self.base("habits","محرك العادات")
        self.button(b,"＋ إضافة عادة",lambda:self.input_popup("عادة جديدة",[("الاسم","اسم العادة",False),("المجال","مثال: العقل والصحة",False),("المحفز","ما الذي يذكرك بها؟",False)],self.add_habit),GOLD)
        rows=self.store.all("SELECT * FROM habits ORDER BY id DESC")
        if not rows:self.label(b,"لا توجد عادات بعد. أضف عادة صغيرة قابلة للاستمرار.",color=MUTED,height=dp(55))
        for r in rows:
            c=self.card(b,r["name"])
            done=self.store.one("SELECT done FROM habit_logs WHERE habit_id=? AND day=?",(r["id"],today()))
            streak=self.store.habit_streak(r["id"])
            c.add_widget(RBLabel(text=f"{r['category'] or 'عام'} · سلسلة الالتزام: {streak} يوم",color=MUTED))
            self.button(c,"✓ تم اليوم" if done and done["done"] else "تسجيل إنجاز اليوم",lambda hid=r["id"]:self.toggle_habit(hid))
            self.button(c,"حذف العادة",lambda hid=r["id"]:self.delete("habits",hid),RED)
    def add_habit(self,v):
        self.store.q("INSERT INTO habits(name,category,cue,created) VALUES(?,?,?,?)",(v.get("الاسم"),v.get("المجال"),v.get("المحفز"),today())); self.show("habits")
    def toggle_habit(self,hid):
        r=self.store.one("SELECT done FROM habit_logs WHERE habit_id=? AND day=?",(hid,today()))
        if r:self.store.q("DELETE FROM habit_logs WHERE habit_id=? AND day=?",(hid,today()))
        else:self.store.q("INSERT OR REPLACE INTO habit_logs(habit_id,day,done) VALUES(?,?,1)",(hid,today()))
        self.show("habits")
    def page_tasks(self):
        b=self.base("tasks","نظام المهمات")
        self.button(b,"＋ مهمة جديدة",lambda:self.input_popup("مهمة جديدة",[("العنوان","ما الذي ستنجزه؟",False),("الأولوية","عالية / متوسطة / منخفضة",False),("الموعد","YYYY-MM-DD أو اتركه فارغاً",False),("المجال","المجال المرتبط",False)],self.add_task),GOLD)
        for r in self.store.all("SELECT * FROM tasks ORDER BY done, CASE priority WHEN 'عالية' THEN 1 WHEN 'متوسطة' THEN 2 ELSE 3 END,id DESC"):
            c=self.card(b,r["title"]); c.add_widget(RBLabel(text=f"{r['priority'] or 'متوسطة'} · {r['due'] or 'دون موعد'} · {'مكتملة' if r['done'] else 'مفتوحة'}",color=MUTED))
            if not r["done"]: self.button(c,"إنجاز المهمة",lambda tid=r["id"]:self.finish_task(tid))
            self.button(c,"حذف",lambda tid=r["id"]:self.delete("tasks",tid),RED)
    def add_task(self,v):
        self.store.q("INSERT INTO tasks(title,priority,due,category,created) VALUES(?,?,?,?,?)",(v.get("العنوان"),v.get("الأولوية") or "متوسطة",v.get("الموعد"),v.get("المجال"),now())); self.show("tasks")
    def finish_task(self,tid):
        self.store.q("UPDATE tasks SET done=1 WHERE id=?",(tid,)); self.show("tasks")
        self.store.q("INSERT INTO achievements(title,detail,day) VALUES(?,?,?)",("إنجاز مهمة","تم إكمال مهمة",today()))
    def page_goals(self):
        b=self.base("goals","الأهداف")
        self.button(b,"＋ إضافة هدف",lambda:self.input_popup("هدف جديد",[("الهدف","هدف واضح قابل للقياس",False),("المجال","الدراسة / الجسد / الشخصية...",False),("النتيجة المستهدفة","كيف تعرف أنك حققته؟",False)],self.add_goal),GOLD)
        for r in self.store.all("SELECT * FROM goals ORDER BY id DESC"):
            c=self.card(b,r["title"]); c.add_widget(RBLabel(text=f"{r['category']} · التقدم {r['progress']}%",color=MUTED))
            self.button(c,"زيادة التقدم 10%",lambda gid=r["id"]:self.goal_progress(gid))
            self.button(c,"حذف الهدف",lambda gid=r["id"]:self.delete("goals",gid),RED)
    def add_goal(self,v):
        self.store.q("INSERT INTO goals(title,category,target) VALUES(?,?,?)",(v.get("الهدف"),v.get("المجال"),v.get("النتيجة المستهدفة"))); self.show("goals")
    def goal_progress(self,gid):
        self.store.q("UPDATE goals SET progress=MIN(100,progress+10) WHERE id=?",(gid,)); self.show("goals")
    def page_routines(self):
        b=self.base("routines","مهندس الروتين")
        self.button(b,"＋ إنشاء روتين",lambda:self.input_popup("روتين جديد",[("الاسم","صباحي / مسائي / دراسة...",False),("الفترة","صباح / مساء / أسبوعي",False),("التفاصيل","اكتب الخطوات بالترتيب",True)],self.add_routine),GOLD)
        for r in self.store.all("SELECT * FROM routines ORDER BY id DESC"):
            c=self.card(b,r["title"]); c.add_widget(RBLabel(text=r["period"] or "",color=MUTED)); c.add_widget(RBLabel(text=r["details"] or "",height=dp(70)))
            self.button(c,"حذف",lambda rid=r["id"]:self.delete("routines",rid),RED)
    def add_routine(self,v):
        self.store.q("INSERT INTO routines(title,period,details,created) VALUES(?,?,?,?)",(v.get("الاسم"),v.get("الفترة"),v.get("التفاصيل"),now())); self.show("routines")
    def page_focus(self):
        b=self.base("focus","التركيز العميق")
        c=self.card(b,"جلسة التركيز")
        self.timer_label=RBLabel(text=self.clock_text(),font_size="42sp",color=PALE,height=dp(70),halign="center"); c.add_widget(self.timer_label)
        self.label(c,f"المدة المحددة: {self.store.get('focus_minutes','25')} دقيقة",color=MUTED)
        self.button(c,"ابدأ / استأنف",self.start_timer,GOLD); self.button(c,"إيقاف مؤقت",self.pause_timer); self.button(c,"إعادة ضبط",self.reset_timer)
        self.button(c,"تغيير مدة التركيز",lambda:self.input_popup("مدة التركيز",[("الدقائق","مثال 25",False)],self.set_focus))
        history=self.card(b,"سجل الجلسات")
        for r in self.store.all("SELECT * FROM focus_sessions ORDER BY id DESC LIMIT 15"):
            self.label(history,f"{r['day']} · {r['minutes']} دقيقة · {r['note'] or 'تركيز'}",color=MUTED)
    def clock_text(self): return f"{self.timer_seconds//60:02d}:{self.timer_seconds%60:02d}"
    def start_timer(self):
        if self.timer_event:return
        self.timer_event=Clock.schedule_interval(self.tick,1)
    def pause_timer(self):
        if self.timer_event:self.timer_event.cancel(); self.timer_event=None
    def reset_timer(self):
        self.pause_timer(); self.timer_seconds=int(self.store.get("focus_minutes","25"))*60
        if self.sm.current=="focus":self.timer_label.text=self.clock_text()
    def tick(self,dt):
        self.timer_seconds=max(0,self.timer_seconds-1)
        if self.sm.current=="focus":self.timer_label.text=self.clock_text()
        if self.timer_seconds<=0:
            self.pause_timer(); minutes=int(self.store.get("focus_minutes","25"))
            self.store.q("INSERT INTO focus_sessions(day,minutes,note) VALUES(?,?,?)",(today(),minutes,"جلسة مكتملة"))
            self.notify("أحسنت! اكتملت جلسة التركيز."); self.reset_timer()
    def set_focus(self,v):
        try:n=max(5,min(180,int(v.get("الدقائق","25"))))
        except:n=25
        self.store.set("focus_minutes",n); self.reset_timer(); self.show("focus")
    def page_dimensions(self):
        b=self.base("dimensions","أبعاد الحياة")
        self.label(b,"قيّم كل بُعد من 0 إلى 100. التقييم ذاتي وليس حكماً علمياً.",color=MUTED,height=dp(42))
        for r in self.store.all("SELECT * FROM dimensions ORDER BY id"):
            c=self.card(b,r["name"]); c.add_widget(RBLabel(text=f"التقييم الحالي: {r['score']}/100",color=PALE))
            self.button(c,"تحديث التقييم والملاحظة",lambda n=r["name"],s=r["score"]:self.edit_dimension(n,s))
    def edit_dimension(self,n,s):
        self.input_popup(n,[("الدرجة من 0 إلى 100",str(s),False),("ملاحظة","ما الذي تريد تحسينه؟",True)],lambda v:self.save_dimension(n,v))
    def save_dimension(self,n,v):
        try:s=max(0,min(100,int(v.get("الدرجة من 0 إلى 100","0"))))
        except:s=0
        self.store.q("UPDATE dimensions SET score=?,note=? WHERE name=?",(s,v.get("ملاحظة"),n)); self.show("dimensions")
    def page_challenges(self):
        b=self.base("challenges","ساحة التحديات")
        self.button(b,"＋ تحدٍ جديد",lambda:self.input_popup("تحدٍ جديد",[("الاسم","اسم التحدي",False),("المدة بالأيام","مثال 30",False),("الهدف","النتيجة المطلوبة",False)],self.add_challenge),GOLD)
        for r in self.store.all("SELECT * FROM challenges ORDER BY active DESC,id DESC"):
            c=self.card(b,r["title"]); c.add_widget(RBLabel(text=f"{r['progress']} / {r['duration']} يوم · البداية {r['start_day']}",color=MUTED))
            self.button(c,"تسجيل يوم مكتمل",lambda cid=r["id"]:self.challenge_progress(cid))
    def add_challenge(self,v):
        try:d=max(1,min(365,int(v.get("المدة بالأيام","30"))))
        except:d=30
        self.store.q("INSERT INTO challenges(title,duration,start_day,target) VALUES(?,?,?,?)",(v.get("الاسم"),d,today(),v.get("الهدف"))); self.show("challenges")
    def challenge_progress(self,cid):
        self.store.q("UPDATE challenges SET progress=MIN(duration,progress+1) WHERE id=?",(cid,)); self.show("challenges")
    def page_review(self):
        b=self.base("review","التدقيق الذاتي")
        self.button(b,"＋ مراجعة اليوم",lambda:self.input_popup("مراجعة ذاتية",[("ما الذي أنجزته؟","اكتب إنجازاتك",True),("ما الذي تعثر؟","بلا جلد للذات؛ اكتب السبب",True),("ما خطوة الغد؟","خطوة واحدة محددة",True)],self.add_review),GOLD)
        for r in self.store.all("SELECT * FROM journal WHERE kind='review' ORDER BY id DESC LIMIT 30"):
            c=self.card(b,r["day"]); c.add_widget(RBLabel(text=r["content"],height=dp(120),color=MUTED))
    def add_review(self,v):
        content="الإنجازات:\n"+v.get("ما الذي أنجزته؟","")+"\n\nالتعثر:\n"+v.get("ما الذي تعثر؟","")+"\n\nخطوة الغد:\n"+v.get("ما خطوة الغد؟","")
        self.store.q("INSERT INTO journal(day,kind,content,created) VALUES(?,?,?,?)",(today(),"review",content,now())); self.show("review")
    def page_anti(self):
        b=self.base("anti","نظام مكافحة العادات")
        self.button(b,"＋ خطة مواجهة محفز",lambda:self.input_popup("خطة مواجهة",[("السلوك الذي أريد تغييره","وصف السلوك",False),("المحفز","متى أو أين يحدث؟",True),("الاستجابة البديلة","ماذا سأفعل بدلاً منه؟",True)],self.add_anti),GOLD)
        for r in self.store.all("SELECT * FROM anti_habits ORDER BY id DESC"):
            c=self.card(b,r["title"]); c.add_widget(RBLabel(text="المحفز: "+(r["trigger_text"] or ""),height=dp(44),color=MUTED)); c.add_widget(RBLabel(text="البديل: "+(r["response_text"] or ""),height=dp(55),color=PALE))
            self.button(c,"حذف",lambda aid=r["id"]:self.delete("anti_habits",aid),RED)
    def add_anti(self,v):
        self.store.q("INSERT INTO anti_habits(title,trigger_text,response_text,created) VALUES(?,?,?,?)",(v.get("السلوك الذي أريد تغييره"),v.get("المحفز"),v.get("الاستجابة البديلة"),now())); self.show("anti")
    def page_reports(self):
        b=self.base("reports","التقارير والتحليل")
        habits=self.store.one("SELECT COUNT(*) n FROM habits")["n"]
        logs=self.store.one("SELECT COUNT(*) n FROM habit_logs WHERE done=1")["n"]
        tasks=self.store.one("SELECT COUNT(*) n FROM tasks")["n"]
        completed=self.store.one("SELECT COUNT(*) n FROM tasks WHERE done=1")["n"]
        sessions=self.store.one("SELECT COALESCE(SUM(minutes),0) n FROM focus_sessions")["n"]
        goals=self.store.one("SELECT COUNT(*) n FROM goals")["n"]
        avg=self.store.one("SELECT COALESCE(AVG(progress),0) n FROM goals")["n"]
        for title,value in [("نقاط Rebirth Score",f"{self.store.score()}/100"),("العادات المسجلة",f"{logs} إنجاز / {habits} عادة"),("المهمات",f"{completed} من {tasks} مكتملة"),("الأهداف",f"{goals} هدف · متوسط تقدم {avg:.0f}%"),("التركيز",f"{sessions} دقيقة إجمالاً")]:
            c=self.card(b,title); self.label(c,value,color=PALE,font_size="20sp")
        self.button(b,"تسجيل الأداء اليومي (النوم والطاقة والمزاج)",lambda:self.input_popup("الأداء اليومي",[("ساعات النوم","مثال 7.5",False),("الطاقة من 1 إلى 5","3",False),("المزاج من 1 إلى 5","3",False),("ملاحظة","اختياري",True)],self.save_performance))
        for r in self.store.all("SELECT * FROM performance ORDER BY day DESC LIMIT 14"):
            self.label(b,f"{r['day']} · نوم {r['sleep']} س · طاقة {r['energy']}/5 · مزاج {r['mood']}/5",color=MUTED)
    def save_performance(self,v):
        try:s=float(v.get("ساعات النوم","0")); e=max(1,min(5,int(v.get("الطاقة من 1 إلى 5","3")))); m=max(1,min(5,int(v.get("المزاج من 1 إلى 5","3"))))
        except:s,e,m=0,3,3
        self.store.q("INSERT OR REPLACE INTO performance(day,sleep,energy,mood,note) VALUES(?,?,?,?,?)",(today(),s,e,m,v.get("ملاحظة"))); self.show("reports")
    def page_modules(self):
        b=self.base("modules","المنظومات الثلاثون")
        self.label(b,"الفهرس الكامل للمنظومات الأصلية. افتح كل منظومة لمعرفة وظائفها ونقطة الوصول إليها.",color=MUTED,height=dp(52))
        for m in MODULES:
            c=self.card(b,f"{m['id']:02d} · {m['ar']}")
            c.add_widget(RBLabel(text=m["en"],color=GOLD,height=dp(22)))
            c.add_widget(RBLabel(text=m["description"],color=MUTED,height=dp(54)))
            self.button(c,"فتح المنظومة",lambda item=m:self.module_detail(item))
    def module_detail(self,m):
        box=BoxLayout(orientation="vertical",spacing=dp(10),padding=dp(14))
        box.add_widget(RBLabel(text=m["ar"],font_size="20sp",color=PALE))
        box.add_widget(RBLabel(text=m["en"],color=GOLD))
        box.add_widget(RBLabel(text=m["description"],height=dp(90),color=MUTED))
        box.add_widget(RBLabel(text="الوصول إلى الوظيفة المرتبطة من القائمة الرئيسية. بعض الأنظمة تعمل كخدمات مشتركة، وبعضها موثق ومهيأ للتوسع.",height=dp(90),color=TEXT))
        btn=RBButton(text="إغلاق"); box.add_widget(btn)
        p=Popup(title=f"SYSTEM {m['id']:02d}",content=box,size_hint=(.9,.55),separator_color=GOLD); btn.bind(on_release=p.dismiss); p.open()
    def page_profile(self):
        b=self.base("profile","الهوية والتخصيص")
        self.button(b,"تعديل الاسم والهوية والميثاق",lambda:self.input_popup("الملف الشخصي",[("اسم العرض",self.store.get("profile_name"),False),("الهوية المستهدفة",self.store.get("identity"),True),("الميثاق الشخصي",self.store.get("personal_code"),True),("قاعدة اليوم",self.store.get("daily_rule"),True)],self.save_profile),GOLD)
        self.label(b,"الهوية الحالية: "+self.store.get("identity"),color=PALE,height=dp(65))
        self.label(b,"الميثاق: "+self.store.get("personal_code"),color=MUTED,height=dp(75))
    def save_profile(self,v):
        for field,key in [("اسم العرض","profile_name"),("الهوية المستهدفة","identity"),("الميثاق الشخصي","personal_code"),("قاعدة اليوم","daily_rule")]:
            if v.get(field):self.store.set(key,v[field])
        self.show("profile")
    def page_data(self):
        b=self.base("data","خزنة البيانات")
        self.label(b,"بياناتك محفوظة محلياً على الجهاز. أنشئ نسخة احتياطية بانتظام.",color=MUTED,height=dp(48))
        self.button(b,"تصدير نسخة احتياطية من قاعدة البيانات",self.export_backup,GOLD)
        self.button(b,"استعادة نسخة احتياطية من ملف",self.choose_restore)
        self.label(b,"ملاحظة: عند الاستعادة تُستبدل قاعدة البيانات الحالية. احتفظ بنسخة قبل الاستعادة.",color=RED,height=dp(55))
        self.button(b,"عرض مجلد بيانات التطبيق",lambda:self.notify("تُحفظ البيانات داخل مساحة التطبيق الخاصة."),)
    def export_backup(self):
        try:
            dest=os.path.join(App.get_running_app().user_data_dir,f"THE_REBIRTH_backup_{today()}.db")
            self.store.backup(dest); self.notify("تم إنشاء النسخة داخل مساحة التطبيق: "+dest)
        except Exception as e:self.notify("تعذر التصدير: "+str(e))
    def choose_restore(self):
        from kivy.uix.filechooser import FileChooserListView
        box=BoxLayout(orientation="vertical",spacing=dp(8))
        chooser=FileChooserListView(filters=["*.db","*.sqlite","*.sqlite3"])
        box.add_widget(chooser); row=BoxLayout(size_hint_y=None,height=dp(45),spacing=dp(8))
        p=Popup(title="اختر ملف النسخة الاحتياطية",content=box,size_hint=(.95,.85),separator_color=GOLD)
        cancel=RBButton(text="إلغاء"); go=RBButton(text="استعادة",background_color=GOLD,color=BG)
        cancel.bind(on_release=p.dismiss)
        def restore(*_):
            if chooser.selection:
                try:self.store.restore(chooser.selection[0]);p.dismiss();self.notify("تمت الاستعادة");self.show("home")
                except Exception as e:self.notify("تعذر الاستعادة: "+str(e))
        go.bind(on_release=restore);row.add_widget(cancel);row.add_widget(go);box.add_widget(row);p.open()
    def page_notes(self):
        b=self.base("notes","الملاحظات والأفكار")
        self.button(b,"＋ ملاحظة جديدة",lambda:self.input_popup("ملاحظة",[("العنوان","العنوان",False),("المحتوى","اكتب الفكرة أو الملاحظة",True)],self.add_note),GOLD)
        for r in self.store.all("SELECT * FROM notes ORDER BY id DESC"):
            c=self.card(b,r["title"]);c.add_widget(RBLabel(text=r["body"],height=dp(70),color=MUTED))
            self.button(c,"حذف",lambda nid=r["id"]:self.delete("notes",nid),RED)
    def add_note(self,v):
        self.store.q("INSERT INTO notes(title,body,created) VALUES(?,?,?)",(v.get("العنوان"),v.get("المحتوى"),now()));self.show("notes")
    def delete(self,table,ident):
        allowed={"habits","tasks","goals","routines","anti_habits","notes"}
        if table not in allowed:return
        self.store.q(f"DELETE FROM {table} WHERE id=?",(ident,))
        self.notify("تم الحذف")
        self.show(self.sm.current)
    def notify(self,msg):
        box=BoxLayout(orientation="vertical",padding=dp(14),spacing=dp(8))
        box.add_widget(RBLabel(text=msg,height=dp(85),color=PALE))
        btn=RBButton(text="حسناً");box.add_widget(btn)
        p=Popup(title="THE REBIRTH",content=box,size_hint=(.9,.35),separator_color=GOLD);btn.bind(on_release=p.dismiss);p.open()

    def on_pause(self):
        self.store.db.commit()
        return True
    def on_stop(self):
        try:self.pause_timer();self.store.db.commit();self.store.db.close()
        except:pass

if __name__ == "__main__":
    RebirthApp().run()
