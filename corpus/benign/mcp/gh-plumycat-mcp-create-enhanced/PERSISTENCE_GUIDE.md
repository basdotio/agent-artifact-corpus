# 🔧 Guide de Persistence des Serveurs MCP

## 🎯 **PROBLÈME RÉSOLU**

**Avant :** Les serveurs MCP créés étaient perdus lors du redémarrage de Claude Desktop.

**Maintenant :** Vous pouvez sauvegarder et restaurer vos serveurs MCP personnalisés !

## 🛠️ **NOUVEAUX OUTILS DISPONIBLES**

### 1. **`save-server`** - Sauvegarder un serveur
```json
{
  "name": "save-server",
  "arguments": {
    "serverId": "server-abc123",
    "name": "Mon serveur de calcul"
  }
}
```

### 2. **`list-saved-servers`** - Lister les serveurs sauvegardés
```json
{
  "name": "list-saved-servers",
  "arguments": {}
}
```

### 3. **`load-saved-server`** - Charger un serveur sauvegardé
```json
{
  "name": "load-saved-server", 
  "arguments": {
    "savedServerId": "server-abc123"
  }
}
```

### 4. **`delete-saved-server`** - Supprimer un serveur sauvegardé
```json
{
  "name": "delete-saved-server",
  "arguments": {
    "savedServerId": "server-abc123"
  }
}
```

## 📋 **WORKFLOW COMPLET**

### **Étape 1 : Créer un serveur**
```bash
# Créer un serveur personnalisé
create-server-from-template
  - language: "python"
  - code: "#!/usr/bin/env python3..."
```

### **Étape 2 : Tester le serveur**
```bash
# Lister les serveurs actifs
list-servers

# Tester les outils
execute-tool
  - serverId: "server-abc123"
  - toolName: "echo"
  - args: {"message": "Hello"}
```

### **Étape 3 : Sauvegarder le serveur**
```bash
# Sauvegarder pour récupération ultérieure
save-server
  - serverId: "server-abc123"
  - name: "Mon serveur de calcul v1.0"
```

### **Étape 4 : Après redémarrage de Claude Desktop**
```bash
# Lister les serveurs sauvegardés
list-saved-servers

# Charger un serveur sauvegardé
load-saved-server
  - savedServerId: "server-abc123"
```

## 🗂️ **STOCKAGE DES DONNÉES**

### **Fichier de sauvegarde :**
```bash
/app/data/saved_servers.json
```

### **Format des données :**
```json
{
  "server-abc123": {
    "name": "Mon serveur de calcul v1.0",
    "code": "#!/usr/bin/env python3\n...",
    "language": "python",
    "savedAt": "2024-01-15T10:30:00.000Z",
    "serverId": "server-abc123"
  }
}
```

## 🔍 **EXEMPLES PRATIQUES**

### **Sauvegarder un serveur Python :**
```bash
# 1. Créer un serveur Python
create-server-from-template
  - language: "python"
  - code: "#!/usr/bin/env python3\nimport json\n..."

# 2. Obtenir l'ID du serveur → "server-xyz789"

# 3. Sauvegarder avec un nom descriptif
save-server
  - serverId: "server-xyz789"
  - name: "API Calculator Python"
```

### **Restaurer après redémarrage :**
```bash
# 1. Voir les serveurs sauvegardés
list-saved-servers
# → Résultat : "📄 API Calculator Python (ID: server-xyz789, Language: python, Saved: 2024-01-15T10:30:00.000Z)"

# 2. Charger le serveur sauvegardé
load-saved-server
  - savedServerId: "server-xyz789"
# → Résultat : "✅ Saved server loaded as new server: server-abc456"

# 3. Le serveur est maintenant actif avec un nouvel ID
```

## ⚠️ **IMPORTANT À RETENIR**

1. **Serveur actif requis** : Vous devez d'abord créer et tester un serveur avant de le sauvegarder
2. **Nouvel ID après restauration** : Le serveur restauré aura un nouvel ID de serveur
3. **Persistence Docker** : Les données sont stockées dans le volume Docker `/app/data`
4. **Nom descriptif** : Utilisez des noms clairs pour identifier facilement vos serveurs

## 🎉 **AVANTAGES**

- **✅ Persistance** : Vos serveurs survivent aux redémarrages
- **✅ Bibliothèque personnelle** : Créez votre collection de serveurs MCP
- **✅ Partage** : Sauvegardez des serveurs pour les réutiliser
- **✅ Versioning** : Sauvegardez différentes versions de vos serveurs

## 🚀 **WORKFLOW RECOMMANDÉ**

1. **Développement** : Créez et testez vos serveurs
2. **Sauvegarde** : Sauvegardez les serveurs qui fonctionnent
3. **Collection** : Constituez votre bibliothèque de serveurs
4. **Restauration** : Chargez rapidement vos serveurs favoris

**Maintenant vous pouvez créer une véritable bibliothèque de serveurs MCP personnalisés ! 🎯**

