from typing import Optional
import streamlit as st
import pandas as pd
import json
from supabase import create_client, Client

# ==========================================
# 0. CONFIGURATION DE LA PAGE STREAMLIT
# ==========================================
st.set_page_config(
    page_title="L.E.Y.L.A. - Serveur Central Multimodaux",
    page_icon="🌐",
    layout="wide"
)

# Import sécurisé du satellite (recherche_ia.py)
try:
    from recherche_ia import rechercher_sur_le_web
except ImportError:
    def rechercher_sur_le_web(historique):
        return {"texte": "Module satellite indisponible temporairement, Mon Professeur."}

# ==========================================
# 0.B SYSTEME D'ACTIVATION ET CODES COOPÉRATIVES
# ==========================================
STRUCTURES_AUTORISEES = {
    "SOC-2026": {"nom": "Coopérative SOCOAMO", "code_db": "SOCOAMO", "type": "COOP"},
    "NEC-2026": {"nom": "Coopérative NECAB", "code_db": "NECAB", "type": "COOP"},
    "TIA-2026": {"nom": "Coopérative TIASSALÉ", "code_db": "TIASSALE", "type": "COOP"},
    "SOU-2026": {"nom": "Coopérative SOUBRÉ", "code_db": "SOUBRE", "type": "COOP"},
    "LAK-2026": {"nom": "Coopérative LAKOTA", "code_db": "LAKOTA", "type": "COOP"},
    "AGRI-SUPER": {"nom": "Cabinet AGRIFORCE (Direction)", "code_db": "ALL", "type": "ADMIN"}
}

if "structure_active" not in st.session_state:
    st.session_state["structure_active"] = None

# Écran de verrouillage si aucun code valide n'est saisi
if not st.session_state["structure_active"]:
    st.title("🔐 Authentification - Serveur Central L.E.Y.L.A.")
    st.markdown("##### Entrez le code d'activation attribué à votre structure pour accéder aux données.")
    
    col_code, col_btn = st.columns([2, 1])
    with col_code:
        code_saisi = st.text_input("Code d'accès structure :", type="password", placeholder="Ex: SOC-2026")
    with col_btn:
        st.write("")
        st.write("")
        if st.button("🔓 Déverrouiller L.E.Y.L.A.", type="primary"):
            if code_saisi in STRUCTURES_AUTORISEES:
                st.session_state["structure_active"] = STRUCTURES_AUTORISEES[code_saisi]
                st.success(f"Accès autorisé : {STRUCTURES_AUTORISEES[code_saisi]['nom']}")
                st.rerun()
            else:
                st.error("Code invalide. Veuillez contacter le Cabinet AGRIFORCE.")
    st.stop()

structure_courante = st.session_state["structure_active"]

# ==========================================
# 1. CONNEXION À SUPABASE (CLOUD)
# ==========================================
@st.cache_resource
def init_supabase() -> Optional[Client]:
    """Initialise le client Supabase à partir des secrets Streamlit."""
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"Erreur de configuration des secrets Supabase : {e}")
        return None

supabase = init_supabase()

def charger_donnees_isolees(module_choisi: str, code_structure_filtre: str) -> pd.DataFrame:
    """Récupère la table unique Supabase et isole strictement les données selon la coopérative et le module."""
    if not supabase:
        return pd.DataFrame()
    try:
        response = supabase.table("producteurs_parcelles").select("*").execute()
        data = response.data
        
        if not data:
            return pd.DataFrame()

        df_global = pd.DataFrame(data)

        # 1. Filtre strict par coopérative
        if code_structure_filtre != "ALL":
            col_coop = "code_cooperative" if "code_cooperative" in df_global.columns else "code_db"
            if col_coop in df_global.columns:
                df_global = df_global[df_global[col_coop] == code_structure_filtre]

        if df_global.empty:
            return pd.DataFrame()

        # 2. Harmonisation et détection des colonnes de module
        # On vérifie module_execute, module_type ou le champ interne dans observations_diagnostic/donnees_module
        col_module = "module_execute" if "module_execute" in df_global.columns else "module_type"
        
        if col_module not in df_global.columns:
            # Si la colonne n'existe pas encore, on évite d'exposer toutes les données
            return pd.DataFrame()

        df_global[col_module] = df_global[col_module].fillna("").astype(str)

        # 3. Mappage strict des motifs par module
        MOTIFS_MODULES = {
            "Géolocalisation & RDUE (Parcelles)": "géo|parcelle|rdue|superficie",
            "Diagnostic Phytosanitaire": "diagnostic|phyto|pathologie|sante",
            "Estimation de Rendement": "rendement|estimation|recolte",
            "Plan de Développement (PDC)": "pdc|développement|plan"
        }

        motif = MOTIFS_MODULES.get(module_choisi, "")

        if motif:
            df_mod = df_global[df_global[col_module].str.contains(motif, case=False, na=False)].copy()
        else:
            df_mod = pd.DataFrame()

        # 4. RETOUR STRICT : On renvoie df_mod tel quel (s'il est vide, on renvoie un tableau vide, JAMAIS df_global)
        return df_mod.reset_index(drop=True)

    except Exception as e:
        st.error(f"Erreur lors de la récupération des données Supabase : {e}")
        return pd.DataFrame()



# ==========================================
# 2. MOTEUR D'ANALYSE DÉCISIONNELLE LEÏLA (PDC)
# ==========================================

def extraire_etapes_pdc(donnees_producteur: dict) -> dict:
    """Extraction robuste et récursive des données PDC peu importe le format de stockage."""
    raw_pdc = {}
    
    # 1. Récupération de la source de données principale
    source = (
        donnees_producteur.get("observations_diagnostic") or 
        donnees_producteur.get("reponses_pdc") or 
        donnees_producteur.get("donnees_module") or 
        donnees_producteur.get("reponses") or 
        {}
    )
    
    # Décodage si c'est une chaîne JSON
    if isinstance(source, str):
        try:
            raw_pdc = json.loads(source)
        except Exception:
            raw_pdc = {}
    elif isinstance(source, dict):
        raw_pdc = source

    # Si les clés sont au premier niveau du dictionnaire global
    if not raw_pdc:
        raw_pdc = donnees_producteur

    # 2. Fonction utilitaire de recherche insensible à la casse et profonde
    def chercher_valeur(cles_possibles, default=None):
        # Recherche directe au premier niveau
        for key, val in raw_pdc.items():
            if val is not None and str(val).strip() != "":
                if any(k.lower() in key.lower() for k in cles_possibles):
                    return val
                
        # Recherche dans les sous-étapes (ex: etape_1_foyer)
        for sub_k, sub_v in raw_pdc.items():
            if isinstance(sub_v, dict):
                for k, v in sub_v.items():
                    if v is not None and str(v).strip() != "":
                        if any(kp.lower() in k.lower() for kp in cles_possibles):
                            return v
        return default

    def to_float(val, default=0.0):
        try:
            if val is None: return default
            # Nettoyage des espaces et symboles monétaires
            clean_val = str(val).replace("FCFA", "").replace("F", "").replace(" ", "").replace(",", ".").strip()
            return float(clean_val)
        except Exception:
            return default

    def to_int(val, default=0):
        try:
            return int(to_float(val, default))
        except Exception:
            return default

    # Extraction sécurisée avec alias multiples pour chaque champ
    return {
        "foyer": to_int(chercher_valeur(["foyer", "taille_foyer", "membres"], 1)),
        "superficie": to_float(chercher_valeur(["superficie", "surface", "ha"], 0.0)),
        "statut_foncier": str(chercher_valeur(["statut_foncier", "foncier", "propriete"], "Inconnu")),
        "sante_verger": to_int(chercher_valeur(["sante", "score_pression", "pression_sanitaire", "pathologie"], 0)),
        "age_verger": to_int(chercher_valeur(["age", "age_moyen", "age_verger"], 0)),
        "maladies": chercher_valeur(["maladies", "maladies_presentes", "symptomes"], []),
        "toposequence": str(chercher_valeur(["toposequence", "relief", "relief_parcelle"], "Plateau")),
        "materiel": str(chercher_valeur(["materiel", "etat_materiel", "equipement"], "Moyen")),
        "eau_proche": bool(chercher_valeur(["eau", "point_eau", "source_eau"], False)),
        "rev_cacao": to_float(chercher_valeur(["rev_cacao", "revenu_annuel_cacao", "revenu_cacao"], 0.0)),
        "rev_hors_cacao": to_float(chercher_valeur(["rev_hors_cacao", "revenu_annuel_hors_cacao", "autres_revenus"], 0.0)),
        "chg_ferme": to_float(chercher_valeur(["chg_ferme", "charges_exploitation", "charges_ferme"], 0.0)),
        "chg_foyer": to_float(chercher_valeur(["chg_foyer", "charges_foyer", "depenses_foyer"], 0.0)),
        "credit_demande": to_float(chercher_valeur(["credit", "montant_credit", "besoin_financement"], 0.0))
    }

def leila_analyse_pdc_metier(donnees_producteur: dict):
    """Moteur d'Analyse Intégrale Leïla avec affichage Markdown propre."""
    if not isinstance(donnees_producteur, dict):
        st.error("⚠️ Données invalides pour l'analyse.")
        return

    p = extraire_etapes_pdc(donnees_producteur)
    
    # Nettoyage des chaînes pour éviter le bug d'affichage Markdown
    nom = str(donnees_producteur.get("nom_producteur") or donnees_producteur.get("producteur") or "Producteur Inconnu").strip()
    code = str(donnees_producteur.get("code_producteur") or donnees_producteur.get("code_ccc") or "N/A").strip()

    st.markdown(f"### 🤖 Diagnostic L.E.Y.L.A. pour **{nom}** (`{code}`)")
    st.markdown("---")

    rev_tot = p["rev_cacao"] + p["rev_hors_cacao"]
    chg_tot = p["chg_ferme"] + p["chg_foyer"]
    solde = rev_tot - chg_tot
    part_cacao = (p["rev_cacao"] / rev_tot * 100) if rev_tot > 0 else 0.0

    st.markdown("**💰 Bilan Financier du Foyer (FCFA)**")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Revenu Total", f"{rev_tot:,.0f} F".replace(",", " "))
    c2.metric("Charges Totales", f"{chg_tot:,.0f} F".replace(",", " "))
    c3.metric("Solde Net Disponible", f"{solde:,.0f} F".replace(",", " "))
    c4.metric("Part Cacao", f"{part_cacao:.0f}%")

    st.markdown("**🌱 Diagnostic Parcelle & Pression Phytosanitaire**")
    if p["sante_verger"] > 6:
        st.error(f"• **Pression Sanitaire Critique ({p['sante_verger']}/10)** : Action corrective immédiate requise.")
    elif p["sante_verger"] > 0:
        st.warning(f"• **Pression Sanitaire Modérée ({p['sante_verger']}/10)** : Surveillance recommandée.")
    else:
        st.success("• **Pression Sanitaire Maîtrisée (0/10)**.")

    maladies_str = str(p["maladies"])
    if p["toposequence"] in ["Bas-fond", "Bas de versant"] and ("Pourriture" in maladies_str or "Phytophthora" in maladies_str):
        st.error("🔥 **Risque Majeur Phytophthora :** Zone humide + Pourriture brune active. Drainer et traiter.")

    st.markdown("**💡 Feuille de Route Opérationnelle Recommandée**")
    plan = []

    if rev_tot > 0 and solde < 100000:
        plan.append("Orienter vers des intrants subventionnés et formations au compostage (marge financière faible).")
    elif rev_tot > 0:
        plan.append("Capacité financière suffisante : Valider le plan de fertilisation raisonnée.")
    else:
        plan.append("Données financières incomplètes : Réévaluer les revenus et charges lors du prochain passage.")

    if p["age_verger"] >= 25:
        plan.append("Verger âgé (>= 25 ans) : Programmer un plan de régénération progressive ou de recépage.")

    if p["materiel"] in ["Vétuste", "Inexistant"]:
        plan.append("Dotation prioritaire en petit matériel de taille (scies/podo-coupes).")

    for idx, action in enumerate(plan, 1):
        st.info(f"**Action {idx} :** {action}")


# ==========================================
# 3. INTERFACE DU SERVEUR CENTRAL
# ==========================================
st.title("🌐 L.E.Y.L.A. - Centre de Commandement Global")
st.markdown(f"*Espace de travail connecté : **{structure_courante['nom']}***")

st.sidebar.title(f"🏢 {structure_courante['nom']}")
if st.sidebar.button("🚪 Changer de structure / Déconnexion"):
    st.session_state["structure_active"] = None
    st.rerun()

st.sidebar.divider()

code_filtre_db = structure_courante["code_db"]
if structure_courante["type"] == "ADMIN":
    st.sidebar.header("👁️ Super-Vision AGRIFORCE")
    choix_coop_admin = st.sidebar.selectbox(
        "Sélectionner la vue coopérative :",
        ["Toutes les coopératives", "SOCOAMO", "NECAB", "TIASSALE", "SOUBRE", "LAKOTA"]
    )
    if choix_coop_admin != "Toutes les coopératives":
        code_filtre_db = choix_coop_admin

st.sidebar.header("🎛️ Sélection du Module")
module_choisi = st.sidebar.selectbox(
    "Choisir le domaine d'analyse",
    [
        "Géolocalisation & RDUE (Parcelles)",
        "Diagnostic Phytosanitaire",
        "Estimation de Rendement",
        "Plan de Développement (PDC)"
    ]
)

df_filtered = charger_donnees_isolees(module_choisi, code_filtre_db)

st.subheader(f"📊 Module actif : {module_choisi}")

with st.expander(f"📁 Afficher / Masquer les données brutes ({len(df_filtered)} enregistrement(s))", expanded=False):
    if not df_filtered.empty:
        st.dataframe(df_filtered, use_container_width=True)
    else:
        st.info(f"Aucune donnée enregistrée pour le module {module_choisi} dans cette structure.")

st.divider()

# ==========================================
# 4. MODULE DÉDIÉ PDC : ANALYSE PAR PRODUCTEUR
# ==========================================
if "PDC" in module_choisi:
    col_titre, col_reset = st.columns([2.5, 1.5])
    
    with col_titre:
        st.subheader("🔍 Consultation Approfondie d'un PDC Synchronisé")
        
    with col_reset:
        if st.button("🔄 Réinitialiser l'affichage PDC", use_container_width=True):
            st.cache_data.clear()
            st.cache_resource.clear()
            if "pdc_select_box" in st.session_state:
                del st.session_state["pdc_select_box"]
            st.success("Interface réinitialisée !")
            st.rerun()

        if structure_courante.get("type") == "ADMIN":
            with st.expander("⚠️ Zone Dangereuse (Admin)"):
                if st.button("🚨 Purger les PDC sur Supabase", type="secondary", use_container_width=True):
                    reinitialiser_table_pdc_supabase()

    # Si la base est vide après la purge, l'interface se vide instantanément
    if df_filtered.empty:
        st.info("ℹ️ Aucun enregistrement PDC disponible. La base de données est propre.")
    else:
        df_pdc = df_filtered.copy()
        
        col_nom = "nom_producteur" if "nom_producteur" in df_pdc.columns else df_pdc.columns[0]
        col_code = "code_producteur" if "code_producteur" in df_pdc.columns else None
        col_id = "id" if "id" in df_pdc.columns else None

        # Filtrage des lignes valides
        df_pdc = df_pdc[df_pdc[col_nom].notna() & (df_pdc[col_nom].astype(str).str.strip() != "")].copy()
        
        if not df_pdc.empty:
            def construire_libelle(row):
                nom_str = str(row[col_nom]).strip()
                code_str = f" | Code: {row[col_code]}" if col_code and pd.notna(row[col_code]) and str(row[col_code]).strip() != "" else ""
                id_str = f" | ID #{row[col_id]}" if col_id and pd.notna(row[col_id]) else ""
                return f"{nom_str}{code_str}{id_str}"

            df_pdc["cle_unique"] = df_pdc.apply(construire_libelle, axis=1)
            
            OPTION_DEFAUT = "--- Sélectionner un producteur ---"
            options_disponibles = [OPTION_DEFAUT] + df_pdc["cle_unique"].tolist()

            with st.form("form_selection_pdc"):
                choix_utilisateur = st.selectbox(
                    "Sélectionner la fiche d'un producteur :",
                    options_disponibles,
                    key="pdc_select_box"
                )
                
                soumis = st.form_submit_button("Analyser le PDC avec Leïla 🤖", type="primary", use_container_width=True)

            if soumis:
                if choix_utilisateur == OPTION_DEFAUT:
                    st.warning("Veuillez choisir un producteur dans la liste.")
                else:
                    ligne_selectionnee = df_pdc[df_pdc["cle_unique"] == choix_utilisateur].iloc[0].to_dict()
                    leila_analyse_pdc_metier(ligne_selectionnee)
        else:
            st.warning("Aucun nom de producteur valide trouvé dans les enregistrements.")

    st.divider()



# ==========================================
# 5. INTERACTION AVEC LE SATELLITE IA (HUB UNIVERSEL)
# ==========================================
st.subheader("🤖 Assistant IA L.E.Y.L.A. (Analyse Experte Ciblée)")
st.markdown(f"Posez vos questions en lien direct avec le module **{module_choisi}**.")

user_query = st.text_input("Votre requête pour le satellite :")

if st.button("Lancer l'analyse du satellite"):
    if not user_query:
        st.warning("Veuillez saisir une question ou une consigne.")
    else:
        with st.spinner(f"Le satellite analyse exclusivement les données de {module_choisi}..."):
            try:
                contexte_donnees = df_filtered.to_string(index=False) if not df_filtered.empty else "Aucune donnée disponible pour ce module."
                
                prompt_complet = (
                    f"Tu es L.E.Y.L.A., l'intelligence artificielle centrale pour la gestion agricole.\n"
                    f"Structure active : {structure_courante['nom']}\n"
                    f"Module en cours d'analyse : {module_choisi}\n"
                    f"Données brutes exclusives à ce module :\n"
                    f"{contexte_donnees}\n\n"
                    f"Consigne / Question de l'administrateur : {user_query}\n\n"
                    f"Fournis une analyse professionnelle, claire et axée uniquement sur ce module."
                )
                
                historique_fictif = [{"role": "user", "content": prompt_complet}]
                reponse_satellite = rechercher_sur_le_web(historique_fictif)
                
                st.success("Rapport du Satellite L.E.Y.L.A. :")
                st.write(reponse_satellite.get("texte", ""))
                
            except Exception as e:
                st.error(f"Erreur lors de la communication avec le satellite : {e}")
