#!/bin/bash

echo "🧹 Nettoyage des containers MCP-Create..."

# 1. Arrêter tous les containers mcp-create en cours
echo "📦 Arrêt des containers actifs..."
docker stop $(docker ps -q -f ancestor=mcp-create) 2>/dev/null || echo "Aucun container actif trouvé"

# 2. Supprimer tous les containers mcp-create arrêtés  
echo "🗑️  Suppression des containers arrêtés..."
docker rm $(docker ps -aq -f ancestor=mcp-create) 2>/dev/null || echo "Aucun container arrêté trouvé"

# 3. Arrêter les containers par nom spécifique (au cas où)
echo "🎯 Nettoyage par nom de container..."
docker stop mcp-create-session 2>/dev/null || true
docker rm mcp-create-session 2>/dev/null || true

# 4. Afficher les containers restants (pour debug)
echo "📋 Containers Docker restants:"
docker ps -a --filter ancestor=mcp-create

# 5. Afficher l'état du volume persistant
echo "💾 État du volume persistant:"
docker volume ls | grep mcp-create-data || echo "Volume mcp-create-data non trouvé"

echo "✅ Nettoyage terminé!"
echo ""
echo "💡 Pour supprimer aussi les données persistantes :"
echo "   docker volume rm mcp-create-data" 