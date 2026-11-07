import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
from streamlit_gsheets import GSheetsConnection

# Configuration de la page
st.set_page_config(page_title="Mon Patrimoine Automatique", page_icon="🏦", layout="centered")

st.title("Patrimoine total")

# ==========================================
# CONNEXION À VOTRE BASE DE DONNÉES GOOGLE SHEETS
# ==========================================
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_patrimoine = conn.read(ttl=60) # Rafraîchissement automatique (1 min)
except:
    st.error("📥 Veuillez lier votre Google Sheets dans les paramètres 'Secrets' de Streamlit.")
    st.stop()

# Nettoyage des lignes vides éventuelles du Sheets
df_patrimoine = df_patrimoine.dropna(subset=["Ticker"])

# ==========================================
# Classification thématique personnalisée
# ==========================================
INFOS_ENTREPRISES = {
    "RKLB": {"nom": "Rocket Lab", "theme": "Aérospatial"},
    "SNDK": {"nom": "SanDisk", "theme": "Technologie"},
    "MP": {"nom": "MP Materials", "theme": "Matériaux"},
    "SU.PA": {"nom": "Schneider Electric", "theme": "Énergie"},
    "PPFB.DE": {"nom": "Or", "theme": "Matières premières"},
    "NBIS": {"nom": "Nebius Group", "theme": "Technologie"},
    "NOK": {"nom": "Nokia", "theme": "Technologie"},
    "VIE.PA": {"nom": "Veolia", "theme": "Énergie"},
    "CASH_TR": {"nom": "Espèces / Liquidités", "theme": "Liquidités"}
}

# ==========================================
# INTERFACE DE L'APPLICATION (4 ONGLETS MOBILE)
# ==========================================
onglet1, onglet2, onglet3, onglet4 = st.tabs(["📊 Synthèse", "💳 Actifs", "➕ Acheter", "➖ Vendre"])

# CONVERTISSEUR DE DEVISES GLOBAL (USD -> EUR)
@st.cache_data(ttl=3600)
def obtenir_taux_change():
    try:
        data = yf.Ticker("EURUSD=X")
        return 1 / data.history(period="1d")["Close"].iloc[-1]
    except:
        return 0.93

taux_usd_to_eur = obtenir_taux_change()

# Traitement des données financières en arrière-plan
total_actuel = 0.0
total_investi = 0.0
data_graphique = []

for _, row in df_patrimoine.iterrows():
    ticker = str(row["Ticker"]).strip()
    quantite = float(row["Quantite"])
    pru_eur = float(row["PRU"])
    nom = str(row["Nom"])
    theme = str(row["Theme"])
    broker = str(row["Broker"])
    enveloppe = str(row["Enveloppe"])
    
    if quantite <= 0:
        continue
        
    if ticker == "CASH_TR":
        valeur_actuelle = quantite
        cout_achat = quantite
        plus_value = 0.0
        pourcentage_gain = 0.0
        enveloppe_active = "Cash"
    else:
        enveloppe_active = enveloppe
        ticker_data = yf.Ticker(ticker)
        info_h = ticker_data.history(period="1d")
        
        if info_h.empty:
            continue
            
        prix_cloture = info_h["Close"].iloc[-1]
        devise = ticker_data.info.get("currency", "EUR")
        prix_eur = prix_cloture * taux_usd_to_eur if devise == "USD" else prix_cloture
        
        valeur_actuelle = prix_eur * quantite
        cout_achat = pru_eur * quantite
        plus_value = valeur_actuelle - cout_achat
        pourcentage_gain = (plus_value / cout_achat) * 100 if cout_achat > 0 else 0
        
    total_actuel += valeur_actuelle
    total_investi += cout_achat
    
    data_graphique.append({
        "Ticker": ticker, "Actif": nom, "Thème": theme,
        "Valeur (€)": valeur_actuelle, "PlusValue": plus_value,
        "GainPct": pourcentage_gain, "Broker": broker,
        "Enveloppe": enveloppe, "Type Enveloppe": enveloppe_active, "Quantite": quantite, "PRU": pru_eur
    })

if data_graphique:
    df_complet = pd.DataFrame(data_graphique)
else:
    df_complet = pd.DataFrame()

# ------------------------------------------
# CONTENU DE L'ONGLET 2 : LES COMPTES (ACTIFS)
# ------------------------------------------
with onglet2:
    if not df_complet.empty:
        for b in df_complet["Broker"].unique():
            st.subheader(b)
            df_b = df_complet[df_complet["Broker"] == b]
            for _, r in df_b.iterrows():
                if r["Ticker"] == "CASH_TR":
                    st.metric(label=f"{r['Actif']} — Disponible", value=f"{r['Valeur (€)']:.2f} €")
                else:
                    st.metric(
                        label=f"{r['Actif']} ({r['Ticker']}) — {r['Quantite']} parts | {r['Enveloppe']}",
                        value=f"{r['Valeur (€)']:.2f} €",
                        delta=f"{r['PlusValue']:.2f} € ({r['GainPct']:.1f}%)"
                    )
            st.divider()
    else:
        st.info("Aucun actif en portefeuille actuellement.")

# ------------------------------------------
# CONTENU DE L'ONGLET 1 : SYNTHÈSE GLOBALE
# ------------------------------------------
with onglet1:
    st.subheader("Patrimoine actualisé")
    pnl_global = total_actuel - total_investi
    pnl_global_pct = (pnl_global / total_investi) * 100 if total_investi > 0 else 0
    
    c1, c2 = st.columns(2)
    c1.metric("Valeur Totale (Titres + Cash)", f"{total_actuel:.2f} €")
    c2.metric("Plus-Value Globale", f"{pnl_global:.2f} €", delta=f"{pnl_global_pct:.2f}%")
    st.divider()
    
    if not df_complet.empty:
        couleurs = ['#2563eb', '#f97316', '#a855f7', '#10b981', '#ef4444', '#eab308', '#6366f1', '#ec4899', '#6b7280']
        
        st.subheader("Répartition par Actif")
        f1 = px.pie(df_complet, values="Valeur (€)", names="Actif", hole=0.5, color_discrete_sequence=couleurs)
        f1.update_traces(textposition='outside', texttemplate='<b>%{label}</b><br>%{percent}')
        f1.update_layout(showlegend=False, margin=dict(t=40, b=40, l=40, r=40), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(f1, use_container_width=True)
        st.divider()
        
        st.subheader("Répartition par Thème")
        df_t = df_complet.groupby("Thème")["Valeur (€)"].sum().reset_index()
        f2 = px.pie(df_t, values="Valeur (€)", names="Thème", hole=0.5, color_discrete_sequence=couleurs)
        f2.update_traces(textposition='outside', texttemplate='<b>%{label}</b><br>%{percent}')
        f2.update_layout(showlegend=False, margin=dict(t=40, b=40, l=40, r=40), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(f2, use_container_width=True)
        st.divider()
        
        st.subheader("Répartition par enveloppe")
        df_e = df_complet.groupby("Type Enveloppe")["Valeur (€)"].sum().reset_index()
        f3 = px.pie(df_e, values="Valeur (€)", names="Type Enveloppe", hole=0, color_discrete_map={"CTO": "#2563eb", "PEA": "#10b981", "Cash": "#6b7280"})
        f3.update_traces(textposition='inside', textinfo='percent')
        f3.update_layout(showlegend=True, legend=dict(x=0.99, y=0.01, xanchor="right", yanchor="bottom"), margin=dict(t=20, b=20, l=20, r=20), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(f3, use_container_width=True)

# ------------------------------------------
# CONTENU DE L'ONGLET 3 : FORMULAIRE D'ACHAT
# ------------------------------------------
with onglet3:
    st.subheader("➕ Acheter / Ajouter une ligne")
    with st.form("ajout_actif_form", clear_on_submit=True):
        n_broker = st.selectbox("Courtier / Broker", ["Trade Republic", "XTB"])
        n_env = st.selectbox("Enveloppe fiscale", ["CTO", "PEA"])
        n_ticker = st.text_input("Ticker Yahoo (ex: RKLB, SU.PA, NVDA)").upper().strip()
        n_nom = st.text_input("Nom de l'entreprise")
        n_theme = st.selectbox("Thème / Secteur", ["Aérospatial", "Technologie", "Matériaux", "Énergie", "Matières premières", "Liquidités"])
        n_qte = st.number_input("Quantité achetée", min_value=0.000001, format="%.6f", step=0.01)
        n_pru = st.number_input("Prix de Revient Unitaire (PRU en €)", min_value=0.01, step=0.1)
        
        if st.form_submit_button("🚀 Enregistrer l'achat"):
            if n_ticker and n_nom and n_qte > 0:
                mask = (df_patrimoine["Ticker"] == n_ticker) & (df_patrimoine["Broker"] == n_broker) & (df_patrimoine["Enveloppe"] == n_env)
                if mask.any():
                    idx = df_patrimoine[mask].index
                    qte_existante = float(df_patrimoine.loc[idx, "Quantite"])
                    pru_existant = float(df_patrimoine.loc[idx, "PRU"])
                    
                    nouvelle_qte = qte_existante + n_qte
                    nouveau_pru = ((qte_existante * pru_existant) + (n_qte * n_pru)) / nouvelle_qte
                    
                    df_patrimoine.loc[idx, "Quantite"] = nouvelle_qte
                    df_patrimoine.loc[idx, "PRU"] = nouveau_pru
                else:
                    nouvel_actif = pd.DataFrame([{"Ticker": n_ticker, "Nom": n_nom, "Quantite": n_qte, "PRU": n_pru, "Enveloppe": n_env, "Theme": n_theme, "Broker": n_broker}])
                    df_patrimoine = pd.concat([df_patrimoine, nouvel_actif], ignore_index=True)
                
                conn.update(data=df_patrimoine)
                st.success(f"✅ {n_nom} ajouté/renforcé avec succès !")
                st.rerun()
            else:
                st.error("❌ Veuillez remplir les cases Ticker, Nom et Quantité.")

# ------------------------------------------
# CONTENU DE L'ONGLET 4 : FORMULAIRE DE VENTE
# ------------------------------------------
with onglet4:
    st.subheader("➖ Vendre / Alléger une ligne")
    
    if not df_complet.empty:
        lignes_vendables = df_complet[df_complet["Ticker"] != "CASH_TR"]
    else:
        lignes_vendables = pd.DataFrame()
    
    if not lignes_vendables.empty:
        options_vente = lignes_vendables.apply(lambda r: f"{r['Actif']} ({r['Ticker']}) — {r['Quantite']:.4f} parts dispos [{r['Broker']}]", axis=1).tolist()
        choix_actif = st.selectbox("Sélectionnez la ligne à vendre", options_vente)
        idx_selectionne = options_vente.index(choix_actif)
        actif_a_vendre = lignes_vendables.iloc[idx_selectionne]
        
        with st.form("vente_actif_form", clear_on_submit=True):
            v_qte = st.number_input("Quantité à vendre", min_value=0.000001, max_value=float(actif_a_vendre["Quantite"]), format="%.6f", step=0.01)
            v_prix = st.number_input("Prix de vente unitaire (€)", min_value=0.01, step=0.1, value=float(actif_a_vendre["PRU"]))
            basculer_en_cash = st.checkbox("💵 Transférer automatiquement l'argent récupéré dans vos 'Espèces / Liquidités'", value=True)
            
            if st.form_submit_button("🔥 Confirmer la vente"):
                mask_sheets = (df_patrimoine["Ticker"] == actif_a_vendre["Ticker"]) & (df_patrimoine["Broker"] == actif_a_vendre["Broker"])
                idx_sheets = df_patrimoine[mask_sheets].index
                
                # Correction pour éviter l'erreur de série d'index dans .loc
                ancienne_qte = float(df_patrimoine.loc[idx_sheets[0], "Quantite"])
                nouvelle_qte = ancienne_qte - v_qte
                montant_recupere = v_qte * v_prix
                
                if nouvelle_qte <= 0.0001:
                    df_patrimoine = df_patrimoine.drop(idx_sheets)
                else:
                    df_patrimoine.loc[idx_sheets, "Quantite"] = nouvelle_qte
                
                if basculer_en_cash:
                    mask_cash = (df_patrimoine["Ticker"] == "CASH_TR")
                    if mask_cash.any():
                        idx_cash = df_patrimoine[mask_cash].index
                        df_patrimoine.loc[idx_cash, "Quantite"] = float(df_patrimoine.loc[idx_cash[0], "Quantite"]) + montant_recupere
                
                conn.update(data=df_patrimoine)
                st.success("🎉 Vente enregistrée avec succès !")
                st.rerun()
    else:
        st.info("Aucune action ou ETF en portefeuille à vendre pour le moment.")
