# 🩺 PULSAR Chatbot - Pr Philippe Humbert

Chatbot médical incarnant le **Professeur Philippe Humbert**, dermatologue et interniste au CHU de Besançon.

## 🎯 Domaines d'expertise

| Skill | Description |
|-------|-------------|
| **Dermatologie** | Psoriasis, eczéma, acné, rosacée, lien peau-intestin |
| **Parasitologie** | Toxocarose, oxyures, gale, lien parasites-immunité |
| **Digestif** | Crohn, RCH, SIBO, microbiote, hyperperméabilité |
| **Intolérances** | Gluten, lait de vache, FODMAPs, sulfites |
| **Holistique** | Liens corps-esprit, carences, psychosomatique |

## 🚀 Installation

### 1. Cloner le repository

```bash
git clone https://github.com/VOTRE_USERNAME/chatbothum.git
cd chatbothum
```

### 2. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 3. Configurer la clé API

```bash
cp .env.example .env
# Éditer .env et ajouter votre clé API Anthropic
```

### 4. Lancer le chatbot

```bash
python chat-ui.py
```

Le chatbot s'ouvre automatiquement dans votre navigateur sur `http://127.0.0.1:7860`

## 📁 Structure du projet

```
chatbothum/
├── chat-ui.py              # Application principale
├── requirements.txt        # Dépendances Python
├── .env.example           # Template pour la clé API
├── TEST-QUESTIONS.md      # Questions de test par skill
└── skills/
    ├── humbert-persona/   # Personnalité du Pr Humbert
    ├── humbert-dermatologie/
    ├── humbert-digestif/
    ├── humbert-parasites/
    ├── humbert-intolerances/
    ├── humbert-holistique/
    └── humbert-guardrails/
```

## 🧪 Tester le chatbot

Voir `TEST-QUESTIONS.md` pour des questions de test par skill.

**Exemples :**
- "Qu'est-ce que le psoriasis ?"
- "Pourquoi dites-vous 'pensez parasites toujours' ?"
- "C'est quoi l'intestin poreux ?"

## ⚙️ Configuration

Le skill approprié est **automatiquement détecté** selon la question posée.

## 📝 Licence

Usage interne - Projet PULSAR
