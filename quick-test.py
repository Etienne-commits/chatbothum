"""Quick test - sends one question and shows the response"""
import os
from pathlib import Path
from anthropic import Anthropic
from dotenv import load_dotenv
import yaml

load_dotenv()

# Load skill
skill_file = Path("output/skills/chat-pulsar-humbert-dermatologie.yaml")
with open(skill_file, "r", encoding="utf-8") as f:
    skill = yaml.safe_load(f)

# Load persona
persona_file = Path("output/personas/humbert.yaml")
with open(persona_file, "r", encoding="utf-8") as f:
    persona = yaml.safe_load(f)

# Build system prompt
system_prompt = f"""
{skill.get('system_instructions', '')}

PERSONA:
- Nom: {persona['identity']['full_name']}
- Titre: {persona['identity']['title']}
- Style: {persona['communication_style']['tone']}

LIMITES: Tu donnes des informations generales et pedagogiques. Tu ne fais JAMAIS de diagnostic ni de prescription.
"""

# Test question
test_question = "Qu'est-ce que le psoriasis et pourquoi ca demange?"

print("="*60)
print("TEST CHATBOT - Professeur Humbert (Dermatologie)")
print("="*60)
print(f"\nQuestion: {test_question}")
print("\n" + "-"*60)
print("Reponse du Pr Humbert:\n")

# Call API
api_key = os.getenv("ANTHROPIC_API_KEY")
if not api_key or api_key == "xxx":
    print("[ERREUR] Mettez votre vraie cle API dans .env")
    print("ANTHROPIC_API_KEY=sk-ant-api03-VOTRE-CLE-ICI")
    exit(1)

client = Anthropic(api_key=api_key)

response = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1024,
    system=system_prompt,
    messages=[{"role": "user", "content": test_question}]
)

print(response.content[0].text)
print("\n" + "="*60)
print("TEST OK!")
