import json
from typing import Optional
import pandas as pd
import streamlit as st
from supabase import Client, create_client

# ==========================================
# 0. CONFIGURATION DE LA PAGE STREAMLIT
# ==========================================
st.set_page_config(
    page_title="L.E.Y.L.A. - Serveur Central Multi-Cabinet",
    page_icon="🌐",
    layout="wide",
)

# Initialisation des variables dans st.session_state
if "user" not in st.session_state:
    st.session_state["user"] = None
if "profile" not in st.session_state:
    st.session_state["profile"] = None
if "cabinet_actif" not in st.session_state:
    st.session_state["cabinet_actif"] = None
if "cooperatives_accessibles" not in st.session_state:
    st.session_state["cooperatives_accessibles"] = []

# Import sécurisé du module de recherche satellite
try:
    from recherche_ia import rechercher_sur_le_web
except ImportError:
    def rechercher_sur_le_web(historique):
        return {"texte": "Module satellite indisponible temporairement, Mon Professeur."}


# ==========================================
# 1. CONNEXION À SUPABASE
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


# ==========================================
# 2. ÉCRAN D'AUTHENTIFICATION UNIVERSEL
# ==========================================
if not st.session_state.get("user"):
    st.title("🔐 Authentification Centralisée - L.E.Y.L.A.")
    st.markdown("##### Connectez-vous avec vos identifiants réseau L.E.Y.L.A.")

    with st.form("login_form", clear_on_submit=False):
        col_email, col_pass = st.columns(2)
        with col_email:
            email_input = st.text_input("Adresse Email professionnelle :")
        with col_pass:
            password_input = st.text_input("Mot de passe :", type="password")

        submit_login = st.form_submit_button("🔓 Se connecter", type="primary")

    if submit_login:
        if email_input and password_input and supabase:
            try:
                # 1. Authentification Supabase Auth
                auth_resp = supabase.auth.sign_in_with_password({
                    "email": email_input.strip(), 
                    "password": password_input.strip()
                })
                user = auth_resp.user

                # 2. Récupération du profil utilisateur
                profile_resp = supabase.table("profiles").select("*").eq("id", user.id).execute()
                
                if not profile_resp.data:
                    st.error("Profil utilisateur introuvable dans la base de données.")
                    st.stop()
                    
                profile = profile_resp.data[0]

                if not profile.get("cabinet_id"):
                    st.error("Aucun cabinet associé à cet utilisateur.")
                    st.stop()

                cabinet_id = profile["cabinet_id"]

                # 3. Récupération des informations du cabinet
                cabinet_resp = supabase.table("cabinets").select("*").eq("id", cabinet_id).execute()
                cabinet = cabinet_resp.data[0] if cabinet_resp.data else {"nom": "Cabinet L.E.Y.L.A."}

                # 4. Récupération des coopératives accessibles selon le RÔLE
                if profile.get("role") == "CHEF_COOP" and profile.get("code_cooperative"):
                    # Un chef de coopérative ne voit QUE sa coopérative
                    coops_resp = supabase.table("cooperatives")\
                        .select("*")\
                        .eq("cabinet_id", cabinet_id)\
                        .eq("code_db", profile["code_cooperative"])\
                        .execute()
                else:
                    # Un Admin voit TOUTES les coopératives du cabinet
                    coops_resp = supabase.table("cooperatives")\
                        .select("*")\
                        .eq("cabinet_id", cabinet_id)\
                        .execute()

                # Stockage en session Streamlit
                st.session_state["user"] = user
                st.session_state["profile"] = profile
                st.session_state["cabinet_actif"] = cabinet
                st.session_state["cooperatives_accessibles"] = coops_resp.data or []

                st.success(f"Bienvenue {profile.get('nom_utilisateur', '')} — Cabinet : {cabinet['nom']}")
                st.rerun()

            except Exception as e:
                st.error(f"Échec d'authentification : Identifiants ou accès invalides. ({e})")
        else:
            st.warning("Veuillez saisir votre email et votre mot de passe.")
            
    st.stop()


# ==========================================
# 3. RÉCUPÉRATION DE LA SESSION ACTIVE
# ==========================================
user_profile = st.session_state["profile"]
cabinet_courant = st.session_state["cabinet_actif"]
liste_cooperatives = st.session_state["cooperatives_accessibles"]


# ==========================================
# 4. BARRE LATÉRALE & SÉLECTEUR DE COOPÉRATIVE
# ==========================================
st.sidebar.title(f"🏢 {cabinet_courant['nom']}")
st.sidebar.caption(f"Connecté : {user_profile.get('nom_utilisateur', 'Utilisateur')} ({user_profile.get('role', '')})")

# Construction des options du sélecteur
options_coop = {}

# La "Vue Direction" globale n'est disponible que pour les ADMIN_CABINET
if user_profile.get("role") == "ADMIN_CABINET":
    options_coop["Toutes les coopératives (Vue Direction)"] = "ALL"

for coop in liste_cooperatives:
    options_coop[coop.get("nom", "Coopérative")] = coop.get("code_db", "")

if options_coop:
    coop_selectionnee_label = st.sidebar.selectbox("Sélectionner la Coopérative :", list(options_coop.keys()))
    code_coop_filtre = options_coop[coop_selectionnee_label]
else:
    code_coop_filtre = "ALL"

if st.sidebar.button("Déconnexion"):
    if supabase:
        supabase.auth.sign_out()
    st.session_state.clear()
    st.rerun()



# ==========================================
# 5. FONCTIONS DE GESTION DES QUOTAS & DONNÉES
# ==========================================
def verifier_et_incrementer_quota(cabinet_id: str) -> bool:
    """Vérifie et consomme le quota d'IA au niveau du Cabinet."""
    if not supabase:
        return True

    try:
        res = supabase.table("credits_ia").select("*").eq("cabinet_id", cabinet_id).execute()

        if not res.data:
            return True

        donnees = res.data[0]
        consommation = donnees.get("requetes_utilisees", 0)
        limite = donnees.get("quota_mensuel", 20000)

        if consommation >= limite:
            return False

        supabase.table("credits_ia").update(
            {"requetes_utilisees": consommation + 1}
        ).eq("cabinet_id", cabinet_id).execute()

        return True

    except Exception as e:
        st.warning(f"Suivi des quotas indisponible : {e}")
        return True


def charger_donnees_isolees(module_choisi: str, cabinet_id: str, code_coop_filtre: str) -> pd.DataFrame:
    """Isole et filtre strictement les données par module métier."""
    if not supabase:
        return pd.DataFrame()
    try:
        # 1. Requête globale sur la table
        response = supabase.table("producteurs_parcelles").select("*").execute()
        data = response.data or []

        if not data:
            return pd.DataFrame()

        df = pd.DataFrame(data)

        # 2. Filtrage par coopérative
        col_coop = "cooperative_id" if "cooperative_id" in df.columns else "code_cooperative"
        if col_coop in df.columns and code_coop_filtre and code_coop_filtre != "ALL":
            df = df[df[col_coop].astype(str).str.strip().str.upper() == code_coop_filtre.strip().upper()]

        if df.empty:
            return pd.DataFrame()

        # 3. Mots-clés stricts et exclusifs par module
        MOTIFS_SQL = {
            "Plan de Développement (PDC)": ["pdc"],
            "Géolocalisation & RDUE (Parcelles)": ["géo", "rdue", "geolocalisation"],
            "Diagnostic Phytosanitaire": ["diagnostic", "phyto", "phytosanitaire"],
            "Estimation de Rendement": ["rendement", "estimation"]
        }

        mots_cles = MOTIFS_SQL.get(module_choisi, [module_choisi.lower()])
        cols_a_verifier = [c for c in ["module_type", "module_execute"] if c in df.columns]
        
        if cols_a_verifier:
            masque = False
            for col in cols_a_verifier:
                for mc in mots_cles:
                    masque |= df[col].astype(str).str.lower().str.contains(mc, na=False)
            
            # Retourne uniquement les lignes correspondant au filtre du module
            return df[masque].reset_index(drop=True)

        return pd.DataFrame()

    except Exception as e:
        st.error(f"Erreur lors du chargement des données : {e}")
        return pd.DataFrame()




# ==========================================
# 6. CORPS DE L'APPLICATION STREAMLIT
# ==========================================
st.title(f"🌐 L.E.Y.L.A. Serveur Central — {cabinet_courant['nom']}")

modules = [               
    "Plan de Développement (PDC)",
    "Géolocalisation & RDUE (Parcelles)",
    "Diagnostic Phytosanitaire",
    "Estimation de Rendement"
]

module_actif = st.selectbox("Choisissez le module métier à consulter :", modules)

# Chargement sécurisé et filtré des données
df_affichage = charger_donnees_isolees(
    module_choisi=module_actif,
    cabinet_id=cabinet_courant["id"],
    code_coop_filtre=code_coop_filtre
)

st.subheader(f"Données : {module_actif} ({coop_selectionnee_label})")

if not df_affichage.empty:
    st.dataframe(df_affichage, use_container_width=True)
else:
    st.info("Aucune donnée enregistrée pour cette sélection.")



# ==========================================
# 2. MOTEUR D'ANALYSE DÉCISIONNELLE LEÏLA (PDC 3.0)
# ==========================================

import json
import pandas as pd
import streamlit as st


def extraire_etapes_pdc_avancees(donnees_producteur: dict) -> dict:
    """Extraction intégrale et granulaire des structures complexes du JSON PDC."""
    raw_pdc = {}

    source = (
        donnees_producteur.get("observations_diagnostic")
        or donnees_producteur.get("reponses_pdc")
        or donnees_producteur.get("donnees_module")
        or donnees_producteur.get("reponses")
        or {}
    )

    if isinstance(source, str) and source.strip().startswith("{"):
        try:
            raw_pdc = json.loads(source)
        except Exception:
            raw_pdc = {}
    elif isinstance(source, dict):
        raw_pdc = source

    if not raw_pdc:
        raw_pdc = donnees_producteur

    def to_float(val, default=0.0):
        try:
            if val is None:
                return default
            clean_val = (
                str(val)
                .replace("FCFA", "")
                .replace("F", "")
                .replace(" ", "")
                .replace(",", ".")
                .strip()
            )
            return float(clean_val)
        except Exception:
            return default

    def to_int(val, default=0):
        try:
            return int(to_float(val, default))
        except Exception:
            return default

    desc_expl = raw_pdc.get("description_exploitation") or {}
    if not isinstance(desc_expl, dict):
        desc_expl = {}

    cultures = (
        raw_pdc.get("cultures_et_revenus") or raw_pdc.get("tableau_cultures") or []
    )
    arbres = (
        raw_pdc.get("inventaire_arbres") or raw_pdc.get("tableau_arbres") or []
    )
    sante = raw_pdc.get("sante_cacaoyere") or []
    densite_carres = raw_pdc.get("donnees_densite") or []
    sol_caract = (
        raw_pdc.get("caracteristiques_sol") or raw_pdc.get("df_sol_caract") or []
    )
    depenses_foyer = raw_pdc.get("depenses_foyer") or []
    prod_historique = (
        raw_pdc.get("prod_historique") or raw_pdc.get("df_prod_historique") or []
    )
    plan_action = (
        raw_pdc.get("plan_quinquennal")
        or raw_pdc.get("plan_quinquennal_detail")
        or []
    )

    # --- CORRECTION DE L'EXTRACTION DES SUPERFICIES ---
    surf_totale = to_float(
        desc_expl.get("superficie_totale", raw_pdc.get("superficie", 0.0))
    )
    surf_cacao_prod = to_float(desc_expl.get("superficie_cacao_productif", 0.0))
    surf_cacao_jeune = to_float(
        desc_expl.get("superficie_cacao_immature", 0.0)
    )

    # 1. Si non spécifié dans desc_expl, on tente la somme dans le tableau des cultures
    if surf_cacao_prod == 0.0 and isinstance(cultures, list):
        for c in cultures:
            nom_c = str(c.get("Culture", "")).lower()
            if "cacao" in nom_c:
                surf_cacao_prod += to_float(c.get("Superficie (ha)", 0.0))

    # 2. Fallback propre : si toujours 0, on prend surf_totale sans double addition
    if surf_cacao_prod == 0.0:
        surf_cacao_prod = surf_totale

    # 3. Ajustement de sécurité : si surf_totale est inférieure à surf_cacao_prod (saisie incomplète)
    if surf_totale > 0 and surf_cacao_prod > surf_totale:
        if (surf_cacao_prod - surf_totale) <= 0.05:
            surf_cacao_prod = surf_totale

    # Calcul dépenses du foyer
    total_depenses_foyer_an = 0.0
    for d in depenses_foyer:
        m = to_float(d.get("Montant moyen (FCFA)", 0.0))
        p = str(d.get("Périodicité", "")).lower()
        if "mois" in p and "2" not in p:
            total_depenses_foyer_an += m * 12
        elif "2 mois" in p:
            total_depenses_foyer_an += m * 6
        else:
            total_depenses_foyer_an += m

    return {
        "nom_producteur": str(
            raw_pdc.get("nom_prenoms_producteur")
            or raw_pdc.get("nom_producteur")
            or donnees_producteur.get("nom_producteur")
            or "Producteur Inconnu"
        ).strip(),
        "code_ccc": str(
            raw_pdc.get("code_producteur")
            or raw_pdc.get("code_national_producteur")
            or "CCC-Non renseigné"
        ).strip(),
        "localite": (
            f"{raw_pdc.get('sous_prefecture', raw_pdc.get('departement', 'N/A'))}"
            f" / {raw_pdc.get('village', 'N/A')}"
        ),
        "statut_foncier": str(desc_expl.get("statut_foncier", "Non précisé")),
        "superficie_totale": surf_totale,
        "superficie_cacao_prod": surf_cacao_prod,
        "superficie_cacao_jeune": surf_cacao_jeune,
        "age_moyen_verger": str(desc_expl.get("age_moyen", "Non précisé")),
        "relief_sol": desc_expl.get("relief_sol", []),
        "contraintes_parcelle": desc_expl.get("contraintes", []),
        "waypoint_gps": str(desc_expl.get("waypoint_gps", "Non renseigné")),
        "densite_calculee_ha": to_float(raw_pdc.get("densite_calculee_ha", 0.0)),
        "donnees_densite": densite_carres,
        "sante_cacaoyere": sante,
        "caracteristiques_sol": sol_caract,
        "inventaire_arbres": arbres,
        "total_arbres_ombrage": to_int(
            raw_pdc.get("total_arbres_ombrage", len(arbres))
        ),
        "revenu_total_estime": to_float(
            raw_pdc.get("revenu_total_estime", 0.0)
        ),
        "charges_totales_estimees": to_float(
            raw_pdc.get("charges_totales_estimees", 0.0)
        ),
        "solde_net_estime": to_float(raw_pdc.get("solde_net_estime", 0.0)),
        "depenses_foyer_annuelles": total_depenses_foyer_an,
        "prod_historique": prod_historique,
        "cultures_et_revenus": cultures,
        "budget_total_5ans": to_float(
            raw_pdc.get(
                "budget_total_5ans", raw_pdc.get("budget_fiche8_total", 0.0)
            )
        ),
        "decision_retenue": str(
            raw_pdc.get("decision_retenue", "Non déterminée")
        ),
        "plan_quinquennal": plan_action,
        "texte_synthese_auto": str(
            desc_expl.get(
                "texte_synthese_auto", raw_pdc.get("texte_synthese_auto", "")
            )
        ),
    }


def generer_synthese_narrative_leila(
    p: dict, score_global: int, ratio_arbres_ha: float, roi_5ans: float
) -> str:
    """Génère une synthèse narrative métier 100% cohérente avec l'analyse LEÏLA."""

    surf_cacao = max(
        0.1, p["superficie_cacao_prod"] + p["superficie_cacao_jeune"]
    )

    # 1. Introduction & Contexte
    intro = (
        f"L'exploitation de M./Mme {p['nom_producteur']} (Code CCC :"
        f" {p['code_ccc']}), localisée à {p['localite']}, couvre une superficie"
        f" totale de {p['superficie_totale']:.1f} ha, dont {surf_cacao:.1f} ha"
        f" dédiés à la culture du cacao ({p['statut_foncier']}). "
    )

    # 2. Diagnostic Technique & RDUE
    if ratio_arbres_ha >= 18.0:
        agro = (
            "Sur le plan environnemental, la parcelle présente une densité"
            " d'ombrage conforme aux normes RDUE"
            f" ({ratio_arbres_ha:.1f} arbres/ha). "
        )
    else:
        manque = int((18.0 * surf_cacao) - p["total_arbres_ombrage"])
        agro = (
            "Sur le plan environnemental, un déficit agroforestier est"
            f" identifié ({ratio_arbres_ha:.1f} arbres/ha). L'introduction de"
            f" {manque} plants d'ombrage est obligatoire pour la conformité"
            " RDUE. "
        )

    # 3. Orientations & Bilan Financier
    orient = (
        "L'orientation stratégique retenue est la"
        f" **{p['decision_retenue']}**. "
    )

    if score_global >= 75:
        finance = (
            "Le profil financier du ménage est solide avec un gain net estimé à"
            f" {roi_5ans:,.0f} FCFA sur 5 ans, rendant le projet hautement"
            " bancable."
        )
    elif score_global >= 50:
        finance = (
            "Le plan quinquennal nécessite un accompagnement financier partiel"
            f" pour couvrir le budget de {p['budget_total_5ans']:,.0f} FCFA."
        )
    else:
        finance = (
            "La capacité d'autofinancement actuelle est critique. Un"
            " préfinancement ou une restructuration des charges est"
            " indispensable."
        )

    return intro + agro + orient + finance


def leila_analyse_pdc_metier(donnees_producteur: dict):
    """Moteur Décisionnel L.E.Y.L.A. 3.0 - Analyse Expert, Credit Scoring & Projection ROI."""
    if not isinstance(donnees_producteur, dict):
        st.error("⚠️ Données invalides pour l'analyse LEÏLA.")
        return

    p = extraire_etapes_pdc_avancees(donnees_producteur)

    # Header Profil
    st.markdown(
        f"### 🤖 Diagnostic Expert L.E.Ï.L.A. — **{p['nom_producteur']}**"
    )
    st.caption(
        f"🆔 **Code CCC :** `{p['code_ccc']}` | 📍 **Localisation :**"
        f" {p['localite']} | 🛰️ **GPS :** {p['waypoint_gps']}"
    )
    st.markdown("---")

    # ---------------------------------------------------------
    # 0. CONTRÔLE QUALITÉ DES DONNÉES (AUDIT AUTOMATIQUE)
    # ---------------------------------------------------------
    anomalies = []
    if (
        p["superficie_totale"] > 0
        and (p["superficie_cacao_prod"] - p["superficie_totale"]) > 0.01
    ):
        anomalies.append(
            f"La superficie en cacao productif ({p['superficie_cacao_prod']:.2f} ha)"
            f" dépasse la superficie totale déclarée ({p['superficie_totale']:.2f} ha)."
        )
    if (
        p["revenu_total_estime"] > 0
        and p["charges_totales_estimees"] > p["revenu_total_estime"]
    ):
        anomalies.append(
            "Les charges de production déclarées sont supérieures au revenu brut."
        )

    if anomalies:
        with st.expander(
            "⚠️ **Alertes Qualité Données (Incohérences Détectées)**",
            expanded=True,
        ):
            for ano in anomalies:
                st.warning(f"• {ano}")

    # ---------------------------------------------------------
    # 1. SCORE DE FAISABILITÉ & BANCARITÉ (CREDIT SCORING LEÏLA)
    # ---------------------------------------------------------
    score_foncier = (
        30
        if "propriétaire" in p["statut_foncier"].lower()
        or "titre" in p["statut_foncier"].lower()
        else 15
    )

    surf_cacao = max(
        0.1, p["superficie_cacao_prod"] + p["superficie_cacao_jeune"]
    )
    ratio_arbres_ha = p["total_arbres_ombrage"] / surf_cacao
    score_rdue = (
        30
        if ratio_arbres_ha >= 18.0
        else int((ratio_arbres_ha / 18.0) * 30)
    )

    revenu_net_foyer = (
        p["revenu_total_estime"]
        - p["charges_totales_estimees"]
        - p["depenses_foyer_annuelles"]
    )
    score_finance = (
        40
        if revenu_net_foyer > (p["budget_total_5ans"] / 5)
        else (20 if revenu_net_foyer > 0 else 5)
    )

    score_global = score_foncier + score_rdue + score_finance

    st.markdown("#### 🎯 1. Score d'Éligibilité et de Bancarité du Plan")
    col_s1, col_s2, col_s3, col_s4 = st.columns(4)

    col_s1.metric("Score Global LEÏLA", f"{score_global} / 100")
    col_s2.metric("Sécurité Foncière", f"{score_foncier} / 30")
    col_s3.metric("Conformité Durabilité", f"{score_rdue} / 30")
    col_s4.metric("Autofinancement", f"{score_finance} / 40")

    if score_global >= 75:
        st.success(
            "🥇 **Dossier Excellent :** Projet bancable, éligible aux"
            " financements à taux préférentiel."
        )
    elif score_global >= 50:
        st.info(
            "🥈 **Dossier Modéré :** Projet faisable avec accompagnement"
            " technique ou préfinancement coopératif."
        )
    else:
        st.error(
            "🥉 **Dossier à Risque élevé :** Restructuration financière ou"
            " sécurisation foncière requise avant investissement."
        )

    # ---------------------------------------------------------
    # 2. PROJECTION DE RENDEMENT ET ROI À 5 ANS
    # ---------------------------------------------------------
    st.markdown("#### 📈 2. Simulation d'Impact Financier & ROI à 5 Ans")

    prix_kg = 1500  # Tarif de référence de la campagne en cours
    rendement_actuel_moyen = (
        (p["revenu_total_estime"] / prix_kg)
        if p["revenu_total_estime"] > 0
        else (surf_cacao * 400)
    )

    if "réhabilitation" in p["decision_retenue"].lower():
        rendement_cible_a5 = surf_cacao * 900
    elif "replantation" in p["decision_retenue"].lower():
        rendement_cible_a5 = surf_cacao * 1200
    else:
        rendement_cible_a5 = surf_cacao * 600

    gain_production_a5 = max(0.0, rendement_cible_a5 - rendement_actuel_moyen)
    gain_financier_annuel_a5 = gain_production_a5 * prix_kg
    roi_5ans = (
        ((gain_financier_annuel_a5 * 5) - p["budget_total_5ans"])
        if p["budget_total_5ans"] > 0
        else 0.0
    )

    col_p1, col_p2, col_p3 = st.columns(3)
    col_p1.metric(
        "Production Actuelle Est.",
        f"{rendement_actuel_moyen:,.0f} kg".replace(",", " "),
    )
    col_p2.metric(
        "Cible Production (Année 5)",
        f"{rendement_cible_a5:,.0f} kg".replace(",", " "),
        delta=f"+{gain_production_a5:,.0f} kg",
    )
    col_p3.metric(
        "Gain Net Cumulé sur 5 Ans",
        f"{roi_5ans:,.0f} FCFA".replace(",", " "),
    )

    # ---------------------------------------------------------
    # 3. CONFORMITÉ RDUE, AGROFORESTERIE ET SANTÉ
    # ---------------------------------------------------------
    st.markdown("#### 🌲 3. Normes RDUE & État Phytosanitaire")
    col_r1, col_r2 = st.columns(2)
    col_r1.metric(
        "Densité Agroforestière Actuelle", f"{ratio_arbres_ha:.1f} arbres/ha"
    )

    if ratio_arbres_ha >= 18.0:
        col_r2.metric("Conformité Marché UE (RDUE)", "Conforme ✅")
    else:
        manque = int((18.0 * surf_cacao) - p["total_arbres_ombrage"])
        col_r2.metric(
            "Conformité Marché UE (RDUE)",
            f"Non-Conforme (-{manque} arbres)",
            delta_color="inverse",
        )

    # ---------------------------------------------------------
    # 4. FEUILLE DE ROUTE CALENDRAIRE (SAISONNIÈRE)
    # ---------------------------------------------------------
    st.markdown("#### 📅 4. Feuillets d'Actions Prioritaires Chronologiques")

    t1, t2 = st.tabs([
        "🌧️ Saison des Pluies (Travaux Lourd)",
        "☀️ Saison Sèche (Récolte & Protection)",
    ])

    with t1:
        st.write("**Priorités Immédiates :**")
        if ratio_arbres_ha < 18.0:
            st.info(
                "• **Reboisement :** Mettre en terre"
                f" {int((18.0 * surf_cacao) - p['total_arbres_ombrage'])} plants"
                " d'essences ombrageables."
            )
        st.write(
            "• **Taille & Émondage :** Aérer le houppier des cacaoyers pour"
            " limiter l'humidité propice à la pourriture brune."
        )
        if "replantation" in p["decision_retenue"].lower():
            st.write(
                "• **Pepinère :** Préparer le matériel végétal haut rendement"
                " (CNRA) pour le schéma de replantation."
            )

    with t2:
        st.write("**Entretien & Post-Récolte :**")
        st.write(
            "• **Ramassage des cabosses mûres :** Fréquence tous les 10-14"
            " jours pour prévenir les attaques de ravageurs."
        )
        st.write(
            "• **EPI & Matériel :** Révision des atomiseurs et mise aux"
            " normes des équipements de protection individuel."
        )

    # ---------------------------------------------------------
    # 5. SYNTHÈSE NARRATIVE GÉNÉRÉE AUTOMATIQUEMENT (AJOUTÉ ICI)
    # ---------------------------------------------------------
    st.markdown("---")
    st.markdown("#### 📄 5. Synthèse Narrative du Plan (Modèle LEÏLA)")

    # 1. Génération du texte via la fonction
    synthese_texte = generer_synthese_narrative_leila(
        p=p,
        score_global=score_global,
        ratio_arbres_ha=ratio_arbres_ha,
        roi_5ans=roi_5ans,
    )

    # 2. Affichage sur Streamlit
    st.info(synthese_texte)

    # 3. Optionnel : Afficher la synthèse brute enregistrée sur le terrain
    if p["texte_synthese_auto"]:
        with st.expander(
            "📝 Voir la synthèse brute enregistrée sur le terrain (CCC)"
        ):
            st.caption(p["texte_synthese_auto"])


# ==========================================
# 3. INTERFACE DU SERVEUR CENTRAL
# ==========================================
cabinet_courant = st.session_state.get("cabinet_actif")
user_profile = st.session_state.get("profile")

st.title("🌐 L.E.Y.L.A. - Centre de Commandement Global")
st.markdown(f"*Espace de travail connecté : **{cabinet_courant['nom']}***")

if st.sidebar.button("🚪 Déconnexion"):
    supabase.auth.sign_out()
    st.session_state.clear()
    st.rerun()

st.sidebar.divider()

cabinet_id_actif = cabinet_courant["id"]

st.sidebar.header("🎛️ Sélection du Module")
module_choisi = st.sidebar.selectbox(
    "Choisir le domaine d'analyse",
    [
        "Plan de Développement (PDC)",
        "Géolocalisation & RDUE (Parcelles)",
        "Diagnostic Phytosanitaire",
        "Estimation de Rendement",
    ],
)

df_filtered = charger_donnees_isolees(
    module_choisi=module_choisi,
    cabinet_id=cabinet_id_actif,
    code_coop_filtre=code_coop_filtre,
)

st.subheader(f"📊 Module actif : {module_choisi}")

with st.expander(
    f"📁 Afficher / Masquer les données brutes ({len(df_filtered)}"
    " enregistrement(s))",
    expanded=False,
):
    if not df_filtered.empty:
        st.dataframe(df_filtered, use_container_width=True)
    else:
        st.info(
            "Aucune donnée enregistrée pour le module"
            f" {module_choisi} dans cette sélection."
        )

st.divider()


# ==========================================
# 4. MODULE DÉDIÉ PDC : ANALYSE PAR PRODUCTEUR
# ==========================================
if "PDC" in module_choisi:
    col_titre, col_reset = st.columns([2.5, 1.5])

    with col_titre:
        st.subheader("🔍 Consultation Approfondie d'un PDC Synchronisé")

    with col_reset:
        if st.button(
            "🔄 Réinitialiser l'affichage PDC", use_container_width=True
        ):
            st.cache_data.clear()
            st.cache_resource.clear()
            if "pdc_select_box" in st.session_state:
                del st.session_state["pdc_select_box"]
            st.success("Interface réinitialisée !")
            st.rerun()

    if df_filtered.empty:
        st.info(
            "ℹ️ Aucun enregistrement PDC disponible. La base de données est"
            " propre."
        )
    else:
        df_pdc = df_filtered.copy()

        col_nom = (
            "nom_producteur"
            if "nom_producteur" in df_pdc.columns
            else df_pdc.columns[0]
        )
        col_code = (
            "code_producteur" if "code_producteur" in df_pdc.columns else None
        )
        col_id = "id" if "id" in df_pdc.columns else None

        df_pdc = df_pdc[
            df_pdc[col_nom].notna()
            & (df_pdc[col_nom].astype(str).str.strip() != "")
        ].copy()

        if not df_pdc.empty:

            def construire_libelle(row):
                nom_str = str(row[col_nom]).strip()
                code_str = (
                    f" | Code: {row[col_code]}"
                    if col_code
                    and pd.notna(row[col_code])
                    and str(row[col_code]).strip() != ""
                    else ""
                )
                id_str = (
                    f" | ID #{row[col_id]}"
                    if col_id and pd.notna(row[col_id])
                    else ""
                )
                return f"{nom_str}{code_str}{id_str}"

            df_pdc["cle_unique"] = df_pdc.apply(construire_libelle, axis=1)

            OPTION_DEFAUT = "--- Sélectionner un producteur ---"
            options_disponibles = [
                OPTION_DEFAUT
            ] + df_pdc["cle_unique"].tolist()

            with st.form("form_selection_pdc"):
                choix_utilisateur = st.selectbox(
                    "Sélectionner la fiche d'un producteur :",
                    options_disponibles,
                    key="pdc_select_box",
                )

                soumis = st.form_submit_button(
                    "Analyser le PDC avec Leïla 🤖",
                    type="primary",
                    use_container_width=True,
                )

            if soumis:
                if choix_utilisateur == OPTION_DEFAUT:
                    st.warning(
                        "Veuillez sélectionner un producteur valide dans la"
                        " liste."
                    )
                else:
                    if verifier_et_incrementer_quota(cabinet_id_actif):
                        ligne_selectionnee = (
                            df_pdc[df_pdc["cle_unique"] == choix_utilisateur]
                            .iloc[0]
                            .to_dict()
                        )
                        # Appelle la fonction qui exécute et affiche tout le diagnostic (y compris la section 5)
                        leila_analyse_pdc_metier(ligne_selectionnee)
                    else:
                        st.error(
                            "🚫 **Quota d'analyses IA mensuel atteint pour votre"
                            " cabinet.**"
                        )
                        st.info(
                            "Veuillez contacter le **Cabinet AGRIFORCE** pour"
                            " recharger votre forfait de requêtes L.E.Y.L.A."
                        )
        else:
            st.warning(
                "Aucun nom de producteur valide trouvé dans les"
                " enregistrements."
            )

    st.divider()
import json
import pandas as pd
import streamlit as st


def extraire_etapes_pdc_avancees(donnees_producteur: dict) -> dict:
    """Extraction intégrale et granulaire des structures complexes du JSON PDC."""
    raw_pdc = {}

    source = (
        donnees_producteur.get("observations_diagnostic")
        or donnees_producteur.get("reponses_pdc")
        or donnees_producteur.get("donnees_module")
        or donnees_producteur.get("reponses")
        or {}
    )

    if isinstance(source, str) and source.strip().startswith("{"):
        try:
            raw_pdc = json.loads(source)
        except Exception:
            raw_pdc = {}
    elif isinstance(source, dict):
        raw_pdc = source

    if not raw_pdc:
        raw_pdc = donnees_producteur

    def to_float(val, default=0.0):
        try:
            if val is None:
                return default
            clean_val = (
                str(val)
                .replace("FCFA", "")
                .replace("F", "")
                .replace(" ", "")
                .replace(",", ".")
                .strip()
            )
            return float(clean_val)
        except Exception:
            return default

    def to_int(val, default=0):
        try:
            return int(to_float(val, default))
        except Exception:
            return default

    desc_expl = raw_pdc.get("description_exploitation") or {}
    if not isinstance(desc_expl, dict):
        desc_expl = {}

    cultures = (
        raw_pdc.get("cultures_et_revenus") or raw_pdc.get("tableau_cultures") or []
    )
    arbres = (
        raw_pdc.get("inventaire_arbres") or raw_pdc.get("tableau_arbres") or []
    )
    sante = raw_pdc.get("sante_cacaoyere") or []
    densite_carres = raw_pdc.get("donnees_densite") or []
    sol_caract = (
        raw_pdc.get("caracteristiques_sol") or raw_pdc.get("df_sol_caract") or []
    )
    depenses_foyer = raw_pdc.get("depenses_foyer") or []
    prod_historique = (
        raw_pdc.get("prod_historique") or raw_pdc.get("df_prod_historique") or []
    )
    plan_action = (
        raw_pdc.get("plan_quinquennal")
        or raw_pdc.get("plan_quinquennal_detail")
        or []
    )

    # --- CORRECTION DE L'EXTRACTION DES SUPERFICIES ---
    surf_totale = to_float(
        desc_expl.get("superficie_totale", raw_pdc.get("superficie", 0.0))
    )
    surf_cacao_prod = to_float(desc_expl.get("superficie_cacao_productif", 0.0))
    surf_cacao_jeune = to_float(
        desc_expl.get("superficie_cacao_immature", 0.0)
    )

    # 1. Si non spécifié dans desc_expl, on tente la somme dans le tableau des cultures
    if surf_cacao_prod == 0.0 and isinstance(cultures, list):
        for c in cultures:
            nom_c = str(c.get("Culture", "")).lower()
            if "cacao" in nom_c:
                surf_cacao_prod += to_float(c.get("Superficie (ha)", 0.0))

    # 2. Fallback propre : si toujours 0, on prend surf_totale sans double addition
    if surf_cacao_prod == 0.0:
        surf_cacao_prod = surf_totale

    # 3. Ajustement de sécurité : si surf_totale est inférieure à surf_cacao_prod (saisie incomplète)
    if surf_totale > 0 and surf_cacao_prod > surf_totale:
        if (surf_cacao_prod - surf_totale) <= 0.05:
            surf_cacao_prod = surf_totale

    # Calcul dépenses du foyer
    total_depenses_foyer_an = 0.0
    for d in depenses_foyer:
        m = to_float(d.get("Montant moyen (FCFA)", 0.0))
        p = str(d.get("Périodicité", "")).lower()
        if "mois" in p and "2" not in p:
            total_depenses_foyer_an += m * 12
        elif "2 mois" in p:
            total_depenses_foyer_an += m * 6
        else:
            total_depenses_foyer_an += m

    return {
        "nom_producteur": str(
            raw_pdc.get("nom_prenoms_producteur")
            or raw_pdc.get("nom_producteur")
            or donnees_producteur.get("nom_producteur")
            or "Producteur Inconnu"
        ).strip(),
        "code_ccc": str(
            raw_pdc.get("code_producteur")
            or raw_pdc.get("code_national_producteur")
            or "CCC-Non renseigné"
        ).strip(),
        "localite": (
            f"{raw_pdc.get('sous_prefecture', raw_pdc.get('departement', 'N/A'))}"
            f" / {raw_pdc.get('village', 'N/A')}"
        ),
        "statut_foncier": str(desc_expl.get("statut_foncier", "Non précisé")),
        "superficie_totale": surf_totale,
        "superficie_cacao_prod": surf_cacao_prod,
        "superficie_cacao_jeune": surf_cacao_jeune,
        "age_moyen_verger": str(desc_expl.get("age_moyen", "Non précisé")),
        "relief_sol": desc_expl.get("relief_sol", []),
        "contraintes_parcelle": desc_expl.get("contraintes", []),
        "waypoint_gps": str(desc_expl.get("waypoint_gps", "Non renseigné")),
        "densite_calculee_ha": to_float(raw_pdc.get("densite_calculee_ha", 0.0)),
        "donnees_densite": densite_carres,
        "sante_cacaoyere": sante,
        "caracteristiques_sol": sol_caract,
        "inventaire_arbres": arbres,
        "total_arbres_ombrage": to_int(
            raw_pdc.get("total_arbres_ombrage", len(arbres))
        ),
        "revenu_total_estime": to_float(
            raw_pdc.get("revenu_total_estime", 0.0)
        ),
        "charges_totales_estimees": to_float(
            raw_pdc.get("charges_totales_estimees", 0.0)
        ),
        "solde_net_estime": to_float(raw_pdc.get("solde_net_estime", 0.0)),
        "depenses_foyer_annuelles": total_depenses_foyer_an,
        "prod_historique": prod_historique,
        "cultures_et_revenus": cultures,
        "budget_total_5ans": to_float(
            raw_pdc.get(
                "budget_total_5ans", raw_pdc.get("budget_fiche8_total", 0.0)
            )
        ),
        "decision_retenue": str(
            raw_pdc.get("decision_retenue", "Non déterminée")
        ),
        "plan_quinquennal": plan_action,
        "texte_synthese_auto": str(
            desc_expl.get(
                "texte_synthese_auto", raw_pdc.get("texte_synthese_auto", "")
            )
        ),
    }


def generer_synthese_narrative_leila(
    p: dict, score_global: int, ratio_arbres_ha: float, roi_5ans: float
) -> str:
    """Génère une synthèse narrative métier 100% cohérente avec l'analyse LEÏLA."""

    surf_cacao = max(
        0.1, p["superficie_cacao_prod"] + p["superficie_cacao_jeune"]
    )

    # 1. Introduction & Contexte
    intro = (
        f"L'exploitation de M./Mme {p['nom_producteur']} (Code CCC :"
        f" {p['code_ccc']}), localisée à {p['localite']}, couvre une superficie"
        f" totale de {p['superficie_totale']:.1f} ha, dont {surf_cacao:.1f} ha"
        f" dédiés à la culture du cacao ({p['statut_foncier']}). "
    )

    # 2. Diagnostic Technique & RDUE
    if ratio_arbres_ha >= 18.0:
        agro = (
            "Sur le plan environnemental, la parcelle présente une densité"
            " d'ombrage conforme aux normes RDUE"
            f" ({ratio_arbres_ha:.1f} arbres/ha). "
        )
    else:
        manque = int((18.0 * surf_cacao) - p["total_arbres_ombrage"])
        agro = (
            "Sur le plan environnemental, un déficit agroforestier est"
            f" identifié ({ratio_arbres_ha:.1f} arbres/ha). L'introduction de"
            f" {manque} plants d'ombrage est obligatoire pour la conformité"
            " RDUE. "
        )

    # 3. Orientations & Bilan Financier
    orient = (
        "L'orientation stratégique retenue est la"
        f" **{p['decision_retenue']}**. "
    )

    if score_global >= 75:
        finance = (
            "Le profil financier du ménage est solide avec un gain net estimé à"
            f" {roi_5ans:,.0f} FCFA sur 5 ans, rendant le projet hautement"
            " bancable."
        )
    elif score_global >= 50:
        finance = (
            "Le plan quinquennal nécessite un accompagnement financier partiel"
            f" pour couvrir le budget de {p['budget_total_5ans']:,.0f} FCFA."
        )
    else:
        finance = (
            "La capacité d'autofinancement actuelle est critique. Un"
            " préfinancement ou une restructuration des charges est"
            " indispensable."
        )

    return intro + agro + orient + finance


def leila_analyse_pdc_metier(donnees_producteur: dict):
    """Moteur Décisionnel L.E.Y.L.A. 3.0 - Analyse Expert, Credit Scoring & Projection ROI."""
    if not isinstance(donnees_producteur, dict):
        st.error("⚠️ Données invalides pour l'analyse LEÏLA.")
        return

    p = extraire_etapes_pdc_avancees(donnees_producteur)

    # Header Profil
    st.markdown(
        f"### 🤖 Diagnostic Expert L.E.Ï.L.A. — **{p['nom_producteur']}**"
    )
    st.caption(
        f"🆔 **Code CCC :** `{p['code_ccc']}` | 📍 **Localisation :**"
        f" {p['localite']} | 🛰️ **GPS :** {p['waypoint_gps']}"
    )
    st.markdown("---")

    # ---------------------------------------------------------
    # 0. CONTRÔLE QUALITÉ DES DONNÉES (AUDIT AUTOMATIQUE)
    # ---------------------------------------------------------
    anomalies = []
    if (
        p["superficie_totale"] > 0
        and (p["superficie_cacao_prod"] - p["superficie_totale"]) > 0.01
    ):
        anomalies.append(
            f"La superficie en cacao productif ({p['superficie_cacao_prod']:.2f} ha)"
            f" dépasse la superficie totale déclarée ({p['superficie_totale']:.2f} ha)."
        )
    if (
        p["revenu_total_estime"] > 0
        and p["charges_totales_estimees"] > p["revenu_total_estime"]
    ):
        anomalies.append(
            "Les charges de production déclarées sont supérieures au revenu brut."
        )

    if anomalies:
        with st.expander(
            "⚠️ **Alertes Qualité Données (Incohérences Détectées)**",
            expanded=True,
        ):
            for ano in anomalies:
                st.warning(f"• {ano}")

    # ---------------------------------------------------------
    # 1. SCORE DE FAISABILITÉ & BANCARITÉ (CREDIT SCORING LEÏLA)
    # ---------------------------------------------------------
    score_foncier = (
        30
        if "propriétaire" in p["statut_foncier"].lower()
        or "titre" in p["statut_foncier"].lower()
        else 15
    )

    surf_cacao = max(
        0.1, p["superficie_cacao_prod"] + p["superficie_cacao_jeune"]
    )
    ratio_arbres_ha = p["total_arbres_ombrage"] / surf_cacao
    score_rdue = (
        30
        if ratio_arbres_ha >= 18.0
        else int((ratio_arbres_ha / 18.0) * 30)
    )

    revenu_net_foyer = (
        p["revenu_total_estime"]
        - p["charges_totales_estimees"]
        - p["depenses_foyer_annuelles"]
    )
    score_finance = (
        40
        if revenu_net_foyer > (p["budget_total_5ans"] / 5)
        else (20 if revenu_net_foyer > 0 else 5)
    )

    score_global = score_foncier + score_rdue + score_finance

    st.markdown("#### 🎯 1. Score d'Éligibilité et de Bancarité du Plan")
    col_s1, col_s2, col_s3, col_s4 = st.columns(4)

    col_s1.metric("Score Global LEÏLA", f"{score_global} / 100")
    col_s2.metric("Sécurité Foncière", f"{score_foncier} / 30")
    col_s3.metric("Conformité Durabilité", f"{score_rdue} / 30")
    col_s4.metric("Autofinancement", f"{score_finance} / 40")

    if score_global >= 75:
        st.success(
            "🥇 **Dossier Excellent :** Projet bancable, éligible aux"
            " financements à taux préférentiel."
        )
    elif score_global >= 50:
        st.info(
            "🥈 **Dossier Modéré :** Projet faisable avec accompagnement"
            " technique ou préfinancement coopératif."
        )
    else:
        st.error(
            "🥉 **Dossier à Risque élevé :** Restructuration financière ou"
            " sécurisation foncière requise avant investissement."
        )

    # ---------------------------------------------------------
    # 2. PROJECTION DE RENDEMENT ET ROI À 5 ANS
    # ---------------------------------------------------------
    st.markdown("#### 📈 2. Simulation d'Impact Financier & ROI à 5 Ans")

    prix_kg = 1500  # Tarif de référence de la campagne en cours
    rendement_actuel_moyen = (
        (p["revenu_total_estime"] / prix_kg)
        if p["revenu_total_estime"] > 0
        else (surf_cacao * 400)
    )

    if "réhabilitation" in p["decision_retenue"].lower():
        rendement_cible_a5 = surf_cacao * 900
    elif "replantation" in p["decision_retenue"].lower():
        rendement_cible_a5 = surf_cacao * 1200
    else:
        rendement_cible_a5 = surf_cacao * 600

    gain_production_a5 = max(0.0, rendement_cible_a5 - rendement_actuel_moyen)
    gain_financier_annuel_a5 = gain_production_a5 * prix_kg
    roi_5ans = (
        ((gain_financier_annuel_a5 * 5) - p["budget_total_5ans"])
        if p["budget_total_5ans"] > 0
        else 0.0
    )

    col_p1, col_p2, col_p3 = st.columns(3)
    col_p1.metric(
        "Production Actuelle Est.",
        f"{rendement_actuel_moyen:,.0f} kg".replace(",", " "),
    )
    col_p2.metric(
        "Cible Production (Année 5)",
        f"{rendement_cible_a5:,.0f} kg".replace(",", " "),
        delta=f"+{gain_production_a5:,.0f} kg",
    )
    col_p3.metric(
        "Gain Net Cumulé sur 5 Ans",
        f"{roi_5ans:,.0f} FCFA".replace(",", " "),
    )

    # ---------------------------------------------------------
    # 3. CONFORMITÉ RDUE, AGROFORESTERIE ET SANTÉ
    # ---------------------------------------------------------
    st.markdown("#### 🌲 3. Normes RDUE & État Phytosanitaire")
    col_r1, col_r2 = st.columns(2)
    col_r1.metric(
        "Densité Agroforestière Actuelle", f"{ratio_arbres_ha:.1f} arbres/ha"
    )

    if ratio_arbres_ha >= 18.0:
        col_r2.metric("Conformité Marché UE (RDUE)", "Conforme ✅")
    else:
        manque = int((18.0 * surf_cacao) - p["total_arbres_ombrage"])
        col_r2.metric(
            "Conformité Marché UE (RDUE)",
            f"Non-Conforme (-{manque} arbres)",
            delta_color="inverse",
        )

    # ---------------------------------------------------------
    # 4. FEUILLE DE ROUTE CALENDRAIRE (SAISONNIÈRE)
    # ---------------------------------------------------------
    st.markdown("#### 📅 4. Feuillets d'Actions Prioritaires Chronologiques")

    t1, t2 = st.tabs([
        "🌧️ Saison des Pluies (Travaux Lourd)",
        "☀️ Saison Sèche (Récolte & Protection)",
    ])

    with t1:
        st.write("**Priorités Immédiates :**")
        if ratio_arbres_ha < 18.0:
            st.info(
                "• **Reboisement :** Mettre en terre"
                f" {int((18.0 * surf_cacao) - p['total_arbres_ombrage'])} plants"
                " d'essences ombrageables."
            )
        st.write(
            "• **Taille & Émondage :** Aérer le houppier des cacaoyers pour"
            " limiter l'humidité propice à la pourriture brune."
        )
        if "replantation" in p["decision_retenue"].lower():
            st.write(
                "• **Pepinère :** Préparer le matériel végétal haut rendement"
                " (CNRA) pour le schéma de replantation."
            )

    with t2:
        st.write("**Entretien & Post-Récolte :**")
        st.write(
            "• **Ramassage des cabosses mûres :** Fréquence tous les 10-14"
            " jours pour prévenir les attaques de ravageurs."
        )
        st.write(
            "• **EPI & Matériel :** Révision des atomiseurs et mise aux"
            " normes des équipements de protection individuel."
        )

    # ---------------------------------------------------------
    # 5. SYNTHÈSE NARRATIVE GÉNÉRÉE AUTOMATIQUEMENT
    # ---------------------------------------------------------
    st.markdown("---")
    st.markdown("#### 📄 5. Synthèse Narrative du Plan (Modèle LEÏLA)")

    # 1. Génération du texte via la fonction
    synthese_texte = generer_synthese_narrative_leila(
        p=p,
        score_global=score_global,
        ratio_arbres_ha=ratio_arbres_ha,
        roi_5ans=roi_5ans,
    )

    # 2. Affichage sur Streamlit
    st.info(synthese_texte)

    # 3. Afficher la synthèse brute (Correction de l'indentation sous 'with')
    if p["texte_synthese_auto"]:
        with st.expander("📝 Voir la synthèse brute enregistrée sur le terrain (CCC)"):
            st.caption(p["texte_synthese_auto"])

    # 4. Bloc Assistant IA (Ligne 1493 corrigée)
    # Assurez-vous d'avoir au moins une instruction indentée sous ce 'with'
    with st.expander("🤖 Assistant IA L.E.Y.L.A. (Analyse Experte Ciblée)"):
        st.write("Analyse automatique et recommandations complémentaires générées.")



# ==========================================
# 3. INTERFACE DU SERVEUR CENTRAL
# ==========================================
cabinet_courant = st.session_state.get("cabinet_actif")
user_profile = st.session_state.get("profile")

st.title("🌐 L.E.Y.L.A. - Centre de Commandement Global")
st.markdown(f"*Espace de travail connecté : **{cabinet_courant['nom']}***")

if st.sidebar.button("🚪 Déconnexion"):
    supabase.auth.sign_out()
    st.session_state.clear()
    st.rerun()

st.sidebar.divider()

cabinet_id_actif = cabinet_courant["id"]

st.sidebar.header("🎛️ Sélection du Module")
module_choisi = st.sidebar.selectbox(
    "Choisir le domaine d'analyse",
    [
        "Plan de Développement (PDC)",
        "Géolocalisation & RDUE (Parcelles)",
        "Diagnostic Phytosanitaire",
        "Estimation de Rendement",
    ],
)

df_filtered = charger_donnees_isolees(
    module_choisi=module_choisi,
    cabinet_id=cabinet_id_actif,
    code_coop_filtre=code_coop_filtre,
)

st.subheader(f"📊 Module actif : {module_choisi}")

with st.expander(
    f"📁 Afficher / Masquer les données brutes ({len(df_filtered)}"
    " enregistrement(s))",
    expanded=False,
):
    if not df_filtered.empty:
        st.dataframe(df_filtered, use_container_width=True)
    else:
        st.info(
            "Aucune donnée enregistrée pour le module"
            f" {module_choisi} dans cette sélection."
        )

st.divider()


    # ---------------------------------------------------------
    # 4. MODULE DÉDIÉ PDC : ANALYSE PAR PRODUCTEUR
    # ---------------------------------------------------------
    OPTION_DEFAUT = "--- Sélectionner un producteur ---"
    options_disponibles = [OPTION_DEFAUT] + df_pdc["cle_unique"].tolist()

    # Début du bloc st.form (Ligne 1491)
    with st.form("form_selection_pdc"):
        choix_utilisateur = st.selectbox(
            "Sélectionner la fiche d'un producteur :",
            options_disponibles,
            key="pdc_select_box",
        )

        soumis = st.form_submit_button(
            "Analyser le PDC avec Leïla 🤖",
            type="primary",
            use_container_width=True,
        )

    # Traitement de la soumission du formulaire
    if soumis:
        if choix_utilisateur == OPTION_DEFAUT:
            st.warning("Veuillez sélectionner un producteur valide dans la liste.")
        else:
            if verifier_et_incrementer_quota(cabinet_id_actif):
                ligne_selectionnee = (
                    df_pdc[df_pdc["cle_unique"] == choix_utilisateur]
                    .iloc[0]
                    .to_dict()
                )
                leila_analyse_pdc_metier(ligne_selectionnee)
            else:
                st.error("🚫 **Quota d'analyses IA mensuel atteint pour votre cabinet.**")
                st.info(
                    "Veuillez contacter votre **Fournisseur** pour recharger votre"
                    " forfait de requêtes L.E.Y.L.A."
                )


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
        # CORRECTION : Passage du cabinet_id (UUID) pour la vérification du quota
        if verifier_et_incrementer_quota(cabinet_id_actif):
            with st.spinner(f"Le satellite analyse exclusivement les données de {module_choisi}..."):
                try:
                    contexte_donnees = (
                        df_filtered.to_string(index=False)
                        if not df_filtered.empty
                        else "Aucune donnée disponible pour ce module."
                    )

                    prompt_complet = (
                        "Tu es L.E.Y.L.A., l'intelligence artificielle centrale pour la gestion"
                        " agricole.\n"
                        f"Cabinet actif : {cabinet_courant['nom']}\n"
                        f"Module en cours d'analyse : {module_choisi}\n"
                        "Données brutes exclusives à ce module :\n"
                        f"{contexte_donnees}\n\n"
                        f"Consigne / Question de l'administrateur : {user_query}\n\n"
                        "Fournis une analyse professionnelle, claire et axée uniquement sur ce"
                        " module."
                    )

                    historique_fictif = [{"role": "user", "content": prompt_complet}]
                    reponse_satellite = rechercher_sur_le_web(historique_fictif)

                    st.success("Rapport du Satellite L.E.Y.L.A. :")
                    st.write(reponse_satellite.get("texte", ""))

                except Exception as e:
                    st.error(f"Erreur lors de la communication avec le satellite : {e}")
        else:
            st.error("🚫 **Quota d'analyses IA mensuel atteint pour votre cabinet.**")
            st.info(
                "Veuillez contacter votre **Fournisseur** pour recharger votre forfait de"
                " requêtes L.E.Y.L.A."
            )

