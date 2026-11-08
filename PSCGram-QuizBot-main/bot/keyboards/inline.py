from telegram import InlineKeyboardButton as B, InlineKeyboardMarkup as M

def home(admin=False, premium=False):
    rows=[[B("📝 Start Quiz",callback_data="modes"),B("📚 Subjects",callback_data="subjects")],
          [B("🔖 Bookmarks",callback_data="mode:bookmarks"),B("❌ Wrong Answers",callback_data="mode:wrong")],
          [B("📊 My Progress",callback_data="history"),B("🏆 Leaderboard",callback_data="lb:all")],
          [B("🌐 Language",callback_data="language"),B("⭐ Premium",callback_data="premium")]]
    if admin: rows.append([B("⚙️ Admin Dashboard",callback_data="admin")])
    return M(rows)

def modes():
    return M([[B("Random",callback_data="mode:random"),B("Topic-wise",callback_data="topics")],
      [B("Full Mock Test",callback_data="mode:mock"),B("Daily Quiz",callback_data="mode:daily")],
      [B("Previous Year",callback_data="mode:previous_year"),B("Practice",callback_data="mode:practice")],
      [B("Timed Test",callback_data="mode:timed"),B("Resume",callback_data="resume")],
      [B("Main Menu",callback_data="home")]])

def list_buttons(items,prefix):
    return M([[B(str(x)[:55],callback_data=f"{prefix}:{x}")] for x in items]+[[B("Back",callback_data="modes")]])

def answer_buttons(qid,opts,saved=False):
    rows=[[B(f"{'ABCD'[i]}. {v[:48]}",callback_data=f"ans:{qid}:{i}")] for i,v in enumerate(opts)]
    rows.append([B("🔖 Remove bookmark" if saved else "🔖 Bookmark",callback_data=f"bm:{qid}")])
    return M(rows)

def next_button(): return M([[B("Next ➜",callback_data="next")],[B("Finish now",callback_data="finish")]])
def admin():
    return M([[B("Create quiz & add questions",callback_data="ad:createquiz")],
      [B("Upload PDF",callback_data="ad:pdf"),B("Review drafts",callback_data="ad:drafts")],
      [B("Statistics",callback_data="ad:stats"),B("Broadcast",callback_data="ad:broadcast")],
      [B("Grant premium",callback_data="ad:grant"),B("Revoke premium",callback_data="ad:revoke")],
      [B("Main menu",callback_data="home")]])
