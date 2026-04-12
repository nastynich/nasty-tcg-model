"""
Nasty TCG Dashboard — v9
"""
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.preprocessing import MinMaxScaler
from sklearn.linear_model import Ridge
import io, time, requests
from datetime import date

st.set_page_config(page_title="Nasty TCG — Fair Value", page_icon="🎴", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
* { font-family: 'Inter', sans-serif; }

/* ── Sidebar ── */
section[data-testid="stSidebar"] { background: #0f0f1a !important; }
section[data-testid="stSidebar"] * { color: #ccd0e0 !important; }
section[data-testid="stSidebar"] .stSlider > div > div { background: #1e1e3a !important; }

/* ── Bouton vert ── */
div[data-testid="stButton"] > button {
    background: linear-gradient(135deg,#1a8a45,#27ae60) !important;
    color: #fff !important; font-weight: 700 !important;
    font-size: 15px !important; border: none !important;
    border-radius: 10px !important; padding: 12px !important;
    width: 100% !important; margin-bottom: 4px !important;
}
div[data-testid="stButton"] > button:hover { background: linear-gradient(135deg,#27ae60,#2ecc71) !important; }
div[data-testid="stButton"] > button:disabled { background: #1e1e30 !important; color: #444 !important; }

/* ── Total badge ── */
.total-pill {
    display:inline-block; padding:5px 14px; border-radius:20px;
    font-size:14px; font-weight:700; margin:6px 0 12px 0;
}
.pill-ok   { background:#0d3d25; color:#2ecc71; }
.pill-low  { background:#3d2200; color:#e67e22; }
.pill-high { background:#3d0d0d; color:#e74c3c; }

/* ── Card UI ── */
.card-wrap {
    background: #12122a;
    border: 1px solid #1e1e40;
    border-radius: 14px;
    overflow: hidden;
    margin-bottom: 12px;
    transition: border-color .2s, transform .15s;
}
.card-wrap:hover { border-color: #4a90e2; transform: translateY(-2px); }

.card-img-container {
    width: 100%;
    background: #0a0a1a;
    display: flex;
    justify-content: center;
    align-items: center;
    padding: 10px;
}
.card-img-container img { width:100%; border-radius:8px; }

.card-body { padding: 10px 12px 12px 12px; }

.card-name {
    font-size: 14px; font-weight: 700; color: #eeeeff;
    margin: 0 0 2px 0; white-space: nowrap;
    overflow: hidden; text-overflow: ellipsis;
}
.card-set-line { font-size: 11px; color: #6677aa; margin-bottom: 8px; }

.price-block {
    display: flex; justify-content: space-between;
    align-items: flex-end; margin-bottom: 8px;
}
.price-market { font-size: 13px; color: #8899bb; }
.price-fv     { font-size: 18px; font-weight: 700; color: #4af0c4; line-height:1; }
.price-label  { font-size: 10px; color: #556677; }

.ecart-pill {
    display:inline-block; padding:3px 10px;
    border-radius:20px; font-size:13px; font-weight:700;
    margin-bottom:8px;
}
.pill-gem  { background:#0d2e1a; color:#2ecc71; }
.pill-over { background:#2e0d0d; color:#e74c3c; }
.pill-fair { background:#2e2200; color:#f39c12; }

/* Dropdown détails */
details { margin-top: 6px; }
summary {
    font-size: 11px; color: #4a90e2; cursor: pointer;
    list-style: none; padding: 3px 0;
}
summary::-webkit-details-marker { display:none; }
.detail-body {
    margin-top:6px; padding: 8px; background:#0a0a20;
    border-radius:8px; font-size:11px; color:#8899bb;
    line-height: 1.8;
}
</style>
""", unsafe_allow_html=True)

from pokemon_popularity import get_popularity_score
from meta_scores import get_meta_score
from grading_ratio import get_grading_difficulty, get_gem_rate

# ─── Constantes ───────────────────────────────────────────────
RARITY_PULL = {
    "Special Illustration Rare": 1/1440, "Hyper Rare": 1/360,
    "Illustration Rare": 1/144, "Ultra Rare": 1/72, "Double Rare": 1/48,
    "ACE SPEC Rare": 1/72, "Rare Holo VMAX": 1/36, "Rare Holo VSTAR": 1/36,
    "Rare Holo V": 1/24, "Rare Holo EX": 1/24, "Rare Holo": 1/12,
    "Rare": 1/10, "Shiny Rare": 1/60, "Shiny Ultra Rare": 1/180,
    "Amazing Rare": 1/40, "Radiant Rare": 1/36,
    "Trainer Gallery Rare Holo": 1/72, "Promo": 1/1,
}

ARTIST_SCORES = {
    "mika pikazo":10.0,"tetsu kayama":9.5,"akira komayama":9.5,
    "ryota murayama":9.0,"nagomibana":9.0,"sowsow":8.8,"5ban graphics":8.5,
    "sanosuke sakuma":8.5,"atsushi furusawa":8.0,"yuka morii":8.0,
    "ryo ueda":7.8,"kiichiro":7.5,"yuu nishida":7.5,"anesaki dynamic":7.5,
    "kagemaru himeno":7.5,"tomokazu komiya":7.5,"hitoshi ariga":7.5,
    "eri yamaki":7.0,"kawayoo":7.0,"ayaka yoshida":7.0,"teeziro":7.0,
    "keiichiro ito":7.0,"yusuke ohmura":7.0,"atsuko nishida":7.5,
    "mitsuhiro arita":7.0,"shigenori negishi":6.8,"suwama ichiro":6.5,
    "kouki saitou":6.5,"mizue":6.5,"aya kusube":6.5,"tomoya kitakaze":6.5,
    "0313":6.5,"daisuke ito":6.5,"narumi sato":6.5,"shizurow":6.5,
    "luncheon":6.5,"uninori":6.0,"shibuzoh":6.0,"hasuno":6.0,"kodama":6.0,
    "nekoramune":6.0,"tika matsuno":6.0,"gossan":6.0,"makoto iguchi":6.0,
    "naoyo kimura":6.5,"keiko fukuyama":6.0,"yuri ex":6.5,
    "satoshi nakai":6.0,"hajime kusajima":6.0,"studio bora":6.0,
    "chihiro mori":6.0,"ken sugimori":6.0,"aky cg works":6.5,
    "kirisaki":5.5,"akira egawa":5.5,"yumi takahara":5.0,
}

def get_artist_score(artist):
    a = artist.lower().strip()
    if a in ARTIST_SCORES: return ARTIST_SCORES[a]
    for n, s in ARTIST_SCORES.items():
        if n in a or a in n: return s
    return 4.5

def set_lifecycle_score(rel):
    try:
        p = rel.split("/")
        days = (date.today() - date(int(p[0]),int(p[1]),int(p[2]))).days
        if days < 60:   return 7.0
        if days < 120:  return 9.0
        if days < 270:  return 8.0
        if days < 450:  return 6.5
        if days < 600:  return 5.0
        if days < 730:  return 3.5
        if days < 1095: return 2.5
        return 2.0
    except: return 5.0

def compute_hype(prices):
    signals, label = [], "—"
    for pt in ["holofoil","reverseHolofoil","normal","1stEditionHolofoil"]:
        if pt not in prices: continue
        p = prices[pt]
        low,mid,high,mkt = (p.get(k,0) or 0 for k in ["low","mid","high","market"])
        if mkt <= 0: continue
        if low > 0:
            r = low/mkt
            if r>=0.85:   signals.append(9.5); label="🔥 Très demandée"
            elif r>=0.70: signals.append(7.5); label="📈 Bonne demande"
            elif r>=0.50: signals.append(5.5); label="➡️ Stable"
            elif r>=0.30: signals.append(3.5); label="📉 Faible"
            else:          signals.append(1.5); label="🧊 Peu d'intérêt"
        if high>0: m=high/mkt; signals.append(9.0 if m>=2 else 7.0 if m>=1.5 else 5.5 if m>=1.2 else 4.0)
        if mid>0:  signals.append(8.0 if mkt>mid*1.15 else 6.0 if mkt>mid else 4.5 if mkt>mid*.9 else 3.0)
        break
    return (round(np.mean(signals),1) if signals else 5.0, label)

QUERY = (
    '(set.series:"Scarlet & Violet" OR set.series:"Sword & Shield") '
    '(rarity:"Special Illustration Rare" OR rarity:"Illustration Rare" '
    'OR rarity:"Hyper Rare" OR rarity:"Ultra Rare" OR rarity:"Double Rare" '
    'OR rarity:"ACE SPEC Rare" OR rarity:"Shiny Rare" OR rarity:"Shiny Ultra Rare")'
)
DEFAULTS = {"tier":35,"scarcity":25,"psa10":10,"meta":10,"hype":8,"artist":7,"lifecycle":5}
FCOLS = ["f_scarcity_inv","f_tier","f_artist","f_meta","f_hype","f_psa10","f_lifecycle"]

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_data(max_cards=400):
    rows, seen, page = [], set(), 1
    while len(rows) < max_cards:
        size = min(250, max_cards-len(rows))
        try:
            r = requests.get("https://api.pokemontcg.io/v2/cards",
                params={"q":QUERY,"page":page,"pageSize":size,"orderBy":"-set.releaseDate"},
                timeout=20)
            r.raise_for_status()
            cards = r.json().get("data",[])
        except Exception as e: st.error(f"API : {e}"); break
        if not cards: break
        for c in cards:
            cid = c.get("id","")
            if cid in seen: continue
            seen.add(cid)
            tcp = c.get("tcgplayer",{})
            prices = tcp.get("prices",{})
            mkt = None
            for pt in ["holofoil","reverseHolofoil","normal","1stEditionHolofoil"]:
                if pt in prices and prices[pt].get("market"):
                    mkt = prices[pt]["market"]; break
            if not mkt or mkt<=0: continue
            rar = c.get("rarity","Unknown")
            art = c.get("artist","")
            nm  = c.get("name","?")
            sid = c.get("set",{}).get("id","")
            num = c.get("number","")
            rel = c.get("set",{}).get("releaseDate","")
            hs, hl = compute_hype(prices)
            rows.append({
                "id": cid, "name": nm,
                "set": c.get("set",{}).get("name","?"),
                "series": c.get("set",{}).get("series","?"),
                "release_date": rel, "rarity": rar, "artist": art,
                "f_scarcity": RARITY_PULL.get(rar,1/20),
                "f_tier": get_popularity_score(nm),
                "f_artist": get_artist_score(art),
                "f_meta": get_meta_score(sid, num),
                "f_hype": hs, "hype_label": hl,
                "f_psa10": get_grading_difficulty(rar),
                "gem_rate": round(get_gem_rate(rar)*100),
                "f_lifecycle": set_lifecycle_score(rel),
                "market_price": round(mkt,2),
                "tcgplayer_url": tcp.get("url",""),
                "image_url": c.get("images",{}).get("small",""),
            })
        if len(cards)<size: break
        page+=1; time.sleep(0.15)
    df = pd.DataFrame(rows) if rows else pd.DataFrame()
    if not df.empty:
        df = df.drop_duplicates(subset=["name","set"])
    return df

def model(df, w, gem_t, over_t):
    df = df.copy()
    df["f_scarcity_inv"] = -np.log(df["f_scarcity"])
    sc = MinMaxScaler()
    for c in FCOLS: df[f"{c}_n"] = sc.fit_transform(df[[c]])
    wa = np.array([w[c] for c in FCOLS])
    df["score"] = df[[f"{c}_n" for c in FCOLS]].values.dot(wa) / (wa.sum() or 1)
    X = df[["score"]].values; y = np.log1p(df["market_price"].values)
    m = Ridge(alpha=1.0); m.fit(X,y)
    yp = m.predict(X)
    r2 = max(0, 1-(np.sum((y-yp)**2)/np.sum((y-np.mean(y))**2)))
    df["Vt"] = np.expm1(yp).round(2)
    df["ecart"] = ((df["Vt"]-df["market_price"])/df["market_price"]*100).round(1)

    # Filtre outliers : si l'écart est > 300% ou < -90%, on met en "prix juste" forcé
    # (le modèle Ridge est trop incertain sur les extrêmes)
    df["Signal"] = df.apply(lambda r:
        "fair" if abs(r["ecart"]) > 300 else
        ("gem" if r["ecart"] > gem_t*100 else
         ("over" if r["ecart"] < -over_t*100 else "fair")), axis=1)

    return df, round(r2,3)

def card_html(c, sig):
    ecart = c["ecart"]
    ecart_str = f"+{ecart:.0f}%" if ecart>=0 else f"{ecart:.0f}%"
    pill_cls = {"gem":"pill-gem","over":"pill-over","fair":"pill-fair"}[sig]
    tcg = f'<a href="{c["tcgplayer_url"]}" target="_blank" style="color:#4a90e2;font-size:11px;">TCGPlayer ↗</a>' if c.get("tcgplayer_url") else ""
    img = f'<img src="{c["image_url"]}" style="width:100%;border-radius:8px;display:block;">' if c.get("image_url") else ""
    return f"""
<div class="card-wrap">
  <div class="card-img-container">{img}</div>
  <div class="card-body">
    <div class="card-name" title="{c['name']}">{c['name']}</div>
    <div class="card-set-line">{c['set']}</div>
    <div class="price-block">
      <div>
        <div class="price-label">Marché</div>
        <div class="price-market">${c['market_price']:.2f}</div>
      </div>
      <div style="text-align:right">
        <div class="price-label">Fair Value</div>
        <div class="price-fv">${c['Vt']:.2f}</div>
      </div>
    </div>
    <div><span class="ecart-pill {pill_cls}">{ecart_str}</span></div>
    <details>
      <summary>▾ Détails</summary>
      <div class="detail-body">
        <b>Rareté:</b> {c['rarity']}<br>
        <b>Artiste:</b> {c['artist']}<br>
        <b>Popularité:</b> {c['f_tier']:.1f}/10<br>
        <b>Compétitivité:</b> {c['f_meta']:.1f}/10<br>
        <b>Hype:</b> {c['hype_label']}<br>
        <b>PSA 10 gem rate:</b> {c['gem_rate']:.0f}%<br>
        {tcg}
      </div>
    </details>
  </div>
</div>"""

def grid(df_cards, sig, n=24):
    df_cards = df_cards.head(n)
    if df_cards.empty:
        st.info("Aucune carte dans cette catégorie."); return
    for i in range(0, len(df_cards), 4):
        row = df_cards.iloc[i:i+4]
        cols = st.columns(4)
        for j, (_, c) in enumerate(row.iterrows()):
            with cols[j]:
                st.markdown(card_html(c, sig), unsafe_allow_html=True)

# ─── SIDEBAR ──────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="text-align:center;padding:16px 0 8px 0;">
      <span style="font-size:28px;">🎴</span>
      <div style="font-size:18px;font-weight:700;color:#eeeeff;margin-top:4px;">Nasty TCG</div>
      <div style="font-size:11px;color:#556677;">Fair Value Model</div>
    </div>
    """, unsafe_allow_html=True)

    # ── Poids ──
    st.markdown('<div style="font-size:12px;font-weight:600;color:#8899cc;letter-spacing:1px;margin:12px 0 8px 0;">POIDS DES FACTEURS</div>', unsafe_allow_html=True)
    w_tier      = st.slider("⭐ Popularité",   0,100,DEFAULTS["tier"],     5)
    w_scarcity  = st.slider("🔮 Rareté",        0,100,DEFAULTS["scarcity"], 5)
    w_psa10     = st.slider("💎 Grading PSA",   0,100,DEFAULTS["psa10"],    5)
    w_meta      = st.slider("🏆 Compétitivité", 0,100,DEFAULTS["meta"],     5)
    w_hype      = st.slider("🔥 Hype marché",   0,100,DEFAULTS["hype"],     5)
    w_artist    = st.slider("🎨 Artiste",        0,100,DEFAULTS["artist"],   5)
    w_lifecycle = st.slider("📅 Cycle de vie",  0,100,DEFAULTS["lifecycle"],5)

    total = w_tier+w_scarcity+w_psa10+w_meta+w_hype+w_artist+w_lifecycle
    if total==100:
        st.markdown('<div class="total-pill pill-ok">✅ 100%</div>', unsafe_allow_html=True)
        ok = True
    elif total<100:
        st.markdown(f'<div class="total-pill pill-low">⚠️ {total}% — il manque {100-total}%</div>', unsafe_allow_html=True)
        ok = False
    else:
        st.markdown(f'<div class="total-pill pill-high">❌ {total}% — trop de {total-100}%</div>', unsafe_allow_html=True)
        ok = False

    fetch_btn = st.button("🚀 Lancer l'analyse", disabled=not ok, use_container_width=True)

    # ── Seuils ──
    st.markdown('<div style="font-size:12px;font-weight:600;color:#8899cc;letter-spacing:1px;margin:16px 0 8px 0;">SEUILS</div>', unsafe_allow_html=True)
    gem_t  = st.slider("🟢 Sous-évalué si +X%", 5,60,15,5)
    over_t = st.slider("🔴 Surévalué si -X%",   5,60,15,5)

    # ── Filtres ──
    st.markdown('<div style="font-size:12px;font-weight:600;color:#8899cc;letter-spacing:1px;margin:16px 0 8px 0;">FILTRES</div>', unsafe_allow_html=True)
    min_p = st.number_input("Prix min ($)", 0,1000,5)
    max_p = st.number_input("Prix max ($)", 0,5000,2000)
    filt_rar = st.multiselect("Raretés", [
        "Special Illustration Rare","Illustration Rare","Hyper Rare",
        "Ultra Rare","Double Rare","ACE SPEC Rare","Shiny Rare","Shiny Ultra Rare"
    ])
    filt_meta = st.checkbox("Tournoi seulement", False)

# ─── SESSION ──────────────────────────────────────────────────
if "df" not in st.session_state: st.session_state.df = pd.DataFrame()

if fetch_btn and ok:
    with st.spinner("Chargement... ~20 sec"):
        fetched = fetch_data(400)
    if fetched.empty: st.error("Aucune carte. Vérifie ta connexion.")
    else:
        st.session_state.df = fetched
        st.success(f"✅ {len(fetched)} cartes chargées !")

df_raw = st.session_state.df

if df_raw.empty:
    st.title("🎴 Nasty TCG — Fair Value")
    st.markdown("""
Ajuste les **poids à 100%** dans le menu de gauche, puis clique **Lancer l'analyse**.

| Facteur | Source | Défaut |
|---|---|---|
| ⭐ Popularité | Sondage officiel TPC | **35%** |
| 🔮 Rareté | Pull rates officiels | **25%** |
| 💎 Grading | Gem rate PSA réel | **10%** |
| 🏆 Compétitivité | Limitless TCG | **10%** |
| 🔥 Hype | Triple signal TCGPlayer | **8%** |
| 🎨 Artiste | 80+ illustrateurs | **7%** |
| 📅 Cycle de vie | Âge set / rotation | **5%** |
    """)
    st.stop()

# ─── MODÈLE ───────────────────────────────────────────────────
W = {
    "f_scarcity_inv":w_scarcity/100,"f_tier":w_tier/100,"f_artist":w_artist/100,
    "f_meta":w_meta/100,"f_hype":w_hype/100,"f_psa10":w_psa10/100,"f_lifecycle":w_lifecycle/100,
}
df, r2 = model(df_raw, W, gem_t/100, over_t/100)

# ─── FILTRES ──────────────────────────────────────────────────
df = df[(df["market_price"]>=min_p)&(df["market_price"]<=max_p)]
if filt_rar: df = df[df["rarity"].isin(filt_rar)]
if filt_meta: df = df[df["f_meta"]>1.0]

series_list = ["Toutes"]+sorted(df["series"].dropna().unique().tolist())
col_s, col_r = st.columns([4,1])
with col_s: sel = st.selectbox("Série",series_list, label_visibility="collapsed")
with col_r: st.markdown(f'<div style="padding-top:8px;font-size:12px;color:{"#2ecc71" if r2>.5 else "#f39c12"};">R² {r2:.2f}</div>',unsafe_allow_html=True)
if sel!="Toutes": df=df[df["series"]==sel]

gems  = df[df["Signal"]=="gem"].sort_values("ecart",ascending=False)
overs = df[df["Signal"]=="over"].sort_values("ecart")
fair  = df[df["Signal"]=="fair"].sort_values("ecart",ascending=False)

# ─── MÉTRIQUES ────────────────────────────────────────────────
c1,c2,c3,c4,c5 = st.columns(5)
c1.metric("📦 Analysées",    len(df))
c2.metric("🟢 Sous-évaluées",len(gems))
c3.metric("🟡 Prix juste",   len(fair))
c4.metric("🔴 Surévaluées",  len(overs))
c5.metric("R²",              f"{r2:.2f}")
st.divider()

# ─── ONGLETS ──────────────────────────────────────────────────
t1,t2,t3,t4 = st.tabs([
    f"🟢 Sous-évaluées ({len(gems)})",
    f"🔴 Surévaluées ({len(overs)})",
    f"🟡 Prix juste ({len(fair)})",
    "📊 Graphiques",
])
with t1: grid(gems,"gem")
with t2: grid(overs,"over")
with t3: grid(fair,"fair")
with t4:
    fig,(ax1,ax2)=plt.subplots(1,2,figsize=(12,5),facecolor="#0e0e1a")
    cm={"gem":"#2ecc71","over":"#e74c3c","fair":"#f39c12"}
    for ax in [ax1,ax2]: ax.set_facecolor("#12122a"); ax.tick_params(colors="#aaa")
    for sig,grp in df.groupby("Signal"):
        ax1.scatter(grp["market_price"],grp["Vt"],color=cm.get(sig,"gray"),alpha=.7,s=45,label=sig)
    mv=max(df["market_price"].max(),df["Vt"].max())*1.05
    ax1.plot([0,mv],[0,mv],"w--",lw=.8); ax1.set_xlabel("Prix marché ($)",color="#aaa")
    ax1.set_ylabel("Fair Value ($)",color="#aaa"); ax1.set_title(f"FV vs Prix  R²={r2:.2f}",color="white")
    ax1.legend(facecolor="#1a1a2e",labelcolor="white")
    top20=df.nlargest(20,"ecart")
    ax2.barh(top20["name"],top20["ecart"],color=[cm.get(s,"gray") for s in top20["Signal"]])
    ax2.axvline(0,color="white",lw=.7,ls="--"); ax2.set_xlabel("Écart (%)",color="#aaa")
    ax2.set_title("Top 20 sous-évaluées",color="white"); ax2.invert_yaxis()
    st.pyplot(fig)

st.divider()
with st.expander("📋 Tableau complet"):
    disp=df[["name","set","rarity","market_price","Vt","ecart","Signal"]].copy()
    disp.columns=["Carte","Set","Rareté","Prix($)","FV($)","Écart(%)","Signal"]
    st.dataframe(disp.sort_values("Écart(%)",ascending=False),use_container_width=True,hide_index=True)

buf=io.StringIO(); df.sort_values("ecart",ascending=False).to_csv(buf,index=False)
st.download_button("📥 Exporter CSV",buf.getvalue(),f"fair_value_{date.today()}.csv","text/csv")
