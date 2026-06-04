import re
import random
import math
import unicodedata
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Bùi Văn Toàn V5", page_icon="📁", layout="wide")
DEFAULT_GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/188bSTqmXvvU55ht8yJt-wlIwfP3mLiOhebhEStcAwvw/edit?gid=881137373#gid=881137373"

st.markdown("""
<style>
.main-title {font-size: 46px; font-weight: 900; margin-bottom: 0px;}
.version-badge {display:inline-block; background:#22c55e; color:white; padding:6px 12px; border-radius:999px; font-weight:800; margin-left:10px;}
.card {border:1px solid #666; border-radius:26px; padding:50px; text-align:center; min-height:320px; background:#0f1117;}
.korean {font-size:64px; font-weight:900; margin-bottom:35px; line-height:1.25;}
.meaning {font-size:28px; font-weight:800; margin-bottom:25px; white-space:pre-wrap; line-height:1.45;}
.detail {font-size:18px; color:#aaa; white-space:pre-wrap; line-height:1.55;}
.folder-card {border:1px solid #555; border-radius:18px; padding:18px; margin:8px 0; background:#141a25;}
.folder-card-active {border:2px solid #22c55e; border-radius:18px; padding:18px; margin:8px 0; background:#10251a;}
.small {color:#aaa; font-size:14px;}
.good {color:#22c55e; font-weight:800;}
.bad {color:#ef4444; font-weight:800;}
</style>
""", unsafe_allow_html=True)

col1, col2, col3 = st.columns([1, 1, 1])
with col2:
    st.image("2612.png", width=180)
@st.cache_data(show_spinner=False)
def read_google_sheet(url: str, sheet_name: str) -> pd.DataFrame:
    m = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", url)
    if not m:
        raise ValueError("Link Google Sheets không đúng. Hãy copy link dạng docs.google.com/spreadsheets/d/...")
    file_id = m.group(1)
    gm = re.search(r"gid=([0-9]+)", url)
    if gm:
        csv_url = f"https://docs.google.com/spreadsheets/d/{file_id}/export?format=csv&gid={gm.group(1)}"
    else:
        csv_url = f"https://docs.google.com/spreadsheets/d/{file_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
    return pd.read_csv(csv_url, dtype=str).fillna("")

@st.cache_data(show_spinner=False)
def read_uploaded_file(uploaded) -> pd.DataFrame:
    name = uploaded.name.lower()
    if name.endswith(".csv"):
        return pd.read_csv(uploaded, dtype=str).fillna("")
    return pd.read_excel(uploaded, dtype=str).fillna("")

def col_letter_to_index(letter: str) -> int:
    letter = str(letter).strip().upper()
    n = 0
    for ch in letter:
        if "A" <= ch <= "Z":
            n = n * 26 + ord(ch) - 64
    return max(n - 1, 0)

def clean_text(x):
    if x is None:
        return ""
    s = str(x).replace("\u00a0", " ").strip()
    if s.lower() == "nan":
        return ""
    return s

def make_cards(df: pd.DataFrame, kr_col: str, vi_col: str, detail_col: str):
    """V5: chỉ cần có tiếng Hàn là tạo thẻ. Thiếu nghĩa thì vẫn giữ thẻ."""
    ki, vi = col_letter_to_index(kr_col), col_letter_to_index(vi_col)
    di = col_letter_to_index(detail_col) if detail_col else None
    cards = []
    raw_rows = 0
    missing_vi = 0
    missing_detail = 0
    skipped_no_kr = 0
    for idx, row in df.iterrows():
        vals = list(row.values)
        raw_rows += 1
        kr = clean_text(vals[ki]) if ki < len(vals) else ""
        mean = clean_text(vals[vi]) if vi < len(vals) else ""
        detail = clean_text(vals[di]) if di is not None and di < len(vals) else ""
        if not kr:
            skipped_no_kr += 1
            continue
        if not mean:
            mean = "Chưa có nghĩa"
            missing_vi += 1
        if not detail:
            missing_detail += 1
        cards.append({"stt": len(cards)+1, "dong_goc": idx+2, "kr": kr, "vi": mean, "detail": detail})
    stats = {
        "raw_rows": raw_rows,
        "cards": len(cards),
        "missing_vi": missing_vi,
        "missing_detail": missing_detail,
        "skipped_no_kr": skipped_no_kr,
    }
    return cards, stats

def get_folder(cards, folder_no, folder_size):
    start = (folder_no - 1) * folder_size
    end = min(start + folder_size, len(cards))
    return cards[start:end], start + 1, end

def normalize_answer(s: str) -> str:
    s = clean_text(s).lower()
    s = unicodedata.normalize("NFC", s)
    s = re.sub(r"\s+", " ", s)
    # bỏ vài dấu câu để dễ chấm hơn
    s = re.sub(r"[.,;:!?()\[\]{}'\"`~]", "", s)
    return s.strip()

def is_correct(user_answer: str, correct_answer: str, mode: str) -> bool:
    ua = normalize_answer(user_answer)
    ca = normalize_answer(correct_answer)
    if not ua or not ca:
        return False
    if mode == "Gõ tiếng Hàn theo nghĩa":
        return ua == ca
    # Với tiếng Việt, cho phép đáp án người học là một phần nghĩa, hoặc khớp một nghĩa trong danh sách phân tách
    parts = re.split(r"[\n/|,;]+", ca)
    parts = [p.strip() for p in parts if p.strip()]
    return ua == ca or ua in parts or any(ua == p for p in parts)

def reset_card():
    st.session_state.card_i = 0
    st.session_state.show_answer = False

def reset_write():
    st.session_state.write_i = 0
    st.session_state.write_score = 0
    st.session_state.write_total = 0
    st.session_state.write_last = None
    st.session_state.write_cards_order = []
    st.session_state.write_input = ""

# session defaults
for k, v in {
    "folder_no": 1,
    "card_i": 0,
    "show_answer": False,
    "write_i": 0,
    "write_score": 0,
    "write_total": 0,
    "write_last": None,
    "write_cards_order": [],
    "write_input": "",
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

st.markdown(
    '<div class="main-title" style="text-align:center; transform: translateX(-3cm);">Tiên học lễ, hậu học han cúc co</div>',
    unsafe_allow_html=True
)
st.caption("Bản V7: có tiếng Hàn là tạo thẻ. Chế độ gõ bắt buộc trả lời đúng mới qua câu tiếp theo.")

with st.sidebar:
    st.header("1) Nguồn dữ liệu")
    source = st.radio("Chọn nguồn", ["Google Sheets link", "Upload file"])
    sheet_name = st.text_input("Tên sheet", value="nhaplieu")
    google_url = ""
    uploaded = None
    if source == "Google Sheets link":
        google_url = st.text_input(
    "Dán link Google Sheets",
    value=DEFAULT_GOOGLE_SHEET_URL
)
        st.info("Share Google Sheets: Anyone with the link → Viewer.")
    else:
        uploaded = st.file_uploader("Upload Excel/CSV", type=["xlsx", "xlsm", "csv"])

    st.header("2) Chọn cột")
    st.caption("File của bạn thường là: B = tiếng Hàn, A = nghĩa Việt, C = giải thích.")
    kr_col = st.text_input("Cột tiếng Hàn", value="B")
    vi_col = st.text_input("Cột nghĩa tiếng Việt", value="A")
    detail_col = st.text_input("Cột giải thích", value="C")

    st.header("3) Chia thư mục")
    folder_size = int(st.number_input("Số từ mỗi thư mục", min_value=10, max_value=500, value=50, step=10))
    st.caption("Để giống set nhỏ, nên để 50.")

try:
    df = None
    if source == "Google Sheets link" and google_url.strip():
        with st.spinner("Đang tải Google Sheets..."):
            df = read_google_sheet(google_url.strip(), sheet_name.strip())
    elif source == "Upload file" and uploaded is not None:
        with st.spinner("Đang đọc file..."):
            df = read_uploaded_file(uploaded)

    if df is None:
        st.warning("Hãy dán link Google Sheets hoặc upload file để bắt đầu.")
        st.stop()

    cards_all, stats = make_cards(df, kr_col, vi_col, detail_col)
    if not cards_all:
        st.error("Không đọc được thẻ. Cột tiếng Hàn đang trống hoặc bạn chọn sai cột tiếng Hàn.")
        st.stop()

    total = len(cards_all)
    total_folders = max(1, math.ceil(total / folder_size))
    if st.session_state.folder_no > total_folders:
        st.session_state.folder_no = 1

    st.success(f"Đã tạo {total:,} thẻ từ các dòng có tiếng Hàn. Đã chia thành {total_folders} thư mục, mỗi thư mục {folder_size} từ.")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Thẻ đã tạo", f"{stats['cards']:,}")
    c2.metric("Thiếu nghĩa", f"{stats['missing_vi']:,}")
    c3.metric("Thiếu giải thích", f"{stats['missing_detail']:,}")
    c4.metric("Bỏ qua vì thiếu tiếng Hàn", f"{stats['skipped_no_kr']:,}")

    top_cols = st.columns([1, 2, 1])
    with top_cols[0]:
        if st.button("⬅️ Bộ trước", disabled=st.session_state.folder_no <= 1, use_container_width=True):
            st.session_state.folder_no -= 1
            reset_card(); reset_write(); st.rerun()
    with top_cols[1]:
        chosen = st.selectbox(
            "📁 Chọn thư mục/bộ để học",
            list(range(1, total_folders + 1)),
            index=st.session_state.folder_no - 1,
            format_func=lambda f: f"Bộ {f:03d}: từ {(f-1)*folder_size+1}–{min(f*folder_size,total)}",
        )
        if chosen != st.session_state.folder_no:
            st.session_state.folder_no = chosen
            reset_card(); reset_write(); st.rerun()
    with top_cols[2]:
        if st.button("Bộ sau ➡️", disabled=st.session_state.folder_no >= total_folders, use_container_width=True):
            st.session_state.folder_no += 1
            reset_card(); reset_write(); st.rerun()

    cards, start_num, end_num = get_folder(cards_all, st.session_state.folder_no, folder_size)
    st.info(f"Đang học: Bộ {st.session_state.folder_no:03d} | từ {start_num}–{end_num} | {len(cards)} thẻ")

    tab_folder, tab_flash, tab_write, tab_learn, tab_quiz, tab_match, tab_search, tab_data = st.tabs([
        "📁 Thư mục", "📚 Flashcard", "⌨️ Gõ văn bản", "🎓 Học", "📝 Quiz", "🧩 Ghép cặp", "🔎 Tìm kiếm", "📋 Dữ liệu"
    ])

    with tab_folder:
    st.subheader("📁 Thư mục")
    st.write("Bấm chọn bộ bên dưới. Sau đó qua Flashcard / Gõ văn bản / Quiz để học đúng bộ đó.")

    folder_sort = st.radio(
        "Sắp xếp thư mục",
        ["Nhỏ → lớn", "Lớn → nhỏ"],
        horizontal=True,
        key="folder_sort"
    )

    folder_list = list(range(1, total_folders + 1))

    if folder_sort == "Lớn → nhỏ":
        folder_list = list(reversed(folder_list))

    grid_cols = st.columns(5)

    for idx, f in enumerate(folder_list):
        s = (f - 1) * folder_size + 1
        e = min(f * folder_size, total)
        active = f == st.session_state.folder_no
        cls = "folder-card-active" if active else "folder-card"

        with grid_cols[idx % 5]:
            st.markdown(
                f"<div class='{cls}'><b>📁 Bộ {f:03d}</b><br>"
                f"<span class='small'>Từ {s}–{e}</span></div>",
                unsafe_allow_html=True
            )

            label = "✅ Đang học" if active else f"Học bộ {f:03d}"

            if st.button(label, key=f"choose_folder_{f}", use_container_width=True, disabled=active):
                st.session_state.folder_no = f
                reset_card()
                reset_write()
                st.rerun()

    with tab_flash:
        st.subheader(f"📚 Flashcard — Bộ {st.session_state.folder_no:03d}")
        i = st.session_state.card_i % len(cards)
        card = cards[i]
        st.markdown(f"### Thẻ {i+1}/{len(cards)}")
        if st.session_state.show_answer:
            st.markdown(f"<div class='card'><div class='korean'>{card['kr']}</div><div class='meaning'>{card['vi']}</div><div class='detail'>{card['detail']}</div></div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='card'><div class='korean'>{card['kr']}</div><div class='detail'>Bấm Hiện nghĩa để xem đáp án.</div></div>", unsafe_allow_html=True)
        b1, b2, b3, b4 = st.columns(4)
        if b1.button("⬅️ Trước", use_container_width=True):
            st.session_state.card_i = (i - 1) % len(cards); st.session_state.show_answer = False; st.rerun()
        if b2.button("👁️ Hiện/ẩn", use_container_width=True):
            st.session_state.show_answer = not st.session_state.show_answer; st.rerun()
        if b3.button("➡️ Sau", use_container_width=True):
            st.session_state.card_i = (i + 1) % len(cards); st.session_state.show_answer = False; st.rerun()
        if b4.button("🔀 Trộn bộ", use_container_width=True):
            random.shuffle(cards); st.session_state.card_i = 0; st.session_state.show_answer = False; st.rerun()

    with tab_write:
        st.subheader(f"⌨️ Kiểm tra bằng gõ văn bản — Bộ {st.session_state.folder_no:03d}")
        st.caption("Nhập đáp án rồi nhấn Enter. Nếu sai, bạn phải gõ lại đúng đáp án mới được qua câu tiếp theo.")
        mode = st.radio("Kiểu kiểm tra", ["Gõ tiếng Hàn theo nghĩa", "Gõ nghĩa tiếng Việt theo tiếng Hàn"], horizontal=True)
        order_key = f"{st.session_state.folder_no}_{folder_size}_{mode}"
        if not st.session_state.write_cards_order or st.session_state.get("write_order_key") != order_key:
            st.session_state.write_order_key = order_key
            st.session_state.write_cards_order = cards.copy()
            random.shuffle(st.session_state.write_cards_order)
            st.session_state.write_i = 0
            st.session_state.write_score = 0
            st.session_state.write_total = 0
            st.session_state.write_last = None
            st.session_state.write_input = ""

        wc = st.session_state.write_cards_order[st.session_state.write_i % len(st.session_state.write_cards_order)]
        st.progress((st.session_state.write_i % len(st.session_state.write_cards_order)) / max(1, len(st.session_state.write_cards_order)))
        st.write(f"Điểm: **{st.session_state.write_score}/{st.session_state.write_total}**")
        if st.session_state.write_last:
            last = st.session_state.write_last
            if last["ok"]:
                st.success(f"Câu trước: Đúng ✅ | {last['kr']} = {last['vi']}")
            else:
                st.error(f"Câu trước: Sai ❌ | Bạn nhập: {last['user']} | Đáp án: {last['answer']}")

        if mode == "Gõ tiếng Hàn theo nghĩa":
            prompt_main = wc["vi"]
            prompt_sub = wc["detail"]
            expected = wc["kr"]
            label = "Nhập tiếng Hàn rồi nhấn Enter"
        else:
            prompt_main = wc["kr"]
            prompt_sub = ""
            expected = wc["vi"]
            label = "Nhập nghĩa tiếng Việt rồi nhấn Enter"

        st.markdown(f"<div class='card'><div class='meaning'>{prompt_main}</div><div class='detail'>{prompt_sub}</div></div>", unsafe_allow_html=True)
        with st.form("write_form", clear_on_submit=True):
            user_ans = st.text_input(label, key="write_answer_box", placeholder="Gõ đáp án ở đây...")
            submitted = st.form_submit_button("Enter / Chấm & câu tiếp theo", use_container_width=True)
        if submitted:
            ok = is_correct(user_ans, expected, mode)
            # Chỉ tính tổng câu khi người học trả lời đúng lần đầu hoặc sai lần đầu.
            # Nếu sai, app KHÔNG chuyển câu; người học phải gõ lại tới khi đúng.
            st.session_state.write_total += 1
            if ok:
                st.session_state.write_score += 1
                st.session_state.write_last = {"ok": True, "user": user_ans, "answer": expected, "kr": wc["kr"], "vi": wc["vi"]}
                st.session_state.write_i = (st.session_state.write_i + 1) % len(st.session_state.write_cards_order)
            else:
                st.session_state.write_last = {"ok": False, "user": user_ans, "answer": expected, "kr": wc["kr"], "vi": wc["vi"]}
                # Giữ nguyên write_i để hiện lại đúng câu hiện tại.
            st.rerun()
        cc1, cc2, cc3 = st.columns(3)
        if cc1.button("👁️ Hiện đáp án", use_container_width=True):
            st.session_state.write_last = {"ok": False, "user": "Đã xem đáp án", "answer": expected, "kr": wc["kr"], "vi": wc["vi"]}
            # Vẫn không chuyển câu; phải gõ đúng mới qua câu tiếp theo.
            st.rerun()
        if cc2.button("🔀 Trộn lại bộ", use_container_width=True):
            random.shuffle(st.session_state.write_cards_order)
            st.session_state.write_i = 0
            st.session_state.write_last = None
            st.rerun()
        if cc3.button("🔄 Reset điểm", use_container_width=True):
            st.session_state.write_score = 0
            st.session_state.write_total = 0
            st.session_state.write_last = None
            st.rerun()

    with tab_learn:
        st.subheader(f"🎓 Học — Bộ {st.session_state.folder_no:03d}")
        if "learn_card" not in st.session_state or st.button("Từ mới"):
            st.session_state.learn_card = random.choice(cards)
        c = st.session_state.learn_card
        st.markdown(f"<div class='card'><div class='korean'>{c['kr']}</div></div>", unsafe_allow_html=True)
        ans = st.text_input("Nhập nghĩa tiếng Việt:")
        if st.button("Kiểm tra"):
            st.success(c['vi'])
            if c['detail']:
                st.info(c['detail'])

    with tab_quiz:
        st.subheader(f"📝 Quiz — Bộ {st.session_state.folder_no:03d}")
        valid_for_quiz = [x for x in cards if x['vi'] != "Chưa có nghĩa"]
        if len(valid_for_quiz) < 4:
            st.warning("Cần ít nhất 4 thẻ có nghĩa để làm quiz.")
        else:
            if "quiz_q" not in st.session_state or st.button("Câu mới"):
                q = random.choice(valid_for_quiz)
                wrong_pool = [x for x in valid_for_quiz if x['vi'] != q['vi']]
                options = [q['vi']] + [x['vi'] for x in random.sample(wrong_pool, min(3, len(wrong_pool)))]
                random.shuffle(options)
                st.session_state.quiz_q = q
                st.session_state.quiz_options = options
            q = st.session_state.quiz_q
            st.markdown(f"<div class='card'><div class='korean'>{q['kr']}</div></div>", unsafe_allow_html=True)
            choice = st.radio("Chọn nghĩa đúng", st.session_state.quiz_options)
            if st.button("Chấm điểm"):
                if choice == q['vi']:
                    st.success("Đúng rồi!")
                else:
                    st.error(f"Sai. Đáp án đúng: {q['vi']}")

    with tab_match:
        st.subheader(f"🧩 Ghép cặp — Bộ {st.session_state.folder_no:03d}")
        valid_for_match = [x for x in cards if x['vi'] != "Chưa có nghĩa"]
        if len(valid_for_match) < 2:
            st.warning("Cần ít nhất 2 thẻ có nghĩa để ghép cặp.")
        else:
            sample = random.sample(valid_for_match, min(8, len(valid_for_match)))
            st.write("Chọn nghĩa đúng cho từng từ:")
            rights = [x['vi'] for x in sample]
            score = 0
            for item in sample:
                ans = st.selectbox(item['kr'], [""] + rights, key=f"match_{item['stt']}_{st.session_state.folder_no}")
                if ans == item['vi']:
                    score += 1
            if st.button("Kiểm tra ghép cặp"):
                st.info(f"Bạn đúng {score}/{len(sample)}")

    with tab_search:
        st.subheader("🔎 Tìm kiếm toàn bộ dữ liệu")
        kw = st.text_input("Nhập từ tiếng Hàn hoặc nghĩa tiếng Việt")
        if kw:
            kwl = kw.lower()
            res = [x for x in cards_all if kwl in x['kr'].lower() or kwl in x['vi'].lower() or kwl in x['detail'].lower()]
            st.write(f"Tìm thấy {len(res)} kết quả")
            st.dataframe(pd.DataFrame(res[:500]), use_container_width=True)

    with tab_data:
        st.subheader("📋 Dữ liệu bộ đang học")
        st.dataframe(pd.DataFrame(cards), use_container_width=True)
        csv = pd.DataFrame(cards).to_csv(index=False).encode("utf-8-sig")
        st.download_button("Tải CSV bộ này", csv, file_name=f"bo_{st.session_state.folder_no:03d}.csv", mime="text/csv")

except Exception as e:
    st.error("Có lỗi khi đọc dữ liệu hoặc chạy app.")
    st.exception(e)
