import streamlit as st
from supabase import create_client
import random
import time
import pandas as pd
import os
import base64
import json

# ページ基本設定
st.set_page_config(page_title="VS Quiz App - 英単語4択バトル", layout="centered")

# --- カスタムCSS（背景画像 JPG の自動検出・文字・ボタンの視認性向上設定）---
bg_path = None
possible_bg_paths = [
    "asset/bg/bg.jpg",
    "asset/bg/background.jpg",
    "assets/bg/bg.jpg",
    "assets/bg/background.jpg"
]

for path in possible_bg_paths:
    if os.path.exists(path):
        bg_path = path
        break

if bg_path and os.path.exists(bg_path):
    with open(bg_path, "rb") as f:
        bg_bytes = f.read()
    encoded_bg = base64.b64encode(bg_bytes).decode()
    
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-image: url("data:image/jpeg;base64,{encoded_bg}");
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            background-attachment: fixed;
            color: #111111;
        }}
        [data-testid="stHeader"] {{
            background-color: rgba(0, 0, 0, 0);
        }}
        .main .block-container {{
            background-color: rgba(255, 255, 255, 0.94);
            padding: 2rem;
            border-radius: 16px;
            box-shadow: 0px 6px 16px rgba(0, 0, 0, 0.2);
            color: #111111;
        }}
        .stButton > button {{
            background-color: #ffffff !important;
            color: #1a202c !important;
            border: 1px solid #cbd5e0 !important;
            font-weight: bold !important;
        }}
        .stButton > button[kind="primary"] {{
            background-color: #3182ce !important;
            color: #ffffff !important;
            border: none !important;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

# アイコンリスト定義
ICON_LIST = [
    {"id": 0, "name": "あかべこ", "filename": "あかべこ"},
    {"id": 1, "name": "いぬ", "filename": "いぬ"},
    {"id": 2, "name": "うま", "filename": "うま"},
    {"id": 3, "name": "かえる", "filename": "かえる"},
    {"id": 4, "name": "かっぱ", "filename": "かっぱ"},
    {"id": 5, "name": "きのこ", "filename": "きのこ"},
    {"id": 6, "name": "さる", "filename": "さる"},
    {"id": 7, "name": "ぞんび", "filename": "ぞんび"},
    {"id": 8, "name": "てんぐ", "filename": "てんぐ"},
    {"id": 9, "name": "ぱんだ", "filename": "ぱんだ"},
    {"id": 10, "name": "ぶろっこりー", "filename": "ぶろっこりー"},
    {"id": 11, "name": "らがーまん", "filename": "らがーまん"},
]

def get_icon_path(icon_id):
    if not (0 <= icon_id < len(ICON_LIST)):
        return None
    target_name = ICON_LIST[icon_id]["filename"]
    search_dirs = ["assets/icon", "assets/icons", "asset/icon", "asset/icons"]
    for dir_path in search_dirs:
        if os.path.exists(dir_path):
            try:
                for f in os.listdir(dir_path):
                    if os.path.splitext(f)[0] == target_name:
                        return os.path.join(dir_path, f)
            except Exception:
                continue
    return None

# Supabase接続初期化
@st.cache_resource
def init_supabase():
    url = st.secrets["SUPABASE_URL"].rstrip("/")
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_supabase()

def safe_execute(query_builder, retries=3, delay=0.5):
    for attempt in range(retries):
        try:
            return query_builder.execute()
        except Exception as e:
            if attempt == retries - 1:
                raise e
            time.sleep(delay)

# 順位に応じた獲得基本ポイント
RANK_POINTS = {1: 100, 2: 70, 3: 50, 4: 30}

st.title("🔤 早押し英単語バトル")

if "player_id" not in st.session_state:
    st.session_state.player_id = None
if "room_id" not in st.session_state:
    st.session_state.room_id = None
if "submitting" not in st.session_state:
    st.session_state.submitting = False
if "answered_step" not in st.session_state:
    st.session_state.answered_step = -1

# サイドバー：途中終了機能
if st.session_state.room_id:
    with st.sidebar:
        st.write(f"🔑 ルームID: **{st.session_state.room_id}**")
        if st.button("⚠️ ゲームを途中終了する", use_container_width=True):
            try:
                if st.session_state.player_id:
                    safe_execute(supabase.table("players").delete().eq("id", st.session_state.player_id))
            except Exception:
                pass
            st.session_state.clear()
            st.rerun()

# --- A. プレイヤー登録・ルーム参加画面 ---
if not st.session_state.room_id:
    st.subheader("👤 プレイヤー情報登録")
    player_name = st.text_input("プレイヤー名を入力", max_chars=10)
    
    st.write("キャラアイコンを選択:")
    icon_names = [item["name"] for item in ICON_LIST]
    selected_name = st.selectbox("キャラ選択", icon_names)
    selected_icon = next(item for item in ICON_LIST if item["name"] == selected_name)
    icon_id = selected_icon["id"]
    selected_icon_path = get_icon_path(icon_id)
    
    if selected_icon_path:
        st.image(selected_icon_path, width=80, caption=f"選択中: {selected_name}")

    st.divider()
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("新しくルームを作成", type="primary", use_container_width=True, disabled=st.session_state.submitting):
            if player_name:
                st.session_state.submitting = True
                room_id = str(random.randint(1000, 9999))
                
                # CSVから英単語データを読み込み
                try:
                    df = pd.read_csv("questions.csv", encoding="utf-8").fillna("")
                except:
                    df = pd.read_csv("questions.csv", encoding="shift-jis").fillna("")
                
                sample_df = df.sample(n=min(10, len(df)))
                quiz_list = []
                for _, row in sample_df.iterrows():
                    options = [str(row["option1"]), str(row["option2"]), str(row["option3"]), str(row["option4"])]
                    random.shuffle(options)  # 選択肢をランダムにシャッフル
                    quiz_list.append({
                        "word": str(row["word"]),
                        "options": options,
                        "answer": str(row["answer"])
                    })
                
                questions_json_str = json.dumps(quiz_list, ensure_ascii=False)
                
                try:
                    safe_execute(supabase.table("rooms").insert({
                        "room_id": room_id,
                        "questions": questions_json_str,
                        "status": "waiting",
                        "current_step": 0
                    }))
                    
                    p_res = safe_execute(supabase.table("players").insert({
                        "room_id": room_id,
                        "player_name": player_name,
                        "icon_id": icon_id,
                        "score": 0,
                        "hp": 100,
                        "combo": 0
                    }))
                    
                    st.session_state.room_id = room_id
                    st.session_state.player_id = p_res.data[0]["id"]
                    st.session_state.is_host = True
                    st.session_state.submitting = False
                    st.rerun()
                except Exception as e:
                    st.session_state.submitting = False
                    st.error(f"❌ 登録エラー: {e}")
            else:
                st.warning("プレイヤー名を入力してください")

    with col2:
        input_room_id = st.text_input("ルームID (4桁)")
        if st.button("ルームに参加", use_container_width=True, disabled=st.session_state.submitting):
            if player_name and input_room_id:
                st.session_state.submitting = True
                try:
                    room_check = safe_execute(supabase.table("rooms").select("*").eq("room_id", input_room_id))
                    if not room_check.data:
                        st.session_state.submitting = False
                        st.error("指定されたルームIDが存在しません。")
                    else:
                        players_res = safe_execute(supabase.table("players").select("*").eq("room_id", input_room_id))
                        players = players_res.data if players_res.data else []
                        
                        if len(players) >= 4:
                            st.session_state.submitting = False
                            st.error("このルームは満員です（最大4名）")
                        else:
                            p_res = safe_execute(supabase.table("players").insert({
                                "room_id": input_room_id,
                                "player_name": player_name,
                                "icon_id": icon_id,
                                "score": 0,
                                "hp": 100,
                                "combo": 0
                            }))
                            
                            st.session_state.room_id = input_room_id
                            st.session_state.player_id = p_res.data[0]["id"]
                            st.session_state.is_host = False
                            st.session_state.submitting = False
                            st.rerun()
                except Exception as e:
                    st.session_state.submitting = False
                    st.error(f"接続エラー: {e}")

# --- B. ゲームメイン処理画面 ---
else:
    room_id = st.session_state.room_id
    
    try:
        room_data_res = safe_execute(supabase.table("rooms").select("*").eq("room_id", room_id))
        players_data_res = safe_execute(supabase.table("players").select("*").eq("room_id", room_id))
        room_data = room_data_res.data[0]
        players_data = players_data_res.data
    except Exception:
        time.sleep(1)
        st.rerun()

    questions = json.loads(room_data["questions"])
    my_p = next((p for p in players_data if p["id"] == st.session_state.player_id), None)

    # マイステータス表示
    if my_p:
        my_hp = my_p.get("hp", 100)
        hp_display = "💀 死亡" if my_hp <= 0 else f"❤️ HP: {my_hp} / 100"
        my_icon_path = get_icon_path(my_p.get("icon_id", 0))
        
        with st.container():
            st.markdown("---")
            c_icon, c_info = st.columns([1, 4])
            with c_icon:
                if my_icon_path:
                    st.image(my_icon_path, width=70)
            with c_info:
                st.markdown(f"### 👤 **{my_p['player_name']}** （あなた）")
                st.markdown(f"**スコア:** {my_p.get('score', 0)} pt | **コンボ:** {my_p.get('combo', 0)} 🔥 | **ステータス:** {hp_display}")
            st.markdown("---")

    # B-1. 待機画面
    if room_data["status"] == "waiting":
        st.info(f"🔑 ルームID: **{room_id}** （参加者待機中 : {len(players_data)}/4 名）")
        p_cols = st.columns(4)
        for idx, p in enumerate(players_data):
            with p_cols[idx]:
                icon_path = get_icon_path(p.get("icon_id", 0))
                if icon_path:
                    st.image(icon_path, width=50)
                st.caption(f"**{p['player_name']}**")

        if st.session_state.get("is_host", False):
            if st.button("ゲームスタート！", type="primary", use_container_width=True):
                safe_execute(supabase.table("rooms").update({"status": "countdown"}).eq("room_id", room_id))
                st.rerun()
        else:
            st.write("⏳ ホストがスタートを押すのをお待ちください...")
            time.sleep(2)
            st.rerun()

    # B-1.5. カウントダウン
    elif room_data["status"] == "countdown":
        st.markdown("<h2 style='text-align: center;'>まもなくゲームが始まります！</h2>", unsafe_allow_html=True)
        countdown_place = st.empty()
        for count in range(3, 0, -1):
            countdown_place.markdown(f"<h1 style='text-align: center; font-size: 80px; color: #e53e3e;'>{count}</h1>", unsafe_allow_html=True)
            time.sleep(1)
        countdown_place.markdown("<h1 style='text-align: center; font-size: 80px; color: #3182ce;'>START!</h1>", unsafe_allow_html=True)
        time.sleep(0.5)

        if st.session_state.get("is_host", False):
            safe_execute(supabase.table("rooms").update({"status": "playing"}).eq("room_id", room_id))
        st.rerun()

    # B-2. プレイ画面
    elif room_data["status"] == "playing":
        step = room_data["current_step"]
        
        # 全員がHP0または全10問終了でゲームセット
        active_players = [p for p in players_data if p.get("hp", 100) > 0]
        if step >= 10 or len(active_players) == 0:
            safe_execute(supabase.table("rooms").update({"status": "finished"}).eq("room_id", room_id))
            st.rerun()

        current_q = questions[step]
        st.markdown(f"### 第 {step + 1} 問 / 10")
        
        # メンバー一覧・HPスコア状況
        p_cols = st.columns(4)
        for idx, p in enumerate(players_data):
            with p_cols[idx]:
                icon_path = get_icon_path(p.get("icon_id", 0))
                if icon_path:
                    st.image(icon_path, width=40)
                hp_val = p.get("hp", 100)
                if hp_val <= 0:
                    st.caption(f"💀 **{p['player_name']}**\n(脱落)")
                else:
                    st.caption(f"**{p['player_name']}**\n{p.get('score', 0)}pt (HP:{hp_val})")

        # 問題表示（英単語）
        st.markdown(
            f"""
            <div style="background-color: rgba(255, 255, 255, 0.95); padding: 24px; border-radius: 12px; border-left: 6px solid #3182ce; margin: 15px 0; text-align: center;">
                <p style="margin:0; font-size: 1rem; color: #718096;">以下の英単語の意味を選択してください</p>
                <h1 style="color: #2b6cb0; margin: 10px 0 0 0; font-size: 2.5rem;">{current_q['word']}</h1>
            </div>
            """,
            unsafe_allow_html=True
        )

        # 現在のステップでの全プレイヤーの回答データを取得
        ans_res = safe_execute(supabase.table("answers").select("*").eq("room_id", room_id).eq("step", step).order("created_at"))
        step_answers = ans_res.data if ans_res.data else []
        
        # 正解済みのプレイヤー一覧を取得
        correct_answers_list = [a for a in step_answers if a["is_correct"]]

        # ホストによるラウンド進行管理（全員回答済み or 一定時間経過）
        if st.session_state.get("is_host", False):
            if len(step_answers) >= len(active_players) and len(active_players) > 0:
                time.sleep(2)
                safe_execute(supabase.table("rooms").update({"current_step": step + 1}).eq("room_id", room_id))
                st.rerun()

        # プレイヤーの操作部分
        if my_p and my_p.get("hp", 100) <= 0:
            st.warning("☠️ HPが0になりました。観戦中...")
        elif st.session_state.answered_step == step:
            st.info("⌛ 回答送信済みです。他プレイヤーの回答をお待ちください。")
            if correct_answers_list:
                st.write("【正解者順位】")
                for idx, ca in enumerate(correct_answers_list, 1):
                    st.write(f"第{idx}位: {ca['player_name']}")
        else:
            st.write("選択肢:")
            # 4択ボタンの配置 (2x2列)
            col_a, col_b = st.columns(2)
            options = current_q["options"]
            
            for idx, opt in enumerate(options):
                target_col = col_a if idx % 2 == 0 else col_b
                with target_col:
                    if st.button(opt, key=f"btn_{step}_{idx}", use_container_width=True):
                        st.session_state.answered_step = step
                        is_correct = (opt == current_q["answer"])
                        
                        if is_correct:
                            # 自分が何番目の正解者かを判定 (1〜4位)
                            rank = len(correct_answers_list) + 1
                            base_pt = RANK_POINTS.get(rank, 30)
                            
                            # コンボ計算 (+10%ボーナス/1コンボ、上限2倍)
                            current_combo = my_p.get("combo", 0) + 1
                            multiplier = min(2.0, 1.0 + (current_combo - 1) * 0.1)
                            gained_score = int(base_pt * multiplier)
                            
                            # DB書き込み（回答ログ & プレイヤー更新）
                            safe_execute(supabase.table("answers").insert({
                                "room_id": room_id,
                                "step": step,
                                "player_id": my_p["id"],
                                "player_name": my_p["player_name"],
                                "is_correct": True
                            }))
                            
                            safe_execute(supabase.table("players").update({
                                "score": my_p.get("score", 0) + gained_score,
                                "combo": current_combo
                            }).eq("id", my_p["id"]))
                            
                            st.success(f"🎉 正解！ {rank}位到着 (+{gained_score}pt) | {current_combo} Combo!")
                        else:
                            # 不正解処理（ダメージ20 & コンボリセット）
                            damage = 20
                            new_hp = max(0, my_p.get("hp", 100) - damage)
                            
                            safe_execute(supabase.table("answers").insert({
                                "room_id": room_id,
                                "step": step,
                                "player_id": my_p["id"],
                                "player_name": my_p["player_name"],
                                "is_correct": False
                            }))
                            
                            safe_execute(supabase.table("players").update({
                                "hp": new_hp,
                                "combo": 0
                            }).eq("id", my_p["id"]))
                            
                            st.error(f"❌ 不正解... {damage} ダメージ！ (HP: {new_hp})")

                        time.sleep(1)
                        st.rerun()

        time.sleep(2)
        st.rerun()

    # B-3. 最終結果発表画面
    elif room_data["status"] == "finished":
        st.balloons()
        st.header("🏆 最終順位発表 🏆")
        
        # スコア順 (同点の場合は残りHP順)
        sorted_players = sorted(players_data, key=lambda x: (x.get("score", 0), x.get("hp", 0)), reverse=True)
        
        for rank, p in enumerate(sorted_players, 1):
            col_rank, col_icon, col_info = st.columns([1, 1, 3])
            with col_rank:
                st.subheader(f"第 {rank} 位")
            with col_icon:
                icon_path = get_icon_path(p.get("icon_id", 0))
                if icon_path:
                    st.image(icon_path, width=50)
            with col_info:
                hp_str = "💀 脱落" if p.get("hp", 100) <= 0 else f"❤️ 残りHP: {p.get('hp', 100)}"
                st.write(f"**{p['player_name']}** — **{p.get('score', 0)} pt** ({hp_str})")
            st.divider()

        if st.button("トップに戻る", type="primary"):
            st.session_state.clear()
            st.rerun()