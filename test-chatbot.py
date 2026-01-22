"""
PULSAR Chatbot Test - Professeur Humbert
=========================================
Script de test pour les skills via l'API Anthropic Claude.

Usage:
    python test-chatbot.py
    
Configuration:
    - Créer un fichier .env avec ANTHROPIC_API_KEY=sk-ant-...
    - Ou exporter la variable d'environnement
"""

import os
import yaml
from pathlib import Path
from anthropic import Anthropic
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# =============================================================================
# CONFIGURATION
# =============================================================================

SKILLS_DIR = Path("output/skills")
PERSONA_FILE = Path("output/personas/humbert.yaml")
GUARDRAILS_FILE = Path("output/guardrails-humbert.yaml")

# Anthropic model
MODEL = "claude-sonnet-4-20250514"  # ou "claude-3-opus-20240229" pour plus de qualité

# =============================================================================
# CHARGEMENT DES FICHIERS
# =============================================================================

def load_yaml(file_path: Path) -> dict:
    """Charge un fichier YAML."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def load_all_skills() -> dict:
    """Charge tous les skills disponibles."""
    skills = {}
    for skill_file in SKILLS_DIR.glob("*.yaml"):
        skill_data = load_yaml(skill_file)
        skill_name = skill_data.get('name', skill_file.stem)
        skills[skill_name] = skill_data
    return skills

def load_persona() -> dict:
    """Charge le persona."""
    return load_yaml(PERSONA_FILE)

def load_guardrails() -> dict:
    """Charge les guardrails."""
    return load_yaml(GUARDRAILS_FILE)

# =============================================================================
# CONSTRUCTION DU SYSTEM PROMPT
# =============================================================================

def build_system_prompt(skill_name: str, skills: dict, persona: dict, guardrails: dict) -> str:
    """Construit le system prompt complet à partir du skill, persona et guardrails."""
    
    skill = skills.get(skill_name)
    if not skill:
        raise ValueError(f"Skill '{skill_name}' not found. Available: {list(skills.keys())}")
    
    # Extraire les instructions du skill
    skill_instructions = skill.get('system_instructions', '')
    
    # Extraire les infos du persona
    persona_identity = persona.get('identity', {})
    persona_style = persona.get('communication_style', {})
    persona_expressions = persona.get('signature_expressions', {})
    
    # Extraire les guardrails critiques
    charter = guardrails.get('editorial_charter', {})
    forbidden = charter.get('strictly_forbidden', {})
    mandatory = charter.get('mandatory_behaviors', {})
    
    # Construire le prompt système complet
    system_prompt = f"""# IDENTITÉ

Tu es le **{persona_identity.get('title', '')} {persona_identity.get('full_name', '')}**, 
{persona_identity.get('profession', '')} au {persona_identity.get('institution', '')}, 
avec {persona_identity.get('experience', '')} d'expérience.

# STYLE DE COMMUNICATION

Ton: {persona_style.get('tone', {}).get('primary', '')} et {persona_style.get('tone', {}).get('secondary', '')}
- Tu utilises des anecdotes cliniques pour illustrer
- Tu valides systématiquement la souffrance du patient
- Tu vulgarises les termes médicaux complexes

Expressions favorites:
- "Rendez-vous compte"
- "Pensez parasites"
- "Ce n'est pas dans votre tête"
- "Le vent sur les braises"

# INSTRUCTIONS SPÉCIFIQUES AU SKILL

{skill_instructions}

# RÈGLES DE SÉCURITÉ STRICTES (GUARDRAILS)

## INTERDICTIONS ABSOLUES
Tu ne dois JAMAIS :
- Donner des recommandations personnalisées ("Dans votre cas, prenez...")
- Utiliser des formulations prescriptives ("Vous devez prendre...", "Prenez X mg de...")
- Poser un diagnostic affirmatif ("Vous avez [maladie]")
- Aider à prendre une décision médicale personnelle
- Donner des posologies ou doses de médicaments

## OBLIGATIONS STRICTES
Tu dois TOUJOURS :
- Utiliser des formulations générales ("De manière générale...", "On observe souvent...")
- Utiliser des formulations conditionnelles ("Il pourrait s'agir de...", "Cela pourrait évoquer...")
- Rappeler tes limites ("Seul un examen clinique permettrait de confirmer")
- Orienter vers des professionnels humains pour les décisions

## EN CAS D'URGENCE VITALE DÉTECTÉE
Si tu détectes des termes comme "douleur thoracique", "difficultés respiratoires", 
"pensées suicidaires", "idées noires", tu dois IMMÉDIATEMENT :
- Stopper ta réponse éducative
- Donner le message d'urgence : "Appelez le 15 (SAMU) ou le 3114 (prévention suicide)"

## POSTURE OBLIGATOIRE
Tu es :
- Pédagogique (expliquer, éduquer)
- Descriptif (ce qui est, pas ce qu'il faut faire)
- Humble (reconnaître tes limites)
- Non-affirmatif (jamais de certitudes sur des cas individuels)
- Non-normatif (jamais de "bonne décision")

# DISCLAIMER À RAPPELER SI PERTINENT

"Je partage des informations générales basées sur l'expérience médicale. 
Cela ne remplace pas une consultation avec examen clinique. 
Pour un diagnostic et un traitement adaptés, consultez votre médecin."
"""
    
    return system_prompt

# =============================================================================
# CLASSE CHATBOT
# =============================================================================

class PulsarChatbot:
    """Chatbot PULSAR utilisant les skills du Pr Humbert."""
    
    def __init__(self, api_key: str = None):
        """Initialise le chatbot."""
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not found. Set it in .env or environment.")
        
        self.client = Anthropic(api_key=self.api_key)
        self.skills = load_all_skills()
        self.persona = load_persona()
        self.guardrails = load_guardrails()
        self.conversation_history = []
        self.current_skill = None
        
        print(f"[OK] Loaded {len(self.skills)} skills:")
        for skill_name in self.skills:
            print(f"   - {skill_name}")
    
    def select_skill(self, skill_name: str):
        """Sélectionne un skill actif."""
        if skill_name not in self.skills:
            print(f"[ERROR] Skill '{skill_name}' not found.")
            print(f"Available skills: {list(self.skills.keys())}")
            return False
        
        self.current_skill = skill_name
        self.conversation_history = []  # Reset conversation
        print(f"[OK] Skill selected: {skill_name}")
        return True
    
    def chat(self, user_message: str) -> str:
        """Envoie un message et reçoit une réponse."""
        if not self.current_skill:
            return "[ERROR] No skill selected. Use select_skill() first."
        
        # Ajouter le message utilisateur à l'historique
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })
        
        # Construire le system prompt
        system_prompt = build_system_prompt(
            self.current_skill, 
            self.skills, 
            self.persona, 
            self.guardrails
        )
        
        # Appeler l'API Anthropic
        try:
            response = self.client.messages.create(
                model=MODEL,
                max_tokens=2048,
                system=system_prompt,
                messages=self.conversation_history
            )
            
            assistant_message = response.content[0].text
            
            # Ajouter la réponse à l'historique
            self.conversation_history.append({
                "role": "assistant",
                "content": assistant_message
            })
            
            return assistant_message
            
        except Exception as e:
            return f"[API ERROR] {str(e)}"
    
    def reset(self):
        """Réinitialise la conversation."""
        self.conversation_history = []
        print("[OK] Conversation reset.")

# =============================================================================
# INTERFACE CLI
# =============================================================================

def print_menu(skills: list):
    """Affiche le menu des skills."""
    print("\n" + "="*60)
    print("PULSAR CHATBOT - Professeur Humbert")
    print("="*60)
    print("\nSkills disponibles:")
    for i, skill in enumerate(skills, 1):
        short_name = skill.replace("chat-pulsar-humbert-", "")
        print(f"  {i}. {short_name}")
    print("\nCommandes:")
    print("  /skill <num>  - Changer de skill")
    print("  /reset        - Réinitialiser la conversation")
    print("  /quit         - Quitter")
    print("="*60)

def main():
    """Point d'entrée principal."""
    
    # Vérifier la clé API
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("[ERROR] ANTHROPIC_API_KEY not found!")
        print("\nOptions:")
        print("1. Create a .env file with: ANTHROPIC_API_KEY=sk-ant-...")
        print("2. Or set environment variable:")
        print("   Windows: set ANTHROPIC_API_KEY=sk-ant-...")
        print("   Linux/Mac: export ANTHROPIC_API_KEY=sk-ant-...")
        
        # Demander la clé en input
        api_key = input("\nOr enter your API key now: ").strip()
        if not api_key:
            return
    
    # Initialiser le chatbot
    try:
        chatbot = PulsarChatbot(api_key)
    except Exception as e:
        print(f"[ERROR] Failed to initialize: {e}")
        return
    
    skills_list = list(chatbot.skills.keys())
    print_menu(skills_list)
    
    # Sélectionner le premier skill par défaut
    chatbot.select_skill(skills_list[0])
    
    # Boucle de conversation
    while True:
        try:
            user_input = input("\nVous: ").strip()
            
            if not user_input:
                continue
            
            # Commandes spéciales
            if user_input.startswith("/"):
                cmd = user_input.lower()
                
                if cmd == "/quit" or cmd == "/exit":
                    print("Au revoir!")
                    break
                
                elif cmd == "/reset":
                    chatbot.reset()
                    continue
                
                elif cmd.startswith("/skill"):
                    parts = cmd.split()
                    if len(parts) == 2:
                        try:
                            idx = int(parts[1]) - 1
                            if 0 <= idx < len(skills_list):
                                chatbot.select_skill(skills_list[idx])
                            else:
                                print(f"[ERROR] Invalid skill number. Use 1-{len(skills_list)}")
                        except ValueError:
                            print("[ERROR] Usage: /skill <number>")
                    else:
                        print_menu(skills_list)
                    continue
                
                elif cmd == "/help":
                    print_menu(skills_list)
                    continue
                
                else:
                    print("[ERROR] Unknown command. Type /help for commands.")
                    continue
            
            # Envoyer le message
            print("\nPr Humbert: ", end="", flush=True)
            response = chatbot.chat(user_input)
            print(response)
            
        except KeyboardInterrupt:
            print("\nAu revoir!")
            break

# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    main()
