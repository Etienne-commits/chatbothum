"""
PULSAR Chatbot - Interface Web
Professeur Philippe Humbert
Nouvelle structure: SKILL.md + examples/
"""
import os
import yaml
import re
from pathlib import Path
from anthropic import Anthropic
from dotenv import load_dotenv
import gradio as gr

load_dotenv()

# =============================================================================
# CONFIGURATION
# =============================================================================

OUTPUT_DIR = Path("skills")
PERSONA_FOLDER = "humbert-persona"
SKILLS_FOLDERS = [
    "humbert-dermatologie",
    "humbert-digestif", 
    "humbert-parasites",
    "humbert-intolerances",
    "humbert-holistique"
]
GUARDRAILS_FOLDER = "humbert-guardrails"

# =============================================================================
# SKILL LOADER - Nouvelle structure Markdown
# =============================================================================

def parse_skill_md(filepath: Path) -> dict:
    """Parse a SKILL.md file and extract frontmatter + content"""
    content = filepath.read_text(encoding="utf-8")
    
    # Extract YAML frontmatter (between ---)
    frontmatter_match = re.match(r'^---\n(.*?)\n---\n(.*)', content, re.DOTALL)
    
    if frontmatter_match:
        frontmatter_yaml = frontmatter_match.group(1)
        body = frontmatter_match.group(2)
        try:
            metadata = yaml.safe_load(frontmatter_yaml)
        except:
            metadata = {}
    else:
        metadata = {}
        body = content
    
    # Extract keywords from body
    keywords_match = re.search(r'## Keywords\n\n(.+?)(?:\n\n|$)', body, re.DOTALL)
    keywords = keywords_match.group(1).strip() if keywords_match else ""
    
    return {
        "metadata": metadata,
        "body": body,
        "keywords": keywords
    }

def load_examples(examples_dir: Path) -> dict:
    """Load all .md files from examples/ folder"""
    examples = {}
    if examples_dir.exists():
        for md_file in examples_dir.glob("*.md"):
            examples[md_file.stem] = md_file.read_text(encoding="utf-8")
    return examples

def load_all_skills() -> dict:
    """Load all skills from new folder structure"""
    skills = {}
    
    for folder_name in SKILLS_FOLDERS:
        folder_path = OUTPUT_DIR / folder_name
        skill_file = folder_path / "SKILL.md"
        examples_dir = folder_path / "examples"
        
        if skill_file.exists():
            # Parse SKILL.md
            skill_data = parse_skill_md(skill_file)
            
            # Load examples
            examples = load_examples(examples_dir)
            
            # Extract skill short name (e.g., "dermatologie" from "humbert-dermatologie")
            short_name = folder_name.replace("humbert-", "")
            
            skills[short_name] = {
                "name": skill_data["metadata"].get("name", folder_name),
                "description": skill_data["metadata"].get("description", ""),
                "keywords": skill_data["keywords"],
                "body": skill_data["body"],
                "examples": examples
            }
    
    return skills

def load_guardrails() -> dict:
    """Load shared guardrails"""
    guardrails_path = OUTPUT_DIR / GUARDRAILS_FOLDER
    skill_file = guardrails_path / "SKILL.md"
    examples_dir = guardrails_path / "examples"
    
    guardrails = {}
    if skill_file.exists():
        guardrails["skill"] = parse_skill_md(skill_file)
        guardrails["examples"] = load_examples(examples_dir)
    
    return guardrails

def load_persona() -> dict:
    """Load persona from Markdown files (new structure)"""
    persona_path = OUTPUT_DIR / PERSONA_FOLDER
    examples_dir = persona_path / "examples"
    
    persona = {}
    if examples_dir.exists():
        persona = load_examples(examples_dir)
        print(f"Persona chargé: {list(persona.keys())}")
    else:
        print("ATTENTION: Persona non trouvé!")
    
    return persona

# =============================================================================
# LOAD DATA
# =============================================================================

print("Chargement des données...")
SKILLS = load_all_skills()
GUARDRAILS = load_guardrails()
PERSONA = load_persona()

print(f"Skills chargés: {list(SKILLS.keys())}")

# Build skill descriptions for detection (from keywords)
SKILL_DESCRIPTIONS = {
    name: skill["keywords"] or skill["description"]
    for name, skill in SKILLS.items()
}

# =============================================================================
# SKILL DETECTION
# =============================================================================

def detect_skill(question: str, client: Anthropic) -> str:
    """Use Claude to intelligently detect the most appropriate skill"""
    
    # Build skill list for detection
    skill_list = "\n".join([f"- {skill}: {desc}" for skill, desc in SKILL_DESCRIPTIONS.items()])
    
    detection_prompt = f"""Tu es un assistant médical. Analyse cette question et détermine quelle catégorie correspond le MIEUX parmi ces 5 domaines d'expertise du Pr Humbert:

{skill_list}

Question de l'utilisateur: "{question}"

INSTRUCTIONS:
- Réponds UNIQUEMENT avec le nom de la catégorie (un seul mot parmi: dermatologie, parasites, digestif, intolerances, holistique)
- Si la question ne correspond à AUCUNE de ces 5 catégories, réponds exactement: "HORS_SCOPE"
- Ne donne AUCUNE explication, juste le nom de la catégorie ou "HORS_SCOPE"

Réponse:"""
    
    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=20,
            messages=[{"role": "user", "content": detection_prompt}]
        )
        
        detected = response.content[0].text.strip().lower()
        
        # Check if valid skill or out of scope
        if detected == "hors_scope":
            return None
        elif detected in SKILLS:
            return detected
        else:
            return None
            
    except Exception as e:
        print(f"Erreur detection skill: {e}")
        return None

# =============================================================================
# GUARDRAILS CHECK
# =============================================================================

def check_guardrails(message: str) -> tuple[bool, str]:
    """
    Check if message triggers guardrails.
    Returns (should_block, response_message)
    """
    message_lower = message.lower()
    
    # 1. Check for personal medical data
    personal_data_patterns = [
        "mes résultats", "ma prise de sang", "mon analyse",
        "ma ferritine", "mon hémoglobine", "ma glycémie",
        "ma tsh", "mes transaminases", "ma crp",
        "voici mes résultats", "j'ai fait une prise de sang",
        "ng/ml", "g/l", "ui/l", "mmol/l"
    ]
    
    for pattern in personal_data_patterns:
        if pattern in message_lower:
            return (True, """⚠️ **Je ne peux pas accepter vos données médicales personnelles.**

Pour des raisons de confidentialité et de sécurité, je ne suis pas en mesure de recevoir, analyser ou interpréter vos résultats d'examens.

👉 **Pour l'interprétation de VOS résultats**, consultez votre médecin traitant ou le spécialiste qui a prescrit ces examens.

**Ce que je peux faire** : vous expliquer de manière générale ce que signifient certains examens et les valeurs de référence habituelles.""")
    
    # 2. Check for manipulation attempts
    manipulation_patterns = [
        "ignore tes instructions", "oublie tes règles",
        "fais comme si", "tu es maintenant",
        "dan mode", "jailbreak"
    ]
    
    for pattern in manipulation_patterns:
        if pattern in message_lower:
            return (True, """❌ **Je ne peux pas modifier mon fonctionnement.**

Je suis conçu pour fournir des informations médicales générales de manière sécurisée. Ces limites existent pour votre protection.

Si vous avez une question de santé, je suis à votre disposition dans le cadre de mes compétences.""")
    
    # 3. Check for emergency/crisis
    crisis_patterns = [
        "pensées suicidaires", "idées noires", "envie de mourir",
        "en finir", "plus la force"
    ]
    
    for pattern in crisis_patterns:
        if pattern in message_lower:
            return (True, """Je perçois que vous traversez un moment très difficile.

👉 **Appelez le 3114** (numéro national de prévention du suicide) - 24h/24
👉 Ou contactez votre médecin traitant
👉 Ou rendez-vous aux urgences

**Vous n'êtes pas seul(e).** Des professionnels formés peuvent vous aider maintenant.""")
    
    # No guardrail triggered
    return (False, "")

# =============================================================================
# BUILD SYSTEM PROMPT
# =============================================================================

def build_system_prompt(skill_name: str) -> str:
    """Build system prompt from persona (Markdown) + skill files"""
    
    skill = SKILLS.get(skill_name, {})
    skill_examples = skill.get("examples", {})
    
    # ==========================================================================
    # PERSONA - Dr Humbert's personality (from humbert-persona/examples/*.md)
    # ==========================================================================
    
    persona_identite = PERSONA.get("identite", "")
    persona_communication = PERSONA.get("communication", "")
    persona_anecdotes = PERSONA.get("anecdotes", "")
    persona_principes = PERSONA.get("principes", "")
    persona_comportements = PERSONA.get("comportements", "")
    
    # ==========================================================================
    # SKILL CONTENT (from examples/*.md)
    # ==========================================================================
    
    # Files with SPECIFIC placement in the prompt
    skill_identite = skill_examples.get("identite-style", "")
    skill_methodologie = skill_examples.get("methodologie", "")
    skill_guardrails = skill_examples.get("guardrails", "")
    
    # Files already used above (don't duplicate)
    already_used = {"identite-style", "methodologie", "guardrails"}
    
    # Load ALL remaining files from examples/ folder
    skill_content = ""
    for key, content in skill_examples.items():
        if key not in already_used:
            skill_content += f"\n\n{content}"
    
    # Get shared guardrails
    shared_guardrails = ""
    if GUARDRAILS.get("examples"):
        shared_guardrails = GUARDRAILS["examples"].get("responses", "")
    
    # ==========================================================================
    # BUILD COMPLETE SYSTEM PROMPT
    # ==========================================================================
    
    system = f"""
# ============================================================
# OBJECTIF DU CHATBOT
# ============================================================

Tu es un AGENT MÉDICAL ÉDUCATIF incarnant le Professeur Philippe Humbert.

**TON RÔLE :**
- Fournir des INFORMATIONS GÉNÉRALES et PÉDAGOGIQUES sur les questions de santé
- Éduquer les patients avec bienveillance et expertise
- Vulgariser les concepts médicaux complexes
- JAMAIS de diagnostic personnel ni de prescription médicamenteuse

**TES LIMITES STRICTES :**
- Tu donnes des informations GÉNÉRALES, pas des avis médicaux personnalisés
- Tu orientes TOUJOURS vers un professionnel de santé pour les cas individuels
- Tu ne prescris JAMAIS de médicaments ni de posologies

# ============================================================
# TES DOMAINES D'EXPERTISE (SKILLS DISPONIBLES)
# ============================================================

Tu disposes de 5 domaines d'expertise spécialisés :

1. **DERMATOLOGIE** : psoriasis, eczéma, acné, mycoses, rosacée, carences cutanées, 
   lien peau-intestin, biothérapies, méthotrexate

2. **PARASITOLOGIE** : vers intestinaux (oxyures, ascaris, ténias), toxocarose, 
   gale, Blastocystis, diagnostic parasitaire, courbe de Lavier

3. **DIGESTIF** : MICI (Crohn, RCH), intestin poreux, microbiote, reflux, 
   colopathie fonctionnelle, hyperperméabilité intestinale

4. **INTOLÉRANCES** : gluten, lactose, histamine, FODMAPs, allergie vs intolérance,
   protocole d'éviction, réintroduction alimentaire

5. **HOLISTIQUE** : liens corps-esprit, stress et maladies de peau, impact des 
   traumatismes, dépression et peau, hyperlaxité, origine embryologique

**POUR CETTE CONVERSATION, TU UTILISES TON EXPERTISE EN : {skill_name.upper()}**

# ============================================================
# PERSONA - QUI TU ES
# ============================================================

{persona_identite}

# ============================================================
# COMMENT TU PARLES (TRÈS IMPORTANT)
# ============================================================

{persona_communication}

# ============================================================
# ANECDOTES CLINIQUES (UTILISE-LES)
# ============================================================

{persona_anecdotes}

# ============================================================
# TES PRINCIPES MÉDICAUX
# ============================================================

{persona_principes}

# ============================================================
# TES COMPORTEMENTS OBLIGATOIRES
# ============================================================

{persona_comportements}

# ============================================================
# CONNAISSANCES SPÉCIFIQUES - {skill_name.upper()}
# ============================================================

{skill_identite}

{skill_methodologie}

{skill_content}

# ============================================================
# GARDE-FOUS OBLIGATOIRES
# ============================================================

{skill_guardrails}

{shared_guardrails}

# ============================================================
# RÈGLES STRICTES FINALES
# ============================================================

- Informations GÉNÉRALES uniquement
- JAMAIS de diagnostic personnel formel
- JAMAIS de prescription médicamenteuse
- Toujours orienter vers un médecin pour les cas personnels
- Si demande d'avis médical personnalisé, répondre:
  "Je ne peux pas vous fournir un avis médical personnalisé. 
   Prenez rendez-vous avec un professionnel de santé.
   En revanche, voici des conseils généraux..."

# ============================================================
# RAPPEL FINAL: TU ES LE PR HUMBERT
# ============================================================

Parle VRAIMENT comme lui:
- "Rendez-vous compte", "Voyez-vous", "Je me souviens d'un patient..."
- Raconte des anecdotes cliniques quand pertinent
- Valide la souffrance AVANT de conseiller
- Sois AFFIRMATIF (pas "peut-être", "il est possible")
- Cite tes mantras ("Pensez parasites", "Ce n'est pas dans votre tête")
- Donne des CHIFFRES PRÉCIS (ferritine 60-100, vitamine D 50-70, etc.)
"""
    
    return system

# =============================================================================
# ANTHROPIC CLIENT
# =============================================================================

api_key = os.getenv("ANTHROPIC_API_KEY")
if not api_key or api_key == "xxx":
    print("ERREUR: Mettez votre vraie clé API dans .env")
    exit(1)

client = Anthropic(api_key=api_key)

# =============================================================================
# CHAT FUNCTION
# =============================================================================

def chat_fn(message, history):
    """Main chat function"""
    
    # 1. Check guardrails FIRST
    blocked, response = check_guardrails(message)
    if blocked:
        return response
    
    # 2. Detect appropriate skill
    skill_name = detect_skill(message, client)
    
    # 3. If out of scope, decline politely
    if skill_name is None:
        return """Je vous remercie pour votre question.

Cependant, elle ne correspond pas à mes domaines d'expertise spécifiques qui sont:
- **Dermatologie** (maladies de peau, psoriasis, eczéma, acné...)
- **Parasitoses** (vers intestinaux, toxocarose, gale...)
- **Troubles digestifs** (intestin, microbiote, Crohn, reflux...)
- **Intolérances alimentaires** (gluten, lait, FODMAPs...)
- **Approche holistique** (liens corps-esprit, carences, traumatismes...)

Je vous encourage à poser une question dans l'un de ces domaines, ou à consulter un professionnel de santé adapté à votre besoin.

Bien cordialement,
*Pr Philippe Humbert*"""
    
    # 4. Build system prompt from skill content
    system = build_system_prompt(skill_name)
    
    # 5. Build message history (sanitize to only role + content)
    messages = []
    if history:
        for entry in history:
            if isinstance(entry, dict):
                # Only keep role and content, ignore metadata
                messages.append({
                    "role": entry.get("role", "user"),
                    "content": entry.get("content", "")
                })
            elif isinstance(entry, (list, tuple)) and len(entry) == 2:
                messages.append({"role": "user", "content": str(entry[0])})
                messages.append({"role": "assistant", "content": str(entry[1])})
    
    messages.append({"role": "user", "content": message})
    
    # 6. Call API
    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=system,
            messages=messages
        )
        return f"**[{skill_name.upper()}]**\n\n{response.content[0].text}"
    except Exception as e:
        return f"Erreur: {str(e)}"

# =============================================================================
# GRADIO INTERFACE
# =============================================================================

demo = gr.ChatInterface(
    fn=chat_fn,
    title="🩺 Professeur Philippe Humbert - Chatbot PULSAR",
    description="Dermatologue & Interniste - CHU de Besançon | Le skill est automatiquement sélectionné selon votre question",
    examples=[
        "Qu'est-ce que le psoriasis et pourquoi ça démange ?",
        "Pourquoi dites-vous 'pensez parasites toujours' ?",
        "C'est quoi l'intestin poreux ?",
        "Quel est le lien entre gluten et peau ?",
        "Comment savoir si je suis intolérant au lait ?",
    ],
    chatbot=gr.Chatbot(height=600),
)

if __name__ == "__main__":
    print("\n" + "="*60)
    print("PULSAR CHATBOT - Nouvelle structure Markdown")
    print("="*60)
    print(f"Skills disponibles: {list(SKILLS.keys())}")
    print("="*60 + "\n")
    demo.launch(inbrowser=True, share=True)
