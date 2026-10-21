# Nettoyage des containers MCP-Create (Windows PowerShell)

Write-Host "🧹 Nettoyage des containers MCP-Create..." -ForegroundColor Yellow

# 1. Arrêter tous les containers mcp-create en cours
Write-Host "📦 Arrêt des containers actifs..." -ForegroundColor Cyan
$activeContainers = docker ps -q -f ancestor=mcp-create
if ($activeContainers) {
    docker stop $activeContainers
    Write-Host "Containers actifs arrêtés" -ForegroundColor Green
} else {
    Write-Host "Aucun container actif trouvé" -ForegroundColor Gray
}

# 2. Supprimer tous les containers mcp-create arrêtés  
Write-Host "🗑️  Suppression des containers arrêtés..." -ForegroundColor Cyan
$stoppedContainers = docker ps -aq -f ancestor=mcp-create
if ($stoppedContainers) {
    docker rm $stoppedContainers
    Write-Host "Containers arrêtés supprimés" -ForegroundColor Green
} else {
    Write-Host "Aucun container arrêté trouvé" -ForegroundColor Gray
}

# 3. Arrêter les containers par nom spécifique (au cas où)
Write-Host "🎯 Nettoyage par nom de container..." -ForegroundColor Cyan
try {
    docker stop mcp-create-session 2>$null
    docker rm mcp-create-session 2>$null
    Write-Host "Container 'mcp-create-session' nettoyé" -ForegroundColor Green
} catch {
    Write-Host "Container 'mcp-create-session' non trouvé" -ForegroundColor Gray
}

# 4. Afficher les containers restants (pour debug)
Write-Host "📋 Containers Docker restants:" -ForegroundColor Cyan
$remainingContainers = docker ps -a --filter ancestor=mcp-create
if ($remainingContainers) {
    docker ps -a --filter ancestor=mcp-create
} else {
    Write-Host "Aucun container mcp-create restant" -ForegroundColor Green
}

# 5. Afficher l'état du volume persistant
Write-Host "💾 État du volume persistant:" -ForegroundColor Cyan
$volume = docker volume ls | Select-String "mcp-create-data"
if ($volume) {
    Write-Host $volume -ForegroundColor Green
} else {
    Write-Host "Volume mcp-create-data non trouvé" -ForegroundColor Gray
}

Write-Host "✅ Nettoyage terminé!" -ForegroundColor Green
Write-Host ""
Write-Host "💡 Pour supprimer aussi les données persistantes :" -ForegroundColor Yellow
Write-Host "   docker volume rm mcp-create-data" -ForegroundColor Gray 