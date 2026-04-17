#!/bin/bash
echo "============================================================"
echo "  ELISFA — Assistant Juridique CCN ALISFA v2.0"
echo "============================================================"
echo ""

# Vérifier Python
if ! command -v python3 &> /dev/null; then
    echo "ERREUR : Python 3 n'est pas installé."
    echo "Installez-le : https://www.python.org/downloads/"
    exit 1
fi

# Charger .env si présent
if [ -f .env ]; then
    echo "Chargement de la configuration .env..."
    export $(grep -v '^#' .env | xargs)
fi

# Installer les dépendances
echo "Installation des dépendances..."
pip3 install -r requirements.txt --quiet

echo ""
echo "============================================================"
echo "  Démarrage du chatbot..."
echo "  Chatbot    : http://localhost:${PORT:-5000}"
echo "  Admin      : http://localhost:${PORT:-5000}/admin"
echo "  API Health : http://localhost:${PORT:-5000}/api/health"
echo "  MCP Config : http://localhost:${PORT:-5000}/api/mcp/config"
echo "============================================================"
echo "  Modèle IA  : ${CLAUDE_MODEL:-claude-haiku-4-5-20251001}"
echo "  Pour arrêter : appuyez sur Ctrl+C"
echo "============================================================"
echo ""

python3 app.py
