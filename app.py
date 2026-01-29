import streamlit as st
import pandas as pd
import itertools
import random

# --- KONFIGURÁCIA ---
st.set_page_config(page_title="FIFA Turnaj Manager", page_icon="🏆", layout="wide")

# --- SESSION STATE ---
if 'stage' not in st.session_state:
    st.session_state.stage = "REGISTRATION"  # REGISTRATION, GROUP, PLAYOFF
if 'players' not in st.session_state:
    st.session_state.players = []
if 'matches' not in st.session_state:
    st.session_state.matches = [] # Zoznam zápasov skupiny
if 'playoff_matches' not in st.session_state:
    st.session_state.playoff_matches = {} # SF1, SF2, FINAL, 3RD

# --- FUNKCIE ---

def generate_schedule(players):
    """Vygeneruje 'každý s každým' a zamieša poradie"""
    names = [p['name'] for p in players]
    # Vytvorí všetky kombinácie dvojíc
    pairs = list(itertools.combinations(names, 2))
    random.shuffle(pairs) # Zamiešať poradie zápasov
    
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

def calculate_standings():
    """Vypočíta tabuľku zo skupiny"""
    data = {p["name"]: {"Tím": p["team"], "Z": 0, "G+": 0, "G-": 0, "Body": 0} for p in st.session_state.players}
    
    for m in st.session_state.matches:
        if m["played"]:
            h, a = m["home"], m["away"]
            sh, sa = m["score_home"], m["score_away"]
            
            data[h]["Z"] += 1; data[a]["Z"] += 1
            data[h]["G+"] += sh; data[a]["G+"] += sa
            data[h]["G-"] += sa; data[a]["G-"] += sh
            
            if sh > sa: data[h]["Body"] += 3
            elif sa > sh: data[a]["Body"] += 3
            else:
                data[h]["Body"] += 1
                data[a]["Body"] += 1
    
    df = pd.DataFrame.from_dict(data, orient='index')
    df["+/-"] = df["G+"] - df["G-"]
    df = df.sort_values(by=["Body", "+/-", "G+"], ascending=False)
    df.index.name = "Meno"
    return df

# --- 1. FÁZA: REGISTRÁCIA ---
if st.session_state.stage == "REGISTRATION":
    st.title("⚽ FIFA Turnaj - Registrácia")
    st.info("Zadajte presne 5 hráčov.")
    
    with st.form("reg_form"):
        cols = st.columns(5)
        temp_data = []
        for i, col in enumerate(cols):
            with col:
                n = st.text_input(f"Meno {i+1}")
                t = st.text_input(f"Tím {i+1}")
                temp_data.append({"name": n, "team": t})
        
        if st.form_submit_button("Generovať turnaj 🎲", use_container_width=True):
            # Validácia: Musia byť vyplnené aspoň mená
            valid_players = [p for p in temp_data if p['name']]
            if len(valid_players) != 5:
                st.error("Pre tento formát (Playoff 1-4) musíte byť presne piati!")
            else:
                st.session_state.players = valid_players
                st.session_state.matches = generate_schedule(valid_players)
                st.session_state.stage = "GROUP"
                st.rerun()

# --- 2. FÁZA: SKUPINA ---
elif st.session_state.stage == "GROUP":
    st.title("🔥 Skupinová Fáza")
    
    col_matches, col_table = st.columns([1, 1])
    
    with col_table:
        st.subheader("📊 Tabuľka")
        df = calculate_standings()
        st.dataframe(df[["Tím", "Z", "G+", "G-", "+/-", "Body"]], use_container_width=True)
        
        # Kontrola, či sú odohrané všetky zápasy
        total_matches = len(st.session_state.matches)
        played_matches = sum(1 for m in st.session_state.matches if m["played"])
        matches_left = total_matches - played_matches
        
        st.metric("Odohrané", f"{played_matches}/{total_matches}")
        
        if matches_left == 0:
            st.success("Skupina ukončená!")
            if st.button("🏆 Prejsť do PLAYOFF", type="primary"):
                # Uložíme poradie pre playoff
                top4 = df.index[:4].tolist() # Zoberie mená prvých 4
                st.session_state.playoff_seeds = top4
                st.session_state.stage = "PLAYOFF"
                st.rerun()
        else:
            st.info(f"Ešte treba odohrať {matches_left} zápasov.")

    with col_matches:
        st.subheader("🎮 Rozpis zápasov")
        
        for i, match in enumerate(st.session_state.matches):
            with st.container():
                # Ak je zápas odohraný, ukážeme len výsledok
                if match["played"]:
                    st.success(f"✅ {match['home']} **{match['score_home']} : {match['score_away']}** {match['away']}")
                else:
                    # Ak nie je, ukážeme formulár
                    st.markdown(f"**Zápas {i+1}:** {match['home']} vs {match['away']}")
                    c1, c2, c3 = st.columns([2,2,2])
                    with c1: s1 = st.number_input("D", key=f"h_{i}", min_value=0, step=1)
                    with c2: s2 = st.number_input("H", key=f"a_{i}", min_value=0, step=1)
                    with c3: 
                        st.write("")
                        st.write("")
                        if st.button("Zapísať", key=f"btn_{i}"):
                            match["score_home"] = s1
                            match["score_away"] = s2
                            match["played"] = True
                            st.rerun()
                st.divider()

# --- 3. FÁZA: PLAYOFF ---
elif st.session_state.stage == "PLAYOFF":
    st.title("⚔️ PLAYOFF")
    seeds = st.session_state.playoff_seeds
    # seeds[0] = 1. miesto, seeds[3] = 4. miesto atď.
    
    # Inicializácia Playoff štruktúry ak ešte nie je
    if not st.session_state.playoff_matches:
        st.session_state.playoff_matches = {
            "SF1": {"h": seeds[0], "a": seeds[3], "sh": 0, "sa": 0, "played": False}, # 1 vs 4
            "SF2": {"h": seeds[1], "a": seeds[2], "sh": 0, "sa": 0, "played": False}, # 2 vs 3
            "3RD": {"h": None, "a": None, "sh": 0, "sa": 0, "played": False},
            "FINAL": {"h": None, "a": None, "sh": 0, "sa": 0, "played": False}
        }

    pm = st.session_state.playoff_matches

    # --- SEMIFINÁLE ---
    st.header("1. Semifinále")
    c1, c2 = st.columns(2)
    
    # SF1
    with c1:
        st.subheader(f"SF1: {seeds[0]} vs {seeds[3]}")
        if pm["SF1"]["played"]:
            st.success(f"Výsledok: {pm['SF1']['sh']} : {pm['SF1']['sa']}")
        else:
            s1 = st.number_input(f"{seeds[0]}", key="sf1_h")
            s2 = st.number_input(f"{seeds[3]}", key="sf1_a")
            if st.button("Uložiť SF1"):
                pm["SF1"]["sh"] = s1
                pm["SF1"]["sa"] = s2
                pm["SF1"]["played"] = True
                st.rerun()

    # SF2
    with c2:
        st.subheader(f"SF2: {seeds[1]} vs {seeds[2]}")
        if pm["SF2"]["played"]:
            st.success(f"Výsledok: {pm['SF2']['sh']} : {pm['SF2']['sa']}")
        else:
            s1 = st.number_input(f"{seeds[1]}", key="sf2_h")
            s2 = st.number_input(f"{seeds[2]}", key="sf2_a")
            if st.button("Uložiť SF2"):
                pm["SF2"]["sh"] = s1
                pm["SF2"]["sa"] = s2
                pm["SF2"]["played"] = True
                st.rerun()

    st.divider()

    # --- FINÁLE A 3. MIESTO ---
    if pm["SF1"]["played"] and pm["SF2"]["played"]:
        # Určenie postupujúcich
        sf1_win = pm["SF1"]["h"] if pm["SF1"]["sh"] > pm["SF1"]["sa"] else pm["SF1"]["a"]
        sf1_los = pm["SF1"]["a"] if pm["SF1"]["sh"] > pm["SF1"]["sa"] else pm["SF1"]["h"]
        
        sf2_win = pm["SF2"]["h"] if pm["SF2"]["sh"] > pm["SF2"]["sa"] else pm["SF2"]["a"]
        sf2_los = pm["SF2"]["a"] if pm["SF2"]["sh"] > pm["SF2"]["sa"] else pm["SF2"]["h"]

        c3, c4 = st.columns(2)
        
        # Zápas o 3. miesto
        with c3:
            st.header("🥉 O 3. Miesto")
            st.write(f"{sf1_los} vs {sf2_los}")
            if pm["3RD"]["played"]:
                st.warning(f"Výsledok: {pm['3RD']['sh']} : {pm['3RD']['sa']}")
            else:
                s3_h = st.number_input(f"Góly {sf1_los}", key="3rd_h")
                s3_a = st.number_input(f"Góly {sf2_los}", key="3rd_a")
                if st.button("Uložiť Bronz"):
                    pm["3RD"]["sh"] = s3_h
                    pm["3RD"]["sa"] = s3_a
                    pm["3RD"]["played"] = True
                    st.rerun()

        # FINÁLE
        with c4:
            st.header("🏆 FINÁLE")
            st.write(f"**{sf1_win} vs {sf2_win}**")
            if pm["FINAL"]["played"]:
                st.balloons()
                winner = sf1_win if pm["FINAL"]["sh"] > pm["FINAL"]["sa"] else sf2_win
                st.success(f"VÍŤAZ TURNAJA: {winner}")
                st.markdown(f"### 👑 {winner} 👑")
            else:
                f_h = st.number_input(f"Góly {sf1_win}", key="fin_h")
                f_a = st.number_input(f"Góly {sf2_win}", key="fin_a")
                if st.button("Uložiť FINÁLE"):
                    pm["FINAL"]["sh"] = f_h
                    pm["FINAL"]["sa"] = f_a
                    pm["FINAL"]["played"] = True
                    st.rerun()

# --- RESET (SIDEBAR) ---
with st.sidebar:
    st.error("⚠️ Refresh stránky vymaže celý turnaj!")
    if st.button("Reštartovať od nuly"):
        st.session_state.clear()
        st.rerun()
