# app.py

import os
import re
import logging
import time
import threading
import uuid  # Import pour générer des identifiants uniques
from datetime import datetime, timedelta
from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_community.utilities import SQLDatabase
from langchain_core.output_parsers import StrOutputParser
from langchain_groq import ChatGroq
import streamlit as st
import pandas as pd
from sqlalchemy import inspect, create_engine
import plotly.express as px
import plotly.graph_objects as go
from rapidfuzz import process, fuzz
import io
import requests  # Added for HTTP requests to the backend
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker, Session
import os, sys, socket, webbrowser



def get_base_path():
    if getattr(sys, 'frozen', False):
        # If running as a bundled executable
        return os.path.dirname(sys.executable)
    else:
        # Normal Python environment
        return os.path.abspath(os.path.dirname(__file__))

base_path = get_base_path()

# Path to the .env file (same directory)
dotenv_path = os.path.join(base_path, ".env")

# Load the .env file
load_dotenv(dotenv_path)

# Retrieve the environment variable
BACKEND_SERVER_URL = os.getenv("BACKEND_SERVER_URL")
if not BACKEND_SERVER_URL:
    st.error("BACKEND_SERVER_URL non défini. Veuillez définir cette variable dans le fichier .env.")
    st.stop()

# Générer un identifiant de session unique si non déjà présent
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

# Configurer le logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Créer un gestionnaire de fichier qui ajoute les logs sans écraser le fichier existant
log_file_path = "app.log"
file_handler = logging.FileHandler(log_file_path, mode='a', encoding='utf-8')
file_handler.setLevel(logging.INFO)

# Définir le format des logs
formatter = logging.Formatter(
    '%(asctime)s - Session: %(session_id)s - %(levelname)s - %(message)s'
)
file_handler.setFormatter(formatter)

# Ajouter le gestionnaire au logger
if not logger.handlers:
    logger.addHandler(file_handler)

# Ajouter un filtre personnalisé pour inclure l'identifiant de session dans chaque log
class SessionFilter(logging.Filter):
    def filter(self, record):
        record.session_id = st.session_state.session_id
        return True

logger.addFilter(SessionFilter())

# Mapping des colonnes avec descriptions
COLUMN_DESCRIPTIONS = {
    # ... [Votre dictionnaire complet de colonnes] ...
    "NumDoss": "Numéro de dossier du patient",
    "NumCha": "Numéro de chambre du patient",
    "ServiceHospitalisation": "Service d'hospitalisation du patient",
    "EtaCli": "État du client",
    "NomPatient": "Nom complet du patient",
    "DatNai": "Date de naissance du patient",
    "Nationalite": "Nationalité du patient",
    "NumCIN": "Numéro de Carte d'Identité Nationale",
    "NumTel": "Numéro de téléphone du patient",
    "AdrCli": "Adresse du client",
    "MotifAdmission": "Motif d'admission du patient",
    "NatureAdmission": "Nature de l'admission du patient",
    "Diagnost": "Diagnostic principal",
    "CodePEC": "Code PEC (Prise en Charge)",
    "SocietePEC": "Société PEC (Prise en Charge)",
    "TypReg": "Type de région",
    "Plafond": "Plafond du client",
    "MedecinTraitant": "Médecin traitant du patient",
    "MedSpec": "Spécialité médicale",
    "NomPac": "Nom du patient secondaire",
    "AdrPac": "Adresse du patient secondaire",
    "TelPac": "Téléphone du patient secondaire",
    "NomEng": "Nom de l'engagé",
    "CINEng": "CIN de l'engagé",
    "TelEng": "Téléphone de l'engagé",
    "Observ": "Observations supplémentaires",
    "DatArr": "Date d'arrivée",
    "HeuArr": "Heure d'arrivée",
    "DatDep": "Date de départ",
    "HeuDep": "Heure de départ",
    "NumFac": "Numéro de facture",
    "DatFac": "Date de facturation",
    "TypeSortie": "Type de sortie",
    "TotFactureHT": "Total facturé HT",
    "TotalHonoraire": "Total des honoraires",
    "TotPECHT": "Total PEC HT",
    "TotHonorairePEC": "Total honoraires PEC",
    "TVAPEC": "TVA PEC",
    "TotTVAFacture": "Total TVA facturé",
    "TotRemise": "Total des remises",
    "TotFactureTTC": "Total facturé TTC",
    "Payer": "Statut de paiement",
    "datepay": "Date de paiement",
    "ModReg": "Mode de règlement",
    "TypeArrive": "Type d'arrivée",
    "Avance": "Avance versée",
    "NumInt": "Numéro interne",
    "MedRad": "Médecin radiologue",
    "MedChir": "Médecin chirurgien",
    "MedecinCorrespondant": "Médecin correspondant",
    "EtabOrg": "Établissement d'origine",
    "Kiné": "Kinésithérapeute",
    "Ergo": "Ergothérapeute",
    "Ortho": "Orthophoniste",
    "Timbre": "Timbre du client",
    "Avoir": "Avoirs",
    "RefPEC": "Référence PEC",
    "DatePEC": "Date PEC",
    "NumVir": "Numéro de virement",
    "MntRecu": "Montant reçu",
    "TimbrePEC": "Timbre PEC",
    "UserCre": "Utilisateur création",
    "UserFac": "Utilisateur facturation",
    "RetenuPEC": "Retenue PEC",
    "Eta_Recouv": "État recouvrement",
    "DatCIN": "Date de CIN",
    "DatCinEng": "Date de CIN de l'engagé",
    "Datf_Plaf": "Date plafond",
    "Profession": "Profession",
    "CodCat": "Code catégorie",
    "TypPCE": "Type PEC",
    "Matricule": "Matricule",
    "typconv": "Type de convention",
    "pere": "Nom du père",
    "RemHO": "Remise HO",
    "MntAvoir": "Montant avoir",
    "DatAvoir": "Date avoir",
    "NumPec": "Numéro PEC",
    "Identifiant": "Identifiant",
    "DatDConv": "Date début convention",
    "DatFConv": "Date fin convention",
    "DateEnt": "Date d'entrée",
    "Lieu": "Lieu",
    "Resident": "Statut résident",
    "Autoris": "Autorisation",
    "DatAutoris": "Date d'autorisation",
    "HeuAutoris": "Heure d'autorisation",
    "PER_PEC": "PER PEC",
    "Rem_autoris": "Remise autorisée",
    "User_autoris": "Utilisateur autorisation",
    "CodBurReg": "Code bureau région",
    "AnPriseCh": "Année prise en charge",
    "NumOrdPriseCh": "Numéro ordre prise en charge",
    "NumBordCNAM": "Numéro bordereau CNAM",
    "Duplication": "Duplication",
    "OrgEmpl": "Organisme employeur",
    "Archive": "Statut archive",
    "DatRecep": "Date réception",
    "Classer": "Statut classer",
    "NumCarte": "Numéro de carte",
    "Memo": "Mémo",
    "P_Plafond": "Plafond PEC",
    "Cha_Bloc": "Chambre bloc",
    "num_rdv": "Numéro de rendez-vous",
    "sex": "Sexe du patient (1 pour masculin, 0 pour féminin)",
    "audit": "Audit",
    "Date_audit": "Date d'audit",
    "Heure_audit": "Heure d'audit",
    "User_audit": "Utilisateur audit",
    "DatBordCnam": "Date bordereau CNAM",
    "Copie_Pas": "Copie PAS",
    "usermodif": "Utilisateur modification",
    "Pr_Plafond": "Pr plafond",
    "Libelle_Avance": "Libellé avance",
    "MatPers": "Matériel personnel",
    "CodPat": "Code patient",
    "HOPATPEC": "HOPAT PEC",
    "Libelle_Appurement": "Libellé appurement",
    "Etat_civil": "État civil",
    "Bord_PER_PEC": "Bord PER PEC",
    "has_piece_joint": "Possède pièce jointe",
    "Epous": "Épouse",
    "EpousVeuve": "Épouse veuve",
    "codMedRecommande": "Code médecin recommandé",
    "Nature_Heberg": "Nature de l'hébergement",
    "delegation": "Délégation",
    "motif_urgence": "Motif d'urgence",
    "CliniqueCorr": "Clinique correspondante",
    "CodeCliniqueCorr": "Code clinique correspondante",
    "patientAdmisPMA": "Patient admis PMA",
    "Port_Taxation": "Port taxation",
    "Gouvernorat": "Gouvernorat",
    "CodePostale": "Code postal",
    "Tel2": "Téléphone secondaire",
    "AdresseLocale": "Adresse locale",
    "LIEN_PER_PEC": "Lien PEC",
    "NATURE_PER_PEC": "Nature PEC",
    "Code_Reservation": "Code réservation",
    "MedUrg": "Médecin urgentiste",
    "PersAContacter": "Personne à contacter",
    "TElPersAContacter": "Téléphone personne à contacter",
    "AdrPersAContacter": "Adresse personne à contacter",
    "Intervention_Bloc": "Intervention bloc",
    "photo": "Photo",
    "avoirPhoto": "Avoir photo",
    "num_sous_soc": "Numéro sous société",
    "date_DebCarte": "Date début carte",
    "date_FinCarte": "Date fin carte",
    "codAdherent": "Code adhérent",
    "Pays": "Pays",
    "Num_Bordereau": "Numéro bordereau",
    "NumConv": "Numéro convention",
    "UserRecep": "Utilisateur réception",
    "NomCliAr": "Nom client arabe",
    "PrenomArb": "Prénom arabe",
    "Prenom2Ar": "Deuxième prénom arabe",
    "EpousVeuveAr": "Épouse veuve arabe",
    "EpousAr": "Épouse arabe",
    "pereAr": "Père arabe",
    "userAutorisModifAv": "Utilisateur autorisation modification avance",
    "NumCheque": "Numéro de chèque",
    "email": "Email du client",
    "Accompagnant2": "Accompagnant secondaire",
    "NomPac2": "Nom patient secondaire 2",
    "AdrPac2": "Adresse patient secondaire 2",
    "TelPac2": "Téléphone patient secondaire 2",
    "LienPac2": "Lien patient secondaire 2",
    "ANES": "Anesthésiste",
    "Oeuil": "Œil",
    "EXCEPTION": "Exception",
    "LienPac": "Lien PAC",
    "PEC_Non_Parvenue": "PEC non parvenue",
    "Date_Autois_per": "Date autorisation per",
    "Heure_Autois_per": "Heure autorisation per",
    "Code_Region": "Code région",
    "TypAjusRadio": "Type ajustement radio",
    "Code_Prest_Cnam": "Code prestation CNAM",
    "date_env": "Date d'envoi",
    "Num_Carte": "Numéro carte",
    "Accompagnant": "Accompagnant",
    "VIP": "VIP",
    "Code_Med_Charge": "Code médecin chargé",
    "Code_Emp_Charge": "Code employeur chargé",
    "VLD_EXCEPTION": "VLD exception",
    "ancienID": "Ancien ID",
    "DatSortiePrevue": "Date sortie prévue",
    "lienPersAContacter": "Lien personne à contacter",
    "numDemandeBloc": "Numéro demande bloc",
    "numSoc2": "Numéro société 2",
    "Date_Dep_Prevu": "Date départ prévu",
    "Heure_Dep_Prevu": "Heure départ prévu",
    "Autorise_Per": "Autorisé PER",
    "Recette": "Recette",
    "code_TypePrest": "Code type prestation",
    "Sequence_OPD": "Séquence OPD",
    "UserInstance": "Utilisateur instance",
    "num_cabinet": "Numéro cabinet",
    "ModeConsultation": "Mode de consultation",
    "TypAjusPayant": "Type ajustement payant",
    "TypAjusOrganisme": "Type ajustement organisme",
    "Nbre_seanceReeducation": "Nombre séances rééducation",
    "Prix_unitaire": "Prix unitaire",
    "MntPatient_AlaCharge": "Montant patient à la charge",
    "Vld_Contentieux": "VLD contentieux",
    "Eta_Recouv_Patient": "État recouvrement patient",
    "NumBord_Transf_Cont": "Numéro bordereau transfert contentieux",
    "Etat_Facture": "État facture",
    "A_recep_par": "À réceptionné par",
    "NumBord_Transf_Cont_Pat": "Numéro bordereau transfert contentieux patient",
    "ImprimeBS": "Imprimé BS",
    "plafond_PER_PEC": "Plafond PER PEC",
    "CoursDollar": "Cours dollar",
    "CoursEuro": "Cours euro",
    "verseEsp": "Versement en espèces",
    "ObservationNutrition": "Observation nutrition",
    "CodePrestation": "Code prestation",
    "Date_Acte": "Date acte",
    "Date_Dece": "Date décès",
    "Heure_Dece": "Heure décès",
    "Medecin_Dece": "Médecin décès",
    "service_Dece": "Service décès",
    "NumDevis": "Numéro devis",
    "Renseignement": "Renseignement",
    "Num_CNAM_Recouv": "Numéro CNAM recouvrement",
    "date_depot": "Date dépôt",
    "Vld_Contentieux_patient": "VLD contentieux patient",
    "Etat_Cont_Patient": "État contentieux patient",
    "Etat_Cont_PEC": "État contentieux PEC",
    "Cont_recep_Patient": "Contentieux réception patient",
    "Cont_recep_PEC": "Contentieux réception PEC",
    "NomArb": "Nom arabe",
    "PrenomArb": "Prénom arabe",
    "Per_PEC_Personnel": "PER PEC personnel",
    "Nature_Per_PEC_Personnel": "Nature PER PEC personnel",
    "Numadmission": "Numéro admission",
    "Comute": "Commute",
    "MedTrait2": "Médecin traitant 2",
    "autorisConsultDMIcentral": "Autorisation consultation DMI central",
    "CINPac": "CIN patient",
    "DocManquant": "Documents manquants",
    "newIdent": "Nouvel identifiant",
    "NumSocMutuelle": "Numéro société mutuelle",
    "Devise": "La devise utilisée par la clinique",
}

# Nombre maximum de messages à conserver dans l'historique de conversation
MAX_CHAT_HISTORY = 3

# Liste des colonnes pour le prompt
COLUMN_LIST = "\n".join(
    [f"- **{col}**: {desc}" for col, desc in COLUMN_DESCRIPTIONS.items()]
)

# -------------------------
# Authentication Implementation
# -------------------------

# Define the secret key
# You can set the secret key as an environment variable, or hardcode it directly
#SECRET_KEY = os.getenv("SECRET_KEY")
#if not SECRET_KEY:
  #  SECRET_KEY = "ghassen"  # Remplacez par votre clé secrète
    # Alternatively, you can enforce setting it via environment variable:
    # st.error("Clé secrète non trouvée. Veuillez définir la variable d'environnement SECRET_KEY.")
    # st.stop()


def check_authentication():
    """
    Verifies user authentication via license key.
    """
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
        st.session_state.api_key = None
        st.session_state.license_key = None
        st.session_state.license_expiry = None

    if not st.session_state.authenticated:
        st.sidebar.title("Authentification Requise")
        license_key_input = st.sidebar.text_input("Entrez votre clé de licence:", type="password")
        auth_button = st.sidebar.button("Valider")
        if auth_button:
            if validate_license(license_key_input):
                st.session_state.authenticated = True
                st.session_state.license_key = license_key_input
                st.sidebar.success("Authentification réussie!")
            else:
                st.sidebar.error("Clé de licence invalide ou inactive. Veuillez réessayer.")
        st.stop()  # Stop execution if not authenticated

def validate_license(license_key: str) -> bool:
    """
    Validates the license key by communicating with the backend server.
    Retrieves and stores the associated API key and expiry date if valid.
    """
    try:
        response = requests.post(
            f"{BACKEND_SERVER_URL}/validate_license",
            json={"license_key": license_key},
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            if data.get("valid"):
                st.session_state.api_key = data.get("api_key")
                st.session_state.license_expiry = data.get("expiry_date")
                logger.info("Licence validée et clé API récupérée.")
                return True
        elif response.status_code == 400:
            data = response.json()
            logger.warning(f"Validation échouée: {data.get('detail')}")
            return False
        else:
            logger.error(f"Erreur lors de la validation de la licence: {response.status_code} - {response.text}")
            st.sidebar.error("Erreur lors de la validation de la licence. Veuillez réessayer plus tard.")
            return False
    except requests.exceptions.RequestException as e:
        logger.exception(f"Erreur lors de la validation de la licence: {e}")
        st.sidebar.error("Erreur de connexion au serveur de licences. Veuillez réessayer plus tard.")
        return False



check_authentication()

def check_license_expiry():
       """
       Checks if the license is about to expire and prompts the user to renew.
       """
       if "license_expiry" in st.session_state and st.session_state.license_expiry:
           expiry = datetime.strptime(st.session_state.license_expiry, "%Y-%m-%dT%H:%M:%S.%f")
           days_left = (expiry - datetime.utcnow()).days
           if days_left <= 30:  # Notify if 30 days or less left
               st.sidebar.warning(f"Votre licence expire dans {days_left} jours.")
               renew_button = st.sidebar.button("Renouveler la licence")
               if renew_button:
                   renew_license()
   
def renew_license():
    """
    Sends a request to the backend server to renew the license.
    """
    try:
        response = requests.post(
            f"{BACKEND_SERVER_URL}/renew_license",
            json={"license_key": st.session_state.license_key, "additional_days": 365},
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            st.session_state.license_expiry = data.get("expiry_date")
            st.sidebar.success("Licence renouvelée avec succès!")
            logger.info("Licence renouvelée avec succès.")
        else:
            data = response.json()
            st.sidebar.error(f"Échec du renouvellement: {data.get('detail')}")
            logger.warning(f"Renouvellement échoué: {data.get('detail')}")
    except requests.exceptions.RequestException as e:
        logger.exception(f"Erreur lors du renouvellement de la licence: {e}")
        st.sidebar.error("Erreur de connexion au serveur de licences. Veuillez réessayer plus tard.")


   # Call the license expiry check
check_license_expiry()
   




def get_global_currency(engine) -> str:
    """
    Récupère la devise globale utilisée par l'application depuis la table param.
    """
    try:
        df = pd.read_sql_query("SELECT Valeur FROM param WHERE code='UNITEMONAITAIRE'", engine)
        if not df.empty and pd.notnull(df.iloc[0]['Valeur']):
            currency = df.iloc[0]['Valeur']
            logger.info(f"Devise globale trouvée: {currency}")
            return currency
        else:
            logger.warning("Aucune devise trouvée dans la table param. Utilisation de 'USD' par défaut.")
            return "USD"  # Valeur par défaut si aucune devise n'est trouvée
    except Exception as e:
        logger.exception(f"Erreur lors de la récupération de la devise globale: {e}")
        return "USD"  # Valeur par défaut en cas d'erreur


# Mapping des codes de devise aux symboles monétaires
CURRENCY_SYMBOLS = {
    "EUR": "€",
    "USD": "$",
    "GBP": "£",
    "JPY": "¥",
    "CHF": "CHF",
    "TND": "TND",
    # Ajoutez d'autres devises selon vos besoins
}

def get_currency_symbol(currency_code: str) -> str:
    """
    Retourne le symbole monétaire correspondant au code de devise.
    """
    return CURRENCY_SYMBOLS.get(currency_code.upper(), currency_code)

# Ajout d'une fonction pour nettoyer les symboles de devise dans les montants
def remove_currency_symbols(text: str) -> str:
    """
    Supprime les symboles de devise des montants dans le texte.
    """
    currency_symbols_pattern = '|'.join(map(re.escape, CURRENCY_SYMBOLS.values()))
    pattern = re.compile(rf'(\d{{1,3}}(?:[ \u202F]\d{{3}})*(?:,\d{{2}})?)\s*({currency_symbols_pattern})')
    cleaned_text = pattern.sub(r'\1', text)
    return cleaned_text

# Implémentation du Token Bucket pour le Throttling
class TokenBucket:
    def __init__(self, tokens_per_minute):
        self.capacity = tokens_per_minute
        self.tokens = tokens_per_minute
        self.lock = threading.Lock()
        self.last_refill = time.monotonic()

    def consume(self, tokens_needed):
        with self.lock:
            current_time = time.monotonic()
            elapsed = current_time - self.last_refill
            refill_tokens = elapsed * (self.capacity / 60)
            if refill_tokens > 0:
                self.tokens = min(self.capacity, self.tokens + refill_tokens)
                self.last_refill = current_time
            if self.tokens >= tokens_needed:
                self.tokens -= tokens_needed
                return True
            else:
                return False

def throttle(token_bucket, tokens_needed):
    """
    Décorateur pour throttler les appels en fonction du TokenBucket.
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            while not token_bucket.consume(tokens_needed):
                with token_bucket.lock:
                    time_since_last_refill = time.monotonic() - token_bucket.last_refill
                    time_to_wait = max(
                        0, (60 / token_bucket.capacity) - time_since_last_refill
                    )
                logger.info(
                    f"Attente de {time_to_wait:.2f} secondes pour respecter la limite TPM..."
                )
                time.sleep(time_to_wait)
            return func(*args, **kwargs)
        return wrapper
    return decorator

def num_tokens_from_string(string: str) -> int:
    """
    Estime le nombre de tokens à partir d'une chaîne de caractères.
    Approximativement 4 caractères par token.
    """
    tokens = max(1, len(string) // 4)
    logger.info(f"Tokens estimés pour la chaîne: {tokens}")
    return tokens
    
@st.cache_data
def init_database_cached(host, user, password, database, port):
    # Build a single ODBC connection string with encryption/trust flags
    odbc_str = (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={host},{port};"
        f"DATABASE={database};"
        f"UID={user};"
        f"PWD={password};"
        "Encrypt=yes;"
        "TrustServerCertificate=yes;"
        "Connection Timeout=30;"
    )
    conn_url = "mssql+pyodbc:///?odbc_connect=" + urllib.parse.quote_plus(odbc_str)

    # Create engine (fast_executemany for bulk ops)
    engine = create_engine(conn_url, fast_executemany=True)

    # Quick connectivity test
    with engine.connect() as conn:
        logger.info("Streamlit DB connection test successful.")

    # Prepare session factory and return a session
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    return db, engine



@st.cache_data
def get_view_schema_cached(
    _engine, view_name: str = "VPatientAI", schema: str = "dbo"
) -> dict:
    """
    Récupère les informations des colonnes pour une vue spécifique en utilisant l'inspecteur de SQLAlchemy.
    """
    try:
        inspector = inspect(_engine)
        columns_info = inspector.get_columns(view_name, schema=schema)
        columns = [
            {"name": col["name"], "type": str(col["type"])} for col in columns_info
        ]
        logger.debug(f"Schéma récupéré pour la vue {view_name}: {columns}")
        return {"columns": columns}
    except Exception as e:
        logger.exception(
            f"Erreur lors de la récupération du schéma de la vue {view_name}: {e}"
        )
        return {"columns": []}

def get_sql_chain(db: SQLDatabase, engine) -> RunnablePassthrough:
    """
    Crée une chaîne LangChain qui génère des requêtes SQL basées sur l'entrée utilisateur.
    """
    current_year = datetime.now().year

    template = f"""
        Vous êtes un analyste de données dans une clinique. Vous interagissez avec un utilisateur qui vous pose des questions sur la base de données de la clinique.
        La base de données est une base de données SQL Server.
        **La date actuelle est {current_year}.**
        **La devise utilisée pour les transactions est {st.session_state.currency}.**
        Ci-dessous se trouve le schéma de la vue VPatientAI avec les descriptions des colonnes.

        <SCHEMA>
        {COLUMN_LIST}
        </SCHEMA>

        Basé sur la question de l'utilisateur, faites ce qui suit:

        1. Écrivez une requête SQL Server qui répond à la question de l'utilisateur.
            - Utilisez la syntaxe SQL appropriée pour SQL Server.
            - N'incluez aucun regroupement inutile.
            - Sélectionnez uniquement les colonnes pertinentes nécessaires pour répondre à la question.
            - **Pour les expressions temporelles comme "cette année", utilisez YEAR(GETDATE()) pour obtenir l'année actuelle.**
            - **N'incluez pas de backticks (`) ou de balises de code markdown (```).**
            - **Écrivez uniquement la requête SQL en texte brut et rien d'autre.**
            - Lorsque vous utilisez GROUP BY, assurez-vous que toutes les colonnes du SELECT qui ne sont pas dans des fonctions d'agrégation sont incluses dans le GROUP BY.
            - Utilisez des fonctions d'agrégation appropriées (comme SUM, COUNT, AVG) pour les colonnes numériques non incluses dans le GROUP BY.
            - **Lorsque l'utilisateur mentionne "sex" ou "sexe", utilisez la colonne sex dans la base de données où `1` représente masculin et `0` représente féminin.**
            - **Même si la question est une demande de visualisation, générez toujours une requête SQL valide.**
            - **N'incluez pas de filtre sur la devise à moins que l'utilisateur ne le demande explicitement.**
            - **Ne mentionnez pas le symbole de la devise dans les montants.**

        2. Déterminez si l'utilisateur demande une représentation graphique des données.
            - Si oui, spécifiez le type de graphique qui serait le plus approprié (par exemple, barres, lignes, camembert, etc.).
            - Sinon, indiquez qu'aucun graphique n'est requis.

        Fournissez votre réponse dans le format suivant (n'incluez pas de backticks ou de balises de code) :

        Requête SQL:
        [Votre requête SQL ici]

        Graphique Requis: [Oui/Non]
        Type de Graphique: [Type de graphique si applicable]

        #### **Exemples :**
        ---
        **Question :** Quel est le chiffre d'affaires total pour Mme Dupont?

        **Requête SQL:**
        SELECT SUM(TotFactureTTC) AS ChiffreAffairesTotal FROM dbo.VPatientAI WHERE NomPatient = 'Dupont';

        **Graphique Requis:** Non
        **Type de Graphique:** Aucun
        ---
        **Question :** Montrez le nombre de patients par nationalité sous forme de graphique en barres.

        **Requête SQL:**
        SELECT Nationalite, COUNT(*) AS NombrePatients FROM dbo.VPatientAI GROUP BY Nationalite;

        **Graphique Requis:** Oui
        **Type de Graphique:** Barres
        ---
        **Question :** Quelle est la distribution des âges des patients sous forme d'histogramme.

        **Requête SQL:**
        SELECT DATEDIFF(year, DatNai, GETDATE()) AS Age
        FROM dbo.VPatientAI;

        **Graphique Requis:** Oui
        **Type de Graphique:** Histogramme
        ---
        **Question :** Affichez un nuage de points du chiffre d'affaires en fonction de l'âge des patients.

        **Requête SQL:**
        SELECT DATEDIFF(year, DatNai, GETDATE()) AS Age, TotFactureTTC
        FROM dbo.VPatientAI;

        **Graphique Requis:** Oui
        **Type de Graphique:** Nuage de points
        ---
        **Question :** Pourriez-vous afficher ces données sous forme de scatter plot ?

        **Requête SQL:**
        [Utiliser la dernière requête SQL]

        **Graphique Requis:** Oui
        **Type de Graphique:** Scatter Plot
        ---
        **Question :** Créez un graphique radar comparant le nombre de diagnostics par service.

        **Requête SQL:**
        SELECT ServiceHospitalisation, COUNT(DISTINCT Diagnost) AS NombreDiagnostics
        FROM dbo.VPatientAI
        GROUP BY ServiceHospitalisation;

        **Graphique Requis:** Oui
        **Type de Graphique:** Radar
        ---
        **Question :** Donnez-moi la liste des patients admis en 2022.

        **Requête SQL:**
        SELECT NomPatient, DatArr, ServiceHospitalisation
        FROM dbo.VPatientAI
        WHERE YEAR(DatArr) = 2022;

        **Graphique Requis:** Non
        **Type de Graphique:** Aucun
        ---
        **Question :** Montrez le nombre de patients par tranche d'âge sous forme de barres.

        **Requête SQL:**
        SELECT
            CASE
                WHEN Age BETWEEN 0 AND 9 THEN '0-9'
                WHEN Age BETWEEN 10 AND 19 THEN '10-19'
                WHEN Age BETWEEN 20 AND 29 THEN '20-29'
                WHEN Age BETWEEN 30 AND 39 THEN '30-39'
                WHEN Age BETWEEN 40 AND 49 THEN '40-49'
                WHEN Age BETWEEN 50 AND 59 THEN '50-59'
                WHEN Age >= 60 THEN '60+'
            END AS TrancheAge,
            COUNT(*) AS NombrePatients
        FROM (
            SELECT DATEDIFF(year, DatNai, GETDATE()) AS Age
            FROM dbo.VPatientAI
        ) AS SousRequête
        GROUP BY
            CASE
                WHEN Age BETWEEN 0 AND 9 THEN '0-9'
                WHEN Age BETWEEN 10 AND 19 THEN '10-19'
                WHEN Age BETWEEN 20 AND 29 THEN '20-29'
                WHEN Age BETWEEN 30 AND 39 THEN '30-39'
                WHEN Age BETWEEN 40 AND 49 THEN '40-49'
                WHEN Age BETWEEN 50 AND 59 THEN '50-59'
                WHEN Age >= 60 THEN '60+'
            END;

        **Graphique Requis:** Oui
        **Type de Graphique:** Barres
        ---
        **Question :** Affichez la répartition des types d'admission des patients.

        **Requête SQL:**
        SELECT NatureAdmission, COUNT(*) AS NombreAdmissions
        FROM dbo.VPatientAI
        GROUP BY NatureAdmission;

        **Graphique Requis:** Non
        **Type de Graphique:** Aucun
        ---
        **Question :** Montrez la répartition des patients féminins par nationalité sous forme de graphique en camembert.

        **Requête SQL:**
        SELECT Nationalite, COUNT(*) AS NombrePatientsFemmes
        FROM dbo.VPatientAI
        WHERE sex = 0
        GROUP BY Nationalite;

        **Graphique Requis:** Oui
        **Type de Graphique:** Camembert
        ---
        **Question :** Quelle est la moyenne d'âge des patients masculins par service d'hospitalisation?

        **Requête SQL:**
        SELECT ServiceHospitalisation, AVG(DATEDIFF(year, DatNai, GETDATE())) AS AgeMoyenHommes
        FROM dbo.VPatientAI
        WHERE sex = 1
        GROUP BY ServiceHospitalisation;

        **Graphique Requis:** Non
        **Type de Graphique:** Aucun
        ---
        **Question :** Quel est le chiffre d'affaires total réalisé en mars pour les patientes (sexe féminin) nées en juin ?

        **Requête SQL:**
        SELECT SUM(TotFactureTTC) AS ChiffreAffairesTotal
        FROM dbo.VPatientAI
        WHERE sex = 0 AND DATEPART(MONTH, DatNai) = 6 AND DATEPART(MONTH, DatFac) = 3;

        **Graphique Requis:** Oui
        **Type de Graphique:** Barres
        ---
        **Question :** Donnez-moi la liste des patients admis cette année.

        **Requête SQL:**
        SELECT NomPatient, DatArr, ServiceHospitalisation
        FROM dbo.VPatientAI
        WHERE YEAR(DatArr) = YEAR(GETDATE());

        **Graphique Requis:** Non
        **Type de Graphique:** Aucun
        ---
        **Question :** Montrez le chiffre d'affaires total par service pour cette année sous forme de camembert.

        **Requête SQL:**
        SELECT ServiceHospitalisation, SUM(TotFactureTTC) AS ChiffreAffairesTotal
        FROM dbo.VPatientAI
        WHERE YEAR(DatFac) = YEAR(GETDATE())
        GROUP BY ServiceHospitalisation;

        **Graphique Requis:** Oui
        **Type de Graphique:** Camembert
        ---
        **Question :** Pouvez-vous visualiser cette répartition sous forme de camembert ?

        **Requête SQL:**
        [Utiliser la dernière requête SQL]

        **Graphique Requis:** Oui
        **Type de Graphique:** Camembert
        ---
        **Question :** Sous forme de scatter plot maintenant.

        **Requête SQL:**
        [Utiliser la dernière requête SQL]

        **Graphique Requis:** Oui
        **Type de Graphique:** Scatter Plot
        ---
    
        Votre tour:
    
        Question: {{question}}
    """

    prompt = ChatPromptTemplate.from_template(template)

    # Initialiser le modèle LLM pour générer des requêtes SQL (Groq AI)
    groq_api_key = st.session_state.get("api_key")
    if not groq_api_key:
        st.error("Clé API Groq AI manquante. Veuillez valider votre licence.")
        return None

    llm_sql = ChatGroq(
        model="llama3-8b-8192", temperature=0.2, api_key=groq_api_key
    )

    sql_chain = (
        RunnablePassthrough.assign(
            schema=lambda vars: get_view_schema_cached(engine, "VPatientAI", "dbo")
        )
        | prompt
        | llm_sql
        | StrOutputParser()
    )

    return sql_chain

def parse_llm_response(response: str) -> dict:
    """
    Analyse la réponse du LLM pour extraire la requête SQL, si un graphique est requis, et le type de graphique.
    """
    result = {"sql_query": "", "graph_required": False, "chart_type": None}

    # Utiliser des expressions régulières pour extraire la requête SQL et autres informations
    sql_match = re.search(
        r"Requête SQL:\s*(.*?)\s*(Graphique Requis:|$)", response, re.DOTALL
    )
    if sql_match:
        sql_query = sql_match.group(1).strip()
        # Supprimer les balises de code et les backticks
        sql_query = re.sub(r"```sql\s*|```", "", sql_query).strip()
        sql_query = sql_query.replace("`", "")
        result["sql_query"] = sql_query

    graph_match = re.search(r"Graphique Requis:\s*(Oui|Non)", response, re.IGNORECASE)
    if graph_match:
        result["graph_required"] = graph_match.group(1).strip().lower() == "oui"

    chart_type_match = re.search(r"Type de Graphique:\s*(.*)", response)
    if chart_type_match:
        chart_type = chart_type_match.group(1).strip()
        if chart_type.lower() != "aucun":
            result["chart_type"] = chart_type

    return result

def is_visualization_request(user_query: str) -> bool:
    """
    Détermine si la requête de l'utilisateur est une demande de visualisation.
    Utilise des phrases spécifiques et des expressions régulières pour une meilleure précision.
    """
    visualization_patterns = [
        r"montrez.*sous forme de (camembert|barres|graphique en ligne|nuage de points|scatter plot|histogramme|radar|boîte à moustaches|aire|carte|ligne)",
        r"visualisez.*en (camembert|barres|graphique en ligne|nuage de points|scatter plot|histogramme|radar|boîte à moustaches|aire|carte|ligne)",
        r"peux-tu.*sous forme de (camembert|barres|graphique en ligne|nuage de points|scatter plot|histogramme|radar|boîte à moustaches|aire|carte|ligne)",
        r"générez.*(camembert|barres|graphique en ligne|nuage de points|scatter plot|histogramme|radar|boîte à moustaches|aire|carte|ligne)",
        r"affichez.*(camembert|barres|graphique en ligne|nuage de points|scatter plot|histogramme|radar|boîte à moustaches|aire|carte|ligne)",
        r"créez.*(camembert|barres|graphique en ligne|nuage de points|scatter plot|histogramme|radar|boîte à moustaches|aire|carte|ligne)",
        # Patterns supplémentaires pour détecter "sous forme de" sans verbe explicite
        r"sous forme de (camembert|barres|graphique en ligne|nuage de points|scatter plot|histogramme|radar|boîte à moustaches|aire|carte|ligne)",
        r"visualiser (camembert|barres|graphique en ligne|nuage de points|scatter plot|histogramme|radar|boîte à moustaches|aire|carte|ligne)",
    ]

    for pattern in visualization_patterns:
        if re.search(pattern, user_query, re.IGNORECASE):
            logger.info(f"Requête détectée comme demande de visualisation: {user_query}")
            return True
    logger.info(f"Requête détectée comme non demande de visualisation: {user_query}")
    return False

def extract_chart_type(user_query: str) -> str:
    """
    Extrait le type de graphique demandé à partir de la requête de l'utilisateur.
    """
    chart_types = ["camembert", "barres", "graphique en ligne", "nuage de points", "scatter plot", "histogramme", "radar", "boîte à moustaches", "aire", "carte", "ligne"]
    for chart in chart_types:
        if chart in user_query.lower():
            return chart
    return ""

def generate_visualization(dataframe: pd.DataFrame, chart_type: str, currency_symbol: str):
    """
    Génère une visualisation Plotly basée sur le DataFrame et le type de graphique souhaité.
    """
    try:
        if dataframe.empty:
            logger.warning("Le DataFrame est vide. Aucune visualisation générée.")
            return None

        fig = None

        # Convertir le type de graphique en minuscule et supprimer les espaces inutiles
        chart_type_cleaned = chart_type.lower().strip()

        # Liste des types de graphiques standardisés
        standardized_chart_types = [
            "line",
            "bar",
            "pie",
            "scatter",
            "box",
            "area",
            "radar",
            "map",
            "histogram"
        ]

        # Mapping des synonymes de types de graphiques aux types standardisés
        chart_type_mapping = {
            "line": [
                "ligne",
                "linéaire",
                "line",
                "courbe",
                "graphique linéaire",
                "graphique de ligne",
            ],
            "bar": [
                "barres",
                "bar",
                "histogramme",
                "barras",
                "graphique en barres",
                "diagramme en barres",
                "bar chart",
            ],
            "pie": [
                "camembert",
                "circulaire",
                "pie",
                "pie chart",
                "graphique camembert",
                "diagramme circulaire",
            ],
            "scatter": [
                "nuage de points",
                "scatter",
                "dispersion",
                "scatter plot",
                "graphique de dispersion",
                "diagramme de dispersion",
            ],
            "box": [
                "boîte à moustaches",
                "box",
                "boîte",
                "box plot",
                "graphique boîte à moustaches",
            ],
            "area": ["aire", "area", "graphique en aire", "graphique area"],
            "radar": ["radar", "graphique radar", "diagramme radar"],
            "map": ["carte", "map", "mapbox", "graphique carte", "carte géographique"],
            "histogram": ["histogramme", "histogram"],
        }

        # Création d'un mapping inversé pour une recherche rapide
        reverse_mapping = {}
        for std_type, synonyms in chart_type_mapping.items():
            for synonym in synonyms:
                reverse_mapping[synonym] = std_type

        # Utilisation de RapidFuzz pour trouver la meilleure correspondance
        all_synonyms = list(reverse_mapping.keys())

        # Trouver la meilleure correspondance avec un score de similarité
        match, score, _ = process.extractOne(
            chart_type_cleaned, all_synonyms, scorer=fuzz.token_sort_ratio
        )

        # Définir un seuil de similarité
        similarity_threshold = 80  # Ajustez en fonction de la rigueur souhaitée

        if score >= similarity_threshold:
            standardized_chart_type = reverse_mapping[match]
            logger.info(
                f"Type de graphique '{chart_type}' mappé au type standardisé '{standardized_chart_type}' avec un score de {score}."
            )
        else:
            logger.warning(
                f"Type de graphique inconnu ou non pris en charge: {chart_type} (meilleur score: {score})."
            )
            return None

        # Générer la figure Plotly appropriée en fonction du type de graphique standardisé
        if standardized_chart_type == "line":
            if dataframe.shape[0] < 2:
                logger.warning("Données insuffisantes pour un graphique linéaire.")
                return None
            x_col = dataframe.columns[0]
            y_col = dataframe.columns[1]
            fig = px.line(
                dataframe,
                x=x_col,
                y=y_col,
                title=f"Graphique Linéaire de {y_col} en fonction de {x_col}",
            )
            fig.update_layout(xaxis_title=x_col, yaxis_title=f"{y_col}")

        elif standardized_chart_type == "bar":
            if dataframe.shape[1] < 2:
                logger.warning("Données insuffisantes pour un graphique en barres.")
                return None
            x_col = dataframe.columns[0]
            y_col = dataframe.columns[1]
            color_col = dataframe.columns[2] if dataframe.shape[1] > 2 else None
            fig = px.bar(
                dataframe,
                x=x_col,
                y=y_col,
                color=color_col,
                title=f"Graphique en Barres de {y_col} par {x_col}"
                + (f" et {color_col}" if color_col else ""),
            )
            fig.update_layout(xaxis_title=x_col, yaxis_title=f"{y_col}")

        elif standardized_chart_type == "pie":
            if dataframe.shape[1] < 2:
                logger.warning("Données insuffisantes pour un graphique en camembert.")
                return None
            names_col = dataframe.columns[0]
            values_col = dataframe.columns[1]
            fig = px.pie(
                dataframe,
                names=names_col,
                values=values_col,
                title=f"Graphique Camembert de {values_col} par {names_col}",
            )

        elif standardized_chart_type == "scatter":
            if dataframe.shape[1] < 2:
                logger.warning("Données insuffisantes pour un nuage de points.")
                return None
            if dataframe.shape[0] < 2:
                logger.warning("Données insuffisantes pour un nuage de points.")
                return None
            x_col = dataframe.columns[0]
            y_col = dataframe.columns[1]
            fig = px.scatter(
                dataframe,
                x=x_col,
                y=y_col,
                title=f"Nuage de Points de {y_col} en fonction de {x_col}",
            )
            fig.update_layout(xaxis_title=x_col, yaxis_title=f"{y_col}")

        elif standardized_chart_type == "box":
            if dataframe.shape[1] < 2:
                logger.warning(
                    "Données insuffisantes pour un graphique boîte à moustaches."
                )
                return None
            x_col = dataframe.columns[0]
            y_col = dataframe.columns[1]
            fig = px.box(
                dataframe,
                x=x_col,
                y=y_col,
                title=f"Boîte à Moustaches de {y_col} par {x_col}",
            )
            fig.update_layout(xaxis_title=x_col, yaxis_title=f"{y_col}")

        elif standardized_chart_type == "area":
            if dataframe.shape[1] < 2:
                logger.warning("Données insuffisantes pour un graphique en aire.")
                return None
            x_col = dataframe.columns[0]
            y_col = dataframe.columns[1]
            fig = px.area(
                dataframe,
                x=x_col,
                y=y_col,
                title=f"Graphique en Aire de {y_col} en fonction de {x_col}",
            )
            fig.update_layout(xaxis_title=x_col, yaxis_title=f"{y_col}")

        elif standardized_chart_type == "radar":
            if dataframe.shape[1] < 3:
                logger.warning("Données insuffisantes pour un graphique radar.")
                return None
            categories = list(dataframe.columns[1:])
            fig = go.Figure()
            for i in range(len(dataframe)):
                fig.add_trace(
                    go.Scatterpolar(
                        r=dataframe.iloc[i, 1:].values.tolist(),
                        theta=categories,
                        fill="toself",
                        name=str(dataframe.iloc[i, 0]),
                    )
                )
            fig.update_layout(
                polar=dict(radialaxis=dict(visible=True)),
                title=f"Graphique Radar"
            )

        elif standardized_chart_type == "map":
            # Vérifier que les colonnes 'latitude' et 'longitude' existent
            if "latitude" in dataframe.columns and "longitude" in dataframe.columns:
                fig = px.scatter_mapbox(
                    dataframe, lat="latitude", lon="longitude", zoom=3, title="Carte"
                )
                fig.update_layout(mapbox_style="open-street-map")
            else:
                logger.warning(
                    "Les colonnes 'latitude' et 'longitude' sont nécessaires pour un graphique de carte."
                )
                return None

        elif standardized_chart_type == "histogram":
            if dataframe.shape[1] < 1:
                logger.warning("Données insuffisantes pour un histogramme.")
                return None
            x_col = dataframe.columns[0]
            fig = px.histogram(
                dataframe,
                x=x_col,
                title=f"Histogramme de {x_col}",
            )
            fig.update_layout(xaxis_title=x_col, yaxis_title="Fréquence")

        else:
            logger.warning(
                f"Type de graphique inconnu ou non pris en charge: {chart_type}"
            )
            return None

        logger.info("Visualisation générée avec succès.")
        return fig
    except Exception as e:
        logger.exception(f"Erreur lors de la génération de la visualisation: {e}")
        return None

def init_groq_ai():
    """
    Initializes Groq AI with the assigned API key.
    """
    try:
        groq_api_key = st.session_state.get("api_key")
        if not groq_api_key:
            st.error("Groq AI API key non assignée. Veuillez valider votre licence.")
            logger.error("Groq AI API key non assignée.")
            return None

        groq_ai = ChatGroq(
            model="llama3-8b-8192", temperature=0.2, api_key=groq_api_key
        )
        logger.info("Groq AI initialized successfully.")
        return groq_ai
    except Exception as e:
        logger.exception(f"Failed to initialize Groq AI: {e}")
        st.error("Erreur lors de l'initialisation de Groq AI.")
        return None


def extract_wait_time(error_message):
    """
    Extrait le temps d'attente en secondes à partir du message d'erreur.
    """
    match = re.search(r"Please try again in (\d+)m(\d+\.\d+)s", error_message)
    if match:
        minutes = int(match.group(1))
        seconds = float(match.group(2))
        total_seconds = minutes * 60 + seconds
        return total_seconds
    return 60  # Défaut à 60 secondes si l'extraction échoue

def get_response(user_query: str, db: SQLDatabase, engine, chat_history: list, groq_ai, token_bucket) -> dict:
    """
    Génère une réponse en langage naturel et une visualisation basée sur la requête de l'utilisateur,
    en utilisant la devise globale stockée.
    """
    try:
        currency = st.session_state.get("currency", "USD")
        currency_symbol = get_currency_symbol(currency)
        limited_chat_history = [msg.content for msg in chat_history[-MAX_CHAT_HISTORY:]]
        logger.debug(f"Historique limité à {MAX_CHAT_HISTORY} messages contenus uniquement.")
        current_convo = st.session_state.current_conversation
        last_sql_query = st.session_state.conversations[current_convo].get("last_sql_query", None)

        if is_visualization_request(user_query):
            if last_sql_query:
                chart_type = extract_chart_type(user_query)
                if not chart_type:
                    return {
                        "response": "Type de graphique non reconnu. Veuillez spécifier un type valide (ex: courbe, barres, camembert).",
                        "visualization": None,
                        "table": None,
                    }
                try:
                    sql_response_df = pd.read_sql_query(last_sql_query, engine)
                    logger.info(f"Réponse SQL pour visualisation: {sql_response_df}")
                except Exception as e:
                    logger.exception(f"Erreur lors de l'exécution de la dernière requête SQL: {e}")
                    return {
                        "response": "Erreur lors de l'exécution de la dernière requête SQL pour la visualisation.",
                        "visualization": None,
                        "table": None,
                    }
                fig = generate_visualization(sql_response_df, chart_type, currency_symbol)
                if fig:
                    ai_response_content = f"Voici la visualisation sous forme de {chart_type}. (Devise utilisée : {currency})"
                    table = sql_response_df if len(sql_response_df) <= 100 else None
                    return {"response": ai_response_content, "visualization": fig, "table": table}
                else:
                    return {"response": "Impossible de générer la visualisation demandée.", "visualization": None, "table": None}
            else:
                return {"response": "Aucune requête précédente à visualiser. Veuillez poser une question d'abord.", "visualization": None, "table": None}
        else:
            sql_chain = get_sql_chain(db, engine)
            if not sql_chain:
                logger.error("Chaîne SQL non initialisée.")
                return {"response": "Erreur lors de la création de la chaîne SQL.", "visualization": None, "table": None}
            try:
                sql_query_response = sql_chain.invoke({"question": user_query, "chat_history": limited_chat_history})
                logger.info(f"Réponse brute du LLM: {sql_query_response}")
                logger.info(f"Question utilisateur: {user_query}")
            except Exception as e:
                logger.exception(f"Erreur lors de l'invocation de la chaîne SQL: {e}")
                return {"response": "Erreur lors de la génération de la requête SQL.", "visualization": None, "table": None}

            response_text = ""
            if hasattr(sql_query_response, "content"):
                response_text = sql_query_response.content
            elif isinstance(sql_query_response, dict):
                response_text = sql_query_response.get("content", "")
            else:
                content_match = re.search(r"content='(.*?)'", str(sql_query_response))
                response_text = content_match.group(1).strip() if content_match else str(sql_query_response).strip()
            response_text = remove_currency_symbols(response_text)
            parsed_response = parse_llm_response(response_text)
            sql_query_extracted = parsed_response["sql_query"]
            graph_required = parsed_response["graph_required"]
            chart_type = parsed_response["chart_type"]
            logger.info(f"Requête SQL extraite: {sql_query_extracted}")
            logger.info(f"Graphique requis: {graph_required}")
            logger.info(f"Type de graphique: {chart_type}")

            if not sql_query_extracted:
                logger.error("Aucune requête SQL n'a été extraite de la réponse de l'IA.")
                return {"response": "Je suis désolé, je n'ai pas pu générer une requête SQL valide. Veuillez reformuler votre question.", "visualization": None, "table": None}
            if not sql_query_extracted.lower().strip().startswith("select"):
                logger.error("La requête SQL extraite ne commence pas par SELECT.")
                return {"response": "La requête SQL générée est invalide.", "visualization": None, "table": None}
            
            # Vérifier si la requête utilise VPatientAI
            if "VPatientAI" in sql_query_extracted:
                # Ajouter la définition de la vue en tant que CTE
                view_definition = """
                WITH VPatientAI AS (
                    -- Contenu de la définition de la vue
                    SELECT NumDoss
                    , client.NumCha --- par chambre
                    ,Services.des_service as ServiceHospitalisation --- par service 
                    , EtaCli, RTRIM(replace(NomCli+' ' + Prenom,'  ',' ')) as NomPatient
                    , DatNai
                    ,Nationnalite.libnat as Nationalite  --- par nationalité
                    , NumCIN, NumTel
                    , AdrCli,motif.Des as MotifAdmission --- par motif d'admission
                    ,natadm.Des as NatureAdmission -- par nature d'admission
                    , Diagnost
                    ,case client.NumSoc when '' then 'PAYANT' else client.NumSoc end as CodePEC, isnull(societe.dessoc,'PAYANT') as SocietePEC --- par organisme / par société de prise en charge

                    , TypReg, client.Plafond
                    ,Medecin.nommed as MedecinTraitant  -- Par médecin traitant
                    , MedSpec, NomPac, AdrPac, TelPac, NomEng, CINEng, TelEng
                    , client.Observ, DatArr, HeuArr, DatDep, HeuDep, NumFac, DatFac
                    ,TypSortie.dessortie as TypeSortie -- par type de sortie
                    , MntCli as TotFactureHT -- HT FACTURE
                    , MntHo as TotalHonoraire -- TOTAL HONORAIRE MEDECIN
                    , MntCliPEC as TotPECHT -- HT CLINIQUE PARTIE PRISE EN CHARGE
                    , MntHoPEC as TotHonorairePEC -- HONORAIRE  PARTIE PRISE EN CHARGE
                    , client.TVAPEC -- TVA  PARTIE PRISE EN CHARGE
                    , MntTva as TotTVAFacture -- TOTAL TVA
                    , MntRem as TotRemise -- REMISE FACTURE
                    ,MntCli+MntHo+MntTva as TotFactureTTC -- TTC Facture
                    , Payer, datepay, ModReg
                    ,TypArr.DesTyp as TypeArrive -- par type d'arrivée
                    , Avance, NumInt, MedRad, MedChir
                    ,isnull(T1.nommed,'') as MedecinCorrespondant  -- par médecin correspondant
                    , EtabOrg
                    , Kiné, Ergo, Ortho, client.Timbre, Avoir, RefPEC, DatePEC, NumVir, MntRecu, client.TimbrePEC, UserCre, UserFac, RetenuPEC
                    , Eta_Recouv, DatCIN, DatCinEng, Datf_Plaf, Profession, CodCat, TypPCE, Matricule, typconv, pere, RemHO
                    , MntAvoir, DatAvoir, NumPec, Identifiant, DatDConv, DatFConv, DateEnt, Lieu, client.Resident, Autoris, DatAutoris
                    , HeuAutoris, PER_PEC, Rem_autoris, User_autoris, CodBurReg, AnPriseCh, NumOrdPriseCh, NumBordCNAM, Duplication
                    , OrgEmpl, Archive, DatRecep, Classer, NumCarte, Memo, P_Plafond, Cha_Bloc, num_rdv, sex, audit, Date_audit
                    , Heure_audit, User_audit, DatBordCnam, Copie_Pas, client.usermodif, Pr_Plafond, Libelle_Avance, MatPers, CodPat
                    , client.HOPATPEC, Libelle_Appurement, Etat_civil, Bord_PER_PEC, has_piece_joint, Epous, EpousVeuve, codMedRecommande
                    , Nature_Heberg, delegation, motif_urgence, CliniqueCorr, CodeCliniqueCorr, patientAdmisPMA, Port_Taxation
                    , Gouvernorat, CodePostale, Tel2, AdresseLocale, LIEN_PER_PEC, NATURE_PER_PEC, Code_Reservation, MedUrg
                    , PersAContacter, TElPersAContacter, AdrPersAContacter, client.Intervention_Bloc, photo, avoirPhoto, num_sous_soc
                    , date_DebCarte, date_FinCarte, codAdherent, Pays, Num_Bordereau, NumConv, UserRecep, NomCliAr, PrenomAr
                    , Prenom2Ar, EpousVeuveAr, EpousAr, pereAr, userAutorisModifAv, NumCheque, client.email, Accompagnant2, NomPac2
                    , AdrPac2, TelPac2, LienPac2, ANES, Oeuil, EXCEPTION, LienPac, PEC_Non_Parvenue, Date_Autois_per, Heure_Autois_per
                    , Code_Region, TypAjusRadio, Code_Prest_Cnam, date_env, Num_Carte, Accompagnant, VIP, Code_Med_Charge
                    , Code_Emp_Charge, VLD_EXCEPTION, ancienID, DatSortiePrevue, lienPersAContacter, numDemandeBloc, numSoc2
                    , Date_Dep_Prevu, Heure_Dep_Prevu, Autorise_Per, Recette, code_TypePrest, Sequence_OPD, UserInstance
                    , num_cabinet, ModeConsultation, TypAjusPayant, TypAjusOrganisme, Nbre_seanceReeducation, Prix_unitaire
                    , MntPatient_AlaCharge, Vld_Contentieux, Eta_Recouv_Patient, NumBord_Transf_Cont, Etat_Facture, A_recep_par
                    , NumBord_Transf_Cont_Pat, ImprimeBS, plafond_PER_PEC, CoursDollar, CoursEuro, verseEsp, ObservationNutrition
                    , CodePrestation, Date_Acte, Date_Dece, Heure_Dece, Medecin_Dece, service_Dece, NumDevis, Renseignement
                    , Num_CNAM_Recouv, client.date_depot, Vld_Contentieux_patient, Etat_Cont_Patient, Etat_Cont_PEC, Cont_recep_Patient
                    , Cont_recep_PEC, client.NomArb, PrenomArb, client.Per_PEC_Personnel, client.Nature_Per_PEC_Personnel, client.Numadmission
                    , client.Comute, client.MedTrait2, client.autorisConsultDMIcentral, client.CINPac, client.DocManquant
                    , newIdent, client.NumSocMutuelle,
                    (select Valeur from param where code='UNITEMONAITAIRE') as Devise
                    from client 
                    left outer join Medecin on Client.MedTrait=Medecin.CodMed
                    left outer join  medecin T1 on client.MedCorr=T1.CodMed
                    inner join chambre on Client.NumCha=Chambre.NumCha
                    inner join motif on Client.TypAdm=Motif.Cod
                    inner join Nationnalite on client.nation=Nationnalite.codnat
                    inner join natadm on client.natadm=natadm.cod
                    left outer join societe on client.numsoc=societe.numsoc
                    left outer join TypSortie on client.TypSortie=TypSortie.CodSortie
                    inner join TypArr on client.TypArr=TypArr.codtyp
                    inner join Services on Chambre.NumSer=Services.Num_Service
                )
                """
                # Combiner la CTE avec la requête initiale
                sql_query_extracted = view_definition + "\n" + sql_query_extracted
                logger.info("La définition de VPatientAI a été ajoutée à la requête.")

            st.session_state.conversations[current_convo]["last_sql_query"] = sql_query_extracted
            try:
                sql_response_df = pd.read_sql_query(sql_query_extracted, engine)
                logger.info(f"Réponse SQL: {sql_response_df}")
            except Exception as e:
                logger.exception(f"Erreur lors de l'exécution de la requête SQL: {e}")
                return {"response": "Erreur lors de l'exécution de la requête SQL.", "visualization": None, "table": None}
            if sql_response_df.empty:
                logger.warning("La requête SQL n'a retourné aucun résultat.")
                ai_text_response = f"La requête n'a retourné aucun résultat. (Devise utilisée : {currency})"
                return {"response": ai_text_response, "visualization": None, "table": None}
            total_rows = len(sql_response_df)
            if total_rows > 100:
                logger.info(f"Result set too large ({total_rows} rows). Generating a downloadable file.")
                csv_buffer = io.StringIO()
                sql_response_df.to_csv(csv_buffer, index=False)
                csv_data = csv_buffer.getvalue()
                filename = f"query_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                # Include the downloadable file in the return value
                downloadable_file = (filename, csv_data)
                ai_text_response = f"Le résultat contient {total_rows} lignes, ce qui est trop volumineux pour être affiché ici. Un fichier CSV a été généré et est prêt pour le téléchargement. (Devise utilisée : {currency})"
                return {"response": ai_text_response, "visualization": None, "table": None, "downloadable_file": downloadable_file}
            else:
                MAX_SQL_ROWS = total_rows
                truncated_sql_response_df = sql_response_df.head(MAX_SQL_ROWS)
                sql_response_str = str(truncated_sql_response_df.to_dict(orient="records"))
                list_all_nationalities = "nationalite" in sql_query_extracted.lower()
                response_prompt = f"""
                    Vous êtes un analyste de données dans une clinique. En vous basant sur la question de l'utilisateur et les résultats de la requête SQL, fournissez une réponse pertinente en français.
                    - **Ne mentionnez pas la requête SQL ni les données brutes de la réponse SQL dans votre réponse.**
                    - N'incluez aucune information inutile.
                    - Concentrez-vous uniquement sur les informations pertinentes pour l'utilisateur.
                    {"- Énumérez toutes les nationalités si cela est pertinent pour la question." if list_all_nationalities else ""}

                    Question de l'utilisateur: {user_query}
                    Résultats de la requête SQL: {sql_response_str}

                    Écrivez une réponse claire et complète basée sur les informations ci-dessus sans mentionner la requête SQL ni les données brutes.
                """
                prompt_tokens = num_tokens_from_string(response_prompt)
                max_response_tokens = 300
                total_tokens_needed = int((prompt_tokens + max_response_tokens) * 0.9)
                logger.info(f"Tokens estimés nécessaires: {total_tokens_needed}")
                MAX_TOKENS_PER_REQUEST = 5000
                if total_tokens_needed > MAX_TOKENS_PER_REQUEST:
                    logger.warning("Le prompt est trop long, il va être ajusté.")
                    if total_rows > 1:
                        MAX_SQL_ROWS = 1
                        truncated_sql_response_df = sql_response_df.head(MAX_SQL_ROWS)
                        sql_response_str = str(truncated_sql_response_df.to_dict(orient="records"))
                        list_all_nationalities = "nationalite" in sql_query_extracted.lower()
                        response_prompt = f"""
                            Vous êtes un analyste de données dans une clinique. En vous basant sur la question de l'utilisateur et un échantillon des résultats de la requête SQL, fournissez une réponse pertinente en français.
                            - **Ne mentionnez pas la requête SQL ni les données brutes de la réponse SQL dans votre réponse.**
                            - N'incluez aucune information inutile.
                            - Concentrez-vous uniquement sur les informations pertinentes pour l'utilisateur.
                            - Notez que seule une partie des résultats est affichée.
                            {"- Énumérez toutes les nationalités si cela est pertinent pour la question." if list_all_nationalities else ""}

                            Question de l'utilisateur: {user_query}
                            Résultats de la requête SQL (échantillon): {sql_response_str}

                            Écrivez une réponse claire et complète basée sur les informations ci-dessus sans mentionner la requête SQL ni les données brutes.
                        """
                        prompt_tokens = num_tokens_from_string(response_prompt)
                        total_tokens_needed = int((prompt_tokens + max_response_tokens) * 0.9)
                if total_tokens_needed > MAX_TOKENS_PER_REQUEST:
                    logger.warning("Le prompt ajusté est toujours trop long. Suppression des résultats SQL du prompt.")
                    response_prompt = f"""
                        Vous êtes un analyste de données dans une clinique. En vous basant sur la question de l'utilisateur, fournissez une réponse pertinente en français.
                        - **Ne mentionnez pas la requête SQL ni les données brutes de la réponse SQL dans votre réponse.**
                        - N'incluez aucune information inutile.
                        - Concentrez-vous uniquement sur les informations pertinentes pour l'utilisateur.
                        {"- Énumérez toutes les nationalités si cela est pertinent pour la question." if list_all_nationalities else ""}

                        Question de l'utilisateur: {user_query}

                        Écrivez une réponse claire et complète basée sur les informations ci-dessus.
                    """
                    prompt_tokens = num_tokens_from_string(response_prompt)
                    total_tokens_needed = int((prompt_tokens + max_response_tokens) * 0.9)
                    if total_tokens_needed > MAX_TOKENS_PER_REQUEST:
                        logger.error("Impossible de réduire le prompt en dessous de la limite de tokens.")
                        return {"response": "Désolé, la réponse est trop volumineuse pour être traitée.", "visualization": None, "table": None}
                @throttle(token_bucket, total_tokens_needed)
                def call_groq_ai(prompt):
                    return groq_ai.invoke(prompt)
                try:
                    ai_response = call_groq_ai(response_prompt)
                    logger.info(f"Réponse IA: {ai_response}")
                except Exception as e:
                    error_message = str(e).lower()
                    if "rate limit" in error_message or "limite de taux" in error_message:
                        wait_time = extract_wait_time(str(e))
                        wait_until = datetime.now() + timedelta(seconds=wait_time)
                        st.session_state.wait_until = wait_until
                        rate_limit_message = f"Désolé, la limite de taux a été atteinte. Veuillez réessayer dans {int(wait_time // 60)} minutes et {int(wait_time % 60)} secondes."
                        logger.warning(f"Rate limit exceeded. Wait for {wait_time} seconds.")
                        return {"response": rate_limit_message, "visualization": None, "table": None}
                    else:
                        logger.exception(f"Erreur lors de la génération de la réponse: {e}")
                        return {"response": "Erreur lors de la génération de la réponse.", "visualization": None, "table": None}
                ai_response_content = ""
                if hasattr(ai_response, "content"):
                    ai_response_content = ai_response.content.strip()
                elif isinstance(ai_response, dict):
                    ai_response_content = ai_response.get("content", "").strip()
                else:
                    content_match = re.search(r"content='(.*?)'", str(ai_response))
                    ai_response_content = content_match.group(1).strip() if content_match else str(ai_response).strip()
                ai_response_content = remove_currency_symbols(ai_response_content)
                if ai_response_content:
                    ai_response_content += f" (Devise utilisée : {currency})"
                fig = None
                table = None
                if graph_required and chart_type:
                    try:
                        fig = generate_visualization(sql_response_df, chart_type, currency_symbol)
                        if fig is None:
                            logger.info("La visualisation n'a pas pu être générée.")
                            ai_response_content += "\n\n**Note**: La visualisation demandée n'a pas pu être générée."
                    except Exception as e:
                        logger.exception(f"Erreur lors de la génération de la visualisation: {e}")
                        ai_response_content += "\n\n**Erreur**: Une erreur s'est produite lors de la génération de la visualisation."
                        fig = None
                if len(sql_response_df) <= 100:
                    table = sql_response_df
                return {"response": ai_response_content, "visualization": fig, "table": table}
    except Exception as e:
        # Handle exceptions not caught by internal try-except blocks
        logger.exception(f"Unexpected error in get_response: {e}")
        return {"response": "Une erreur inattendue s'est produite. Veuillez réessayer plus tard.", "visualization": None, "table": None}

# Initialiser le Token Bucket globalement dans st.session_state
if "token_bucket" not in st.session_state:
    st.session_state.token_bucket = TokenBucket(tokens_per_minute=30000)  # Ajusté pour respecter la limite TPM de Groq AI

# Initializing conversations in st.session_state
if "conversations" not in st.session_state:
    st.session_state.conversations = {}

# Initializing the current conversation ID
if "current_conversation" not in st.session_state:
    initial_convo_id = "Conversation 1"
    st.session_state.conversations[initial_convo_id] = {
        "chat_history": [
            AIMessage(content="Bonjour ! Je suis un assistant SQL. Posez-moi vos questions sur la base de données.")
        ],
        "figures": [{'visualization': None, 'table': None}],
        "last_sql_query": None
    }
    st.session_state.current_conversation = initial_convo_id

 

# Sidebar pour les paramètres de connexion à la base de données et gestion des conversations
with st.sidebar:
    st.subheader("Paramètres de Connexion")
    st.write("Entrez les détails de connexion à la base de données SQL Server exposée en ligne.")
    
    host = st.text_input("Hôte (ex: xxxx.ngrok.io)", key="Host")
    port = st.text_input("Port (ex: 1433 ou celui fourni par ngrok)", key="Port")
    user = st.text_input("Utilisateur", value="sa", key="User")
    password = st.text_input("Mot de passe", type="password", value="123", key="Password")
    database = st.text_input("Base de données", value="GClinique", key="Database")

    if st.button("Se Connecter"):
        with st.spinner("Connexion à la base de données..."):
            # Construct the connection string with separate host and port
            try:
                # Make sure port is an integer
                port_int = int(port)
            except ValueError:
                st.error("Le port doit être un nombre entier. Veuillez corriger et réessayer.")
                st.stop()

            # Construct the SQLAlchemy connection URL
            connection_string = (
                f"mssql+pyodbc://{user}:{password}@{host}:{port_int}/{database}"
                f"?driver=ODBC+Driver+17+for+SQL+Server"
            )

            # Attempt to initialize the database
            db, engine = init_database_cached(host, user, password, database, port_int)

            if db and engine:
                st.session_state.db = db
                st.session_state.engine = engine
                st.success("Connecté à la base de données !")
                logger.info("Utilisateur connecté à la base de données.")
                # Extraire la devise globale et la stocker dans la session
                currency = get_global_currency(engine)
                st.session_state.currency = currency
                logger.info(f"Devise stockée dans la session: {currency}")

    st.markdown("---")
    st.subheader("Gestion des Conversations")
    if st.session_state.conversations:
        selected_convo = st.selectbox(
            "Sélectionnez une conversation:",
            options=list(st.session_state.conversations.keys()),
            index=list(st.session_state.conversations.keys()).index(st.session_state.current_conversation)
        )
        st.session_state.current_conversation = selected_convo
        logger.info(f"Conversation sélectionnée: {selected_convo}")
    if st.button("Nouvelle Conversation"):
        existing_ids = list(st.session_state.conversations.keys())
        new_id_num = len(existing_ids) + 1
        new_convo_id = f"Conversation {new_id_num}"
        st.session_state.conversations[new_convo_id] = {
            "chat_history": [
                AIMessage(content="Bonjour ! Je suis un assistant SQL. Posez-moi vos questions sur la base de données.")
            ],
            "figures": [{'visualization': None, 'table': None}],  # Corrected initialization
            "last_sql_query": None
        }
        st.session_state.current_conversation = new_convo_id
        st.success(f"{new_convo_id} créée et sélectionnée.")
        logger.info(f"{new_convo_id} créée et sélectionnée.")
# Récupérer la conversation courante
current_convo = st.session_state.current_conversation

# Afficher l'historique du chat avec les figures et les tables associées
for i, message in enumerate(st.session_state.conversations[current_convo]["chat_history"]):
    if isinstance(message, AIMessage):
        with st.chat_message("AI"):
            st.markdown(message.content)
            if i < len(st.session_state.conversations[current_convo]["figures"]):
                item = st.session_state.conversations[current_convo]["figures"][i]
                # Check and display the downloadable file
                if item.get("downloadable_file") is not None:
                    filename, file_content = item["downloadable_file"]
                    st.download_button(
                        label="Télécharger les résultats",
                        data=file_content,
                        file_name=filename,
                        mime="text/csv",
                        key=f"{current_convo}_download_{i}",
                    )
                if item.get("visualization") is not None:
                    st.plotly_chart(
                        item["visualization"],
                        use_container_width=True,
                        key=f"{current_convo}_plot_{i}"
                    )
                if item.get("table") is not None:
                    st.dataframe(
                        item["table"],
                        use_container_width=True,
                        key=f"{current_convo}_table_{i}"
                    )
    elif isinstance(message, HumanMessage):
        with st.chat_message("Human"):
            st.markdown(message.content)

# Vérifier si le rate limit est actif
rate_limit_active = False
wait_until = st.session_state.get("wait_until", None)
if wait_until:
    if datetime.now() < wait_until:
        rate_limit_active = True
        remaining_time = wait_until - datetime.now()
        minutes, seconds = divmod(int(remaining_time.total_seconds()), 60)
        wait_message = f"Limite de taux atteinte. Veuillez réessayer dans {minutes} minutes et {seconds} secondes."
        if not any(message.content == wait_message for message in st.session_state.conversations[current_convo]["chat_history"] if isinstance(message, AIMessage)):
            st.session_state.conversations[current_convo]["chat_history"].append(AIMessage(content=wait_message))
            st.session_state.conversations[current_convo]["figures"].append(None)
            logger.info("Limite de taux atteinte, message informatif ajouté à la conversation.")
    else:
        st.session_state.wait_until = None
        logger.info("Période de wait terminée.")

# Entrée utilisateur pour le chat
if not rate_limit_active:
    user_query = st.chat_input("Tapez votre message ici...")
else:
    st.chat_input("Limite de taux active. Veuillez réessayer plus tard.")
    user_query = None

if user_query is not None and user_query.strip() != "":
    # Ajouter le message de l'utilisateur à l'historique du chat de la conversation courante
    st.session_state.conversations[current_convo]["chat_history"].append(HumanMessage(content=user_query))
    # Ajouter un dict vide pour 'figures' correspondant au message utilisateur
    st.session_state.conversations[current_convo]["figures"].append({'visualization': None, 'table': None})
    logger.info(f"Question reçue de l'utilisateur: {user_query}")

    # Afficher le message de l'utilisateur
    with st.chat_message("Human"):
        st.markdown(user_query)

    # Vérifier si la base de données est connectée
    if "db" in st.session_state and "engine" in st.session_state and st.session_state.db and st.session_state.engine:
        db = st.session_state.db
        engine = st.session_state.engine
        # Initialiser Groq AI
        groq_ai = init_groq_ai()
        if not groq_ai:
            error_message = "Erreur lors de l'initialisation de Groq AI."
            st.error(error_message)
            logger.error(error_message)
        else:
            # Générer la réponse de l'IA et la visualisation
            response_data = get_response(
            user_query,
            db,
            engine,
            st.session_state.conversations[current_convo]["chat_history"],
            groq_ai,
            st.session_state.token_bucket,
        )
        ai_response = response_data.get("response")
        fig = response_data.get("visualization")
        table = response_data.get("table")
        downloadable_file = response_data.get("downloadable_file", None)  # Get the downloadable file

        if ai_response:
            try:
                # Add the AI response to the conversation history
                st.session_state.conversations[current_convo]["chat_history"].append(AIMessage(content=ai_response))
                # Include the downloadable file in the figures dictionary
                st.session_state.conversations[current_convo]["figures"].append({
                    "visualization": fig,
                    "table": table,
                    "downloadable_file": downloadable_file  # Store the downloadable file
                })
                # Display the AI response
                with st.chat_message("AI"):
                    st.markdown(ai_response)
                    logger.debug("Réponse de l'IA affichée dans l'interface utilisateur.")
                    # The downloadable file is now stored in the conversation history
                    # No need to retrieve it from st.session_state
                    if downloadable_file:
                        filename, file_content = downloadable_file
                        st.download_button(
                            label="Télécharger les résultats",
                            data=file_content,
                            file_name=filename,
                            mime="text/csv",
                            key=f"{current_convo}_download_{len(st.session_state.conversations[current_convo]['chat_history'])-1}",
                        )
                        logger.debug(f"Bouton de téléchargement créé pour le fichier: {filename}")
                    # Display the figure or table if they exist
                    if fig:
                        st.plotly_chart(
                            fig,
                            use_container_width=True,
                            key=f"{current_convo}_plot_{len(st.session_state.conversations[current_convo]['chat_history'])-1}",
                        )
                        logger.debug("Figure affichée dans l'interface utilisateur.")
                    if table is not None:
                        st.dataframe(
                            table,
                            use_container_width=True,
                            key=f"{current_convo}_table_{len(st.session_state.conversations[current_convo]['chat_history'])-1}"
                        )
                        logger.debug("Table affichée dans l'interface utilisateur.")
                # Log the AI response
                logger.info(f"Réponse de l'IA: {ai_response}")
            except Exception as e:
                logger.exception(f"Erreur lors de la gestion de la réponse de l'IA: {e}")
                st.error("Une erreur s'est produite lors de l'affichage de la réponse de l'IA.")

    else:
        # Si la base de données n'est pas connectée
        response_message = "Veuillez vous connecter à la base de données depuis la barre latérale avant de poser des questions."
        with st.chat_message("AI"):
            st.markdown(response_message)
        st.session_state.conversations[current_convo]["chat_history"].append(AIMessage(content=response_message))
        st.session_state.conversations[current_convo]["figures"].append({'visualization': None, 'table': None})
        logger.warning("Utilisateur a tenté de poser une question sans être connecté à la base de données.")


