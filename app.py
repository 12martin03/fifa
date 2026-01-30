import streamlit as st
import pandas as pd
import itertools
import random

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
if 'group_standings_snapshot' not in st.session_state:
    st.session_state.group_standings_snapshot = [] # Pre uloženie poradia 5. a 6. miesta

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
    """Tabuľka len pre skupinu"""
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
                    data[h]["Body"] += 1
                    data[a]["Body"] += 1
    
    df = pd.DataFrame.from_dict(data, orient='index')
    df["+/-"] = df["G+"] - df["G-"]
    df = df.sort_values(by=["Body", "+/-", "G+"], ascending=False)
    df.index.name = "Meno"
    return df

def calculate_final_stats(final_ranking):
    """
    Vypočíta celkové štatistiky (Skupina + Playoff)
    final_ranking: zoznam mien zoradený od 1. miesta po posledné
    """
    # 1. Inicializácia
    stats = {p["name"]: {"Tím": p["team"], "Z": 0, "G+": 0, "G-": 0, "Výhry": 0, "Remízy": 0, "Prehry": 0} for p in st.session_state.players}
    
    # 2. Pomocná funkcia na spracovanie zápasu
    def process_match(h, a, sh, sa):
        if h in stats and a in stats:
            stats[h]["Z"] += 1; stats[a]["Z"] += 1
            stats[h]["G+"] += sh; stats[a]["G+"] += sa
            stats[h]["G-"] += sa; stats[a]["G-"] += sh
            
            if sh > sa:
                stats[h]["Výhry"] += 1
                stats[a]["Prehry"] += 1
            elif sa > sh:
                stats[a]["Výhry"] += 1
                stats[h]["Prehry"] += 1
            else:
                stats[h]["Remízy"] += 1
                stats[a]["Remízy"] += 1

    # 3. Prejdi Skupinu
    for m in st.session_state.matches:
        if m["played"]:
            process_match(m["home"], m["away"], m["score_home"], m["score_away"])

    # 4. Prejdi Playoff
    pm = st.session_state.playoff_matches
    for key in pm:
        m = pm[key]
        if m["played"] and m["h"] is not None and m["a"] is not None:
             process_match(m["h"], m["a"], m["sh"], m["sa"])

    # 5. Vytvor DataFrame zoradený podľa final_ranking
    data_list = []
    for rank, name in enumerate(final_ranking, 1):
        if name in stats:
            row = stats[name]
            row["Meno"] = name
            row["Poradie"] = f"{rank}."
            row["+/-"] = row["G+"] - row["G-"]
            data_list.append(row)
            
    df = pd.DataFrame(data_list)
    # Usporiadanie stĺpcov
    df = df[["Poradie", "Meno", "Tím", "Z", "Výhry", "Remízy", "Prehry", "G+", "G-", "+/-"]]
    df.set_index("Poradie", inplace=True)
    return df

# --- 1. FÁZA: REGISTRÁCIA ---
if st.session_state.stage == "REGISTRATION":
    st.title("⚽ FIFA Turnaj - Nebo vol. 4⚽")
    st.info("Vyplň mená a tímy. Ak hráte 3, pôjde sa rovno finále. Ak 4+, ide sa Playoff.")
    
    with st.form("reg_form"):
        temp_data = []
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown("**Hráč 1**")
            n1 = st.text_input("Meno", key="n1"); t1 = st.text_input("Tím", key="t1")
            temp_data.append({"name": n1, "team": t1})
        with c2:
            st.markdown("**Hráč 2**")
            n2 = st.text_input("Meno", key="n2"); t2 = st.text_input("Tím", key="t2")
            temp_data.append({"name": n2, "team": t2})
        with c3:
            st.markdown("**Hráč 3**")
            n3 = st.text_input("Meno", key="n3"); t3 = st.text_input("Tím", key="t3")
            temp_data.append({"name": n3, "team": t3})

        st.write("") 
        c4, c5, c6 = st.columns(3)
        with c4:
            st.markdown("**Hráč 4**")
            n4 = st.text_input("Meno", key="n4"); t4 = st.text_input("Tím", key="t4")
            temp_data.append({"name": n4, "team": t4})
        with c5:
            st.markdown("**Hráč 5**")
            n5 = st.text_input("Meno", key="n5"); t5 = st.text_input("Tím", key="t5")
            temp_data.append({"name": n5, "team": t5})
        with c6:
            st.markdown("**Hráč 6**")
            n6 = st.text_input("Meno", key="n6"); t6 = st.text_input("Tím", key="t6")
            temp_data.append({"name": n6, "team": t6})
        
        st.write("")
        submit = st.form_submit_button("Let's goooooooooo 🎲", use_container_width=True, type="primary")
        
        if submit:
            valid_players = [p for p in temp_data if p['name'].strip() != ""]
            names = [p['name'] for p in valid_players]
            
            if len(names) != len(set(names)):
                 st.error("Mená hráčov musia byť unikátne!")
            elif len(valid_players) < 3:
                st.error("Musíte byť aspoň traja!")
            else:
                st.session_state.players = valid_players
                st.session_state.player_count = len(valid_players)
                st.session_state.matches = generate_schedule(valid_players)
                st.session_state.stage = "GROUP"
                st.rerun()

# --- 2. FÁZA: SKUPINA ---
elif st.session_state.stage == "GROUP":
    st.title("🔥 Skupinová Fáza")
    
    count = st.session_state.player_count
    limit = 2 if count == 3 else 4 
    
    col_matches, col_table = st.columns([1, 1])
    
    with col_table:
        st.subheader("📊 Tabuľka")
        df = calculate_group_standings()
        
        def highlight_top(s):
            return ['background-color: #d4edda' if i < limit else '' for i in range(len(s))]

        st.dataframe(df[["Tím", "Z", "G+", "G-", "+/-", "Body"]].style.apply(highlight_top, axis=0), use_container_width=True, height=300)
        
        if count == 3:
            st.caption("🟢 Prví dvaja postupujú priamo do FINÁLE.")
        else:
            st.caption("🟢 Prví štyria postupujú do Semifinále.")
        
        total_matches = len(st.session_state.matches)
        played_matches = sum(1 for m in st.session_state.matches if m["played"])
        matches_left = total_matches - played_matches
        
        if matches_left == 0:
            st.success("Skupina ukončená!")
            if st.button("🏆 Prejsť do ĎALŠEJ FÁZY", type="primary", use_container_width=True):
                # Uložíme si kompletné poradie zo skupiny (potrebujeme pre 5. a 6. miesto)
                st.session_state.group_standings_snapshot = df.index.tolist()
                # Seeds pre playoff sú len prví X
                st.session_state.playoff_seeds = df.index[:limit].tolist() 
                st.session_state.stage = "PLAYOFF"
                st.rerun()
        else:
             st.info(f"Zostáva odohrať: {matches_left}")

    with col_matches:
        st.subheader("🎮 Rozpis zápasov")
        matches_sorted = sorted(enumerate(st.session_state.matches), key=lambda x: x[1]['played'])
        for i, match in matches_sorted:
            with st.container(border=True):
                if match["played"]:
                    st.markdown(f"✅ **{match['home']}** {match['score_home']} : {match['score_away']} **{match['away']}**")
                    if st.button("Opraviť", key=f"fix_{i}"):
                        match["played"] = False
                        st.rerun()
                else:
                    st.markdown(f"**{match['home']}** vs **{match['away']}**")
                    c1, c2, c3 = st.columns([2,2,2])
                    with c1: s1 = st.number_input("D", key=f"h_{i}", min_value=0, step=1)
                    with c2: s2 = st.number_input("H", key=f"a_{i}", min_value=0, step=1)
                    with c3: 
                        st.write("")
                        st.write("")
                        if st.button("Uložiť", key=f"btn_{i}", type="primary"):
                            match["score_home"] = s1; match["score_away"] = s2; match["played"] = True
                            st.rerun()

# --- 3. FÁZA: PLAYOFF ---
elif st.session_state.stage == "PLAYOFF":
    seeds = st.session_state.playoff_seeds
    count = st.session_state.player_count
    pm = st.session_state.playoff_matches
    group_ranking = st.session_state.group_standings_snapshot

    # --- VARIANTA A: 3 HRÁČI ---
    if count == 3:
        st.title("🏆 VEĽKÉ FINÁLE")
        if "FINAL_3P" not in pm:
            pm["FINAL_3P"] = {"h": seeds[0], "a": seeds[1], "sh": 0, "sa": 0, "played": False}
        
        fin = pm["FINAL_3P"]
        st.markdown(f"<h2 style='text-align: center'>{fin['h']} vs {fin['a']}</h2>", unsafe_allow_html=True)
        st.write("")
        
        if fin["played"]:
            # Vyhodnotenie
            winner = fin['h'] if fin['sh'] > fin['sa'] else fin['a']
            loser = fin['a'] if fin['sh'] > fin['sa'] else fin['h']
            third = group_ranking[2] # Tretí zo skupiny
            
            st.balloons()
            st.markdown(f"<div class='highlight-winner'><h1>👑 VÍŤAZ: {winner} 👑</h1></div>", unsafe_allow_html=True)
            st.success(f"Konečný výsledok: {fin['sh']} : {fin['sa']}")
            
            st.divider()
            
            # --- CELKOVÁ TABUĽKA ---
            st.markdown("<h2 class='final-stats-header'>📊 CELKOVÉ ŠTATISTIKY TURNAJA</h2>", unsafe_allow_html=True)
            final_order = [winner, loser, third]
            final_df = calculate_final_stats(final_order)
            st.dataframe(final_df, use_container_width=True)
            
        else:
            c1, c2 = st.columns(2)
            with c1: s1 = st.number_input(f"Góly {fin['h']}", min_value=0, key="f3_h")
            with c2: s2 = st.number_input(f"Góly {fin['a']}", min_value=0, key="f3_a")
            st.write("")
            if st.button("Ukončiť turnaj", type="primary", use_container_width=True):
                fin["sh"] = s1; fin["sa"] = s2; fin["played"] = True
                st.rerun()

    # --- VARIANTA B: 4+ HRÁČOV ---
    else:
        st.title("⚽ PLAY-OFF PAVÚK ⚽")
        if not pm:
            pm["SF1"] = {"h": seeds[0], "a": seeds[3], "sh": 0, "sa": 0, "played": False}
            pm["SF2"] = {"h": seeds[1], "a": seeds[2], "sh": 0, "sa": 0, "played": False}
            pm["3RD"] = {"h": None, "a": None, "sh": 0, "sa": 0, "played": False}
            pm["FINAL"] = {"h": None, "a": None, "sh": 0, "sa": 0, "played": False}

        st.markdown("### SEMIFINÁLE")
        c1, c2 = st.columns(2)
        with c1:
            st.info(f"SF1: **{seeds[0]}** vs **{seeds[3]}**")
            if pm["SF1"]["played"]:
                st.success(f"**{pm['SF1']['sh']} : {pm['SF1']['sa']}**")
            else:
                s1 = st.number_input(f"{seeds[0]}", key="sf1_h", min_value=0)
                s2 = st.number_input(f"{seeds[3]}", key="sf1_a", min_value=0)
                if st.button("Uložiť SF1"):
                    pm["SF1"]["sh"] = s1; pm["SF1"]["sa"] = s2; pm["SF1"]["played"] = True
                    st.rerun()
        with c2:
            st.info(f"SF2: **{seeds[1]}** vs **{seeds[2]}**")
            if pm["SF2"]["played"]:
                st.success(f"**{pm['SF2']['sh']} : {pm['SF2']['sa']}**")
            else:
                s1 = st.number_input(f"{seeds[1]}", key="sf2_h", min_value=0)
                s2 = st.number_input(f"{seeds[2]}", key="sf2_a", min_value=0)
                if st.button("Uložiť SF2"):
                    pm["SF2"]["sh"] = s1; pm["SF2"]["sa"] = s2; pm["SF2"]["played"] = True
                    st.rerun()

        st.divider()

        if pm["SF1"]["played"] and pm["SF2"]["played"]:
            sf1_win = pm["SF1"]["h"] if pm["SF1"]["sh"] > pm["SF1"]["sa"] else pm["SF1"]["a"]
            sf1_los = pm["SF1"]["a"] if pm["SF1"]["sh"] > pm["SF1"]["sa"] else pm["SF1"]["h"]
            sf2_win = pm["SF2"]["h"] if pm["SF2"]["sh"] > pm["SF2"]["sa"] else pm["SF2"]["a"]
            sf2_los = pm["SF2"]["a"] if pm["SF2"]["sh"] > pm["SF2"]["sa"] else pm["SF2"]["h"]

            c3, c4 = st.columns(2)
            
            with c3:
                st.markdown("### 🥉 O 3. Miesto")
                st.warning(f"**{sf1_los}** vs **{sf2_los}**")
                if pm["3RD"]["played"]:
                    st.success(f"**{pm['3RD']['sh']} : {pm['3RD']['sa']}**")
                else:
                    s3_h = st.number_input(f"{sf1_los}", key="3rd_h", min_value=0)
                    s3_a = st.number_input(f"{sf2_los}", key="3rd_a", min_value=0)
                    if st.button("Uložiť Bronz"):
                        pm["3RD"]["sh"] = s3_h; pm["3RD"]["sa"] = s3_a; pm["3RD"]["played"] = True
                        st.rerun()

            with c4:
                st.markdown("### 🏆 FINÁLE")
                st.markdown(f"### **{sf1_win}** vs **{sf2_win}**")
                
                # Zobrazíme finále až keď je uložený Bronz (aby bola tabuľka kompletná)
                if pm["FINAL"]["played"]:
                    winner = sf1_win if pm["FINAL"]["sh"] > pm["FINAL"]["sa"] else sf2_win
                    loser = sf2_win if winner == sf1_win else sf1_win
                    
                    # Logika pre 3. a 4. miesto
                    if pm["3RD"]["played"]:
                        bronze_winner = pm["3RD"]["h"] if pm["3RD"]["sh"] > pm["3RD"]["sa"] else pm["3RD"]["a"]
                        bronze_loser = pm["3RD"]["a"] if pm["3RD"]["sh"] > pm["3RD"]["sa"] else pm["3RD"]["h"]
                    else:
                        bronze_winner = "TBD"; bronze_loser = "TBD"

                    st.balloons()
                    st.markdown(f"<div class='highlight-winner'><h1>👑 {winner} 👑</h1></div>", unsafe_allow_html=True)
                    st.success(f"Výsledok: {pm['FINAL']['sh']} : {pm['FINAL']['sa']}")
                    
                    st.divider()
                    
                    # --- CELKOVÁ TABUĽKA ---
                    st.markdown("<h2 class='final-stats-header'>📊 CELKOVÉ ŠTATISTIKY TURNAJA</h2>", unsafe_allow_html=True)
                    
                    # Zostavíme poradie
                    final_order = [winner, loser, bronze_winner, bronze_loser]
                    # Pridáme 5. a 6. miesto zo skupiny (ak existujú)
                    if len(group_ranking) > 4:
                        final_order.extend(group_ranking[4:])
                    
                    final_df = calculate_final_stats(final_order)
                    st.dataframe(final_df, use_container_width=True)

                else:
                    f_h = st.number_input(f"{sf1_win}", key="fin_h", min_value=0)
                    f_a = st.number_input(f"{sf2_win}", key="fin_a", min_value=0)
                    if st.button("Uložiť FINÁLE", type="primary"):
                        if not pm["3RD"]["played"]:
                            st.error("Najprv ulož zápas o 3. miesto!")
                        else:
                            pm["FINAL"]["sh"] = f_h; pm["FINAL"]["sa"] = f_a; pm["FINAL"]["played"] = True
                            st.rerun()

# --- SIDEBAR INFO ---
with st.sidebar:
    st.error("⚠️ NEZATVÁRAJ ANI NEREFRESHUJ STRÁNKU, LEBO SA VYMAŽÚ ÚDAJE!")
    if st.button("AK POTREBUJEŠ, KLIKNI PRE RESET"):
        st.session_state.clear()
        st.rerun()
