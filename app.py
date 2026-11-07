import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px

# Configuration de la page
st.set_page_config(page_title="Mon Patrimoine", page_icon="🏦", layout="centered")

st.title("Patrimoine total")

# ==========================================
# Classification thématique personnalisée
# ==========================================
INFOS_ENTREPRISES = {
    "RKLB": {"nom": "Rocket Lab", "theme": "Aérospatial"},
    "SNDK": {"nom": "SanDisk", "theme": "Technologie"},
    "MP": {"nom": "MP Materials", "theme": "Matériaux"},
    "SU.PA": {"nom": "Schneider Electric", "theme": "Énergie"},
    "PPFB.DE": {"nom": "iShares Gold", "theme": "Matières premières"},
    "NBIS": {"nom": "Nebius Group", "theme": "Technologie"},
    "NOK": {"nom": "Nokia", "theme": "Technologie"},
    "VIE.PA": {"nom": "Veolia", "theme": "Énergie"},
    "CASH_TR": {"nom": "Espèces / Liquidités", "theme": "Liquidités"}  # Ajout du Cash
}

# ==========================================
# 1. COMPTES-TITRES : VOS VRAIS ACTIFS
# ==========================================
# Vos liquidités de 333,85 € sont ajoutées ici avec un PRU de 1.0
tr_cto = {
    "RKLB": {"quantite": 18, "pru_eur": 61.38},
    "SNDK": {"quantite": 0.583094, "pru_eur": 858.87},
    "MP": {"quantite": 5, "pru_eur": 37.45},
    "SU.PA": {"quantite": 0.612948, "pru_eur": 246.35},
    "PPFB.DE": {"quantite": 1.281086, "pru_eur": 71.03},
    "CASH_TR": {"quantite": 333.85, "pru_eur": 1.0}  # Ligne Cash TR
}

tr_pea = {
    "NBIS": {"quantite": 2, "pru_eur": 110.08},
}

xtb_portfolio = {
    "NOK": {"quantite": 6, "pru_eur": 7.70},
    "VIE.PA": {"quantite": 1, "pru_eur": 32.00},
}

# ==========================================
# 2. CONVERTISSEUR DE DEVISES (USD -> EUR)
# ==========================================
@st.cache_data(ttl=3600)
def obtenir_taux_change():
    try:
        data = yf.Ticker("EURUSD=X")
        taux = 1 / data.history(period="1d")["Close"].iloc[-1]
        return taux
    except:
        return 0.93

taux_usd_to_eur = obtenir_taux_change()

total_actuel = 0.0
total_investi = 0.0
data_graphique = []

# Fonction d'analyse financière des sous-comptes
def analyser_sous_compte(portefeuille, nom_affichage, categorie_graphique, type_enveloppe):
    global total_actuel, total_investi
    
    st.markdown(f"#### {nom_affichage}")
    
    if not portefeuille:
        st.info("Aucun actif enregistré dans cette section.")
        return

    for ticker, infos in portefeuille.items():
        info_ent = INFOS_ENTREPRISES.get(ticker, {"nom": ticker, "theme": "Inconnu"})
        
        # Si c'est du cash, la valeur actuelle est fixe et égale à la quantité d'euros
        if ticker == "CASH_TR":
            prix_actuel_eur = 1.0
            valeur_actuelle_ligne = infos["quantite"]
            cout_achat_ligne = infos["quantite"]
            plus_value_ligne = 0.0
            pourcentage_gain = 0.0
        else:
            ticker_data = yf.Ticker(ticker)
            info_historique = ticker_data.history(period="1d")
            
            if info_historique.empty:
                st.error(f"Impossible de récupérer le prix pour {ticker}")
                continue
                
            prix_cloture = info_historique["Close"].iloc[-1]
            devise = ticker_data.info.get("currency", "EUR")
            
            if devise == "USD":
                prix_actuel_eur = prix_cloture * taux_usd_to_eur
            else:
                prix_actuel_eur = prix_cloture
                
            valeur_actuelle_ligne = prix_actuel_eur * infos["quantite"]
            cout_achat_ligne = infos["pru_eur"] * infos["quantite"]
            plus_value_ligne = valeur_actuelle_ligne - cout_achat_ligne
            pourcentage_gain = (plus_value_ligne / cout_achat_ligne) * 100 if cout_achat_ligne > 0 else 0
        
        total_actuel += valeur_actuelle_ligne
        total_investi += cout_achat_ligne
        
        data_graphique.append({
            "Ticker": ticker,
            "Actif": info_ent["nom"],
            "Thème": info_ent["theme"],
            "Valeur (€)": valeur_actuelle_ligne,
            "Enveloppe": categorie_graphique,
            "Type Enveloppe": type_enveloppe
        })
        
        # Affichage métrique adapté
        if ticker == "CASH_TR":
            st.metric(
                label=f"{info_ent['nom']} — Disponible sur le compte",
                value=f"{valeur_actuelle_ligne:.2f} €"
            )
        else:
            st.metric(
                label=f"{info_ent['nom']} ({ticker}) — {infos['quantite']} parts",
                value=f"{valeur_actuelle_ligne:.2f} €",
                delta=f"{plus_value_ligne:.2f} € ({pourcentage_gain:.1f}%)"
            )

# ==========================================
# 3. INTERFACE DE L'APPLICATION (ONGLETS)
# ==========================================
onglet1, onglet2 = st.tabs(["Synthèse", "Actifs"])

with onglet2:
    st.subheader("Trade Republic")
    analyser_sous_compte(tr_cto, "CTO", "TR - CTO", "CTO")
    analyser_sous_compte(tr_pea, "PEA", "TR - PEA", "PEA")
    st.divider()
    st.subheader("XTB")
    analyser_sous_compte(xtb_portfolio, "CTO", "XTB", "CTO")

with onglet1:
    st.subheader("Patrimoine actualisé")
    
    pnl_global = total_actuel - total_investi
    pnl_global_pourcent = (pnl_global / total_investi) * 100 if total_investi > 0 else 0
    
    c1, c2 = st.columns(2)
    c1.metric("Valeur Totale (Titres + Cash)", f"{total_actuel:.2f} €")
    c2.metric(label="Plus-Value Globale", value=f"{pnl_global:.2f} €", delta=f"{pnl_global_pourcent:.2f}%")
    
    st.divider()
    
    if data_graphique and total_actuel > 0:
        df = pd.DataFrame(data_graphique)
        df = df.sort_values(by="Valeur (€)", ascending=False)
        
        couleurs_premium = ['#2563eb', '#f97316', '#a855f7', '#10b981', '#ef4444', '#eab308', '#6366f1', '#ec4899', '#6b7280']
        
        # 1. Graphique répartition par Actions & Cash
        st.subheader("Répartition par Actif")
        fig_actifs = px.pie(df, values="Valeur (€)", names="Actif", hole=0.5, color_discrete_sequence=couleurs_premium)
        fig_actifs.update_traces(textposition='outside', texttemplate='<b>%{label}</b><br>%{percent}')
        fig_actifs.update_layout(showlegend=False, margin=dict(t=40, b=40, l=40, r=40), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_actifs, use_container_width=True)
        
        st.divider()
        
        # 2. Graphique répartition par THÈME (avec bloc Liquidités)
        st.subheader("Répartition par Thème")
        df_themes = df.groupby("Thème")["Valeur (€)"].sum().reset_index()
        
        fig_themes = px.pie(df_themes, values="Valeur (€)", names="Thème", hole=0.5, color_discrete_sequence=couleurs_premium)
        fig_themes.update_traces(textposition='outside', texttemplate='<b>%{label}</b><br>%{percent}')
        fig_themes.update_layout(showlegend=False, margin=dict(t=40, b=40, l=40, r=40), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_themes, use_container_width=True)
        
        st.divider()
        
        # 3. Graphique répartition par type d'enveloppe (Le Cash augmente la part du CTO)
        st.subheader("Répartition par enveloppe")
        df_enveloppe = df.groupby("Type Enveloppe")["Valeur (€)"].sum().reset_index()
        
        fig_env = px.pie(
            df_enveloppe, 
            values="Valeur (€)", 
            names="Type Enveloppe", 
            hole=0, 
            color_discrete_map={"CTO": "#2563eb", "PEA": "#10b981"}
        )
        fig_env.update_traces(textposition='inside', textinfo='percent')
        fig_env.update_layout(
            showlegend=True,
            legend=dict(x=0.99, y=0.01, xanchor="right", yanchor="bottom"),
            margin=dict(t=20, b=20, l=20, r=20),
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig_env, use_container_width=True)

