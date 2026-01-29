import streamlit as st
import pandas as pd
import itertools
import random
import time

# --- KONFIGURÁCIA ---
st.set_page_config(page_title="FIFA Turnaj Manager", page_icon="⚽", layout="wide")

# --- CSS ÚPRAVY ---
st.markdown("""
<style>
    .stButton button {
        height: 3rem;
        font-weight: bold;
    }
    .highlight-winner {
        background-color: #FFD700;
        padding: 20px;
        border-radius: 15px;
        text-align: center;
        color: black;
        margin-bottom: 20px;
        border: 2px solid #daa520;
    }
    .final-stats-header {
        text-align: center;
        margin-top: 30px;
        margin-bottom: 20px;
        text-transform: uppercase;
        letter-spacing: 2px;
        color: #1e3c72;
    }
</style>
""", unsafe_allow_html=True)

# --- SESSION STATE ---
if 'stage' not in st.session_state:
    st.session_state.stage = "REGISTRATION"
if 'players' not in st.session_state:
    st.session_state.players = []
if 'matches' not in st.session_state:
    st.session_state.matches = [] 
if 'playoff_matches' not in st.session_state:
    st.session_state.playoff_matches = {}
if 'playoff_seeds' not in st.session_state:
    st.session_state.playoff_seeds = []
if 'player_count' not in st.session_state:
    st.session_state.player_count = 0
if 'group_ranking' not in st.session_state:
    st.session_state.group_ranking = []

# --- FUNKCIE ---

def generate_schedule(players):
    names = [p['name'] for p in players]
    pairs = list(itertools.combinations(names, 2))
    random.shuffle(pairs) 
    
    schedule = []
    for home, away in pairs:
        schedule.append({
            "home": home,
            "away": away,
            "score_home": None,
            "score_away": None,
            "played": False
        })
    return schedule

def calculate_group_standings():
    data = {p["name"]: {"Tím": p["team"], "Z": 0, "G+": 0, "G-": 0, "Body": 0} for p in st.session_state.players}
    
    for m in st.session_state.matches:
        if m["played"]:
            h, a = m["home"], m["away"]
            sh, sa = m["score_home"], m["score_away"]
            if h in data and a in data:
                data[h]["Z"] += 1; data[a]["Z"] += 1
                data[h]["G+"] += sh; data[a]["G+"] += sa
                data[h]["G-"] += sa; data[a]["G-"] += sh
                if sh > sa: data[h]["Body"] += 3
                elif sa > sh: data[a]["Body"] += 3
                else:
                    data[h]["Body"] += 1; data[a]["Body"] += 1
    
    df = pd.DataFrame.from_dict(data, orient='index')
    df["+/-"] = df["G+"] - df["G-"]
    df = df.sort_values(by=["Body", "+/-", "G+"], ascending=False)
    return df

def calculate_final_stats(final_ranking):
    stats = {p["name"]: {"Tím": p["team"], "Z": 0, "G+": 0, "G-": 0, "V": 0, "R": 0, "P": 0} for p in st.session_state.players}
    
    def process(h, a, sh, sa):
        if h in stats and a in stats:
            stats[h]["Z"] += 1; stats[a]["Z"] += 1
            stats[h]["G+"] += sh; stats[a]["G+"] += sa
            stats[h]["G-"] += sa; stats[a]["G-"] += sh
            if sh > sa: stats[h]["V"] += 1; stats[a]["P"] += 1
            elif sa > sh: stats[a]["V"] += 1; stats[h]["P"] += 1
            else: stats[h]["R"] += 1; stats[a]["R"] += 1

    for m in st.session_state.matches:
        if m["played"]: process(m["home"], m["away"], m["score_home"], m["score_away"])
    for key in st.session_state.playoff_matches:
        m = st.session_state.playoff_matches[key]
        if m.get("played") and m.get("h") and m.get("a"):
             process(m["h"], m["a"], m["sh"], m["sa"])

    data_list = []
    for rank, name in enumerate(final_ranking, 1):
        if name in stats:
            row = stats[name]
            row["Meno"] = name
            row["Poradie"] = f"{rank}."
            row["+/-"] = row["G+"] - row["G-"]
            data_list.append(row)
            
    df = pd.DataFrame(data_list)
    df = df[["Poradie", "Meno", "Tím", "Z", "V", "R", "P", "G+", "G-", "+/-"]]
    df.set_index("Poradie", inplace=True)
    return df

# --- 1. REGISTRÁCIA ---
if st.session_state.stage == "REGISTRATION":
    st.title("⚽ FIFA Turnaj - Registrácia")
    with st.form("reg_form"):
        temp_data = []
        c1, c2, c3 = st.columns(3)
        for i in range(1, 4):
            with [c1, c2, c3][i-1]:
                st.markdown(f"**Hráč {i}**")
                temp_data.append({"name": st.text_input("Meno", key=f"n{i}"), "team": st.text_input("Tím", key=f"t{i}")})
        c4, c5, c6 = st.columns(3)
        for i in range(4, 7):
            with [c4, c5, c6][i-4]:
                st.markdown(f"**Hráč {i}**")
                temp_data.append({"name": st.text_input("Meno", key=f"n{i}"), "team": st.text_input("Tím", key=f"t{i}")})
        if st.form_submit_button("Generovať turnaj 🎲", use_container_width=True, type="primary"):
            valid = [p for p in temp_data if p['name'].strip()]
            if len(valid) < 3: st.error("Musíte byť aspoň traja!")
            else:
                st.session_state.players, st.session_state.player_count = valid, len(valid)
                st.session_state.matches = generate_schedule(valid)
                st.session_state.stage = "GROUP"; st.rerun()

# --- 2. SKUPINA ---
elif st.session_state.stage == "GROUP":
    st.title("🔥 Skupinová Fáza")
    df = calculate_group_standings()
    col_matches, col_table = st.columns([1, 1])
    limit = 2 if st.session_state.player_count == 3 else 4
    
    with col_table:
        st.subheader("📊 Tabuľka")
        st.dataframe(df.style.apply(lambda s: ['background-color: #d4edda' if i < limit else '' for i in range(len(s))], axis=0), use_container_width=True)
        played = sum(1 for m in st.session_state.matches if m["played"])
        if played == len(st.session_state.matches):
            if st.button("🏆 POSTÚPIŤ", type="primary", use_container_width=True):
                st.session_state.group_ranking = df.index.tolist()
                st.session_state.playoff_seeds = df.index[:limit].tolist()
                st.session_state.stage = "PLAYOFF"; st.rerun()
        else: st.info(f"Zostáva odohrať: {len(st.session_state.matches) - played}")

    with col_matches:
        for i, match in enumerate(st.session_state.matches):
            with st.container(border=True):
                if match["played"]:
                    st.write(f"✅ {match['home']} {match['score_home']}:{match['score_away']} {match['away']}")
                    if st.button("Opraviť", key=f"fx{i}"): match["played"] = False; st.rerun()
                else:
                    st.write(f"{match['home']} vs {match['away']}")
                    c1, c2, c3 = st.columns(3)
                    with c1: s1 = st.number_input("D", key=f"h{i}", min_value=0, step=1)
                    with c2: s2 = st.number_input("H", key=f"a{i}", min_value=0, step=1)
                    with c3:
                        st.write(""); st.write("")
                        if st.button("OK", key=f"b{i}"): match["score_home"], match["score_away"], match["played"] = s1, s2, True; st.rerun()

# --- 3. PLAYOFF ---
elif st.session_state.stage == "PLAYOFF":
    seeds, count, pm = st.session_state.playoff_seeds, st.session_state.player_count, st.session_state.playoff_matches
    ranking = st.session_state.group_ranking

    if count == 3:
        st.title("🏆 FINÁLE")
        if "FINAL_3P" not in pm: pm["FINAL_3P"] = {"h": seeds[0], "a": seeds[1], "sh": 0, "sa": 0, "played": False}
        f = pm["FINAL_3P"]
        if f["played"]:
            w = f['h'] if f['sh'] > f['sa'] else f['a']
            l = f['a'] if f['sh'] > f['sa'] else f['h']
            st.markdown(f"<div class='highlight-winner'><h1>👑 VÍŤAZ: {w} 👑</h1></div>", unsafe_allow_html=True)
            # POISTKA: Ak nie je tretí hráč v zozname (chyba session), dáme prázdny reťazec
            third = [ranking[2]] if len(ranking) > 2 else []
            st.dataframe(calculate_final_stats([w, l] + third), use_container_width=True)
        else:
            c1, c2 = st.columns(2); s1 = c1.number_input(f"{f['h']}", 0); s2 = c2.number_input(f"{f['a']}", 0)
            if st.button("UKONČIŤ TURNAJ", use_container_width=True): f["sh"], f["sa"], f["played"] = s1, s2, True; st.rerun()
    else:
        st.title("⚔️ PLAYOFF")
        if not pm:
            pm["SF1"] = {"h": seeds[0], "a": seeds[3], "sh": 0, "sa": 0, "played": False}
            pm["SF2"] = {"h": seeds[1], "a": seeds[2], "sh": 0, "sa": 0, "played": False}
            pm["3RD"] = {"h": None, "a": None, "sh": 0, "sa": 0, "played": False}
            pm["FIN"] = {"h": None, "a": None, "sh": 0, "sa": 0, "played": False}
        
        c1, c2 = st.columns(2)
        for key, name in [("SF1", "SF 1"), ("SF2", "SF 2")]:
            with [c1, c2][0 if key=="SF1" else 1]:
                m = pm[key]
                st.subheader(f"{name}: {m['h']} vs {m['a']}")
                if m["played"]: st.success(f"{m['sh']}:{m['sa']}")
                else:
                    s1 = st.number_input("G1", key=f"s{key}1"); s2 = st.number_input("G2", key=f"s{key}2")
                    if st.button(f"Uložiť {key}"): m["sh"], m["sa"], m["played"] = s1, s2, True; st.rerun()

        if pm["SF1"]["played"] and pm["SF2"]["played"]:
            w1 = pm["SF1"]["h"] if pm["SF1"]["sh"] > pm["SF1"]["sa"] else pm["SF1"]["a"]
            l1 = pm["SF1"]["a"] if pm["SF1"]["sh"] > pm["SF1"]["sa"] else pm["SF1"]["h"]
            w2 = pm["SF2"]["h"] if pm["SF2"]["sh"] > pm["SF2"]["sa"] else pm["SF2"]["a"]
            l2 = pm["SF2"]["a"] if pm["SF2"]["sh"] > pm["SF2"]["sa"] else pm["SF2"]["h"]
            
            st.divider()
            c3, c4 = st.columns(2)
            with c3:
                st.subheader(f"🥉 O 3. MIESTO: {l1} vs {l2}")
                if pm["3RD"]["played"]: st.warning(f"{pm['3RD']['sh']}:{pm['3RD']['sa']}")
                else:
                    s1 = st.number_input("G1", key="s31"); s2 = st.number_input("G2", key="s32")
                    if st.button("Uložiť 3RD"): pm["3RD"]["h"], pm["3RD"]["a"], pm["3RD"]["sh"], pm["3RD"]["sa"], pm["3RD"]["played"] = l1, l2, s1, s2, True; st.rerun()
            with c4:
                st.subheader(f"🏆 FINÁLE: {w1} vs {w2}")
                if pm["FIN"]["played"]:
                    st.balloons(); win = w1 if pm["FIN"]["sh"] > pm["FIN"]["sa"] else w2; los = w2 if win == w1 else w1
                    st.markdown(f"<div class='highlight-winner'><h1>👑 {win} 👑</h1></div>", unsafe_allow_html=True)
                    bw = pm["3RD"]["h"] if pm["3RD"]["sh"] > pm["3RD"]["sa"] else pm["3RD"]["a"]
                    bl = pm["3RD"]["a"] if pm["3RD"]["sh"] > pm["3RD"]["sa"] else pm["3RD"]["h"]
                    rest = ranking[4:] if len(ranking) > 4 else []
                    st.dataframe(calculate_final_stats([win, los, bw, bl] + rest), use_container_width=True)
                else:
                    s1 = st.number_input("G1", key="sf1"); s2 = st.number_input("G2", key="sf2")
                    if st.button("Uložiť FIN"): 
                        if not pm["3RD"]["played"]: st.error("Najprv 3. miesto!")
                        else: pm["FIN"]["h"], pm["FIN"]["a"], pm["FIN"]["sh"], pm["FIN"]["sa"], pm["FIN"]["played"] = w1, w2, s1, s2, True; st.rerun()

with st.sidebar:
    st.error("⚠️ NEREFRESHOVAŤ!")
    if st.button("REŠTART"): st.session_state.clear(); st.rerun()
