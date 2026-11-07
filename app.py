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
# Note : Pour lier l'app, il faudra coller l'URL de votre Google Sheets 
# dans les "Secrets" de votre tableau de bord Streamlit Cloud.
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_patrimoine = conn.read(ttl=300) # Rafraîchissement automatique toutes les 5 min
except:
    st.error("📥 Veuillez lier votre Google Sheets dans les paramètres 'Secrets' de Streamlit.")
    st.stop()

# ==========================================
# INTERFACE DE L'APPLICATION (3 ONGLETS MOBILE)
# ==========================================
onglet1, onglet2, onglet3 = st.tabs(["📊 Synthèse", "💳 Actifs", "➕ Ajouter un Actif"])

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
    ticker = row["Ticker"]
    quantite = float(row["Quantite"])
    pru_eur = float(row["PRU"])
    nom = row["Nom"]
    theme = row["Theme"]
    broker = row["Broker"]
    enveloppe = row["Enveloppe"]
    
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
        "Enveloppe": enveloppe, "Type Enveloppe": enveloppe_active, "Quantite": quantite
    })

df_complet = pd.DataFrame(data_graphique)

# ------------------------------------------
# CONTENU DE L'ONGLET 2 : LES COMPTES
# ------------------------------------------
with onglet2:
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
# CONTENU DE L'ONGLET 3 : FORMULAIRE D'AJOUT MOBILE (Chaque Vendredi)
# ------------------------------------------
with onglet3:
    st.subheader("➕ Ajouter une nouvelle ligne")
    st.markdown("Remplissez ce formulaire pour insérer un achat directement depuis votre téléphone.")
    
    with st.form("ajout_actif_form", clear_on_submit=True):
        n_broker = st.selectbox("Courtier / Broker", ["Trade Republic", "XTB"])
        n_env = st.selectbox("Enveloppe fiscale", ["CTO", "PEA"])
        n_ticker = st.text_input("Ticker Yahoo Finance (ex: NVDA, AAPL, Air Liquide -> AI.PA)").upper().strip()
        n_nom = st.text_input("Nom de l'entreprise (ex: Nvidia)")
        n_theme = st.selectbox("Thème / Secteur Économique", ["Aérospatial", "Technologie", "Matériaux", "Énergie", "Matières premières", "Liquidités"])
        n_qte = Skinner = st.number_input("Quantité achetée", min_value=0.000001, step=0.01, format="%.6f")
        n_pru = st.number_input("Prix de Revient Unitaire (PRU en €)", min_value=0.01, step=0.1)
        
        bouton_valider = st.form_submit_form_button = st.form_submit_button("🚀 Valider et Enregistrer l'achat")
        
        if bouton_valider:
            if n_ticker and n_nom and n_qte > 0:
                # Création de la nouvelle ligne de données
                nouvel_actif = pd.DataFrame([{
                    "Ticker": n_ticker, "Nom": n_nom, "Quantite": n_qte,
                    "PRU": n_pru, "Enveloppe": n_env, "Theme": n_theme, "Broker": n_broker
                }])
                # Fusion et envoi automatique vers Google Sheets
                df_maj = pd.concat([df_patrimoine, nouvel_actif], ignore_index=True)
                conn.update(data=df_maj)
                st.success(f"✅ {n_nom} a été ajouté avec succès ! L'application se met à jour...")
                st.rerun()
            else:
                st.error("❌ Veuillez remplir toutes les cases avant de valider.")
