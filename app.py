import re
import os
import random
import math
import unicodedata
import html
import inspect
import json
import difflib
import textwrap
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode, quote

import pandas as pd
import requests
import streamlit as st
import streamlit.components.v1 as components

try:
    from streamlit_mic_recorder import speech_to_text
    MIC_AVAILABLE = True
except Exception:
    MIC_AVAILABLE = False


st.set_page_config(page_title="Bùi Văn Toàn V13", page_icon="📁", layout="wide", initial_sidebar_state="expanded")

APP_DIR = Path(__file__).parent
LOGO_PATH = APP_DIR / "2612.png"

DEFAULT_GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/188bSTqmXvvU55ht8yJt-wlIwfP3mLiOhebhEStcAwvw/edit?gid=881137373#gid=881137373"

SAVED_GOOGLE_SHEETS = {
    "NhapLieu": "https://docs.google.com/spreadsheets/d/188bSTqmXvvU55ht8yJt-wlIwfP3mLiOhebhEStcAwvw/edit?gid=881137373#gid=881137373",
    "trang 21-24": "https://docs.google.com/spreadsheets/d/188bSTqmXvvU55ht8yJt-wlIwfP3mLiOhebhEStcAwvw/edit?gid=418545698#gid=418545698",
    "ngu phap": "https://docs.google.com/spreadsheets/d/188bSTqmXvvU55ht8yJt-wlIwfP3mLiOhebhEStcAwvw/edit?gid=268035535#gid=268035535",
}

SAVED_SHEET_COLUMNS = {
    "NhapLieu": {
        "kr": "B",
        "vi": "A",
        "detail": "C",
        "synonym": "",
    },
    "trang 21-24": {
        "kr": "C",
        "vi": "",
        "detail": "E",
        "synonym": "G",
    },
    "ngu phap": {
        "kr": "D",
        "vi": "E",
        "detail": "F",
        "synonym": "G",
    },
}

DEFAULT_EXCEL_QUIZ_GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/188bSTqmXvvU55ht8yJt-wlIwfP3mLiOhebhEStcAwvw/edit?gid=421247814#gid=421247814"

STATE_FILE = APP_DIR / "app_star_state.json"
LOCAL_API_KEY_FILE = APP_DIR / "google_sheets_api_key.txt"


def load_saved_google_api_key():
    """
    Đọc API key từ máy của bạn, không cần nhập lại mỗi lần.

    Ưu tiên theo thứ tự:
    1) Biến môi trường GOOGLE_SHEETS_API_KEY
    2) File .streamlit/secrets.toml với dòng: GOOGLE_SHEETS_API_KEY = "..."
    3) File google_sheets_api_key.txt đặt cùng thư mục app
    """
    env_key = os.getenv("GOOGLE_SHEETS_API_KEY", "").strip()

    if env_key:
        return env_key

    try:
        secret_key = st.secrets.get("GOOGLE_SHEETS_API_KEY", "").strip()
        if secret_key:
            return secret_key
    except Exception:
        pass

    try:
        if LOCAL_API_KEY_FILE.exists():
            return LOCAL_API_KEY_FILE.read_text(encoding="utf-8").strip()
    except Exception:
        pass

    return ""


BUTTON_SUPPORTS_SHORTCUT = "shortcut" in inspect.signature(st.button).parameters


def load_persistent_state():
    if not STATE_FILE.exists():
        return {}

    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_persistent_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def card_identity(card):
    return "|".join([
        normalize_answer(card.get("kr", "")),
        normalize_answer(card.get("vi", "")),
        normalize_answer(card.get("detail", ""))
    ])


def restore_starred_state(cards, data_key):
    if not data_key:
        return

    state = load_persistent_state()
    starred_map = state.get(data_key, {})

    for card in cards:
        card_id = card_identity(card)

        if card_id:
            card["starred"] = bool(starred_map.get(card_id, False))


def persist_starred_state(cards, data_key):
    if not data_key:
        return

    state = load_persistent_state()
    state[data_key] = state.get(data_key, {})

    for card in cards:
        card_id = card_identity(card)

        if card_id:
            state[data_key][card_id] = bool(card.get("starred", False))

    save_persistent_state(state)


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
.quiz-box {background:#2f3b5c; border-radius:18px; padding:32px 36px; margin-top:18px; margin-bottom:22px; border:1px solid #3f4d72; position:relative;}
.quiz-box {background:#2f3b5c; border-radius:18px; padding:32px 36px; margin-top:18px; margin-bottom:22px; border:1px solid #3f4d72; position:relative;}
.quiz-star-button {
    position:absolute;
    top:20px;
    right:20px;
    width:56px;
    height:56px;
    border-radius:50%;
    border:1px solid #4b5563;
    background:#111827;
    color:#fbbf24;
    font-size:28px;
    display:inline-flex;
    align-items:center;
    justify-content:center;
    cursor:pointer;
    z-index:9999;
    pointer-events:auto;
    box-shadow: 0 20px 40px rgba(0, 0, 0, 0.25);
}
.quiz-star-button:hover { opacity:0.92; }
button[title="quiz backend button"] { display:none !important; }
button[title="quiz-star-btn"] {
    position:relative;
    top:-196px;
    left:84%;
    width:56px;
    height:56px;
    border-radius:50%;
    border:1px solid #4b5563;
    background:#111827;
    color:#fbbf24;
    font-size:28px;
    display:inline-flex;
    align-items:center;
    justify-content:center;
    cursor:pointer;
    z-index:9999;
    margin-bottom:-156px;
}
button[title="quiz-star-btn"]:hover { opacity:0.92; }
.quiz-label {font-size:15px; font-weight:800; color:#fff; margin-bottom:28px;}
.quiz-question {font-size:34px; font-weight:900; color:#fff; min-height:130px; display:flex; align-items:flex-start; line-height:1.35;}
.quiz-answer-title {font-size:15px; font-weight:800; color:#fff; margin-top:18px;}
.quiz-num {height:48px; display:flex; align-items:center; justify-content:center; font-weight:900; color:#fff; border:1px solid #4b5563; border-radius:10px; background:#111827; margin-top:2px;}
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
    """
    Tách nhiều đáp án trong một ô.

    Quan trọng:
    - Chỉ tách dấu "/" khi nó có khoảng trắng hai bên: " / "
      Ví dụ: "아/어도 / 지 않아도 / (으)ㄴ 것도 없이"
      sẽ tách thành:
      1) 아/어도
      2) 지 않아도
      3) (으)ㄴ 것도 없이

    - Không tách dấu "/" nằm trong bản thân ngữ pháp:
      "아/어도", "(으)ㄴ/는", "V/A" vẫn được giữ nguyên.
    """
    raw = clean_text(text)

    if not raw:
        return []

    parts = []

    for line in re.split(r"[\r\n]+", raw):
        line = line.strip()

        if not line:
            continue

        # Tách các đáp án dạng A / B / C, nhưng không phá "아/어도", "(으)ㄴ/는", "V/A"
        sub_parts = re.split(r"\s+[/／]\s+", line)

        for part in sub_parts:
            part = part.strip()

            if part:
                parts.append(part)

    return parts


def normalize_answer(s: str) -> str:
    s = clean_text(s).lower()
    s = unicodedata.normalize("NFC", s)
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"[.,;:!?()\[\]{}'\"`~]", "", s)
    return s.strip()


def normalize_quiz_key(s: str) -> str:
    """
    Chuẩn hóa riêng cho Quiz để so sánh cột G với toàn bộ cột C.
    Mục tiêu: các dạng sau được coi là trùng nhau:
    - "-(으)ㄹ까요", "(으)ㄹ까요", "V-(으)ㄹ까요", "V/A + (으)ㄹ까요"
    - "아/어 보다", "V-아/어 보다"
    - khác nhau do khoảng trắng, dấu -, /, +, ngoặc, dấu chấm...
    """
    s = clean_text(s).lower()
    s = unicodedata.normalize("NFKC", s)

    # Bỏ ký hiệu HTML / mũi tên / bullet thường gặp trong dữ liệu học
    s = html.unescape(s)
    s = s.replace("➜", " ").replace("→", " ").replace("⇒", " ")
    s = s.replace("ㆍ", " ").replace("·", " ").replace("•", " ")

    # Bỏ nhãn loại từ/ngữ pháp ở đầu: V-, A-, N-, V/A +, V/N + ...
    s = re.sub(r"^\s*(v|a|n|adj|verb|noun)\s*[/+,-]\s*", "", s)
    s = re.sub(r"^\s*(v\s*/\s*a|a\s*/\s*v|v\s*/\s*n|n\s*/\s*v)\s*[/+,-]?\s*", "", s)

    # Bỏ toàn bộ khoảng trắng và hầu hết ký hiệu phân tách
    s = re.sub(r"\s+", "", s)
    s = re.sub(r"[\\/\-+_=.,;:!?~`'\"|]", "", s)
    s = re.sub(r"[()\[\]{}<>〈〉《》「」『』]", "", s)

    # Chuẩn hóa một số ký tự gạch/dấu giống nhau
    s = s.replace("–", "").replace("—", "").replace("−", "")

    return s.strip()


def is_same_as_any_term(answer_key: str, all_term_keys: set) -> bool:
    """
    Trả True nếu đáp án ở cột G trùng với bất kỳ thuật ngữ nào ở cột C.
    Ngoài trùng tuyệt đối, có xét trường hợp một bên còn dư tiền tố/ký hiệu.
    """
    if not answer_key:
        return False

    if answer_key in all_term_keys:
        return True

    # Nếu một bên chứa bên còn lại và độ dài đủ dài thì coi như trùng.
    # Dùng để bắt các dạng như "v아어보다" vs "아어보다".
    for term_key in all_term_keys:
        if not term_key:
            continue
        short_len = min(len(answer_key), len(term_key))
        if short_len >= 3 and (answer_key in term_key or term_key in answer_key):
            return True

    return False


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
            "starred": False,
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
    variants = []

    if clean_text(correct_answer) != "Chưa có nghĩa":
        # Giữ cả cụm gốc để hiển thị đáp án đầy đủ
        variants.append(clean_text(correct_answer))
        # Thêm từng đáp án con để khi chọn "아/어도" vẫn được tính đúng
        variants.extend(split_answer_parts(correct_answer))

    variants.extend(split_answer_parts(extra_answers))

    unique = []
    seen = set()

    for item in variants:
        # Nếu normalize_quiz_key đã được định nghĩa thì dùng để chống trùng mạnh hơn.
        try:
            norm = normalize_quiz_key(item)
        except NameError:
            norm = normalize_answer(item)

        if item and norm and norm not in seen:
            unique.append(item)
            seen.add(norm)

    return unique


def format_expected_answer(correct_answer: str, extra_answers: str = "") -> str:
    return "\n".join(answer_variants(correct_answer, extra_answers))


def unique_by_quiz_key(items):
    unique = []
    seen = set()

    for item in items:
        key = normalize_quiz_key(item)

        if item and key and key not in seen:
            unique.append(item)
            seen.add(key)

    return unique


def quiz_match_keys(s: str):
    """
    Tạo nhiều kiểu key để so sánh đáp án chắc hơn.
    Dùng cả normalize_quiz_key và normalize_answer để tránh lỗi:
    - Có dấu / trong ngữ pháp.
    - Có ngoặc, dấu gạch, khoảng trắng.
    - Đáp án đúng được lưu dạng "A / B / C" nhưng người học chọn riêng A.
    """
    keys = set()

    for part in [clean_text(s)] + split_answer_parts(s):
        if not part:
            continue

        k1 = normalize_quiz_key(part)
        k2 = normalize_answer(part)

        if k1:
            keys.add(k1)

        if k2:
            keys.add(k2)

    return keys


def quiz_answer_matches(selected_option: str, correct_variants) -> bool:
    selected_keys = quiz_match_keys(selected_option)

    if not selected_keys:
        return False

    correct_keys = set()

    for ans in correct_variants:
        correct_keys.update(quiz_match_keys(ans))

    return bool(selected_keys & correct_keys)


def current_quiz_answer_is_correct(selected_option: str) -> bool:
    """
    Kiểm tra đáp án hiện tại thật chắc.
    Dùng cho trường hợp:
    - Người học trả lời sai trước.
    - App hiện đáp án.
    - Người học chọn lại đáp án đúng.
    Khi đúng thì phải tự chuyển câu.
    """
    correct_variants = st.session_state.get("quiz_correct_variants", [])
    correct_option = st.session_state.get("quiz_correct", "")

    all_correct = []
    all_correct.extend(correct_variants)
    all_correct.append(correct_option)
    all_correct.extend(split_answer_parts(correct_option))

    return quiz_answer_matches(selected_option, all_correct)


def answer_variants_for_card(card: dict, question_text: str = ""):
    question_norm = normalize_answer(question_text or card.get("kr", ""))
    variants = answer_variants(card.get("vi", ""), card.get("synonyms", ""))
    filtered = []
    seen = set()

    for item in variants:
        norm = normalize_answer(item)

        if not item or not norm:
            continue

        if question_norm and norm == question_norm:
            continue

        if norm in seen:
            continue

        filtered.append(item)
        seen.add(norm)

    return filtered


def quiz_entries_for_card(card: dict):
    return [
        {
            "card": card,
            "answer": x,
        }
        for x in answer_variants_for_card(card)
        if clean_text(x)
    ]


def build_all_term_norms(cards):
    """
    Lấy toàn bộ thuật ngữ ở cột C / cột câu hỏi.
    Dùng normalize_quiz_key để so sánh mạnh hơn:
    - bỏ V/A/N, dấu -, /, +, ngoặc, khoảng trắng...
    """
    return {
        normalize_quiz_key(card.get("kr", ""))
        for card in cards
        if clean_text(card.get("kr", ""))
    }


def answer_variants_for_card_filtered(card: dict, all_term_norms=None):
    """
    Lấy các đáp án hợp lệ cho quiz.
    - Tách nhiều đáp án theo từng dòng.
    - Loại đáp án trùng chính câu hỏi hiện tại.
    - Loại đáp án trùng với BẤT KỲ thuật ngữ nào trong cột C.
    - So sánh bằng normalize_quiz_key nên bắt được cả dạng khác dấu/khoảng trắng.
    """
    if all_term_norms is None:
        all_term_norms = set()

    question_norm = normalize_quiz_key(card.get("kr", ""))
    filtered = []
    seen = set()

    for item in answer_variants_for_card(card):
        ans_norm = normalize_quiz_key(item)

        if not item or not ans_norm:
            continue

        # Loại nếu đáp án trùng với chính câu hỏi
        if question_norm and ans_norm == question_norm:
            continue

        # Loại nếu đáp án trùng với bất kỳ thuật ngữ nào trong cột C
        if is_same_as_any_term(ans_norm, all_term_norms):
            continue

        if ans_norm in seen:
            continue

        filtered.append(item)
        seen.add(ans_norm)

    return filtered


def quiz_entries_filtered(cards_subset, all_cards):
    """
    Tạo danh sách quiz đã lọc.

    Điểm sửa quan trọng:
    1) So sánh cột G với TOÀN BỘ cột C bằng normalize_quiz_key.
    2) Mỗi đáp án hợp lệ chỉ tính 1 lần trong quiz.
       Trước đây nếu cùng một đáp án xuất hiện ở nhiều dòng khác nhau,
       app vẫn đếm nhiều lần nên còn 85 thay vì số bạn đếm thủ công.
    """
    all_term_norms = build_all_term_norms(all_cards)
    entries = []
    seen_answers = set()

    for card in cards_subset:
        if not card.get("kr"):
            continue

        for ans in answer_variants_for_card_filtered(card, all_term_norms):
            ans_norm = normalize_quiz_key(ans)

            if not ans_norm:
                continue

            # Tránh đếm lặp cùng một đáp án ở nhiều dòng / nhiều thuật ngữ
            if ans_norm in seen_answers:
                continue

            seen_answers.add(ans_norm)

            entries.append({
                "card": card,
                "answer": ans,
            })

    return entries


@st.cache_data(show_spinner=False)
def cached_quiz_entry_count(subset_rows, all_rows):
    """
    Đếm số thẻ có thể tạo quiz và cache kết quả.

    Streamlit chạy lại toàn bộ file sau mỗi lần bấm đáp án. Với sheet lớn,
    không nên dựng lại toàn bộ danh sách câu hỏi chỉ để hiển thị thống kê.
    Theo mặc định Hàn -> Việt, mỗi thẻ hợp lệ tương ứng một câu.
    """
    count = 0

    for kr, vi, synonyms in subset_rows:
        has_question = bool(clean_text(kr))
        has_primary_answer = bool(clean_text(vi)) and clean_text(vi) != "Chưa có nghĩa"
        has_fallback_answer = bool(split_answer_parts(synonyms))

        if has_question and (has_primary_answer or has_fallback_answer):
            count += 1

    return count


def quiz_count_rows(cards):
    return tuple(
        (
            clean_text(card.get("kr", "")),
            clean_text(card.get("vi", "")),
            clean_text(card.get("synonyms", "")),
        )
        for card in cards
    )


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


def reset_quiz(clear_mastered=False, clear_attempts=True, clear_retry_filter=True):
    st.session_state.quiz_q = None
    st.session_state.quiz_options = []
    st.session_state.quiz_last_result = None
    st.session_state.quiz_round = 0
    st.session_state.quiz_show_detail = False
    st.session_state.quiz_wrong_queue = []
    st.session_state.quiz_wrong_keys = set()
    st.session_state.quiz_since_wrong_review = 0
    st.session_state.quiz_is_review = False

    # V6: quản lý một lượt quiz hữu hạn.
    # Câu thường chỉ hỏi đủ total_quiz câu, sau đó chỉ hỏi nốt câu sai đang chờ ôn lại rồi dừng.
    st.session_state.quiz_seen_keys = set()
    st.session_state.quiz_review_count = 0
    st.session_state.quiz_completed = False
    st.session_state.quiz_last_option_orders = {}
    st.session_state.quiz_history_saved = False

    if clear_attempts:
        st.session_state.quiz_attempt_stats = {}

    if clear_retry_filter:
        st.session_state.quiz_retry_only_keys = set()

    if clear_mastered:
        st.session_state.quiz_mastered_keys = set()


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


def excel_quiz_reset(clear_wrong=True):
    st.session_state.excel_quiz_idx = 0
    st.session_state.excel_quiz_checked = False
    st.session_state.excel_quiz_selected = None
    st.session_state.excel_quiz_question_order = []
    st.session_state.excel_quiz_order_signature = ""

    if clear_wrong:
        st.session_state.excel_quiz_results = {}
        st.session_state.excel_quiz_wrong_indices = []

    st.session_state.excel_quiz_review_wrong_only = False


def excel_quiz_clean(x):
    if pd.isna(x):
        return ""
    return str(x).strip()


def excel_quiz_load_google_sheet(google_url: str):
    """
    Đọc dữ liệu Quiz từ Google Sheets.

    Yêu cầu:
    - Link Google Sheet phải được share: Anyone with the link -> Viewer.
    - Link nên có gid ở cuối để app đọc đúng sheet chứa câu hỏi quiz.
    """
    google_url = clean_text(google_url)

    if not google_url:
        return None, "", ""

    df = read_google_sheet(google_url, "quiz_excel").fillna("")
    df.columns = [str(c).strip() for c in df.columns]

    gid_match = re.search(r"gid=([0-9]+)", google_url)
    sheet_name = f"gid={gid_match.group(1)}" if gid_match else "quiz_excel"

    return df, sheet_name, google_url

def google_sheet_ids_from_url(google_url: str):
    google_url = clean_text(google_url)

    spreadsheet_match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", google_url)
    gid_match = re.search(r"gid=([0-9]+)", google_url)

    if not spreadsheet_match:
        raise ValueError("Link Google Sheet không đúng. Không tìm thấy spreadsheet id.")

    spreadsheet_id = spreadsheet_match.group(1)
    gid = int(gid_match.group(1)) if gid_match else None

    return spreadsheet_id, gid


def excel_quiz_text_format_to_html(text: str, fmt: dict):
    text = html.escape(text or "")

    if not text:
        return ""

    if fmt.get("underline"):
        text = f"<u>{text}</u>"

    if fmt.get("bold"):
        text = f"<b>{text}</b>"

    if fmt.get("italic"):
        text = f"<i>{text}</i>"

    color_style = fmt.get("foregroundColorStyle", {})
    rgb = color_style.get("rgbColor") or fmt.get("foregroundColor", {})

    if rgb:
        r = int(float(rgb.get("red", 0)) * 255)
        g = int(float(rgb.get("green", 0)) * 255)
        b = int(float(rgb.get("blue", 0)) * 255)

        if r or g or b:
            text = f"<span style='color: rgb({r}, {g}, {b})'>{text}</span>"

    return text


def excel_quiz_cell_to_html(cell: dict):
    """
    Chuyển ô Google Sheet có định dạng rich text thành HTML đơn giản.
    Hỗ trợ: gạch chân, in đậm, in nghiêng, màu chữ.
    """
    plain = cell.get("formattedValue", "")

    if not plain:
        return ""

    runs = cell.get("textFormatRuns") or []

    if not runs:
        cell_fmt = cell.get("effectiveFormat", {}).get("textFormat", {})

        if cell_fmt.get("underline") or cell_fmt.get("bold") or cell_fmt.get("italic"):
            return excel_quiz_text_format_to_html(plain, cell_fmt)

        return html.escape(plain)

    runs = sorted(runs, key=lambda r: int(r.get("startIndex", 0) or 0))

    if int(runs[0].get("startIndex", 0) or 0) != 0:
        runs = [{"startIndex": 0, "format": {}}] + runs

    parts = []

    for i, run in enumerate(runs):
        start = int(run.get("startIndex", 0) or 0)
        end = int(runs[i + 1].get("startIndex", len(plain)) or len(plain)) if i + 1 < len(runs) else len(plain)

        if start >= len(plain):
            continue

        segment = plain[start:end]

        if not segment:
            continue

        fmt = run.get("format", {}) or {}
        parts.append(excel_quiz_text_format_to_html(segment, fmt))

    return "".join(parts)


def excel_quiz_google_api_metadata_url(spreadsheet_id: str, api_key: str):
    """
    Lấy danh sách sheet nhẹ trước để biết gid tương ứng với tên sheet nào.
    Không tải grid data ở bước này nên nhanh hơn rất nhiều.
    """
    base = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}"
    fields = "sheets(properties(sheetId,title))"

    return f"{base}?fields={quote(fields, safe='(),')}&key={api_key}"


def excel_quiz_google_api_url(spreadsheet_id: str, api_key: str, sheet_title: str):
    """
    Chỉ tải dữ liệu của đúng sheet đang chọn, không tải toàn bộ spreadsheet.
    Đây là phần sửa lỗi timeout.
    """
    base = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}"

    # Giới hạn vùng đọc tới A:M vì file quiz đang dùng 13 cột:
    # Trang, Số câu, Dạng, Câu hỏi, Dịch nghĩa, ①, ②, ③, ④, Đáp án, Đáp án đúng, Giải thích ngắn, Tất cả đáp án
    safe_title = str(sheet_title).replace("'", "''")
    range_a1 = f"'{safe_title}'!A:M"

    fields = (
        "sheets("
        "properties(sheetId,title),"
        "data(rowData(values(formattedValue,textFormatRuns,effectiveFormat(textFormat))))"
        ")"
    )

    query = urlencode({
        "includeGridData": "true",
        "ranges": range_a1,
        "fields": fields,
        "key": api_key,
    })

    return f"{base}?{query}"


def excel_quiz_load_google_sheet_with_format(google_url: str, api_key: str):
    """
    Đọc Google Sheet bằng Google Sheets API để giữ định dạng gạch chân/in đậm.
    Kết quả vẫn giữ cột 'Câu hỏi' sạch và tự thêm cột 'Câu hỏi hiển thị' có HTML.
    """
    google_url = clean_text(google_url)
    api_key = clean_text(api_key)

    if not google_url:
        return None, "", ""

    if not api_key:
        raise ValueError("Bạn cần nhập Google API key để đọc định dạng gạch chân bằng Google Sheets API.")

    spreadsheet_id, gid = google_sheet_ids_from_url(google_url)

    # Bước 1: lấy metadata nhẹ để tìm tên sheet theo gid
    metadata_url = excel_quiz_google_api_metadata_url(spreadsheet_id, api_key)
    meta_response = requests.get(metadata_url, timeout=30)

    if meta_response.status_code != 200:
        raise RuntimeError(f"Google Sheets API metadata lỗi {meta_response.status_code}: {meta_response.text[:500]}")

    metadata = meta_response.json()
    meta_sheets = metadata.get("sheets", [])

    if not meta_sheets:
        raise RuntimeError("Google Sheets API không trả về danh sách sheet.")

    selected_props = None

    if gid is not None:
        for sheet in meta_sheets:
            props = sheet.get("properties", {})
            if int(props.get("sheetId", -1)) == gid:
                selected_props = props
                break

    if selected_props is None:
        selected_props = meta_sheets[0].get("properties", {})

    sheet_title = selected_props.get("title", "quiz_excel")
    sheet_id = selected_props.get("sheetId", "")

    # Bước 2: chỉ lấy gridData của đúng sheet đó, vùng A:M
    api_url = excel_quiz_google_api_url(spreadsheet_id, api_key, sheet_title)
    response = requests.get(api_url, timeout=90)

    if response.status_code != 200:
        raise RuntimeError(f"Google Sheets API dữ liệu lỗi {response.status_code}: {response.text[:500]}")

    data = response.json()
    sheets = data.get("sheets", [])

    if not sheets:
        raise RuntimeError("Google Sheets API không trả về dữ liệu sheet.")

    selected_sheet = sheets[0]

    grid_data = selected_sheet.get("data", [])

    if not grid_data:
        raise RuntimeError("Sheet không có grid data.")

    rows = grid_data[0].get("rowData", [])

    if not rows:
        raise RuntimeError("Sheet không có dòng dữ liệu.")

    max_cols = 0

    for row in rows:
        max_cols = max(max_cols, len(row.get("values", [])))

    table = []
    html_table = []

    for row in rows:
        values = row.get("values", [])
        plain_row = []
        html_row = []

        for col_i in range(max_cols):
            cell = values[col_i] if col_i < len(values) else {}
            plain_row.append(excel_quiz_clean(cell.get("formattedValue", "")))
            html_row.append(excel_quiz_cell_to_html(cell))

        table.append(plain_row)
        html_table.append(html_row)

    while table and not any(excel_quiz_clean(x) for x in table[0]):
        table.pop(0)
        html_table.pop(0)

    if not table:
        raise RuntimeError("Sheet không có dữ liệu chữ.")

    headers = [excel_quiz_clean(x) for x in table[0]]
    headers = [h if h else f"Column_{i + 1}" for i, h in enumerate(headers)]

    data_rows = table[1:]
    html_rows = html_table[1:]

    df = pd.DataFrame(data_rows, columns=headers).fillna("")

    if "Câu hỏi" in df.columns:
        question_col_idx = headers.index("Câu hỏi")
        display_values = []

        for plain_row, html_row in zip(data_rows, html_rows):
            plain_question = plain_row[question_col_idx] if question_col_idx < len(plain_row) else ""
            html_question = html_row[question_col_idx] if question_col_idx < len(html_row) else ""

            if html_question and html_question != html.escape(plain_question):
                display_values.append(html_question)
            else:
                display_values.append("")

        df["Câu hỏi hiển thị"] = display_values

    df.columns = [str(c).strip() for c in df.columns]

    sheet_name = f"{sheet_title} (gid={sheet_id})"

    return df, sheet_name, google_url




def excel_quiz_get_options(row):
    return [
        ("①", excel_quiz_clean(row.get("①", ""))),
        ("②", excel_quiz_clean(row.get("②", ""))),
        ("③", excel_quiz_clean(row.get("③", ""))),
        ("④", excel_quiz_clean(row.get("④", ""))),
    ]


def excel_quiz_correct_label(row):
    """
    Lấy nhãn đáp án đúng từ cột 'Đáp án'.
    Hỗ trợ nhiều kiểu:
    - ① ② ③ ④
    - 1 2 3 4
    - A B C D
    - Nếu cột Đáp án không có, thử dò theo cột 'Đáp án đúng'
    """
    ans = excel_quiz_clean(row.get("Đáp án", ""))

    mapping = {
        "1": "①", "2": "②", "3": "③", "4": "④",
        "A": "①", "B": "②", "C": "③", "D": "④",
        "①": "①", "②": "②", "③": "③", "④": "④",
        "1.": "①", "2.": "②", "3.": "③", "4.": "④",
    }

    if ans.upper() in mapping:
        return mapping[ans.upper()]

    # Có trường hợp ghi "③ 축구하다가"
    for label in ["①", "②", "③", "④"]:
        if ans.startswith(label):
            return label

    # Thử dò theo nội dung đáp án đúng
    right_text = excel_quiz_clean(row.get("Đáp án đúng", ""))

    if right_text:
        for label, text in excel_quiz_get_options(row):
            if normalize_quiz_key(right_text) and normalize_quiz_key(right_text) == normalize_quiz_key(text):
                return label

    return ans


def excel_quiz_real_index():
    if st.session_state.excel_quiz_review_wrong_only:
        wrongs = st.session_state.excel_quiz_wrong_indices
        if 0 <= st.session_state.excel_quiz_idx < len(wrongs):
            return wrongs[st.session_state.excel_quiz_idx]
    return st.session_state.excel_quiz_idx


def render_excel_quiz_tab():
    st.subheader("📘 Quiz từ Google Sheet")
    st.caption(
        "Dùng cho dữ liệu câu hỏi đã đẩy lên Google Sheets. "
        "Có thể chọn học một trang, nhiều trang hoặc học tất cả. "
        "Có cài đặt học tập giống tab Quiz chính: học theo thứ tự, trộn câu hỏi, tự chuyển khi đúng, chỉ học câu chưa thuộc."
    )

    st.markdown("""
    <style>
    div[data-testid="stVerticalBlock"]:has(#excel-quiz-answer-scope) div[data-testid="stButton"] > button {
        min-height: 58px !important;
    }
    div[data-testid="stVerticalBlock"]:has(#excel-quiz-answer-scope) div[data-testid="stButton"] > button p {
        font-size: 32px !important;
        font-weight: 900 !important;
        line-height: 1.35 !important;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("### 🔗 Nguồn câu hỏi")
    quiz_google_url = st.text_input(
        "Link Google Sheet chứa câu hỏi quiz",
        value=st.session_state.get("excel_quiz_google_url", DEFAULT_EXCEL_QUIZ_GOOGLE_SHEET_URL),
        key="excel_quiz_google_url",
        help="Dán link Google Sheet có gid của sheet chứa câu hỏi quiz."
    )

    api_col1, api_col2 = st.columns([1, 2])

    with api_col1:
        use_api_format = st.checkbox(
            "Dùng Google Sheets API để đọc gạch chân/in đậm",
            value=st.session_state.get("excel_quiz_use_google_api_format", False),
            key="excel_quiz_use_google_api_format"
        )

    with api_col2:
        api_key = st.text_input(
            "Google API key",
            value=st.session_state.get("excel_quiz_google_api_key", load_saved_google_api_key()),
            key="excel_quiz_google_api_key",
            type="password",
            help="Cần API key nếu muốn đọc định dạng gạch chân/in đậm từ Google Sheet."
        )

    save_key_col1, save_key_col2 = st.columns([1, 4])

    with save_key_col1:
        if st.button("💾 Lưu key", key="excel_quiz_save_api_key", use_container_width=True):
            if clean_text(api_key):
                LOCAL_API_KEY_FILE.write_text(clean_text(api_key), encoding="utf-8")
                st.success("Đã lưu API key vào file google_sheets_api_key.txt trên máy của bạn.")
                st.rerun()
            else:
                st.warning("Chưa có API key để lưu.")

    with save_key_col2:
        if load_saved_google_api_key():
            st.caption("✅ Đã tìm thấy API key đã lưu trên máy. Bạn không cần nhập lại mỗi lần.")
        else:
            st.caption("Bạn có thể lưu key bằng nút 💾 Lưu key, hoặc dùng file .streamlit/secrets.toml.")

    reload_col1, reload_col2 = st.columns([1, 4])

    with reload_col1:
        if st.button("🔄 Tải lại sheet", key="excel_quiz_reload_google_sheet", use_container_width=True):
            read_google_sheet.clear()
            excel_quiz_reset(clear_wrong=True)
            st.rerun()

    with reload_col2:
        if use_api_format:
            st.info("Đang dùng Google Sheets API để đọc gạch chân/in đậm. Bản này chỉ tải đúng sheet hiện tại để tránh timeout.")
        else:
            st.info("Đang dùng chế độ CSV nhanh. Chế độ này không đọc được gạch chân/in đậm.")

    try:
        if use_api_format:
            df, sheet_name, source_name = excel_quiz_load_google_sheet_with_format(quiz_google_url, api_key)
        else:
            df, sheet_name, source_name = excel_quiz_load_google_sheet(quiz_google_url)
    except Exception as e:
        st.error("Không đọc được Google Sheet. Hãy kiểm tra link, quyền chia sẻ và API key.")
        st.exception(e)
        return

    if df is None:
        st.info("Hãy dán link Google Sheet chứa dữ liệu câu hỏi quiz.")
        return

    required_cols = ["Câu hỏi", "①", "②", "③", "④", "Đáp án"]
    missing_cols = [c for c in required_cols if c not in df.columns]

    if missing_cols:
        st.error(f"File Excel đang thiếu cột: {missing_cols}")
        st.write("Các cột hiện có trong file:")
        st.write(list(df.columns))
        return

    # Chỉ lấy dòng có câu hỏi
    df = df[df["Câu hỏi"].astype(str).str.strip() != ""].reset_index(drop=True)

    if df.empty:
        st.error("File không có câu hỏi hợp lệ.")
        return

    def row_key(row):
        return "|".join([
            excel_quiz_clean(row.get("Trang", "")),
            excel_quiz_clean(row.get("Số câu", "")),
            normalize_quiz_key(row.get("Câu hỏi", "")),
            normalize_quiz_key(row.get("Đáp án", "")),
        ])

    # =========================
    # LỌC THEO TRANG
    # =========================
    full_df = df.copy()

    if "Trang" in full_df.columns:
        page_values = [
            excel_quiz_clean(x)
            for x in full_df["Trang"].tolist()
            if excel_quiz_clean(x)
        ]

        def page_sort_key(x):
            try:
                return (0, int(float(x)))
            except Exception:
                return (1, x)

        real_page_options = sorted(set(page_values), key=page_sort_key)
        page_options = ["Tất cả"] + real_page_options

        current_page_filter = st.session_state.get("excel_quiz_page_filter", ["Tất cả"])
        if isinstance(current_page_filter, str):
            current_page_filter = [current_page_filter]

        current_page_filter = [x for x in current_page_filter if x in page_options]

        if not current_page_filter:
            current_page_filter = ["Tất cả"]

        selected_pages = st.multiselect(
            "📄 Chọn trang để học",
            page_options,
            default=current_page_filter,
            key="excel_quiz_page_filter",
            help="Có thể chọn nhiều trang cùng lúc. Chọn 'Tất cả' để học toàn bộ câu hỏi."
        )

        if (not selected_pages) or ("Tất cả" in selected_pages):
            selected_pages_clean = ["Tất cả"]
            selected_base_df = full_df.reset_index(drop=True)
        else:
            selected_pages_clean = selected_pages
            selected_set = set(selected_pages_clean)
            selected_base_df = full_df[
                full_df["Trang"].astype(str).map(lambda x: excel_quiz_clean(x)).isin(selected_set)
            ].reset_index(drop=True)

        selected_page_label = "Tất cả" if selected_pages_clean == ["Tất cả"] else ", ".join(selected_pages_clean)

        st.caption(
            f"Đang chọn: {selected_page_label} | "
            f"Số câu theo trang: {len(selected_base_df)} / {len(full_df)}"
        )
    else:
        selected_pages_clean = ["Tất cả"]
        selected_page_label = "Tất cả"
        selected_base_df = full_df.reset_index(drop=True)
        st.warning("File Excel chưa có cột 'Trang', nên app sẽ học tất cả câu hỏi.")

    if selected_base_df.empty:
        st.warning("Các trang đang chọn không có câu hỏi hợp lệ.")
        return

    selected_base_df = selected_base_df.copy()
    selected_base_df["__source_index"] = range(len(selected_base_df))

    # =========================
    # CÀI ĐẶT HỌC TẬP
    # =========================
    with st.expander("⚙️ Cài đặt học tập", expanded=False):
        st.markdown("##### Lọc câu hỏi")
        filter_col1, filter_col2 = st.columns(2)

        with filter_col1:
            excel_only_unmastered = st.checkbox(
                "🎓 Chỉ học câu chưa thuộc",
                value=st.session_state.get("excel_quiz_only_unmastered", False),
                key="excel_quiz_only_unmastered",
                help="Câu trả lời đúng sẽ được xem là đã thuộc trong phiên hiện tại."
            )

        with filter_col2:
            mastered_count = len(st.session_state.get("excel_quiz_mastered_keys", set()))
            st.metric("Đã thuộc", mastered_count)

        st.markdown("##### Thứ tự và hành vi")
        behavior_col1, behavior_col2 = st.columns(2)

        with behavior_col1:
            excel_in_order = st.checkbox(
                "Học theo thứ tự (không xáo trộn)",
                value=st.session_state.get("excel_quiz_in_order", True),
                key="excel_quiz_in_order"
            )

            excel_shuffle_options = st.checkbox(
                "Trộn vị trí đáp án",
                value=st.session_state.get("excel_quiz_shuffle_options", False),
                key="excel_quiz_shuffle_options",
                help="Chỉ đổi vị trí hiển thị đáp án, không đổi đáp án đúng."
            )

        with behavior_col2:
            excel_auto_continue = st.checkbox(
                "Tự động tiếp tục khi trả lời đúng",
                value=st.session_state.get("excel_quiz_auto_continue", False),
                key="excel_quiz_auto_continue"
            )

        st.markdown("##### Loại câu hỏi")
        type_col1, type_col2 = st.columns(2)

        with type_col1:
            excel_fill_blank = st.checkbox(
                "Điền từ (Fill in the blank)",
                value=st.session_state.get("excel_quiz_fill_blank", False),
                key="excel_quiz_fill_blank"
            )

        with type_col2:
            excel_multiple_choice = st.checkbox(
                "Trắc nghiệm 4 đáp án",
                value=st.session_state.get("excel_quiz_multiple_choice", True),
                key="excel_quiz_multiple_choice"
            )

        action_col1, action_col2 = st.columns(2)

        with action_col1:
            if st.button("↻ Reset tiến độ học", key="excel_quiz_reset_progress", use_container_width=True):
                st.session_state.excel_quiz_mastered_keys = set()
                excel_quiz_reset(clear_wrong=True)
                st.rerun()

        with action_col2:
            if st.button("Áp dụng cài đặt", key="excel_quiz_apply_settings", type="primary", use_container_width=True):
                st.session_state.excel_quiz_settings_version += 1
                excel_quiz_reset(clear_wrong=True)
                st.rerun()

    if not (excel_fill_blank or excel_multiple_choice):
        st.warning("Hãy chọn ít nhất một loại câu hỏi.")
        return

    use_fill_blank = excel_fill_blank and not excel_multiple_choice

    if excel_fill_blank and excel_multiple_choice:
        st.info("Bạn đang bật cả 2 loại câu hỏi. App sẽ ưu tiên chế độ trắc nghiệm 4 đáp án.")

    # =========================
    # ÁP DỤNG LỌC CHƯA THUỘC
    # =========================
    quiz_base_df = selected_base_df.copy()

    if excel_only_unmastered:
        mastered_keys = st.session_state.get("excel_quiz_mastered_keys", set())
        quiz_base_df = quiz_base_df[
            ~quiz_base_df.apply(lambda r: row_key(r) in mastered_keys, axis=1)
        ].reset_index(drop=True)

        if quiz_base_df.empty:
            st.success("🎉 Bạn đã thuộc hết các câu trong phạm vi đang chọn.")
            if st.button("↻ Học lại toàn bộ phạm vi này", key="excel_quiz_learn_all_again", use_container_width=True):
                st.session_state.excel_quiz_mastered_keys = set()
                excel_quiz_reset(clear_wrong=True)
                st.rerun()
            return

    data_key = (
        f"{source_name}|{sheet_name}|{','.join(selected_pages_clean)}|"
        f"{len(quiz_base_df)}|{use_api_format}|{excel_only_unmastered}|{excel_in_order}|"
        f"{excel_shuffle_options}|{use_fill_blank}|{st.session_state.get('excel_quiz_settings_version', 0)}|"
        f"{'|'.join([c for c in quiz_base_df.columns if not str(c).startswith('__')])}"
    )

    if st.session_state.excel_quiz_data_key != data_key:
        st.session_state.excel_quiz_data_key = data_key
        excel_quiz_reset(clear_wrong=True)

    # Tạo thứ tự câu hỏi
    order_signature = data_key + f"|order|{len(quiz_base_df)}"
    if st.session_state.get("excel_quiz_order_signature") != order_signature:
        order = list(range(len(quiz_base_df)))

        if not excel_in_order:
            random.shuffle(order)

        st.session_state.excel_quiz_question_order = order
        st.session_state.excel_quiz_order_signature = order_signature
        st.session_state.excel_quiz_idx = 0
        st.session_state.excel_quiz_checked = False
        st.session_state.excel_quiz_selected = None

    order = st.session_state.get("excel_quiz_question_order", list(range(len(quiz_base_df))))
    order = [i for i in order if 0 <= i < len(quiz_base_df)]

    if len(order) != len(quiz_base_df):
        order = list(range(len(quiz_base_df)))
        if not excel_in_order:
            random.shuffle(order)
        st.session_state.excel_quiz_question_order = order

    st.success(
        f"Đã đọc Google Sheet | Sheet: {sheet_name} | "
        f"Đang học: {selected_page_label} | Số câu học: {len(quiz_base_df)}"
    )

    control_col1, control_col2, control_col3, control_col4 = st.columns(4)

    with control_col1:
        if st.button("🔄 Làm lại lượt này", key="excel_quiz_restart", use_container_width=True):
            excel_quiz_reset(clear_wrong=True)
            st.rerun()

    with control_col2:
        if st.button("❌ Học lại câu sai", key="excel_quiz_wrong_only", use_container_width=True):
            if st.session_state.excel_quiz_wrong_indices:
                st.session_state.excel_quiz_review_wrong_only = True
                st.session_state.excel_quiz_idx = 0
                st.session_state.excel_quiz_checked = False
                st.session_state.excel_quiz_selected = None
                st.rerun()
            else:
                st.warning("Hiện chưa có câu sai nào.")

    with control_col3:
        if st.button("📋 Hiện/ẩn dữ liệu", key="excel_quiz_toggle_data", use_container_width=True):
            st.session_state.excel_quiz_show_data = not st.session_state.excel_quiz_show_data
            st.rerun()

    with control_col4:
        if st.button("↩️ Thoát học lại sai", key="excel_quiz_exit_wrong", use_container_width=True):
            st.session_state.excel_quiz_review_wrong_only = False
            st.session_state.excel_quiz_idx = 0
            st.session_state.excel_quiz_checked = False
            st.session_state.excel_quiz_selected = None
            st.rerun()

    if st.session_state.excel_quiz_show_data:
        display_df = selected_base_df.drop(columns=["__source_index"], errors="ignore")
        st.dataframe(display_df, use_container_width=True)

    if st.session_state.excel_quiz_review_wrong_only:
        valid_wrong_indices = [
            i for i in st.session_state.excel_quiz_wrong_indices
            if isinstance(i, int) and 0 <= i < len(selected_base_df)
        ]

        if not valid_wrong_indices:
            st.success("Không còn câu sai để học lại.")
            return

        quiz_df = selected_base_df.iloc[valid_wrong_indices].reset_index(drop=True)
        st.warning(f"Đang học lại {len(quiz_df)} câu sai.")
    else:
        quiz_df = quiz_base_df.iloc[order].reset_index(drop=True)

    if st.session_state.excel_quiz_idx >= len(quiz_df):
        st.success("🎉 Bạn đã làm xong lượt quiz!")

        total_answered = len(st.session_state.excel_quiz_results)
        correct_count = sum(1 for v in st.session_state.excel_quiz_results.values() if v == "correct")
        wrong_count = len(st.session_state.excel_quiz_wrong_indices)

        metric_col1, metric_col2, metric_col3 = st.columns(3)
        metric_col1.metric("Đã làm", total_answered)
        metric_col2.metric("Đúng", correct_count)
        metric_col3.metric("Sai", wrong_count)

        if st.session_state.excel_quiz_wrong_indices:
            valid_wrong_indices = [
                i for i in st.session_state.excel_quiz_wrong_indices
                if isinstance(i, int) and 0 <= i < len(selected_base_df)
            ]
            wrong_df = selected_base_df.iloc[valid_wrong_indices].drop(columns=["__source_index"], errors="ignore").reset_index(drop=True)

            st.markdown("### Danh sách câu sai")
            st.dataframe(wrong_df, use_container_width=True)

        return

    row = quiz_df.iloc[st.session_state.excel_quiz_idx]
    real_idx = int(row.get("__source_index", st.session_state.excel_quiz_idx))

    st.markdown("---")
    st.markdown(f"### Câu {st.session_state.excel_quiz_idx + 1} / {len(quiz_df)}")

    page_no = excel_quiz_clean(row.get("Trang", ""))
    question_no = excel_quiz_clean(row.get("Số câu", ""))
    q_type = excel_quiz_clean(row.get("Dạng", ""))

    meta = []
    if page_no:
        meta.append(f"Trang {page_no}")
    if question_no:
        meta.append(f"Câu {question_no}")
    if q_type:
        meta.append(q_type)

    if meta:
        st.caption(" | ".join(meta))

    question_text = excel_quiz_clean(row.get("Câu hỏi", ""))
    question_display = excel_quiz_clean(row.get("Câu hỏi hiển thị", ""))

    if question_display:
        question_html = question_display
    else:
        question_html = html.escape(question_text)

    st.markdown(
        f"""
        <div class='quiz-box'>
            <div class='quiz-label'>Câu hỏi</div>
            <div class='quiz-question'>{question_html}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    options = excel_quiz_get_options(row)
    right_label = excel_quiz_correct_label(row)

    right_text = ""
    for label, text in options:
        if label == right_label:
            right_text = text
            break

    selected = None
    fill_blank_checked = False
    fill_blank_correct = False
    fill_blank_answer = ""

    if use_fill_blank:
        with st.form(f"excel_fill_form_{st.session_state.excel_quiz_idx}_{st.session_state.excel_quiz_review_wrong_only}"):
            fill_blank_answer = st.text_input(
                "Nhập đáp án đúng",
                placeholder="Có thể nhập số đáp án, ký hiệu đáp án hoặc nội dung đáp án..."
            )
            fill_blank_checked = st.form_submit_button("Kiểm tra", use_container_width=True)

        if fill_blank_checked:
            user_norm = normalize_quiz_key(fill_blank_answer)
            valid_norms = {
                normalize_quiz_key(right_label),
                normalize_quiz_key(right_text),
                normalize_quiz_key(excel_quiz_clean(row.get("Đáp án", ""))),
                normalize_quiz_key(excel_quiz_clean(row.get("Đáp án đúng", ""))),
            }

            fill_blank_correct = bool(user_norm and user_norm in valid_norms)

            st.session_state.excel_quiz_selected = fill_blank_answer
            st.session_state.excel_quiz_checked = True

            if fill_blank_correct:
                selected = right_label
            else:
                selected = "__wrong_fill_blank__"
    else:
        display_options = list(options)

        if excel_shuffle_options:
            shuffle_key = f"{data_key}|{real_idx}|{st.session_state.excel_quiz_idx}|options"
            rnd = random.Random(shuffle_key)
            rnd.shuffle(display_options)

        option_container = st.container()
        with option_container:
            st.markdown("<div id='excel-quiz-answer-scope'></div>", unsafe_allow_html=True)

            for idx, (label, text) in enumerate(display_options, start=1):
                btn_col1, btn_col2 = st.columns([1, 12])

                with btn_col1:
                    st.markdown(f"<div class='quiz-num'>{idx}</div>", unsafe_allow_html=True)

                with btn_col2:
                    if st.button(
                        text,
                        key=f"excel_quiz_opt_{st.session_state.excel_quiz_idx}_{idx}_{label}_{st.session_state.excel_quiz_review_wrong_only}",
                        use_container_width=True
                    ):
                        selected = label

    if selected is not None:
        st.session_state.excel_quiz_checked = True

        if selected != "__wrong_fill_blank__":
            st.session_state.excel_quiz_selected = selected

        current_row_key = row_key(row)

        if selected == right_label:
            st.session_state.excel_quiz_results[real_idx] = "correct"
            st.session_state.excel_quiz_mastered_keys.add(current_row_key)

            if excel_auto_continue:
                st.session_state.excel_quiz_idx += 1
                st.session_state.excel_quiz_checked = False
                st.session_state.excel_quiz_selected = None
        else:
            st.session_state.excel_quiz_results[real_idx] = "wrong"
            if real_idx not in st.session_state.excel_quiz_wrong_indices:
                st.session_state.excel_quiz_wrong_indices.append(real_idx)

        st.rerun()

    if st.session_state.excel_quiz_checked and st.session_state.excel_quiz_selected is not None:
        selected_value = st.session_state.excel_quiz_selected

        if selected_value == right_label or normalize_quiz_key(selected_value) == normalize_quiz_key(right_text):
            st.success("✅ Đúng rồi!")
        else:
            st.error(f"❌ Sai. Đáp án đúng là: {right_label} {right_text}")

        translation = excel_quiz_clean(row.get("Dịch nghĩa", ""))
        explanation = excel_quiz_clean(row.get("Giải thích ngắn", ""))

        if translation:
            with st.expander("📌 Dịch nghĩa"):
                st.write(translation)

        if explanation:
            with st.expander("💡 Giải thích"):
                st.write(explanation)

        if st.button("➡️ Câu tiếp theo", key="excel_quiz_next", use_container_width=True):
            st.session_state.excel_quiz_idx += 1
            st.session_state.excel_quiz_checked = False
            st.session_state.excel_quiz_selected = None
            st.rerun()

    total_answered = len(st.session_state.excel_quiz_results)
    correct_count = sum(1 for v in st.session_state.excel_quiz_results.values() if v == "correct")
    wrong_count = len(st.session_state.excel_quiz_wrong_indices)
    mastered_count = len(st.session_state.get("excel_quiz_mastered_keys", set()))

    st.markdown("---")
    st.caption(
        f"Đã làm: {total_answered} | Đúng: {correct_count} | Sai: {wrong_count} | Đã thuộc: {mastered_count}"
    )


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
    "quiz_show_detail": False,
    "quiz_wrong_queue": [],
    "quiz_wrong_keys": set(),
    "quiz_since_wrong_review": 0,
    "quiz_is_review": False,
    "quiz_seen_keys": set(),
    "quiz_review_count": 0,
    "quiz_completed": False,
    "quiz_last_option_orders": {},
    "quiz_mastered_keys": set(),
    "quiz_settings_version": 0,
    "quiz_attempt_stats": {},
    "quiz_history": [],
    "quiz_history_saved": False,
    "quiz_retry_only_keys": set(),
    "speaking_i": 0,
    "speaking_cards_order": [],
    "speaking_last_text": "",
    "speaking_last_score": None,
    "learn_show_answer": False,
    "editor_cards": [],
    "editor_data_key": "",
    "editor_i": 0,
    "applied_cards": [],
    "applied_data_key": "",

    # Tab Quiz từ Excel
    "excel_quiz_idx": 0,
    "excel_quiz_checked": False,
    "excel_quiz_selected": None,
    "excel_quiz_results": {},
    "excel_quiz_wrong_indices": [],
    "excel_quiz_review_wrong_only": False,
    "excel_quiz_data_key": "",
    "excel_quiz_show_data": False,
    "excel_quiz_page_filter": ["Tất cả"],

    # Cài đặt học tập cho tab Quiz từ Excel
    "excel_quiz_only_unmastered": False,
    "excel_quiz_in_order": True,
    "excel_quiz_auto_continue": False,
    "excel_quiz_shuffle_options": False,
    "excel_quiz_fill_blank": False,
    "excel_quiz_multiple_choice": True,
    "excel_quiz_mastered_keys": set(),
    "excel_quiz_question_order": [],
    "excel_quiz_order_signature": "",
    "excel_quiz_settings_version": 0,
    "excel_quiz_google_url": DEFAULT_EXCEL_QUIZ_GOOGLE_SHEET_URL,
    "excel_quiz_use_google_api_format": False,
    "excel_quiz_google_api_key": load_saved_google_api_key(),
}.items():
    if k not in st.session_state:
        st.session_state[k] = v


if st.session_state.folder_no not in st.session_state.folder_learn_count:
    st.session_state.folder_learn_count[st.session_state.folder_no] = 1


st.markdown(
    '<div class="main-title" style="text-align:center; transform: translateX(-3cm);">Tiên học lễ, hậu học han cúc co</div>',
    unsafe_allow_html=True
)

st.caption("BẢN V14 - CÓ TỔNG KẾT QUIZ THEO VÒNG: sau khi hoàn thành sẽ hiện Vòng 1, Vòng 2, sai 1 lần/sai 2 lần và nút học lại từ sai.")


with st.sidebar:
    st.header("1) Nguồn dữ liệu")

    source = st.radio("Chọn nguồn", ["Google Sheets link", "Upload file"])

    google_url = ""
    sheet_name = ""
    uploaded = None

    if source == "Google Sheets link":
        saved_sheet_choice = st.selectbox(
            "Chọn Google Sheet đã lưu",
            list(SAVED_GOOGLE_SHEETS) + ["Link khác"],
            index=0,
            key="saved_google_sheet_choice"
        )

        if saved_sheet_choice == "Link khác":
            sheet_name = st.text_input("Tên sheet", value="nhaplieu")
            google_url = st.text_input(
                "Dán link Google Sheets",
                value=DEFAULT_GOOGLE_SHEET_URL
            )
        else:
            sheet_name = saved_sheet_choice
            google_url = SAVED_GOOGLE_SHEETS[saved_sheet_choice]
            st.success(f"Đã chọn: {saved_sheet_choice}")
            st.caption(google_url)

        st.info("Share Google Sheets: Anyone with the link → Viewer.")
    else:
        uploaded = st.file_uploader("Upload Excel/CSV", type=["xlsx", "xlsm", "csv"])

    st.header("2) Chọn cột")
    st.caption("Ví dụ của bạn: C = ngữ pháp ban đầu, F hoặc H = từ đồng nghĩa.")

    if source == "Google Sheets link" and saved_sheet_choice != "Link khác":
        column_profile_name = saved_sheet_choice
        column_defaults = SAVED_SHEET_COLUMNS[saved_sheet_choice]
    elif source == "Google Sheets link":
        column_profile_name = "custom_link"
        column_defaults = {"kr": "", "vi": "", "detail": "", "synonym": ""}
    else:
        column_profile_name = "uploaded_file"
        column_defaults = {"kr": "", "vi": "", "detail": "", "synonym": ""}

    kr_col = st.text_input(
        "Cột tiếng Hàn / ngữ pháp ban đầu",
        value=column_defaults["kr"],
        key=f"kr_col_v2_{column_profile_name}"
    )
    vi_col = st.text_input(
        "Cột nghĩa tiếng Việt",
        value=column_defaults["vi"],
        key=f"vi_col_v2_{column_profile_name}"
    )
    detail_col = st.text_input(
        "Cột giải thích / ví dụ",
        value=column_defaults["detail"],
        key=f"detail_col_v2_{column_profile_name}"
    )
    synonym_col = st.text_input(
        "Cột từ đồng nghĩa / đáp án thay thế",
        value=column_defaults["synonym"],
        key=f"synonym_col_v2_{column_profile_name}"
    )

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
    apply_data = st.button("Áp dụng", type="primary", use_container_width=True)


try:
    if apply_data:
        df = None
        read_google_sheet.clear()
        read_uploaded_file.clear()

        if source == "Google Sheets link":
            if not google_url.strip():
                st.sidebar.error("Bạn cần dán link Google Sheets trước.")
                st.stop()

            with st.spinner("Đang tải Google Sheets..."):
                df = read_google_sheet(google_url.strip(), sheet_name.strip())

        elif source == "Upload file":
            if uploaded is None:
                st.sidebar.error("Bạn cần upload file trước.")
                st.stop()

            with st.spinner("Đang đọc file..."):
                df = read_uploaded_file(uploaded)

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

        st.session_state.applied_cards = loaded_cards
        st.session_state.applied_data_key = data_key
        restore_starred_state(st.session_state.applied_cards, data_key)
        st.session_state.folder_no = 1
        st.session_state.card_i = 0
        st.session_state.show_answer = False
        st.session_state.write_cards_order = []
        st.session_state.quiz_q = None
        st.session_state.quiz_options = []
        st.session_state.quiz_last_result = None
        st.session_state.quiz_wrong_queue = []
        st.session_state.quiz_wrong_keys = set()
        st.session_state.quiz_since_wrong_review = 0
        st.session_state.quiz_is_review = False
        st.session_state.quiz_seen_keys = set()
        st.session_state.quiz_review_count = 0
        st.session_state.quiz_completed = False
        st.session_state.quiz_last_option_orders = {}
        st.session_state.quiz_mastered_keys = set()
        st.session_state.quiz_attempt_stats = {}
        st.session_state.quiz_history = []
        st.session_state.quiz_history_saved = False
        st.session_state.quiz_retry_only_keys = set()
        st.session_state.speaking_cards_order = []
        if "learn_card" in st.session_state:
            del st.session_state["learn_card"]

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

    if not st.session_state.applied_cards:
        st.warning("Hãy chọn nguồn dữ liệu, nhập cột cần dùng rồi bấm Áp dụng để bắt đầu. Hoặc dùng ngay mục Quiz từ Excel bên dưới.")
        render_excel_quiz_tab()
        st.stop()

    cards_all = st.session_state.applied_cards
    stats = make_stats(cards_all)

    total = len(cards_all)
    total_folders = max(1, math.ceil(total / folder_size))

    if st.session_state.folder_no > total_folders:
        st.session_state.folder_no = 1

    all_quiz_count_rows = quiz_count_rows(cards_all)
    quiz_card_count = cached_quiz_entry_count(
        all_quiz_count_rows,
        all_quiz_count_rows
    )

    st.success(
        f"Đã tạo {total:,} thẻ. "
        f"Đã chia thành {total_folders} thư mục, mỗi thư mục {folder_size} từ."
    )

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Thẻ đã tạo", f"{stats['cards']:,}")
    c2.metric("Thiếu nghĩa", f"{stats['missing_vi']:,}")
    c3.metric("Thiếu giải thích", f"{stats['missing_detail']:,}")
    c4.metric("Thiếu đồng nghĩa", f"{stats['missing_synonyms']:,}")
    c5.metric("Bỏ qua vì thiếu tiếng Hàn", f"{stats['skipped_no_kr']:,}")
    c6.metric("Số quiz", f"{quiz_card_count:,}")

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
    folder_quiz_card_count = cached_quiz_entry_count(
        quiz_count_rows(cards),
        all_quiz_count_rows
    )

    st.info(
        f"Đang học: Bộ {st.session_state.folder_no:03d} | "
        f"từ {start_num}–{end_num} | {len(cards)} thẻ | {folder_quiz_card_count} quiz"
    )

    tab_input, tab_folder, tab_starred, tab_flash, tab_write, tab_learn, tab_quiz, tab_excel_quiz, tab_speaking, tab_match, tab_search, tab_data = st.tabs([
        "✍️ Nhập thẻ",
        "📁 Thư mục",
        "⭐ Đã gắn sao",
        "📚 Flashcard",
        "⌨️ Gõ văn bản",
        "🎓 Học",
        "📝 Quiz",
        "📘 Quiz từ Excel",
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

    with tab_starred:
        st.subheader("⭐ Đã gắn sao — Tất cả bộ")

        folder_options = ["Tất cả bộ"] + [f"Bộ {i:03d}" for i in range(1, total_folders + 1)]
        folder_choice = st.selectbox("Lọc theo bộ", folder_options, index=0, key="starred_folder_filter")
        selected_folder = None if folder_choice == "Tất cả bộ" else int(folder_choice.split()[1])

        starred_cards = []
        for idx, card in enumerate(cards_all):
            if not card.get("starred"):
                continue

            folder_no = (idx // folder_size) + 1
            if selected_folder is None or folder_no == selected_folder:
                starred_cards.append((card, folder_no))

        if not starred_cards:
            st.info("Chưa có thẻ nào được gắn sao.")
        else:
            for card, folder_no in starred_cards:
                synonym_html = (
                    f"<div class='synonyms'><b>Đồng nghĩa:</b><br>{html.escape(card.get('synonyms', ''))}</div>"
                    if card.get("synonyms") else ""
                )

                star_label = "⭐" if card.get("starred") else "☆"
                if st.button(star_label, key=f"starred_list_{card.get('stt')}", help="Bỏ dấu sao thẻ này"):
                    card["starred"] = not card.get("starred", False)

                    persist_starred_state(st.session_state.applied_cards, st.session_state.applied_data_key)
                    st.rerun()

                st.markdown(
                    f"<div class='card'>"
                    f"<div class='small'>Bộ {folder_no:03d}</div>"
                    f"<div class='korean'>{html.escape(card.get('kr', ''))}</div>"
                    f"<div class='meaning'>{html.escape(card.get('vi', ''))}</div>"
                    f"{synonym_html}"
                    f"<div class='detail'>{html.escape(card.get('detail', ''))}</div>"
                    f"</div>",
                    unsafe_allow_html=True
                )
                st.markdown("<hr>", unsafe_allow_html=True)

    with tab_flash:
        st.subheader(f"📚 Flashcard — Bộ {st.session_state.folder_no:03d}")

        i = st.session_state.card_i % len(cards)
        card = cards[i]

        st.markdown(f"### Thẻ {i + 1}/{len(cards)}")

        synonym_html = (
            f"<div class='synonyms'><b>Đồng nghĩa:</b><br>{html.escape(card.get('synonyms', ''))}</div>"
            if card.get("synonyms") else ""
        )

        star_label = "⭐" if card.get("starred") else "☆"

        if st.button(star_label, key=f"star_card_{card.get('stt')}_{st.session_state.folder_no}", help="Gắn / bỏ dấu sao thẻ này"):
            card["starred"] = not card.get("starred", False)
            persist_starred_state(st.session_state.applied_cards, st.session_state.applied_data_key)
            st.rerun()

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
        st.info("✅ Bản V14: Sau khi làm xong lượt quiz, phần tổng kết theo Vòng sẽ hiện ngay bên dưới.")

        with st.expander("⚙️ Cài đặt học tập", expanded=False):
            st.markdown("##### Chế độ trả lời")
            setting_col1, setting_col2 = st.columns(2)
            with setting_col1:
                quiz_kr_to_vi = st.checkbox(
                    "Hỏi tiếng Hàn, trả lời tiếng Việt",
                    value=True,
                    key="quiz_kr_to_vi"
                )
                quiz_vi_to_kr = st.checkbox(
                    "Hỏi tiếng Việt, trả lời tiếng Hàn",
                    value=False,
                    key="quiz_vi_to_kr"
                )
            with setting_col2:
                quiz_synonym_mode = st.checkbox(
                    "Trả lời bằng từ đồng nghĩa",
                    value=False,
                    key="quiz_synonym_mode"
                )
                quiz_accept_synonyms = st.checkbox(
                    "Chấp nhận từ đồng nghĩa làm đáp án",
                    value=True,
                    key="quiz_accept_synonyms"
                )

            st.markdown("##### Lọc từ vựng")
            filter_col1, filter_col2 = st.columns(2)
            with filter_col1:
                only_starred = st.checkbox(
                    "⭐ Chỉ học từ đánh dấu sao",
                    value=False,
                    key="quiz_only_starred"
                )
            with filter_col2:
                only_unmastered = st.checkbox(
                    "🎓 Chỉ học từ chưa thuộc",
                    value=False,
                    key="quiz_only_unmastered"
                )

            st.markdown("##### Thứ tự và hành vi")
            behavior_col1, behavior_col2 = st.columns(2)
            with behavior_col1:
                quiz_in_order = st.checkbox(
                    "Học theo thứ tự (không xáo trộn)",
                    value=False,
                    key="quiz_in_order"
                )
            with behavior_col2:
                quiz_auto_continue = st.checkbox(
                    "Tự động tiếp tục khi trả lời đúng",
                    value=True,
                    key="quiz_auto_continue"
                )

            st.markdown("##### Loại câu hỏi")
            type_col1, type_col2 = st.columns(2)
            with type_col1:
                quiz_fill_blank = st.checkbox(
                    "Điền từ (Fill in the blank)",
                    value=False,
                    key="quiz_fill_blank"
                )
            with type_col2:
                quiz_multiple_choice = st.checkbox(
                    "Trắc nghiệm 4 đáp án",
                    value=True,
                    key="quiz_multiple_choice"
                )

            action_col1, action_col2 = st.columns(2)
            with action_col1:
                if st.button("↻ Reset tiến độ học", key="quiz_reset_progress", use_container_width=True):
                    reset_quiz(clear_mastered=True)
                    st.rerun()
            with action_col2:
                if st.button("Áp dụng cài đặt", key="quiz_apply_settings", type="primary", use_container_width=True):
                    reset_quiz()
                    st.session_state.quiz_settings_version += 1
                    st.rerun()

        quiz_settings_signature = (
            "quiz_answers_v5",
            quiz_kr_to_vi,
            quiz_vi_to_kr,
            quiz_synonym_mode,
            quiz_accept_synonyms,
            only_starred,
            only_unmastered,
            quiz_in_order,
            quiz_auto_continue,
            quiz_fill_blank,
            quiz_multiple_choice,
        )

        if st.session_state.get("quiz_active_settings_signature") != quiz_settings_signature:
            st.session_state.quiz_active_settings_signature = quiz_settings_signature
            reset_quiz()

        if not (quiz_kr_to_vi or quiz_vi_to_kr or quiz_synonym_mode):
            st.warning("Hãy chọn ít nhất một chế độ trả lời.")

        if not (quiz_fill_blank or quiz_multiple_choice):
            st.warning("Hãy chọn ít nhất một loại câu hỏi.")

        quiz_source = [card for card in cards if card.get("starred")] if only_starred else list(cards)
        all_term_norms_for_quiz = build_all_term_norms(cards_all)
        valid_for_quiz = []
        seen_quiz_entries = set()
        seen_synonym_answer_keys = set()

        def append_quiz_entry(card, question, answer, correct_variants, direction):
            question = clean_text(question)
            answer = clean_text(answer)
            correct_variants = unique_by_quiz_key(
                [x for x in correct_variants if clean_text(x)] + [answer]
            )

            if not question or not answer or normalize_quiz_key(question) == normalize_quiz_key(answer):
                return

            entry_key = (
                direction
                + "|"
                + normalize_quiz_key(question)
                + "|"
                + normalize_quiz_key(answer)
            )

            retry_only_keys = st.session_state.get("quiz_retry_only_keys", set())
            if retry_only_keys and entry_key not in retry_only_keys:
                return

            if entry_key in seen_quiz_entries:
                return

            if only_unmastered and entry_key in st.session_state.get("quiz_mastered_keys", set()):
                return

            entry = {
                "card": card,
                "question": question,
                "answer": answer,
                "correct_variants": correct_variants,
                "direction": direction,
                "key": entry_key,
            }

            seen_quiz_entries.add(entry_key)
            valid_for_quiz.append(entry)
        for source_card in quiz_source:
            kr_text = clean_text(source_card.get("kr", ""))
            synonym_answers = split_answer_parts(source_card.get("synonyms", ""))

            if quiz_kr_to_vi:
                primary_vi_answers = split_answer_parts(source_card.get("vi", ""))
                primary_vi_answers = [
                    answer for answer in primary_vi_answers
                    if clean_text(answer) and clean_text(answer) != "Chưa có nghĩa"
                ]

                # Chỉ sheet không có cột nghĩa được cấu hình mới dùng cột G
                # làm nguồn đáp án thay thế. Với các sheet có cột nghĩa như
                # "ngu phap", Hàn -> Việt phải chỉ lấy đúng cột nghĩa E.
                if not primary_vi_answers and not clean_text(vi_col):
                    primary_vi_answers = list(synonym_answers)

                accepted_vi = list(primary_vi_answers)
                if primary_vi_answers:
                    # Mỗi thẻ chỉ tạo một câu Hàn -> Việt.
                    # Nếu thẻ có nhiều nghĩa trên nhiều dòng, nghĩa đầu tiên
                    # được hiển thị trong lựa chọn; các nghĩa còn lại vẫn
                    # được chấp nhận là đáp án đúng.
                    append_quiz_entry(
                        source_card,
                        kr_text,
                        primary_vi_answers[0],
                        accepted_vi,
                        "kr_to_vi"
                    )

            if quiz_vi_to_kr:
                vi_question = clean_text(source_card.get("vi", ""))
                accepted_kr = [kr_text] + (synonym_answers if quiz_accept_synonyms else [])
                if vi_question and vi_question != "Chưa có nghĩa":
                    append_quiz_entry(source_card, vi_question, kr_text, accepted_kr, "vi_to_kr")

            if quiz_synonym_mode:
                filtered_synonym_answers = answer_variants_for_card_filtered(
                    source_card,
                    all_term_norms_for_quiz
                )

                for answer in filtered_synonym_answers:
                    answer_key = normalize_quiz_key(answer)

                    # Chế độ từ đồng nghĩa tính mỗi đáp án duy nhất một lần
                    # trong cả bộ, đồng thời loại đáp án trùng với cột câu hỏi.
                    if not answer_key or answer_key in seen_synonym_answer_keys:
                        continue

                    seen_synonym_answer_keys.add(answer_key)
                    append_quiz_entry(
                        source_card,
                        kr_text,
                        answer,
                        filtered_synonym_answers,
                        "synonym"
                    )

        if only_starred:
            st.info(f"Đang quiz {len(quiz_source)} thẻ đã gắn sao trong Bộ {st.session_state.folder_no:03d}.")

        if st.session_state.get("quiz_retry_only_keys"):
            st.warning(f"🔁 Đang ở chế độ học lại {len(st.session_state.quiz_retry_only_keys)} câu đã từng sai.")
            if st.button("Thoát chế độ học lại từ sai", key="quiz_exit_retry_only", use_container_width=True):
                reset_quiz(clear_mastered=True, clear_attempts=True, clear_retry_filter=True)
                st.rerun()

        mastered_count = len(st.session_state.get("quiz_mastered_keys", set()))
        st.caption(f"🎓 Đã thuộc trong phiên này: {mastered_count} câu.")

        # Khi học lại chỉ các câu sai, có thể chỉ còn 1–3 câu.
        # Vì vậy không ép phải đủ 4 đáp án, tránh lỗi "Cần ít nhất 4 đáp án".
        retry_mode_active = bool(st.session_state.get("quiz_retry_only_keys"))
        minimum_answers = 1 if retry_mode_active else (4 if quiz_multiple_choice else 1)

        if len(valid_for_quiz) < minimum_answers:
            st.warning(f"Cần ít nhất {minimum_answers} câu hỏi hợp lệ với cài đặt hiện tại.")
        else:
            def pick_one_answer(card):
                answers = answer_variants_for_card_filtered(card, all_term_norms_for_quiz)
                answers = [x for x in answers if clean_text(x)]

                if not answers:
                    return ""

                return random.choice(answers)

            def quiz_entry_key(entry):
                return (
                    entry.get("direction", "kr_to_vi")
                    + "|"
                    + normalize_quiz_key(entry.get("question", entry["card"].get("kr", "")))
                    + "|"
                    + normalize_quiz_key(entry.get("answer", ""))
                )

            def get_quiz_summary_rows():
                rows = []
                stats = st.session_state.get("quiz_attempt_stats", {})

                for item in stats.values():
                    attempt_count = int(item.get("attempt_count", 0) or 0)

                    if attempt_count <= 0:
                        continue

                    rows.append({
                        "key": item.get("key", ""),
                        "Câu hỏi": item.get("question", ""),
                        "Đáp án đúng": item.get("answer", ""),
                        "Bạn chọn gần nhất": item.get("last_selected", ""),
                        "Số lần sai": int(item.get("wrong_count", 0) or 0),
                        "Số lần đúng": int(item.get("correct_count", 0) or 0),
                        "Tổng lần trả lời": attempt_count,
                        "Kết quả gần nhất": item.get("last_result", ""),
                        "Chi tiết / ví dụ": item.get("detail", ""),
                    })

                rows.sort(key=lambda x: (-x["Số lần sai"], x["Câu hỏi"]))
                return rows

            def make_quiz_history_item(total_quiz, regular_done, review_done):
                rows = get_quiz_summary_rows()
                wrong_rows = [r for r in rows if r["Số lần sai"] > 0]

                return {
                    "finished_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "folder_no": st.session_state.folder_no,
                    "total_questions": total_quiz,
                    "regular_done": regular_done,
                    "review_done": review_done,
                    "answered_terms": len(rows),
                    "wrong_terms": len(wrong_rows),
                    "wrong_once": sum(1 for r in wrong_rows if r["Số lần sai"] == 1),
                    "wrong_twice": sum(1 for r in wrong_rows if r["Số lần sai"] == 2),
                    "wrong_three_plus": sum(1 for r in wrong_rows if r["Số lần sai"] >= 3),
                    "wrong_total_attempts": sum(r["Số lần sai"] for r in wrong_rows),
                    "rows": rows,
                }

            def save_quiz_history_once(total_quiz, regular_done, review_done):
                if st.session_state.get("quiz_history_saved"):
                    return

                item = make_quiz_history_item(total_quiz, regular_done, review_done)

                if item["answered_terms"] > 0:
                    st.session_state.quiz_history.append(item)

                st.session_state.quiz_history_saved = True

            def start_retry_from_wrong_keys(wrong_keys):
                wrong_keys = set(wrong_keys or [])

                if not wrong_keys:
                    return

                # Gắn sao các thẻ sai để dễ xem lại trong tab Đã gắn sao.
                for entry in valid_for_quiz:
                    if quiz_entry_key(entry) in wrong_keys:
                        entry.get("card", {})["starred"] = True

                persist_starred_state(st.session_state.applied_cards, st.session_state.applied_data_key)
                st.session_state.quiz_retry_only_keys = set(wrong_keys)
                reset_quiz(clear_mastered=True, clear_attempts=True, clear_retry_filter=False)
                st.rerun()

            def start_retry_all_questions():
                reset_quiz(clear_mastered=True, clear_attempts=True, clear_retry_filter=True)
                st.rerun()

            def render_one_quiz_round_card(item, round_index, show_buttons=True):
                rows = item.get("rows", []) or []
                total_rows = len(rows)
                correct_rows = [row for row in rows if int(row.get("Số lần sai", 0) or 0) == 0]
                wrong_rows = [row for row in rows if int(row.get("Số lần sai", 0) or 0) > 0]
                wrong_keys = {row.get("key", "") for row in wrong_rows if row.get("key")}
                percent = round((len(correct_rows) / total_rows) * 100) if total_rows else 0

                html_rows = []
                for row in rows:
                    wrong_count = int(row.get("Số lần sai", 0) or 0)
                    ok = wrong_count == 0
                    icon = "✓" if ok else "×"
                    icon_color = "#22c55e" if ok else "#ff6b4a"
                    question = html.escape(str(row.get("Câu hỏi", "")))
                    answer = html.escape(str(row.get("Đáp án đúng", "")))
                    note = "" if ok else f"<span style='font-size:13px;color:#fca5a5;margin-left:10px;'>sai {wrong_count} lần</span>"
                    html_rows.append(
                        f"""
                        <div style="display:grid;grid-template-columns:44px 1fr 1fr;gap:12px;align-items:center;padding:14px 8px;">
                            <div style="color:{icon_color};font-size:24px;font-weight:900;text-align:center;">{icon}</div>
                            <div style="font-size:18px;color:#f8fafc;">{question}{note}</div>
                            <div style="font-size:18px;color:#f8fafc;">{answer}</div>
                        </div>
                        """
                    )

                rows_html = "\n".join(textwrap.dedent(row).strip() for row in html_rows) if html_rows else "<div style='color:#94a3b8;padding:16px;'>Chưa có dữ liệu.</div>"

                st.markdown(
                    textwrap.dedent(f"""
                    <div style="background:#171a24;border-radius:4px;padding:30px 36px;margin:12px 0 10px 0;border:1px solid #242838;">
                        <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:20px;">
                            <div>
                                <div style="font-size:28px;font-weight:900;color:#ffffff;margin-bottom:4px;">Vòng {round_index}</div>
                                <div style="font-size:20px;font-weight:900;color:#ffffff;">{len(correct_rows)}/{total_rows} - {percent}%</div>
                            </div>
                            <div style="font-size:14px;color:#94a3b8;text-align:right;">
                                Sai 1 lần: <b>{item.get('wrong_once', 0)}</b><br>
                                Sai 2 lần: <b>{item.get('wrong_twice', 0)}</b><br>
                                Sai ≥3 lần: <b>{item.get('wrong_three_plus', 0)}</b>
                            </div>
                        </div>
                        <div style="height:18px;"></div>
                        {rows_html}
                    </div>
                    """).strip(),
                    unsafe_allow_html=True
                )

                if show_buttons:
                    b1, b2, b3 = st.columns([2, 2, 5])
                    with b1:
                        if st.button("Bắt đầu lại", key=f"quiz_restart_round_{round_index}", use_container_width=True):
                            start_retry_all_questions()
                    with b2:
                        if st.button(
                            "⭐ Học lại các từ sai",
                            key=f"quiz_retry_wrong_round_{round_index}",
                            use_container_width=True,
                            disabled=not bool(wrong_keys)
                        ):
                            start_retry_from_wrong_keys(wrong_keys)

            def render_quiz_round_history_cards():
                history = st.session_state.get("quiz_history", [])

                if not history:
                    return

                st.markdown("### 📚 Kết quả theo vòng")
                st.caption("Dấu × là câu bạn từng chọn sai trong vòng đó. Bấm ⭐ Học lại các từ sai để app chỉ hỏi lại những câu sai.")

                for idx, item in enumerate(history, start=1):
                    render_one_quiz_round_card(item, idx, show_buttons=True)

            def render_quiz_history():
                # Giữ tên hàm cũ để các phần khác của code vẫn gọi được,
                # nhưng đổi cách hiển thị thành dạng Vòng 1, Vòng 2 như mẫu.
                render_quiz_round_history_cards()

            def record_quiz_attempt(entry, selected_option, ok):
                if not entry:
                    return

                key = quiz_entry_key(entry)

                if not key:
                    return

                if "quiz_attempt_stats" not in st.session_state or not isinstance(st.session_state.quiz_attempt_stats, dict):
                    st.session_state.quiz_attempt_stats = {}

                card = entry.get("card", {})
                stats = st.session_state.quiz_attempt_stats
                item = stats.get(key, {
                    "key": key,
                    "question": entry.get("question", ""),
                    "answer": entry.get("answer", ""),
                    "correct_variants": list(entry.get("correct_variants", [])),
                    "direction": entry.get("direction", ""),
                    "kr": card.get("kr", ""),
                    "vi": card.get("vi", ""),
                    "detail": card.get("detail", ""),
                    "synonyms": card.get("synonyms", ""),
                    "wrong_count": 0,
                    "correct_count": 0,
                    "attempt_count": 0,
                    "last_selected": "",
                    "last_result": "",
                    "last_time": "",
                })

                item["attempt_count"] = int(item.get("attempt_count", 0) or 0) + 1

                if ok:
                    item["correct_count"] = int(item.get("correct_count", 0) or 0) + 1
                    item["last_result"] = "Đúng"
                else:
                    item["wrong_count"] = int(item.get("wrong_count", 0) or 0) + 1
                    item["last_result"] = "Sai"

                item["last_selected"] = clean_text(selected_option)
                item["last_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                stats[key] = item

            def render_quiz_completion_summary(total_quiz, regular_done, review_done):
                save_quiz_history_once(total_quiz, regular_done, review_done)
                history = st.session_state.get("quiz_history", [])

                if not history:
                    st.info("Chưa có dữ liệu tổng kết.")
                    return

                last_item = history[-1]
                rows = last_item.get("rows", []) or []
                wrong_rows = [row for row in rows if int(row.get("Số lần sai", 0) or 0) > 0]
                total_answered = len(rows)
                correct_terms = total_answered - len(wrong_rows)
                percent = round((correct_terms / total_answered) * 100) if total_answered else 0

                st.markdown("### 📊 Tổng kết lượt quiz")
                m1, m2, m3, m4, m5 = st.columns(5)
                m1.metric("Điểm", f"{correct_terms}/{total_answered}")
                m2.metric("Tỉ lệ đúng", f"{percent}%")
                m3.metric("Từ bị sai", len(wrong_rows))
                m4.metric("Sai 1 lần", last_item.get("wrong_once", 0))
                m5.metric("Sai ≥2 lần", int(last_item.get("wrong_twice", 0) or 0) + int(last_item.get("wrong_three_plus", 0) or 0))

                render_quiz_round_history_cards()
            def add_wrong_review(entry):
                """
                Nếu trả lời sai, đưa câu đó vào hàng chờ ôn lại.
                Câu sai sẽ được hỏi thêm 1 lần nữa sau khoảng 5 câu thường.
                Nếu lần ôn lại vẫn sai, nó sẽ tiếp tục được đưa lại vào hàng chờ.
                """
                key = quiz_entry_key(entry)

                if not key:
                    return

                if "quiz_wrong_keys" not in st.session_state or not isinstance(st.session_state.quiz_wrong_keys, set):
                    st.session_state.quiz_wrong_keys = set(st.session_state.get("quiz_wrong_keys", []))

                if key in st.session_state.quiz_wrong_keys:
                    return

                st.session_state.quiz_wrong_keys.add(key)
                st.session_state.quiz_wrong_queue.append(dict(entry))

            def get_next_quiz_entry():
                """
                V6 - Quizlet-style nhưng KHÔNG chạy quá vô hạn.

                Cách hoạt động:
                1) Câu thường: mỗi đáp án hợp lệ chỉ hỏi 1 lần trong lượt hiện tại.
                2) Nếu sai: đưa vào hàng chờ ôn lại.
                3) Sau khoảng 3 câu thường, app hỏi lại câu sai.
                4) Khi đã hỏi hết câu thường và không còn câu sai chờ ôn lại -> dừng quiz.
                """
                if "quiz_seen_keys" not in st.session_state or not isinstance(st.session_state.quiz_seen_keys, set):
                    st.session_state.quiz_seen_keys = set(st.session_state.get("quiz_seen_keys", []))

                wrong_queue = st.session_state.get("quiz_wrong_queue", [])
                since_review = st.session_state.get("quiz_since_wrong_review", 0)

                # Ưu tiên hỏi lại câu sai sau 5 câu thường.
                # Nếu đã hết câu thường thì hỏi luôn câu sai còn tồn lại.
                remaining_regular = [
                    entry for entry in valid_for_quiz
                    if quiz_entry_key(entry) not in st.session_state.quiz_seen_keys
                ]

                should_review_now = bool(wrong_queue) and (since_review >= 5 or not remaining_regular)

                if should_review_now:
                    review_entry = wrong_queue.pop(0)
                    st.session_state.quiz_wrong_queue = wrong_queue

                    if "quiz_wrong_keys" not in st.session_state or not isinstance(st.session_state.quiz_wrong_keys, set):
                        st.session_state.quiz_wrong_keys = set(st.session_state.get("quiz_wrong_keys", []))

                    st.session_state.quiz_wrong_keys.discard(quiz_entry_key(review_entry))
                    st.session_state.quiz_since_wrong_review = 0
                    st.session_state.quiz_is_review = True
                    st.session_state.quiz_review_count = st.session_state.get("quiz_review_count", 0) + 1
                    return review_entry

                # Nếu hết câu thường và không còn câu sai thì kết thúc.
                if not remaining_regular:
                    st.session_state.quiz_completed = True
                    st.session_state.quiz_q = None
                    st.session_state.quiz_options = []
                    return None

                # Chọn một câu thường chưa hỏi trong lượt hiện tại.
                new_entry = remaining_regular[0] if quiz_in_order else random.choice(remaining_regular)
                st.session_state.quiz_seen_keys.add(quiz_entry_key(new_entry))
                st.session_state.quiz_since_wrong_review = since_review + 1
                st.session_state.quiz_is_review = False
                return new_entry

            def option_order_key(options):
                return tuple(normalize_quiz_key(x) for x in options)

            def shuffle_options_for_entry(options, entry):
                """
                Trộn đáp án và cố gắng tránh trùng vị trí cũ của chính câu đó.
                Dùng cho:
                - câu sai bị hỏi lại ngay
                - câu sai được đưa vào hàng chờ ôn lại kiểu Quizlet
                """
                options = list(options)
                entry_key = quiz_entry_key(entry)

                if "quiz_last_option_orders" not in st.session_state:
                    st.session_state.quiz_last_option_orders = {}

                old_order = st.session_state.quiz_last_option_orders.get(entry_key)

                if len(options) <= 1:
                    return options

                # Thử nhiều lần để tránh ra đúng thứ tự cũ.
                for _ in range(20):
                    random.shuffle(options)

                    if option_order_key(options) != old_order:
                        return options

                return options

            def make_new_quiz_question():
                new_entry = get_next_quiz_entry()

                if new_entry is None:
                    return

                new_card = new_entry["card"]
                question_text = new_entry.get("question", new_card.get("kr", ""))
                correct_variants = list(new_entry.get("correct_variants", []))
                correct_option = new_entry["answer"]

                correct_variants = unique_by_quiz_key(
                    [x for x in correct_variants if clean_text(x)]
                    + [correct_option]
                    + split_answer_parts(correct_option)
                    + answer_variants(correct_option, "")
                )

                new_wrong_pool = [
                    entry
                    for entry in valid_for_quiz
                    if entry.get("direction") == new_entry.get("direction")
                    and quiz_entry_key(entry) != quiz_entry_key(new_entry)
                ]

                wrong_answers = []
                random.shuffle(new_wrong_pool)

                current_question_norm = normalize_quiz_key(question_text)
                correct_norms = [normalize_quiz_key(a) for a in correct_variants]
                wrong_norms = set(correct_norms)

                for entry in new_wrong_pool:
                    wrong_text = entry.get("answer", "")
                    wrong_norm = normalize_quiz_key(wrong_text)

                    if (
                        wrong_text
                        and wrong_norm
                        and wrong_norm != current_question_norm
                        and wrong_norm not in wrong_norms
                        and not quiz_answer_matches(wrong_text, correct_variants)
                    ):
                        wrong_answers.append(wrong_text)
                        wrong_norms.add(wrong_norm)

                    if len(wrong_answers) >= 3:
                        break

                new_options = [correct_option] + wrong_answers
                new_options = [x for x in new_options if normalize_quiz_key(x) != current_question_norm]

                if not new_options:
                    new_options = [correct_option]

                new_options = shuffle_options_for_entry(new_options, new_entry)

                st.session_state.quiz_q = new_card
                st.session_state.quiz_question_text = question_text
                st.session_state.quiz_current_entry = {
                    "card": new_card,
                    "question": question_text,
                    "answer": correct_option,
                    "correct_variants": correct_variants,
                    "direction": new_entry.get("direction", "kr_to_vi"),
                }
                st.session_state.quiz_correct = correct_option
                st.session_state.quiz_correct_variants = correct_variants
                st.session_state.quiz_options = new_options

                if "quiz_last_option_orders" not in st.session_state:
                    st.session_state.quiz_last_option_orders = {}

                st.session_state.quiz_last_option_orders[quiz_entry_key(new_entry)] = option_order_key(new_options)

                st.session_state.quiz_round = st.session_state.get("quiz_round", 0) + 1
                st.session_state.quiz_show_detail = False
                
            def check_answer(selected_option):
                current_entry = st.session_state.get("quiz_current_entry")
                ok = current_quiz_answer_is_correct(selected_option)

                record_quiz_attempt(current_entry, selected_option, ok)

                if ok:
                    if current_entry:
                        st.session_state.quiz_mastered_keys.add(quiz_entry_key(current_entry))

                    st.session_state.quiz_last_result = "correct"

                    if quiz_auto_continue:
                        make_new_quiz_question()

                    st.rerun()
                else:
                    if current_entry:
                        if "quiz_last_option_orders" not in st.session_state:
                            st.session_state.quiz_last_option_orders = {}

                        # Lưu vị trí đáp án vừa bị sai để lần hỏi lại sau 5 câu sẽ trộn khác vị trí cũ
                        st.session_state.quiz_last_option_orders[quiz_entry_key(current_entry)] = option_order_key(
                            st.session_state.get("quiz_options", [])
                        )

                        # Đưa câu sai vào hàng chờ ôn lại sau 5 câu thường
                        add_wrong_review(current_entry)

                    # Trả lời sai -> hiện đáp án và GIỮ NGUYÊN câu hiện tại,
                    # không tự nhảy sang câu tiếp theo.
                    st.session_state.quiz_last_result = "wrong"
                    st.rerun()

            if st.session_state.quiz_q is None or not st.session_state.quiz_options:
                make_new_quiz_question()
                st.session_state.quiz_last_result = None

            if st.button("Câu mới", key="quiz_new_btn", use_container_width=True):
                if st.session_state.get("quiz_completed"):
                    reset_quiz()
                make_new_quiz_question()
                st.session_state.quiz_last_result = None
                st.rerun()

            if st.session_state.get("quiz_is_review"):
                st.warning("🔁 Câu ôn lại: câu này trước đó bạn đã trả lời sai, nên app hỏi lại thêm 1 lần để nhớ tốt hơn.")

            wrong_waiting = len(st.session_state.get("quiz_wrong_queue", []))
            if wrong_waiting > 0:
                st.caption(f"📌 Đang có {wrong_waiting} câu sai trong hàng chờ ôn lại.")

            q = st.session_state.quiz_q
            options = st.session_state.quiz_options
            question_text = st.session_state.get("quiz_question_text", q.get("kr", "") if q else "")
            total_quiz = len(valid_for_quiz)
            regular_done = len(st.session_state.get("quiz_seen_keys", set()))
            review_done = st.session_state.get("quiz_review_count", 0)

            if st.session_state.get("quiz_completed") or q is None or not options:
                st.success(
                    f"🎉 Hoàn thành lượt quiz: đã hỏi đủ {regular_done}/{total_quiz} câu thường"
                    + (f" và {review_done} câu ôn lại." if review_done else ".")
                )

                render_quiz_completion_summary(total_quiz, regular_done, review_done)

                st.stop()

            quiz_star_label = "⭐" if q.get("starred") else "☆"
            quiz_round = st.session_state.get("quiz_round", 0)

            header_col, star_col = st.columns([11, 1])
            with header_col:
                if st.session_state.get("quiz_is_review"):
                    header_text = f"🔁 Ôn lại {review_done} | Câu thường {regular_done}/{total_quiz}"
                else:
                    header_text = f"Câu {regular_done} / {total_quiz}"

                st.markdown(
                    f"<div class='quiz-help'>{header_text}</div>",
                    unsafe_allow_html=True
                )

            q = st.session_state.quiz_q
            star_help = "quiz-star-btn"

            if st.button(quiz_star_label, key=f"quiz_star_btn_{quiz_round}", help=star_help):
                q["starred"] = not q.get("starred", False)
                persist_starred_state(st.session_state.applied_cards, st.session_state.applied_data_key)
                st.rerun()

            st.markdown(
                f"""
                <div class='quiz-box'>
                    <div class='quiz-label'>Thuật ngữ</div>
                    <div class='quiz-question'>{html.escape(question_text)}</div>
                    <div class='quiz-answer-title'>Trả lời đáp án đúng</div>
                </div>
                """,
                unsafe_allow_html=True
            )

            detail_text = clean_text(q.get("detail", ""))

            if detail_text:
                if st.button(
                    "👁️ Hiện/ẩn giải thích / ví dụ",
                    key=f"quiz_detail_{quiz_round}",
                    use_container_width=True
                ):
                    st.session_state.quiz_show_detail = not st.session_state.quiz_show_detail
                    st.rerun()

                if st.session_state.get("quiz_show_detail"):
                    st.info(detail_text)

            speak_button(question_text)

            if st.session_state.get("quiz_last_result") == "correct":
                st.success("Đúng rồi! Đã chuyển sang câu tiếp theo ✅")
            elif st.session_state.get("quiz_last_result") == "wrong_saved":
                st.warning("Sai. Câu này đã được đưa vào hàng chờ và sẽ hỏi lại sau 5 câu.")
            elif st.session_state.get("quiz_last_result") == "wrong":
                correct_show = st.session_state.get("quiz_correct_variants", [])
                if not correct_show:
                    correct_show = [st.session_state.get("quiz_correct", "")]

                st.error(
                    "Sai. Các đáp án đúng là: "
                    + " / ".join([x for x in correct_show if clean_text(x)])
                )

            if quiz_fill_blank:
                with st.form(f"quiz_fill_form_{quiz_round}", clear_on_submit=True):
                    typed_answer = st.text_input(
                        "Nhập đáp án",
                        placeholder="Gõ đáp án rồi nhấn Enter...",
                        key=f"quiz_fill_answer_{quiz_round}"
                    )
                    fill_submitted = st.form_submit_button(
                        "Kiểm tra đáp án",
                        use_container_width=True
                    )

                if fill_submitted:
                    check_answer(typed_answer)

            if quiz_multiple_choice:
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

    with tab_excel_quiz:
        render_excel_quiz_tab()

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
