# 🐳 GUIDE DE GESTION DOCKER - MCP-CREATE

## 🎯 **PROBLÈMES RÉSOLUS**

### ❌ **Problèmes Avant (Configuration de Base)**

```json
{
  "command": "docker",
  "args": ["run", "-i", "--rm", "mcp-create"]
}
```

**Problèmes identifiés :**

- Container reste actif après fermeture Claude Desktop
- Données perdues à chaque redémarrage (`--rm`)
- Gestion manuelle des containers orphelins
- Pas de persistance des serveurs créés

### ✅ **Solutions Implémentées**

1. **🚀 Gestion des signaux d'arrêt propre**
2. **💾 Persistence des données avec volumes**
3. **🧹 Nettoyage automatique des containers**
4. **⚡ Timeouts configurés pour arrêt gracieux**

---

## 🛠️ **CONFIGURATION RECOMMANDÉE**

### **claude-desktop-config.json**

```json
{
  "mcpServers": {
    "mcp-create": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",                           // ✅ Container se supprime automatiquement
        "-v", "mcp-create-data:/app/data", // ✅ Volume persistant
        "--name", "mcp-create-session",    // ✅ Nom fixe pour gestion
        "--stop-timeout", "5",             // ✅ Timeout d'arrêt gracieux
        "--log-driver", "none",            // ✅ Pas de logs Docker (optionnel)
        "mcp-create"
      ],
      "env": {
        "MCP_CREATE_DATA_DIR": "/app/data"
      }
    }
  }
}
```

### **Avantages de cette configuration :**

- ✅ **Arrêt automatique** avec Claude Desktop
- ✅ **Données persistantes** entre sessions
- ✅ **Nom de container fixe** pour debug/monitoring
- ✅ **Timeout gracieux** évite les arrêts forcés
- ✅ **Variables d'environnement** pour configuration

---

## 🧹 **NETTOYAGE AUTOMATIQUE**

### **Script cleanup-mcp.sh**

```bash
chmod +x cleanup-mcp.sh
./cleanup-mcp.sh
```

**Ce que fait le script :**

1. 📦 Arrête tous les containers mcp-create actifs
2. 🗑️ Supprime les containers arrêtés
3. 🎯 Nettoie les containers par nom spécifique
4. 📋 Affiche l'état des containers restants
5. 💾 Vérifie l'état du volume persistant

### **Nettoyage manuel si besoin :**

```bash
# Arrêter tous les containers mcp-create
docker stop $(docker ps -q -f ancestor=mcp-create)

# Supprimer tous les containers mcp-create
docker rm $(docker ps -aq -f ancestor=mcp-create)

# Supprimer le volume (ATTENTION: perte de données)
docker volume rm mcp-create-data
```

---

## 🔄 **CYCLE DE VIE AMÉLIORÉ**

### **1. Démarrage de Claude Desktop**

```text
Claude Desktop démarre
    ↓
Création du container "mcp-create-session"
    ↓
Volume "mcp-create-data" monté sur /app/data
    ↓
mcp-create démarre avec gestion des signaux
    ↓
✅ Prêt à utiliser
```

### **2. Fonctionnement Normal**

```text
Serveurs créés → Sauvegardés dans /app/data (persistant)
Outils exécutés → Logs dans container
Communications MCP → Via stdio
```

### **3. Arrêt de Claude Desktop**

```text
Claude Desktop ferme
    ↓
Signal SIGTERM envoyé au container
    ↓
mcp-create reçoit le signal
    ↓
Nettoyage gracieux des serveurs actifs
    ↓
Container s'arrête (--stop-timeout 5s)
    ↓
Container supprimé automatiquement (--rm)
    ↓
✅ Volume persistant préservé
```

---

## 📊 **MONITORING ET DEBUG**

### **Vérifier l'état actuel :**

```bash
# Containers actifs
docker ps --filter ancestor=mcp-create

# Tous les containers mcp-create
docker ps -a --filter ancestor=mcp-create

# État du volume persistant
docker volume ls | grep mcp-create-data

# Inspecter le volume
docker volume inspect mcp-create-data
```

### **Logs de debug :**

```bash
# Logs du container actif
docker logs mcp-create-session

# Logs en temps réel
docker logs -f mcp-create-session
```

### **Accès au container pour debug :**

```bash
# Shell dans le container
docker exec -it mcp-create-session /bin/bash

# Vérifier les fichiers persistants
docker exec mcp-create-session ls -la /app/data/
```

---

## 🚨 **RÉSOLUTION DE PROBLÈMES**

### **Container ne s'arrête pas**

```bash
# Force stop avec timeout
docker stop --time 10 mcp-create-session

# Force kill si nécessaire
docker kill mcp-create-session
```

### **Données perdues**

```bash
# Vérifier que le volume existe
docker volume inspect mcp-create-data

# Sauvegarder le volume
docker run --rm -v mcp-create-data:/data -v $(pwd):/backup busybox tar czf /backup/mcp-backup.tar.gz -C /data .

# Restaurer le volume
docker run --rm -v mcp-create-data:/data -v $(pwd):/backup busybox tar xzf /backup/mcp-backup.tar.gz -C /data
```

### **Container ne démarre pas**

```bash
# Vérifier l'image
docker images | grep mcp-create

# Reconstruire si nécessaire
docker build -t mcp-create .

# Test manuel
docker run -it --rm mcp-create
```

---

## 📈 **AMÉLIORATIONS FUTURES**

### **Option 1 : Health Checks**

```dockerfile
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD node -e "console.log('healthy')" || exit 1
```

### **Option 2 : Container On-Demand**

```bash
# Script wrapper pour démarrage conditionnel
if ! docker ps -q -f name=mcp-create-session; then
    docker run -d --name mcp-create-session \
        -v mcp-create-data:/app/data mcp-create
fi
```

### **Option 3 : Resource Limits**

```json
"args": [
  "run", "-i", "--rm",
  "--memory", "512m",
  "--cpus", "0.5",
  "-v", "mcp-create-data:/app/data",
  "mcp-create"
]
```

---

## ✅ **RÉSUMÉ DES BÉNÉFICES**

| Aspect | Avant | Après |
|--------|-------|-------|
| **Persistence** | ❌ Données perdues | ✅ Volume persistant |
| **Arrêt** | ❌ Manuel requis | ✅ Automatique avec Claude |
| **Gestion** | ❌ Containers orphelins | ✅ Nettoyage automatique |
| **Debug** | ❌ Difficile | ✅ Logs et monitoring |
| **Stabilité** | ❌ Arrêts forcés | ✅ Signaux gracieux |
| **Maintenance** | ❌ Manuelle | ✅ Scripts automatisés |

**🎉 Résultat : Experience utilisateur grandement améliorée !**
