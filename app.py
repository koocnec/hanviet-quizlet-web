import re
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
from urllib.parse import urlencode

import pandas as pd
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

STATE_FILE = APP_DIR / "app_star_state.json"

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
        st.warning("Hãy chọn nguồn dữ liệu, nhập cột cần dùng rồi bấm Áp dụng để bắt đầu.")
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

    tab_input, tab_folder, tab_starred, tab_flash, tab_write, tab_learn, tab_quiz, tab_speaking, tab_match, tab_search, tab_data = st.tabs([
        "✍️ Nhập thẻ",
        "📁 Thư mục",
        "⭐ Đã gắn sao",
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
