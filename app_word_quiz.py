import base64
import os
import random
import time
import pandas as pd
import streamlit as st
from supabase import create_client

# ==========================================
# ページ初期設定
# ==========================================
st.set_page_config(
    page_title="早押し英単語バトル",
    page_icon="⚔️",
    layout="wide",
)

# 出題上限（10問固定）
MAX_QUESTIONS = 10

# ==========================================
# Supabase 接続設定
# ==========================================
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "")

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error(
        "Supabaseの接続情報（SUPABASE_URL / SUPABASE_KEY）がSecretsに設定されていません。"
    )
    st.stop()

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ==========================================
# キャラクター定義
# ==========================================
ICON_LIST = [
    {"id": 0, "name": "あかべこ", "filename": "あかべこ"},
    {"id": 1, "name": "いぬ", "filename": "いぬ"},
    {"id": 2, "name": "ウサギ", "filename": "ウサギ"},
    {"id": 3, "name": "カッパ", "filename": "カッパ"},
    {"id": 4, "name": "キツネ", "filename": "キツネ"},
    {"id": 5, "name": "クマ", "filename": "クマ"},
    {"id": 6, "name": "シーサー", "filename": "シーサー"},
    {"id": 7, "name": "たぬき", "filename": "たぬき"},
    {"id": 8, "name": "ツル", "filename": "ツル"},
    {"id": 9, "name": "トラ", "filename": "トラ"},
    {"id": 10, "name": "トリ", "filename": "トリ"},
    {"id": 11, "name": "ネコ", "filename": "ネコ"},
    {"id": 12, "name": "パンダ", "filename": "パンダ"},
    {"id": 13, "name": "ペンギン", "filename": "ペンギン"},
    {"id": 14, "name": "ライオン", "filename": "ライオン"},
    {"id": 15, "name": "リス", "filename": "リス"},
]


# ==========================================
# 画像取得ヘルパー関数
# ==========================================
def get_icon_path(icon_id):
    """大文字・小文字・拡張子の違いを吸収してアイコン画像を自動検索"""
    if not isinstance(icon_id, int) or not (0 <= icon_id < len(ICON_LIST)):
        return None

    target_name = ICON_LIST[icon_id]["filename"].lower()
    search_dirs = [
        "assets/icon",
        "assets/icons",
        "asset/icon",
        "asset/icons",
    ]

    for dir_path in search_dirs:
        if os.path.exists(dir_path):
            try:
                files = os.listdir(dir_path)
                for f in files:
                    name_without_ext = os.path.splitext(f)[0].lower()
                    if name_without_ext == target_name:
                        return os.path.join(dir_path, f)
            except Exception:
                continue
    return None


def get_background_style():
    """背景画像の自動読み込み"""
    bg_paths = [
        "assets/bg/background.jpg",
        "assets/bg/background.png",
        "assets/bg/background.JPG",
        "assets/bg/background.PNG",
    ]
    bg_file = None
    for path in bg_paths:
        if os.path.exists(path):
            bg_file = path
            break

    if bg_file:
        with open(bg_file, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode()
        return f"""
        <style>
        .stApp {{
            background-image: url("data:image/jpeg;base64,{encoded_string}");
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
        }}
        </style>
        """
    return ""


# ==========================================
# デザイン・CSS調整（背景を隠さないスマートな装飾）
# ==========================================
bg_css = get_background_style()
st.markdown(bg_css, unsafe_allow_html=True)

st.markdown(
    """
<style>
/* タイトルや見出し文字の読みやすさ向上 */
h1, h2, h3 {
    background-color: rgba(255, 255, 255, 0.85) !important;
    padding: 4px 12px !important;
    border-radius: 6px !important;
    display: inline-block !important;
    color: #111111 !important;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.3) !important;
}

/* プレイヤー情報などのブロック部分 */
div[data-testid="stVerticalBlock"] > div {
    background-color: rgba(255, 255, 255, 0.70) !important;
    border-radius: 8px !important;
    padding: 6px !important;
}

/* ボタンのデザイン */
.stButton > button {
    background-color: rgba(255, 255, 255, 0.9) !important;
    color: #111111 !important;
    font-weight: bold !important;
    border: 2px solid #222222 !important;
    box-shadow: 0 2px 4px rgba(0,0,0,0.2) !important;
}
</style>
""",
    unsafe_allow_html=True,
)


# ==========================================
# 安全なSupabase通信関数
# ==========================================
def safe_execute(query_builder):
    try:
        return query_builder.execute()
    except Exception as e:
        st.error(f"データベースエラーが発生しました: {e}")
        raise e


# ==========================================
# 途中退室処理関数
# ==========================================
def leave_room():
    """ルームを退室し、セッションおよびデータベースを初期化"""
    if st.session_state.player_id:
        try:
            supabase.table("players").delete().eq(
                "id", st.session_state.player_id
            ).execute()
        except Exception:
            pass
    st.session_state.room_id = None
    st.session_state.player_id = None
    st.session_state.player_name = ""
    st.rerun()


# ==========================================
# 問題データのロード関数
# ==========================================
@st.cache_data
def load_questions():
    csv_path = "questions.csv"
    if not os.path.exists(csv_path):
        return [
            {
                "word": "apple",
                "options": ["りんご", "みかん", "ぶどう", "いちご"],
                "answer": "りんご",
            },
            {
                "word": "dog",
                "options": ["ねこ", "いぬ", "とり", "ライオン"],
                "answer": "いぬ",
            },
            {
                "word": "sun",
                "options": ["月", "星", "太陽", "雲"],
                "answer": "太陽",
            },
        ]
    df = pd.read_csv(csv_path)
    questions = []
    for _, row in df.iterrows():
        ans = (
            str(row["answer"])
            if "answer" in row and pd.notna(row["answer"])
            else str(row["option1"])
        )
        opts = [
            str(row["option1"]),
            str(row["option2"]),
            str(row["option3"]),
            str(row["option4"]),
        ]
        questions.append({"word": row["word"], "options": opts, "answer": ans})
    return questions


# ルームIDをシード値にして「全員共通の10問」を抽出する関数
def get_shuffled_10_questions(raw_q, room_id=None):
    q_copy = raw_q.copy()
    if room_id:
        seed_value = abs(hash(room_id)) % (2**32)
        random.seed(seed_value)
    else:
        random.seed(int(time.time()))
    random.shuffle(q_copy)
    return q_copy[:MAX_QUESTIONS]


# ==========================================
# セッション状態の初期化
# ==========================================
if "room_id" not in st.session_state:
    st.session_state.room_id = None
if "player_id" not in st.session_state:
    st.session_state.player_id = None
if "player_name" not in st.session_state:
    st.session_state.player_name = ""

raw_questions = load_questions()

# ==========================================
# メイン画面分岐
# ==========================================

# A. ルーム参加 / 作成画面
if not st.session_state.room_id:
    st.title("⚔️ 早押し英単語バトル")

    tab1, tab2 = st.tabs(["ルーム作成", "ルームに参加"])

    with tab1:
        st.subheader("新しい対戦ルームを作る")
        host_name = st.text_input("あなたの名前", key="host_name")
        selected_icon = st.selectbox(
            "アイコン選択",
            options=range(len(ICON_LIST)),
            format_func=lambda x: ICON_LIST[x]["name"],
            key="host_icon",
        )

        icon_path = get_icon_path(selected_icon)
        if icon_path:
            st.image(icon_path, width=80)

        if st.button("ルームを作成して待機"):
            if host_name.strip():
                import uuid

                new_room_id = str(uuid.uuid4())[:6].upper()

                # ルーム作成
                safe_execute(
                    supabase.table("rooms").insert(
                        {
                            "room_id": new_room_id,
                            "status": "waiting",
                            "step": 0,
                        }
                    )
                )

                # プレイヤー追加
                res = safe_execute(
                    supabase.table("players").insert(
                        {
                            "room_id": new_room_id,
                            "player_name": host_name,
                            "icon_id": selected_icon,
                            "score": 0,
                            "hp": 100,
                            "combo": 0,
                        }
                    )
                )

                st.session_state.room_id = new_room_id
                st.session_state.player_name = host_name
                st.session_state.player_id = res.data[0]["id"]
                st.rerun()

    with tab2:
        st.subheader("既存のルームに参加する")
        join_room_id = st.text_input("ルームID (6文字)", key="join_room_id")
        guest_name = st.text_input("あなたの名前", key="guest_name")
        selected_icon_g = st.selectbox(
            "アイコン選択",
            options=range(len(ICON_LIST)),
            format_func=lambda x: ICON_LIST[x]["name"],
            key="guest_icon",
        )

        icon_path_g = get_icon_path(selected_icon_g)
        if icon_path_g:
            st.image(icon_path_g, width=80)

        if st.button("ルームに参加"):
            if join_room_id and guest_name.strip():
                target_room = (
                    supabase.table("rooms")
                    .select("*")
                    .eq("room_id", join_room_id.upper())
                    .execute()
                )
                if target_room.data:
                    res = safe_execute(
                        supabase.table("players").insert(
                            {
                                "room_id": join_room_id.upper(),
                                "player_name": guest_name,
                                "icon_id": selected_icon_g,
                                "score": 0,
                                "hp": 100,
                                "combo": 0,
                            }
                        )
                    )

                    st.session_state.room_id = join_room_id.upper()
                    st.session_state.player_name = guest_name
                    st.session_state.player_id = res.data[0]["id"]
                    st.rerun()
                else:
                    st.error("指定されたルームIDが見つかりません。")

# B. ゲーム対戦画面
else:
    room_id = st.session_state.room_id
    player_id = st.session_state.player_id

    # 最新状態取得
    room_res = (
        supabase.table("rooms").select("*").eq("room_id", room_id).execute()
    )
    players_res = (
        supabase.table("players").select("*").eq("room_id", room_id).execute()
    )

    if not room_res.data:
        st.error("ルーム情報が存在しません。")
        if st.button("ロビーへ戻る"):
            leave_room()
        st.stop()

    room_data = room_res.data[0]
    players_data = players_res.data
    status = room_data["status"]
    step = room_data["step"]

    # ヘッダーと途中退室ボタンの配置
    head_col1, head_col2 = st.columns([4, 1])
    with head_col1:
        st.title(f"⚔️ 早押し英単語バトル (ROOM: {room_id})")
    with head_col2:
        if st.button("🚪 途中退室", key="leave_btn"):
            leave_room()

    # B-1. 待機画面
    if status == "waiting":
        st.info("対戦相手の参加を待っています...")
        st.write(f"現在の参加メンバー ({len(players_data)}人):")

        cols = st.columns(4)
        for idx, p in enumerate(players_data):
            with cols[idx % 4]:
                p_icon = get_icon_path(p.get("icon_id"))
                if p_icon:
                    st.image(p_icon, width=60)
                st.write(f"**{p['player_name']}**")

        if len(players_data) >= 1:
            if st.button("バトルスタート！", type="primary"):
                safe_execute(
                    supabase.table("rooms")
                    .update({"status": "playing", "step": 0})
                    .eq("room_id", room_id)
                )
                st.rerun()

        time.sleep(2)
        st.rerun()

    # B-2. プレイ画面
    elif status == "playing":
        # 部屋IDを共通キーとして、全参加者にまったく同じ10問を抽出
        questions = get_shuffled_10_questions(raw_questions, room_id)

        # 生存プレイヤーチェック
        active_players = [p for p in players_data if p.get("hp", 100) > 0]

        # 10問終了時、または全員HP0でリザルト画面へ
        if step >= len(questions) or len(active_players) == 0:
            safe_execute(
                supabase.table("rooms")
                .update({"status": "finished"})
                .eq("room_id", room_id)
            )
            st.rerun()

        current_q = questions[step]

        # プレイヤー情報表示
        cols = st.columns(len(players_data) if players_data else 1)
        for idx, p in enumerate(players_data):
            with cols[idx]:
                p_icon = get_icon_path(p.get("icon_id"))
                if p_icon:
                    st.image(p_icon, width=50)
                is_me = "(あなた)" if p["id"] == player_id else ""
                st.write(f"**{p['player_name']}** {is_me}")
                st.write(
                    f"スコア: {p.get('score', 0)}pt | コンボ: {p.get('combo', 0)} 🔥"
                )
                st.write(f"❤️ HP: {p.get('hp', 100)} / 100")

        st.divider()

        # 問題表示（全10問固定）
        st.header(f"第 {step + 1} 問 / {len(questions)}")
        st.subheader("以下の英単語の意味を選択してください")
        st.markdown(f"# **{current_q['word']}**")

        # 選択肢のシャッフル（部屋IDと問題番号から共通配置を生成）
        option_seed = abs(hash(f"{room_id}_{step}")) % (2**32)
        shuffled_options = current_q["options"].copy()
        random.seed(option_seed)
        random.shuffle(shuffled_options)

        # すでにこの問題に回答しているか確認
        my_ans = (
            supabase.table("answers")
            .select("*")
            .eq("room_id", room_id)
            .eq("step", step)
            .eq("player_id", player_id)
            .execute()
        )

        if len(my_ans.data) > 0:
            st.success("回答を送信しました！他のプレイヤーの回答を待っています...")
        else:
            # 4択ボタン（全員同じランダム配置のボタンを表示）
            b_cols = st.columns(2)
            for idx, opt in enumerate(shuffled_options):
                with b_cols[idx % 2]:
                    if st.button(
                        opt, key=f"opt_{step}_{idx}", use_container_width=True
                    ):
                        is_correct = opt == current_q["answer"]

                        # 回答記録（早押し判定用）
                        safe_execute(
                            supabase.table("answers").insert(
                                {
                                    "room_id": room_id,
                                    "step": step,
                                    "player_id": player_id,
                                    "player_name": st.session_state.player_name,
                                    "is_correct": is_correct,
                                }
                            )
                        )

                        # スコアとHPの更新計算
                        me = next(
                            (p for p in players_data if p["id"] == player_id),
                            None,
                        )
                        if me:
                            new_score = me.get("score", 0)
                            new_hp = me.get("hp", 100)
                            new_combo = me.get("combo", 0)

                            if is_correct:
                                new_combo += 1
                                new_score += 100 + (new_combo * 10)
                            else:
                                new_combo = 0
                                new_hp = max(0, new_hp - 20)

                            safe_execute(
                                supabase.table("players")
                                .update(
                                    {
                                        "score": new_score,
                                        "hp": new_hp,
                                        "combo": new_combo,
                                    }
                                )
                                .eq("id", player_id)
                            )

                        st.rerun()

        # 全員の回答待ちチェック
        ans_res = (
            supabase.table("answers")
            .select("*")
            .eq("room_id", room_id)
            .eq("step", step)
            .execute()
        )
        if len(ans_res.data) >= len(players_data):
            time.sleep(1.5)
            # 全員回答済みのため次の問題に進む
            safe_execute(
                supabase.table("rooms")
                .update({"step": step + 1})
                .eq("room_id", room_id)
            )
            st.rerun()

        time.sleep(2)
        st.rerun()

    # B-3. リザルト画面
    elif status == "finished":
        st.balloons()
        st.header("🏆 ゲームセット！最終結果")

        # スコア順にソート
        sorted_players = sorted(
            players_data, key=lambda x: x.get("score", 0), reverse=True
        )

        for rank, p in enumerate(sorted_players, 1):
            cols = st.columns([1, 2, 3])
            with cols[0]:
                st.subheader(f"第 {rank} 位")
            with cols[1]:
                p_icon = get_icon_path(p.get("icon_id"))
                if p_icon:
                    st.image(p_icon, width=60)
            with cols[2]:
                st.write(f"### **{p['player_name']}**")
                st.write(
                    f"最終スコア: **{p.get('score', 0)} pt** | 残りHP: ❤️ {p.get('hp', 0)}"
                )
            st.divider()

        if st.button("ロビーへ戻る"):
            leave_room()