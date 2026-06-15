import re
import random
import math
import unicodedata
import html
import inspect
import json
import difflib
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

try:
    from streamlit_mic_recorder import speech_to_text
    MIC_AVAILABLE = True
except Exception:
    MIC_AVAILABLE = False


st.set_page_config(page_title="Bùi Văn Toàn V13", page_icon="📁", layout="wide")

APP_DIR = Path(__file__).parent
LOGO_PATH = APP_DIR / "2612.png"

DEFAULT_GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/188bSTqmXvvU55ht8yJt-wlIwfP3mLiOhebhEStcAwvw/edit?gid=881137373#gid=881137373"

BUTTON_SUPPORTS_SHORTCUT = "shortcut" in inspect.signature(st.button).parameters


st.markdown("""
<style>
.main-title {font-size: 46px; font-weight: 900; margin-bottom: 0px;}
.card {border:1px solid #666; border-radius:26px; padding:50px; text-align:center; min-height:320px; background:#0f1117;}
.korean {font-size:64px; font-weight:900; margin-bottom:35px; line-height:1.25;}
.meaning {font-size:28px; font-weight:800; margin-bottom:25px; white-space:pre-wrap; line-height:1.45;}
.detail {font-size:18px; color:#aaa; white-space:pre-wrap; line-height:1.55;}
.synonyms {font-size:22px; color:#93c5fd; white-space:pre-wrap; line-height:1.6; margin-top:18px;}
.folder-card {border:1px solid #555; border-radius:18px; padding:18px; margin:8px 0; background:#141a25;}
.folder-card-active {border:2px solid #22c55e; border-radius:18px; padding:18px; margin:8px 0; background:#10251a;}
.small {color:#aaa; font-size:14px;}
.quiz-box {background:#2f3b5c; border-radius:18px; padding:32px 36px; margin-top:18px; margin-bottom:22px; border:1px solid #3f4d72;}
.quiz-label {font-size:15px; font-weight:800; color:#fff; margin-bottom:28px;}
.quiz-question {font-size:34px; font-weight:900; color:#fff; min-height:130px; display:flex; align-items:flex-start; line-height:1.35;}
.quiz-answer-title {font-size:15px; font-weight:800; color:#fff; margin-top:18px;}
.quiz-num {height:48px; display:flex; align-items:center; justify-content:center; font-weight:900; color:#fff; border:1px solid #4b5563; border-radius:10px; background:#111827; margin-top:2px;}
.quiz-help {text-align:right; color:#c7c9ff; font-weight:800; margin-top:18px;}
.speaking-box {border:1px solid #4b5563; border-radius:24px; padding:34px; background:#111827; margin-top:18px;}
.speaking-target {font-size:44px; font-weight:900; line-height:1.35; color:#fff; margin-bottom:18px;}
.speaking-vi {font-size:22px; font-weight:700; color:#d1d5db; line-height:1.45; margin-bottom:10px;}
.speaking-detail {font-size:17px; color:#9ca3af; white-space:pre-wrap; line-height:1.5;}
.editor-card {background:#111827; border:1px solid #1f2937; border-radius:14px; padding:18px; margin-top:16px; margin-bottom:14px;}
.editor-index {font-size:18px; font-weight:900; color:white;}
div[data-testid="stButton"] button kbd {display:none !important;}
div[data-testid="stButton"] button [data-testid="stShortcutBadge"] {display:none !important;}
div[data-testid="stButton"] button span[data-testid="stShortcutBadge"] {display:none !important;}
</style>
""", unsafe_allow_html=True)


col1, col2, col3 = st.columns([1, 1, 1])
with col2:
    if LOGO_PATH.exists():
        st.image(str(LOGO_PATH), width=180)


@st.cache_data(show_spinner=False)
def read_google_sheet(url: str, sheet_name: str) -> pd.DataFrame:
    m = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", url)
    if not m:
        raise ValueError("Link Google Sheets không đúng.")

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


def col_letter_to_index(letter: str):
    letter = str(letter).strip().upper()

    if not letter:
        return None

    n = 0

    for ch in letter:
        if "A" <= ch <= "Z":
            n = n * 26 + ord(ch) - 64

    if n <= 0:
        return None

    return n - 1


def clean_text(x):
    if x is None:
        return ""

    s = str(x).replace("\u00a0", " ").strip()

    if s.lower() == "nan":
        return ""

    return s


def split_answer_parts(text: str):
    parts = re.split(r"[\n/|,;；]+", clean_text(text))
    return [p.strip() for p in parts if p.strip()]


def normalize_answer(s: str) -> str:
    s = clean_text(s).lower()
    s = unicodedata.normalize("NFC", s)
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"[.,;:!?()\[\]{}'\"`~]", "", s)
    return s.strip()


def unique_join(old_text: str, new_text: str, sep: str = "\n"):
    items = []
    seen = set()

    for item in split_answer_parts(old_text) + split_answer_parts(new_text):
        norm = normalize_answer(item)

        if item and norm and norm not in seen:
            items.append(item)
            seen.add(norm)

    return sep.join(items)


def make_cards(
    df: pd.DataFrame,
    kr_col: str,
    vi_col: str,
    detail_col: str,
    synonym_col: str,
    auto_fill_merged: bool = True,
    group_same_term: bool = True
):
    ki = col_letter_to_index(kr_col)
    vi = col_letter_to_index(vi_col)
    di = col_letter_to_index(detail_col)
    si = col_letter_to_index(synonym_col)

    if ki is None:
        return []

    work_df = df.copy()

    if auto_fill_merged:
        fill_indexes = [ki]

        if vi is not None:
            fill_indexes.append(vi)

        if di is not None:
            fill_indexes.append(di)

        for col_i in fill_indexes:
            if col_i < len(work_df.columns):
                col_name = work_df.columns[col_i]
                work_df[col_name] = (
                    work_df[col_name]
                    .replace("", pd.NA)
                    .ffill()
                    .fillna("")
                )

    raw_cards = []

    for idx, row in work_df.iterrows():
        vals = list(row.values)

        kr = clean_text(vals[ki]) if ki is not None and ki < len(vals) else ""
        mean = clean_text(vals[vi]) if vi is not None and vi < len(vals) else ""
        detail = clean_text(vals[di]) if di is not None and di < len(vals) else ""
        synonyms = clean_text(vals[si]) if si is not None and si < len(vals) else ""

        if not kr:
            continue

        if not mean:
            mean = "Chưa có nghĩa"

        raw_cards.append({
            "stt": len(raw_cards) + 1,
            "dong_goc": idx + 2,
            "kr": kr,
            "vi": mean,
            "detail": detail,
            "synonyms": synonyms,
            "pronunciation": "",
            "word_type": "",
        })

    if not group_same_term:
        return raw_cards

    grouped = {}

    for card in raw_cards:
        key = normalize_answer(card["kr"])

        if key not in grouped:
            grouped[key] = dict(card)
            grouped[key]["detail"] = ""
            grouped[key]["synonyms"] = ""

        if card.get("vi") and grouped[key].get("vi") in ["", "Chưa có nghĩa"]:
            grouped[key]["vi"] = card["vi"]

        if card.get("detail"):
            grouped[key]["detail"] = unique_join(grouped[key].get("detail", ""), card["detail"])

        if card.get("synonyms"):
            grouped[key]["synonyms"] = unique_join(grouped[key].get("synonyms", ""), card["synonyms"])

    cards = list(grouped.values())

    for i, card in enumerate(cards, start=1):
        card["stt"] = i

    return cards


def make_stats(cards):
    return {
        "cards": len(cards),
        "missing_vi": sum(1 for x in cards if not x.get("vi") or x.get("vi") == "Chưa có nghĩa"),
        "missing_detail": sum(1 for x in cards if not x.get("detail")),
        "missing_synonyms": sum(1 for x in cards if not x.get("synonyms")),
        "skipped_no_kr": 0,
    }


def get_folder(cards, folder_no, folder_size):
    start = (folder_no - 1) * folder_size
    end = min(start + folder_size, len(cards))
    return cards[start:end], start + 1, end


def answer_variants(correct_answer: str, extra_answers: str = ""):
    variants = [clean_text(correct_answer)]
    variants.extend(split_answer_parts(correct_answer))
    variants.extend(split_answer_parts(extra_answers))

    unique = []
    seen = set()

    for item in variants:
        norm = normalize_answer(item)

        if item and norm and norm not in seen:
            unique.append(item)
            seen.add(norm)

    return unique


def format_expected_answer(correct_answer: str, extra_answers: str = "") -> str:
    return " / ".join(answer_variants(correct_answer, extra_answers))


def normalize_speaking_text(s: str) -> str:
    s = clean_text(s).lower()
    s = unicodedata.normalize("NFC", s)
    s = re.sub(r"[^0-9a-zA-Z가-힣ㄱ-ㅎㅏ-ㅣ\s]", "", s)
    s = re.sub(r"\s+", "", s)
    return s.strip()


def speaking_score(target: str, spoken: str) -> float:
    t = normalize_speaking_text(target)
    s = normalize_speaking_text(spoken)

    if not t or not s:
        return 0.0

    return difflib.SequenceMatcher(None, t, s).ratio()


def speak_button(text, lang="ko-KR", rate=0.85):
    safe_text = json.dumps(text)

    components.html(
        f"""
        <button onclick='
            window.speechSynthesis.cancel();
            const utterance = new SpeechSynthesisUtterance({safe_text});
            utterance.lang = "{lang}";
            utterance.rate = {rate};
            window.speechSynthesis.speak(utterance);
        ' style="
            width:100%;
            padding:12px 16px;
            border-radius:10px;
            border:1px solid #4b5563;
            background:#2563eb;
            color:white;
            font-size:17px;
            font-weight:800;
            cursor:pointer;
        ">
            🔊 Nghe phát âm
        </button>
        """,
        height=60
    )


def is_correct(user_answer: str, correct_answer: str, mode: str, extra_answers: str = "") -> bool:
    ua = normalize_answer(user_answer)

    if not ua:
        return False

    if mode == "Gõ tiếng Hàn theo nghĩa":
        ca = normalize_answer(correct_answer)
        return bool(ca) and ua == ca

    valid_answers = [normalize_answer(x) for x in answer_variants(correct_answer, extra_answers)]
    valid_answers = [x for x in valid_answers if x]

    return ua in valid_answers


def reset_card():
    st.session_state.card_i = 0
    st.session_state.show_answer = False


def reset_write():
    st.session_state.write_i = 0
    st.session_state.write_score = 0
    st.session_state.write_total = 0
    st.session_state.write_last = None
    st.session_state.write_cards_order = []


def reset_quiz():
    st.session_state.quiz_q = None
    st.session_state.quiz_options = []
    st.session_state.quiz_last_result = None
    st.session_state.quiz_round = 0


def reset_speaking():
    st.session_state.speaking_i = 0
    st.session_state.speaking_cards_order = []
    st.session_state.speaking_last_text = ""
    st.session_state.speaking_last_score = None


def choose_folder(folder_no):
    old_folder = st.session_state.get("folder_no", None)

    if old_folder != folder_no:
        st.session_state.folder_learn_count[folder_no] = (
            st.session_state.folder_learn_count.get(folder_no, 0) + 1
        )

    st.session_state.folder_no = folder_no
    reset_card()
    reset_write()
    reset_quiz()
    reset_speaking()
    st.session_state.learn_show_answer = False
    st.session_state.pop("learn_card", None)
    st.rerun()


def get_folder_status(folder_no):
    count = st.session_state.folder_learn_count.get(folder_no, 0)

    if folder_no == st.session_state.folder_no:
        if count <= 0:
            return "🟢 Đang học lần thứ 1"
        return f"🟢 Đang học lần thứ {count}"

    if count <= 0:
        return "⚪ Chưa học"

    return f"✅ Đã học {count} lần"


def get_folder_state(folder_no):
    count = st.session_state.folder_learn_count.get(folder_no, 0)

    if folder_no == st.session_state.folder_no:
        return "Đang học"

    if count <= 0:
        return "Chưa học"

    return "Đã học"


def make_quiz_button(label, key, shortcut):
    kwargs = {
        "key": key,
        "use_container_width": True
    }

    if BUTTON_SUPPORTS_SHORTCUT:
        kwargs["shortcut"] = shortcut

    return st.button(label, **kwargs)


for k, v in {
    "folder_no": 1,
    "card_i": 0,
    "show_answer": False,
    "write_i": 0,
    "write_score": 0,
    "write_total": 0,
    "write_last": None,
    "write_cards_order": [],
    "folder_learn_count": {},
    "quiz_q": None,
    "quiz_options": [],
    "quiz_last_result": None,
    "quiz_round": 0,
    "speaking_i": 0,
    "speaking_cards_order": [],
    "speaking_last_text": "",
    "speaking_last_score": None,
    "learn_show_answer": False,
    "editor_cards": [],
    "editor_data_key": "",
    "editor_i": 0,
}.items():
    if k not in st.session_state:
        st.session_state[k] = v


if st.session_state.folder_no not in st.session_state.folder_learn_count:
    st.session_state.folder_learn_count[st.session_state.folder_no] = 1


st.markdown(
    '<div class="main-title" style="text-align:center; transform: translateX(-3cm);">Tiên học lễ, hậu học han cúc co</div>',
    unsafe_allow_html=True
)

st.caption("Bản V13: tự nhận diện ô gộp, gộp ngữ pháp trùng và gom từ đồng nghĩa để học thuận tiện hơn.")


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
    st.caption("Ví dụ của bạn: C = ngữ pháp ban đầu, F hoặc H = từ đồng nghĩa.")

    kr_col = st.text_input("Cột tiếng Hàn / ngữ pháp ban đầu", value="C")
    vi_col = st.text_input("Cột nghĩa tiếng Việt", value="")
    detail_col = st.text_input("Cột giải thích / ví dụ", value="")
    synonym_col = st.text_input("Cột từ đồng nghĩa / đáp án thay thế", value="F")

    auto_fill_merged = st.checkbox(
        "Tự nhận diện ô gộp / điền dữ liệu xuống dòng dưới",
        value=True
    )

    group_same_term = st.checkbox(
        "Gộp các dòng có cùng ngữ pháp ban đầu thành 1 thẻ",
        value=True
    )

    st.caption("Nếu cột F chưa đúng, đổi sang H theo file của bạn.")

    st.header("3) Chia thư mục")
    folder_size = int(st.number_input("Số từ mỗi thư mục", min_value=10, max_value=500, value=50, step=10))


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

    loaded_cards = make_cards(
        df,
        kr_col,
        vi_col,
        detail_col,
        synonym_col,
        auto_fill_merged,
        group_same_term
    )

    if not loaded_cards:
        st.error("Không đọc được thẻ. Hãy kiểm tra lại cột tiếng Hàn / ngữ pháp ban đầu.")
        st.stop()

    data_key = (
        f"{source}|{google_url}|{getattr(uploaded, 'name', '')}|"
        f"{kr_col}|{vi_col}|{detail_col}|{synonym_col}|"
        f"{auto_fill_merged}|{group_same_term}|{len(loaded_cards)}"
    )

    if st.session_state.editor_data_key != data_key:
        st.session_state.editor_data_key = data_key
        st.session_state.editor_cards = [{
            "stt": 1,
            "dong_goc": "",
            "kr": "",
            "vi": "",
            "detail": "",
            "synonyms": "",
            "pronunciation": "",
            "word_type": "",
        }]
        st.session_state.editor_i = 0

    cards_all = loaded_cards
    stats = make_stats(cards_all)

    total = len(cards_all)
    total_folders = max(1, math.ceil(total / folder_size))

    if st.session_state.folder_no > total_folders:
        st.session_state.folder_no = 1

    st.success(
        f"Đã tạo {total:,} thẻ. "
        f"Đã chia thành {total_folders} thư mục, mỗi thư mục {folder_size} từ."
    )

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Thẻ đã tạo", f"{stats['cards']:,}")
    c2.metric("Thiếu nghĩa", f"{stats['missing_vi']:,}")
    c3.metric("Thiếu giải thích", f"{stats['missing_detail']:,}")
    c4.metric("Thiếu đồng nghĩa", f"{stats['missing_synonyms']:,}")
    c5.metric("Bỏ qua vì thiếu tiếng Hàn", f"{stats['skipped_no_kr']:,}")

    top_cols = st.columns([1, 2, 1])

    with top_cols[0]:
        if st.button("⬅️ Bộ trước", disabled=st.session_state.folder_no <= 1, use_container_width=True):
            choose_folder(st.session_state.folder_no - 1)

    with top_cols[1]:
        chosen = st.selectbox(
            "📁 Chọn thư mục/bộ để học",
            list(range(1, total_folders + 1)),
            index=st.session_state.folder_no - 1,
            format_func=lambda f: f"Bộ {f:03d}: từ {(f - 1) * folder_size + 1}–{min(f * folder_size, total)}",
        )

        if chosen != st.session_state.folder_no:
            choose_folder(chosen)

    with top_cols[2]:
        if st.button("Bộ sau ➡️", disabled=st.session_state.folder_no >= total_folders, use_container_width=True):
            choose_folder(st.session_state.folder_no + 1)

    cards, start_num, end_num = get_folder(cards_all, st.session_state.folder_no, folder_size)

    st.info(
        f"Đang học: Bộ {st.session_state.folder_no:03d} | "
        f"từ {start_num}–{end_num} | {len(cards)} thẻ"
    )

    tab_input, tab_folder, tab_flash, tab_write, tab_learn, tab_quiz, tab_speaking, tab_match, tab_search, tab_data = st.tabs([
        "✍️ Nhập thẻ",
        "📁 Thư mục",
        "📚 Flashcard",
        "⌨️ Gõ văn bản",
        "🎓 Học",
        "📝 Quiz",
        "🎙️ Speaking",
        "🧩 Ghép cặp",
        "🔎 Tìm kiếm",
        "📋 Dữ liệu"
    ])

    with tab_input:
        st.subheader("✍️ Nhập / sửa thẻ")

        if not st.session_state.editor_cards:
            st.session_state.editor_cards.append({
                "stt": 1,
                "dong_goc": "",
                "kr": "",
                "vi": "",
                "detail": "",
                "synonyms": "",
                "pronunciation": "",
                "word_type": "",
            })

        st.session_state.editor_i = min(
            st.session_state.editor_i,
            len(st.session_state.editor_cards) - 1
        )

        edit_i = st.session_state.editor_i
        edit_card = st.session_state.editor_cards[edit_i]

        st.markdown("<div class='editor-card'>", unsafe_allow_html=True)

        top_left, top_right = st.columns([1, 12])

        with top_left:
            st.markdown(f"<div class='editor-index'>{edit_i + 1}</div>", unsafe_allow_html=True)

        with top_right:
            st.caption("Bạn có thể sửa lại từ chính và danh sách đồng nghĩa tại đây.")

        col_a, col_b = st.columns(2)

        with col_a:
            new_kr = st.text_input(
                "THUẬT NGỮ / NGỮ PHÁP BAN ĐẦU",
                value=edit_card.get("kr", ""),
                key=f"editor_kr_{edit_i}"
            )

        with col_b:
            new_vi = st.text_area(
                "ĐỊNH NGHĨA",
                value=edit_card.get("vi", ""),
                height=80,
                key=f"editor_vi_{edit_i}"
            )

        col_c, col_d = st.columns(2)

        with col_c:
            new_detail = st.text_area(
                "Ví dụ / Giải thích",
                value=edit_card.get("detail", ""),
                height=120,
                key=f"editor_detail_{edit_i}"
            )

        with col_d:
            new_synonyms = st.text_area(
                "Từ đồng nghĩa",
                value=edit_card.get("synonyms", ""),
                placeholder="VD:\n는 것 같다\n는 듯하다\n나 보다\n는 모양이다",
                height=120,
                key=f"editor_synonyms_{edit_i}"
            )

        st.markdown("</div>", unsafe_allow_html=True)

        st.session_state.editor_cards[edit_i].update({
            "kr": new_kr,
            "vi": new_vi,
            "detail": new_detail,
            "synonyms": new_synonyms,
        })

        btn1, btn2, btn3, btn4 = st.columns(4)

        if btn1.button("⬅️ Trước", key="editor_prev_btn", use_container_width=True, disabled=edit_i <= 0):
            st.session_state.editor_i -= 1
            st.rerun()

        if btn2.button("➕ Thêm thẻ", use_container_width=True):
            st.session_state.editor_cards.append({
                "stt": len(st.session_state.editor_cards) + 1,
                "dong_goc": "",
                "kr": "",
                "vi": "",
                "detail": "",
                "synonyms": "",
                "pronunciation": "",
                "word_type": "",
            })
            st.session_state.editor_i = len(st.session_state.editor_cards) - 1
            st.rerun()

        if btn3.button("🗑️ Xóa thẻ", use_container_width=True, disabled=len(st.session_state.editor_cards) <= 1):
            st.session_state.editor_cards.pop(edit_i)
            st.session_state.editor_i = max(0, edit_i - 1)
            st.rerun()

        if btn4.button("Sau ➡️", key="editor_next_btn", use_container_width=True, disabled=edit_i >= len(st.session_state.editor_cards) - 1):
            st.session_state.editor_i += 1
            st.rerun()

        export_df = pd.DataFrame(st.session_state.editor_cards)
        export_csv = export_df.to_csv(index=False).encode("utf-8-sig")

        st.download_button(
            "⬇️ Tải CSV đã sửa",
            export_csv,
            file_name="tu_vung_da_gop_dong_nghia.csv",
            mime="text/csv",
            use_container_width=True
        )

    with tab_folder:
        st.subheader("📁 Thư mục")
        st.write("Bấm chọn bộ bên dưới. Sau đó qua Flashcard / Gõ văn bản / Quiz / Speaking để học đúng bộ đó.")

        col_sort, col_filter, col_empty = st.columns([2, 1, 3])

        with col_sort:
            folder_sort = st.radio(
                "Sắp xếp thư mục",
                ["Nhỏ → lớn", "Lớn → nhỏ"],
                horizontal=True,
                key="folder_sort"
            )

        with col_filter:
            folder_filter = st.multiselect(
                "Lọc thư mục",
                ["Chưa học", "Đang học", "Đã học"],
                default=["Chưa học", "Đang học", "Đã học"],
                key="folder_filter"
            )

        folder_list = list(range(1, total_folders + 1))

        if folder_sort == "Lớn → nhỏ":
            folder_list = list(reversed(folder_list))

        folder_list = [
            f for f in folder_list
            if get_folder_state(f) in folder_filter
        ]

        if not folder_list:
            st.warning("Không có thư mục nào phù hợp với bộ lọc đang chọn.")
        else:
            grid_cols = st.columns(5)

            for idx, f in enumerate(folder_list):
                s = (f - 1) * folder_size + 1
                e = min(f * folder_size, total)

                active = f == st.session_state.folder_no
                cls = "folder-card-active" if active else "folder-card"
                status_text = get_folder_status(f)

                with grid_cols[idx % 5]:
                    st.markdown(
                        f"<div class='{cls}'>"
                        f"<b>📁 Bộ {f:03d}</b><br>"
                        f"<span class='small'>Từ {s}–{e}</span><br>"
                        f"<span class='small'>{status_text}</span>"
                        f"</div>",
                        unsafe_allow_html=True
                    )

                    label = "✅ Đang học" if active else f"Học bộ {f:03d}"

                    if st.button(label, key=f"choose_folder_{f}", use_container_width=True, disabled=active):
                        choose_folder(f)

    with tab_flash:
        st.subheader(f"📚 Flashcard — Bộ {st.session_state.folder_no:03d}")

        i = st.session_state.card_i % len(cards)
        card = cards[i]

        st.markdown(f"### Thẻ {i + 1}/{len(cards)}")

        synonym_html = (
            f"<div class='synonyms'><b>Đồng nghĩa:</b><br>{html.escape(card.get('synonyms', ''))}</div>"
            if card.get("synonyms") else ""
        )

        if st.session_state.show_answer:
            st.markdown(
                f"<div class='card'>"
                f"<div class='korean'>{html.escape(card.get('kr', ''))}</div>"
                f"<div class='meaning'>{html.escape(card.get('vi', ''))}</div>"
                f"{synonym_html}"
                f"<div class='detail'>{html.escape(card.get('detail', ''))}</div>"
                f"</div>",
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f"<div class='card'>"
                f"<div class='korean'>{html.escape(card.get('kr', ''))}</div>"
                f"<div class='detail'>Bấm Hiện nghĩa để xem đáp án.</div>"
                f"</div>",
                unsafe_allow_html=True
            )

        fb1, fb2, fb3, fb4, fb5 = st.columns(5)

        if fb1.button("⬅️ Trước", key="flash_prev_btn", use_container_width=True):
            st.session_state.card_i = (i - 1) % len(cards)
            st.session_state.show_answer = False
            st.rerun()

        if fb2.button("👁️ Hiện/ẩn", use_container_width=True):
            st.session_state.show_answer = not st.session_state.show_answer
            st.rerun()

        if fb3.button("➡️ Sau", key="flash_next_btn", use_container_width=True):
            st.session_state.card_i = (i + 1) % len(cards)
            st.session_state.show_answer = False
            st.rerun()

        if fb4.button("🔀 Trộn bộ", use_container_width=True):
            random.shuffle(cards)
            st.session_state.card_i = 0
            st.session_state.show_answer = False
            st.rerun()

        with fb5:
            speak_button(card.get("kr", ""))

    with tab_write:
        st.subheader(f"⌨️ Kiểm tra bằng gõ văn bản — Bộ {st.session_state.folder_no:03d}")
        st.caption("Khi gõ nghĩa tiếng Việt theo tiếng Hàn, app sẽ chấp nhận cả đáp án chính và từ đồng nghĩa.")

        mode = st.radio(
            "Kiểu kiểm tra",
            ["Gõ tiếng Hàn theo nghĩa", "Gõ nghĩa tiếng Việt theo tiếng Hàn"],
            horizontal=True
        )

        order_key = f"{st.session_state.folder_no}_{folder_size}_{mode}_{len(cards)}"

        if not st.session_state.write_cards_order or st.session_state.get("write_order_key") != order_key:
            st.session_state.write_order_key = order_key
            st.session_state.write_cards_order = cards.copy()
            random.shuffle(st.session_state.write_cards_order)
            st.session_state.write_i = 0
            st.session_state.write_score = 0
            st.session_state.write_total = 0
            st.session_state.write_last = None

        wc = st.session_state.write_cards_order[
            st.session_state.write_i % len(st.session_state.write_cards_order)
        ]

        st.progress(
            (st.session_state.write_i % len(st.session_state.write_cards_order)) /
            max(1, len(st.session_state.write_cards_order))
        )

        st.write(f"Điểm: **{st.session_state.write_score}/{st.session_state.write_total}**")

        if st.session_state.write_last:
            last = st.session_state.write_last

            if last["ok"]:
                st.success(f"Câu trước: Đúng ✅ | {last['kr']} = {last['answer']}")
            else:
                st.error(f"Câu trước: Sai ❌ | Bạn nhập: {last['user']} | Đáp án: {last['answer']}")

        if mode == "Gõ tiếng Hàn theo nghĩa":
            prompt_main = wc.get("vi", "")
            prompt_sub = wc.get("detail", "")
            expected = wc.get("kr", "")
            extra_answers = ""
            label = "Nhập tiếng Hàn rồi nhấn Enter"
        else:
            prompt_main = wc.get("kr", "")
            prompt_sub = wc.get("detail", "")
            expected = wc.get("vi", "")
            extra_answers = wc.get("synonyms", "")
            label = "Nhập nghĩa / từ đồng nghĩa rồi nhấn Enter"

        shown_answer = format_expected_answer(expected, extra_answers)

        st.markdown(
            f"<div class='card'>"
            f"<div class='meaning'>{html.escape(prompt_main)}</div>"
            f"<div class='detail'>{html.escape(prompt_sub)}</div>"
            f"</div>",
            unsafe_allow_html=True
        )

        with st.form("write_form", clear_on_submit=True):
            user_ans = st.text_input(label, key="write_answer_box", placeholder="Gõ đáp án ở đây...")
            submitted = st.form_submit_button("Enter / Chấm & câu tiếp theo", use_container_width=True)

        if submitted:
            ok = is_correct(user_ans, expected, mode, extra_answers)
            st.session_state.write_total += 1

            if ok:
                st.session_state.write_score += 1
                st.session_state.write_i = (
                    st.session_state.write_i + 1
                ) % len(st.session_state.write_cards_order)

            st.session_state.write_last = {
                "ok": ok,
                "user": user_ans,
                "answer": shown_answer,
                "kr": wc.get("kr", ""),
                "vi": wc.get("vi", "")
            }

            st.rerun()

        cc1, cc2, cc3 = st.columns(3)

        if cc1.button("👁️ Hiện đáp án", use_container_width=True):
            st.session_state.write_last = {
                "ok": False,
                "user": "Đã xem đáp án",
                "answer": shown_answer,
                "kr": wc.get("kr", ""),
                "vi": wc.get("vi", "")
            }
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
            st.session_state.learn_show_answer = False

        c = st.session_state.learn_card

        learn_synonym_html = (
            f"<div class='synonyms'><b>Đồng nghĩa:</b><br>{html.escape(c.get('synonyms', ''))}</div>"
            if c.get("synonyms") else ""
        )

        st.markdown(
            f"<div class='card'>"
            f"<div class='korean'>{html.escape(c.get('kr', ''))}</div>"
            f"{learn_synonym_html if st.session_state.get('learn_show_answer') else ''}"
            f"</div>",
            unsafe_allow_html=True
        )

        speak_button(c.get("kr", ""))

        ans = st.text_input("Nhập nghĩa / từ đồng nghĩa:")

        if st.button("Kiểm tra"):
            st.session_state.learn_show_answer = True

            if is_correct(ans, c.get("vi", ""), "Gõ nghĩa tiếng Việt theo tiếng Hàn", c.get("synonyms", "")):
                st.success(f"Đúng rồi: {format_expected_answer(c.get('vi', ''), c.get('synonyms', ''))}")
            else:
                st.warning(f"Đáp án: {format_expected_answer(c.get('vi', ''), c.get('synonyms', ''))}")

            if c.get("detail"):
                st.info(c.get("detail"))

    with tab_quiz:
        st.subheader(f"📝 Quiz — Bộ {st.session_state.folder_no:03d}")

        valid_for_quiz = [x for x in cards if x.get("kr")]

        if len(valid_for_quiz) < 4:
            st.warning("Cần ít nhất 4 thẻ để làm quiz.")
        else:
            def pick_one_answer(card):
                answers = answer_variants(
                    card.get("vi", ""),
                    card.get("synonyms", "")
                )

                if not answers:
                    answers = [card.get("kr", "")]

                answers = [x for x in answers if clean_text(x)]

                if not answers:
                    return ""

                return random.choice(answers)

            def make_new_quiz_question():
                new_q = random.choice(valid_for_quiz)

                correct_variants = answer_variants(
                    new_q.get("vi", ""),
                    new_q.get("synonyms", "")
                )

                if not correct_variants:
                    correct_variants = [new_q.get("kr", "")]

                correct_variants = [x for x in correct_variants if clean_text(x)]
                correct_option = random.choice(correct_variants)

                new_wrong_pool = [
                    x for x in valid_for_quiz
                    if x.get("kr") != new_q.get("kr")
                ]

                wrong_answers = []
                random.shuffle(new_wrong_pool)

                correct_norms = [normalize_answer(a) for a in correct_variants]

                for x in new_wrong_pool:
                    wrong_text = pick_one_answer(x)
                    wrong_norm = normalize_answer(wrong_text)

                    if (
                        wrong_text
                        and wrong_norm not in correct_norms
                        and wrong_norm not in [normalize_answer(a) for a in wrong_answers]
                    ):
                        wrong_answers.append(wrong_text)

                    if len(wrong_answers) >= 3:
                        break

                new_options = [correct_option] + wrong_answers
                random.shuffle(new_options)

                st.session_state.quiz_q = new_q
                st.session_state.quiz_correct = correct_option
                st.session_state.quiz_correct_variants = correct_variants
                st.session_state.quiz_options = new_options
                st.session_state.quiz_round = st.session_state.get("quiz_round", 0) + 1

            def check_answer(selected_option):
                correct_variants = st.session_state.get("quiz_correct_variants", [])

                selected_norm = normalize_answer(selected_option)
                correct_norms = [normalize_answer(x) for x in correct_variants]

                if selected_norm in correct_norms:
                    st.session_state.quiz_last_result = "correct"
                    make_new_quiz_question()
                    st.rerun()
                else:
                    st.session_state.quiz_last_result = "wrong"
                    st.rerun()

            if st.session_state.quiz_q is None or not st.session_state.quiz_options:
                make_new_quiz_question()
                st.session_state.quiz_last_result = None

            if st.button("Câu mới", key="quiz_new_btn", use_container_width=True):
                make_new_quiz_question()
                st.session_state.quiz_last_result = None
                st.rerun()

            q = st.session_state.quiz_q
            options = st.session_state.quiz_options
            quiz_round = st.session_state.get("quiz_round", 0)

            st.markdown(
                f"""
                <div class="quiz-box">
                    <div class="quiz-label">Thuật ngữ</div>
                    <div class="quiz-question">{html.escape(q.get("kr", ""))}</div>
                    <div class="quiz-answer-title">Chọn đáp án đúng</div>
                </div>
                """,
                unsafe_allow_html=True
            )

            speak_button(q.get("kr", ""))

            if st.session_state.get("quiz_last_result") == "correct":
                st.success("Đúng rồi! Đã tự chuyển sang câu tiếp theo ✅")
            elif st.session_state.get("quiz_last_result") == "wrong":
                st.error(
                    "Sai. Các đáp án đúng là: "
                    + " / ".join(st.session_state.get("quiz_correct_variants", []))
                )

            answer_cols = st.columns(2)

            for idx, option in enumerate(options, start=1):
                with answer_cols[(idx - 1) % 2]:
                    num_col, btn_col = st.columns([1, 9])

                    with num_col:
                        st.markdown(
                            f"<div class='quiz-num'>{idx}</div>",
                            unsafe_allow_html=True
                        )

                    with btn_col:
                        btn_key = f"quiz_option_{st.session_state.folder_no}_{quiz_round}_{idx}"

                        clicked = make_quiz_button(
                            str(option),
                            key=btn_key,
                            shortcut=str(idx)
                        )

                        if clicked:
                            check_answer(option)

    with tab_speaking:
        st.subheader(f"🎙️ Speaking — Luyện nói tiếng Hàn — Bộ {st.session_state.folder_no:03d}")

        if not MIC_AVAILABLE:
            st.error("Bạn chưa cài thư viện streamlit-mic-recorder.")
            st.code("pip install streamlit-mic-recorder", language="bash")
        else:
            speaking_mode = st.radio(
                "Chọn kiểu luyện nói",
                ["Luyện theo thuật ngữ tiếng Hàn", "Luyện theo ví dụ/giải thích nếu có"],
                horizontal=True,
                key="speaking_mode"
            )

            speaking_order_key = f"{st.session_state.folder_no}_{folder_size}_{speaking_mode}_{len(cards)}"

            if (
                not st.session_state.speaking_cards_order
                or st.session_state.get("speaking_order_key") != speaking_order_key
            ):
                st.session_state.speaking_order_key = speaking_order_key
                st.session_state.speaking_cards_order = cards.copy()
                random.shuffle(st.session_state.speaking_cards_order)
                st.session_state.speaking_i = 0
                st.session_state.speaking_last_text = ""
                st.session_state.speaking_last_score = None

            sc = st.session_state.speaking_cards_order[
                st.session_state.speaking_i % len(st.session_state.speaking_cards_order)
            ]

            target_text = sc.get("kr", "")

            if speaking_mode == "Luyện theo ví dụ/giải thích nếu có":
                target_text = sc.get("detail") or sc.get("kr", "")

            st.progress(
                (st.session_state.speaking_i % len(st.session_state.speaking_cards_order)) /
                max(1, len(st.session_state.speaking_cards_order))
            )

            st.write(f"Câu: **{(st.session_state.speaking_i % len(st.session_state.speaking_cards_order)) + 1}/{len(st.session_state.speaking_cards_order)}**")

            synonym_html = (
                f'<div class="synonyms"><b>Đồng nghĩa:</b><br>{html.escape(sc.get("synonyms", ""))}</div>'
                if sc.get("synonyms") else ""
            )

            st.markdown(
                f"""
                <div class="speaking-box">
                    <div class="speaking-target">{html.escape(target_text)}</div>
                    <div class="speaking-vi">{html.escape(sc.get("vi", ""))}</div>
                    {synonym_html}
                    <div class="speaking-detail">{html.escape(sc.get("detail", ""))}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

            sp_col1, sp_col2, sp_col3 = st.columns(3)

            with sp_col1:
                speak_button(target_text)

            with sp_col2:
                if st.button("➡️ Câu tiếp theo", use_container_width=True):
                    st.session_state.speaking_i = (
                        st.session_state.speaking_i + 1
                    ) % len(st.session_state.speaking_cards_order)
                    st.session_state.speaking_last_text = ""
                    st.session_state.speaking_last_score = None
                    st.rerun()

            with sp_col3:
                if st.button("🔀 Trộn lại", use_container_width=True):
                    random.shuffle(st.session_state.speaking_cards_order)
                    st.session_state.speaking_i = 0
                    st.session_state.speaking_last_text = ""
                    st.session_state.speaking_last_score = None
                    st.rerun()

            st.markdown("### 🎤 Bấm nút dưới để nói")

            spoken_text = speech_to_text(
                language="ko-KR",
                start_prompt="🎙️ Bấm để nói",
                stop_prompt="⏹️ Dừng ghi âm",
                just_once=True,
                use_container_width=True,
                key=f"speech_{st.session_state.folder_no}_{st.session_state.speaking_i}_{speaking_mode}"
            )

            if spoken_text:
                score = speaking_score(target_text, spoken_text)
                st.session_state.speaking_last_text = spoken_text
                st.session_state.speaking_last_score = score

            if st.session_state.speaking_last_text:
                st.markdown("### Kết quả")
                st.write("Bạn đã nói:")
                st.success(st.session_state.speaking_last_text)

                score = st.session_state.speaking_last_score or 0
                st.write(f"Độ giống: **{score:.0%}**")
                st.progress(score)

                if score >= 0.85:
                    st.success("Rất tốt! Phát âm khá giống ✅")
                elif score >= 0.6:
                    st.warning("Khá ổn, nhưng nên đọc chậm và rõ hơn.")
                else:
                    st.error("Chưa giống lắm. Hãy bấm nghe lại rồi nói lại.")

    with tab_match:
        st.subheader(f"🧩 Ghép cặp — Bộ {st.session_state.folder_no:03d}")

        valid_for_match = [x for x in cards if x.get("kr")]

        if len(valid_for_match) < 2:
            st.warning("Cần ít nhất 2 thẻ để ghép cặp.")
        else:
            sample = random.sample(valid_for_match, min(8, len(valid_for_match)))

            st.write("Chọn đáp án đúng cho từng từ:")

            rights = [
                format_expected_answer(x.get("vi", ""), x.get("synonyms", "")) or x.get("kr", "")
                for x in sample
            ]

            score = 0

            for item in sample:
                correct = format_expected_answer(item.get("vi", ""), item.get("synonyms", "")) or item.get("kr", "")

                ans = st.selectbox(
                    item.get("kr", ""),
                    [""] + rights,
                    key=f"match_{item.get('stt')}_{st.session_state.folder_no}"
                )

                if ans == correct:
                    score += 1

            if st.button("Kiểm tra ghép cặp"):
                st.info(f"Bạn đúng {score}/{len(sample)}")

    with tab_search:
        st.subheader("🔎 Tìm kiếm toàn bộ dữ liệu")

        kw = st.text_input("Nhập từ tiếng Hàn, nghĩa tiếng Việt hoặc từ đồng nghĩa")

        if kw:
            kwl = kw.lower()

            res = [
                x for x in cards_all
                if kwl in x.get("kr", "").lower()
                or kwl in x.get("vi", "").lower()
                or kwl in x.get("detail", "").lower()
                or kwl in x.get("synonyms", "").lower()
            ]

            st.write(f"Tìm thấy {len(res)} kết quả")
            st.dataframe(pd.DataFrame(res[:500]), use_container_width=True)

    with tab_data:
        st.subheader("📋 Dữ liệu bộ đang học")

        st.dataframe(pd.DataFrame(cards), use_container_width=True)

        csv = pd.DataFrame(cards).to_csv(index=False).encode("utf-8-sig")

        st.download_button(
            "Tải CSV bộ này",
            csv,
            file_name=f"bo_{st.session_state.folder_no:03d}.csv",
            mime="text/csv"
        )

except Exception as e:
    st.error("Có lỗi khi đọc dữ liệu hoặc chạy app.")
    st.exception(e)
