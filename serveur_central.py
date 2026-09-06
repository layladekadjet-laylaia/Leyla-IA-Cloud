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

import json
import streamlit as st


def extraire_etapes_pdc(donnees_producteur: dict) -> dict:
    """Extraction robuste et récursive des données PDC peu importe le format de stockage (session_state ou DB)."""
    raw_pdc = {}

    # 1. Récupération de la source de données principale
    source = (
        donnees_producteur.get("reponses_pdc")
        or donnees_producteur.get("observations_diagnostic")
        or donnees_producteur.get("donnees_module")
        or donnees_producteur.get("reponses")
        or {}
    )

    # Décodage si c'est une chaîne JSON
    if isinstance(source, str):
        try:
            raw_pdc = json.loads(source)
        except Exception:
            raw_pdc = {}
    elif isinstance(source, dict):
        raw_pdc = source

    if not raw_pdc:
        raw_pdc = donnees_producteur

    # 2. Utilitaires de recherche et conversion sécurisés
    def chercher_valeur(cles_possibles, default=None):
        for key, val in raw_pdc.items():
            if val is not None and str(val).strip() != "":
                if any(k.lower() in key.lower() for k in cles_possibles):
                    return val

        for sub_k, sub_v in raw_pdc.items():
            if isinstance(sub_v, dict):
                for k, v in sub_v.items():
                    if v is not None and str(v).strip() != "":
                        if any(
                            kp.lower() in k.lower() for kp in cles_possibles
                        ):
                            return v
        return default

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

    # Extraction des blocs complexes
    desc_expl = raw_pdc.get("description_exploitation", {})
    if not isinstance(desc_expl, dict):
        desc_expl = {}

    facteurs = raw_pdc.get("facteurs_succes", {})
    if not isinstance(facteurs, dict):
        facteurs = {}

    # Extraction sécurisée couvrant les 14 étapes du PDC
    return {
        # Identification & Localisation
        "nom_producteur": str(
            donnees_producteur.get("nom_producteur")
            or raw_pdc.get("nom_prenoms_producteur")
            or "Producteur Inconnu"
        ).strip(),
        "code_ccc": str(
            donnees_producteur.get("code_producteur")
            or raw_pdc.get("code_national_producteur")
            or "CCC-N/A"
        ).strip(),
        "delegation": str(raw_pdc.get("delegation_regionale", "Non spécifiée")),
        "departement": str(raw_pdc.get("departement", "Non spécifié")),
        "village": str(raw_pdc.get("village", "Non spécifié")),
        # Foncier & Exploitation
        "statut_foncier": str(
            desc_expl.get(
                "statut_foncier",
                chercher_valeur(["statut_foncier", "foncier"], "Inconnu"),
            )
        ),
        "superficie_totale": to_float(
            desc_expl.get(
                "superficie_totale",
                chercher_valeur(["superficie_totale", "surf_totale"], 0.0),
            )
        ),
        "superficie_cacao_prod": to_float(
            desc_expl.get(
                "superficie_cacao_productif",
                chercher_valeur(["cacao_productif", "surf_cacao_prod"], 0.0),
            )
        ),
        "superficie_cacao_jeune": to_float(
            desc_expl.get(
                "superficie_cacao_immature",
                chercher_valeur(["cacao_immature", "surf_cacao_jeune"], 0.0),
            )
        ),
        "age_moyen_verger": str(
            desc_expl.get(
                "age_moyen",
                chercher_valeur(["age_moyen", "age_verger"], "Non précisé"),
            )
        ),
        "relief_sol": desc_expl.get("relief_sol", []),
        "contraintes_parcelle": desc_expl.get("contraintes", []),
        "waypoint_gps": str(
            desc_expl.get("waypoint_gps", "Coordonnées non saisies")
        ),
        "texte_synthese_auto": str(desc_expl.get("texte_synthese_auto", "")),
        # Agroforesterie
        "nb_arbres_forestiers": to_int(
            desc_expl.get(
                "nb_arbres_forestiers",
                chercher_valeur(["nb_arbres_forestiers", "arbres"], 0),
            )
        ),
        "essences_arbres": desc_expl.get("essences_arbres", []),
        "densite_ombrage": str(
            desc_expl.get("densite_ombrage", "Non évaluée")
        ),
        "inventaire_arbres_detail": raw_pdc.get("inventaire_arbres", []),
        # Bilan Socio-Économique
        "situation_epargne": raw_pdc.get("situation_epargne", []),
        "situation_main_oeuvre": raw_pdc.get("situation_main_oeuvre", []),
        "solde_net_estime": to_float(
            chercher_valeur(
                ["solde_net_estime", "solde_net", "solde"], 0.0
            )
        ),
        "budget_annuel_total": to_float(
            raw_pdc.get(
                "budget_annuel_total",
                raw_pdc.get(
                    "budget_annee_1",
                    chercher_valeur(["budget_annuel", "budget_annee_1"], 0.0),
                ),
            )
        ),
        "budget_total_5ans": to_float(
            raw_pdc.get(
                "budget_total_5ans",
                raw_pdc.get(
                    "budget_global_5ans",
                    chercher_valeur(["budget_5ans", "total_5ans"], 0.0),
                ),
            )
        ),
        # Décision & Planification
        "decision_retenue": str(
            raw_pdc.get(
                "decision_retenue",
                chercher_valeur(["decision_retenue", "decision"], "À déterminer"),
            )
        ),
        "plan_quinquennal_detail": raw_pdc.get(
            "plan_quinquennal_detail", raw_pdc.get("df_plan_action_5ans", [])
        ),
        "programme_annuel_detail": raw_pdc.get(
            "programme_annuel_detail", raw_pdc.get("df_programme_annuel", [])
        ),
        "moyens_fiche8_details": raw_pdc.get("moyens_fiche8_details", []),
        "cultures_et_revenus": raw_pdc.get("cultures_et_revenus", []),
        "materiel_agricole": raw_pdc.get("materiel_agricole", []),
        # Facteurs de Succès & Risques
        "facteurs_internes": facteurs.get("facteurs_internes", []),
        "soutiens_attendus": facteurs.get("soutiens_attendus", []),
        "risques_identifies": facteurs.get("risques_identifies", []),
        "mesures_mitigation": str(
            facteurs.get("mesures_mitigation", "Aucune mesure spécifiée")
        ),
    }


def leila_analyse_avancee_rdue_et_rendement(p: dict) -> dict:
    """Analyse décisionnelle poussée : Conformité RDUE, Projections de production et Analyse de Sensibilité."""
    surf_cacao = p["superficie_cacao_prod"] + p["superficie_cacao_jeune"]
    ratio_arbres_ha = (p["nb_arbres_forestiers"] / surf_cacao) if surf_cacao > 0 else 0.0
    rdue_conforme = ratio_arbres_ha >= 18.0

    prix_kg_cacao = 1500  # Hypothèse de calcul FCFA/kg
    rendement_actuel_estime = (p["solde_net_estime"] / prix_kg_cacao) if p["solde_net_estime"] > 0 else (surf_cacao * 400)
    
    if p["decision_retenue"] == "Réhabilitation":
        rendement_cible_a3 = surf_cacao * 800
    elif p["decision_retenue"] == "Replantation":
        rendement_cible_a3 = surf_cacao * 1000
    else:
        rendement_cible_a3 = surf_cacao * 500

    gain_brut_estime_a3 = (rendement_cible_a3 - (rendement_actuel_estime / prix_kg_cacao)) * prix_kg_cacao
    revenu_choc_prix = (p["solde_net_estime"] * 0.8) - p["budget_annuel_total"]

    return {
        "ratio_arbres_ha": ratio_arbres_ha,
        "rdue_conforme": rdue_conforme,
        "gain_brut_estime_a3": max(0.0, gain_brut_estime_a3),
        "resilience_choc_financier": revenu_choc_prix >= 0,
        "marge_choc_valeur": revenu_choc_prix
    }


def leila_analyse_pdc_metier(donnees_producteur: dict):
    """Moteur Décisionnel L.E.Y.L.A. - Analyse Intégrale et Prédictive du PDC."""
    if not isinstance(donnees_producteur, dict):
        st.error("⚠️ Données invalides pour l'analyse LEÏLA.")
        return

    p = extraire_etapes_pdc(donnees_producteur)
    p_av = leila_analyse_avancee_rdue_et_rendement(p)

    st.markdown(f"### 🤖 Diagnostic & Copilote L.E.Ï.L.A. pour **{p['nom_producteur']}** (`{p['code_ccc']}`)")
    st.caption(f"📍 **Localisation :** Délégation {p['delegation']} | Dép. {p['departement']} | Village {p['village']}")
    st.markdown("---")

    # ---------------------------------------------------------
    # 1. SYNTHÈSE AGRONOMIQUE & DÉCISION STRATÉGIQUE
    # ---------------------------------------------------------
    st.markdown("#### 🌳 1. Profil Agronomique & Orientation Stratégique")
    col_a1, col_a2, col_a3, col_a4 = st.columns(4)

    col_a1.metric("Surface Totale", f"{p['superficie_totale']:.1f} ha")
    col_a2.metric("Cacao Productif", f"{p['superficie_cacao_prod']:.1f} ha")
    col_a3.metric("Arbres Ombrage", f"{p['nb_arbres_forestiers']} pieds")
    col_a4.metric("Décision Retenue", p["decision_retenue"])

    if p["decision_retenue"] == "Replantation":
        st.error("🔴 **Décision : Replantation requise.** Le verger présente des facteurs de vétusté majeure ou de forte baisse de densité.")
    elif p["decision_retenue"] == "Reconversion":
        st.warning("🟠 **Décision : Reconversion conseillée.** Contraintes édaphiques (cuirasse) ou pluviométriques critiques.")
    elif p["decision_retenue"] == "Réhabilitation":
        st.success("🟢 **Décision : Réhabilitation.** Le verger possède un bon potentiel de relance via la taille et la fertilisation.")

    # ---------------------------------------------------------
    # 2. CONFORMITÉ RDUE & PROJECTIONS DE RENDEMENT
    # ---------------------------------------------------------
    st.markdown("#### 🌲 2. Traçabilité, Norme RDUE & Projection de Gain à 3 Ans")
    col_r1, col_r2, col_r3 = st.columns(3)

    col_r1.metric("Densité Agroforestière", f"{p_av['ratio_arbres_ha']:.1f} arbres/ha")
    
    if p_av["rdue_conforme"]:
        col_r2.metric("Statut RDUE / UE", "Conforme ✅")
    else:
        col_r3_delta = 18.0 - p_av["ratio_arbres_ha"]
        col_r2.metric("Statut RDUE / UE", "Non-Conforme ⚠️", delta=f"-{col_r3_delta:.1f} d'arbres/ha", delta_color="inverse")

    col_r3.metric("Gain Brut Estimé (A3)", f"+{p_av['gain_brut_estime_a3']:,.0f} FCFA".replace(",", " "))

    # ---------------------------------------------------------
    # 3. CAPACITÉ FINANCIÈRE & ANALYSE DE SENSIBILITÉ (CHOC DE PRIX)
    # ---------------------------------------------------------
    st.markdown("#### 💳 3. Faisabilité Financière & Résilience aux Chocs")
    solde = p["solde_net_estime"]
    budget_a1 = p["budget_annuel_total"]
    budget_5ans = p["budget_total_5ans"]

    col_f1, col_f2, col_f3 = st.columns(3)
    col_f1.metric("Solde Net Annuel (N-1)", f"{solde:,.0f} FCFA".replace(",", " "))
    col_f2.metric("Budget Requis (Année 1)", f"{budget_a1:,.0f} FCFA".replace(",", " "))
    col_f3.metric("Budget Total (5 Ans)", f"{budget_5ans:,.0f} FCFA".replace(",", " "))

    if solde < budget_a1:
        st.error(f"⚠️ **Déficit de Trésorerie Détecté :** Le solde net disponible ({solde:,.0f} FCFA) ne couvre pas le budget de l'Année 1 ({budget_a1:,.0f} FCFA). Un financement externe ou un préfinancement coopératif est indispensable.")
    else:
        st.success("✅ **Capacité d'Autofinancement Validée :** Le producteur dispose de la marge financière requise pour démarrer les opérations de l'Année 1.")

    # Alerte de sensibilité marché
    if not p_av["resilience_choc_financier"]:
        st.warning(f"📉 **Analyse de Sensibilité :** En cas de baisse de 20% des cours du cacao, la trésorerie nette deviendrait négative ({p_av['marge_choc_valeur']:,.0f} FCFA). Diversification vivement recommandée.")

    # ---------------------------------------------------------
    # 4. RECOMMANDATIONS TECHNIQUES & FEUILLE DE ROUTE LEÏLA
    # ---------------------------------------------------------
    st.markdown("#### 💡 Feuille de Route Opérationnelle Automatisée")
    actions = []

    if not p_av["rdue_conforme"]:
        actions.append(f"**Conformité RDUE (Prioritaire) :** Densité d'ombrage insuffisante ({p_av['ratio_arbres_ha']:.1f} arbres/ha). Introduire au moins {18 - p_av['ratio_arbres_ha']:.0f} arbres forestiers supplémentaires/ha (Akpi, Framiré, Iroko).")

    contraintes_list = [str(c) for c in p["contraintes_parcelle"]]
    if any("Swollen Shoot" in c or "Pourriture" in c or "Foreurs" in c for c in contraintes_list):
        actions.append("**Protection Phytosanitaire :** Attaques parasitaires majeures. Effectuer la taille d'aération, le débroussaillage et la régulation de l'ombrage avant le pic de floraison.")

    if "Métayage" in p["statut_foncier"] or "Fermage" in p["statut_foncier"]:
        actions.append("**Sécurité Foncière :** Exploitants sous régime de partage temporaire. Formaliser un contrat écrit d'exploitation avant d'engager les investissements du plan quinquennal.")

    materiels = p["materiel_agricole"]
    if any(isinstance(m, dict) and m.get("État") == "Mauvais" for m in materiels):
        actions.append("**Équipement & Sécurité :** Renouvellement prioritaire des appareils de traitement et équipement de protection individuel (EPI) déclarés en mauvais état.")

    if not actions:
        actions.append("Le plan est techniquement conforme. Exécuter le programme d'action annuel trimestriel conformément aux échéances prévues.")

    for idx, act in enumerate(actions, 1):
        st.info(f"**Action Prioritaire {idx} :** {act}")

    if p["texte_synthese_auto"]:
        with st.expander("📄 **Voir la synthèse narrative officielle (Modèle CCC)**"):
            st.write(p["texte_synthese_auto"])




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
