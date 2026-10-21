# 🧪 Test de Persistence - Plan de Validation

## ✅ **TEST 1 : Sauvegarder un serveur**

### Étapes :
1. **Créer un serveur Python**
   ```bash
   create-server-from-template
   - language: "python"
   - code: (utiliser le template par défaut)
   ```

2. **Obtenir l'ID du serveur**
   ```bash
   list-servers
   # → Résultat attendu : ID du serveur créé
   ```

3. **Tester le serveur**
   ```bash
   execute-tool
   - serverId: "server-[ID]"
   - toolName: "echo"
   - args: {"message": "Test persistence"}
   ```

4. **Sauvegarder le serveur**
   ```bash
   save-server
   - serverId: "server-[ID]"
   - name: "Test Persistence Server"
   ```

### Résultat attendu :
- ✅ Message : "Server [ID] saved as 'Test Persistence Server'"
- ✅ Fichier `/app/data/saved_servers.json` créé

## ✅ **TEST 2 : Lister les serveurs sauvegardés**

### Étapes :
1. **Lister les serveurs sauvegardés**
   ```bash
   list-saved-servers
   ```

### Résultat attendu :
- ✅ Message : "📄 Test Persistence Server (ID: server-[ID], Language: python, Saved: [timestamp])"

## ✅ **TEST 3 : Charger un serveur sauvegardé**

### Étapes :
1. **Supprimer le serveur actif**
   ```bash
   delete-server
   - serverId: "server-[ID]"
   ```

2. **Vérifier qu'il n'y a plus de serveurs actifs**
   ```bash
   list-servers
   # → Résultat attendu : Aucun serveur actif
   ```

3. **Charger le serveur sauvegardé**
   ```bash
   load-saved-server
   - savedServerId: "server-[ID]"
   ```

4. **Vérifier que le serveur est actif**
   ```bash
   list-servers
   # → Résultat attendu : Nouveau serveur avec nouvel ID
   ```

5. **Tester le serveur chargé**
   ```bash
   execute-tool
   - serverId: "server-[NOUVEAU_ID]"
   - toolName: "echo"
   - args: {"message": "Server loaded successfully"}
   ```

### Résultat attendu :
- ✅ Message : "Saved server loaded as new server: server-[NOUVEAU_ID]"
- ✅ Serveur fonctionnel avec nouvel ID
- ✅ Outil "echo" fonctionne correctement

## ✅ **TEST 4 : Supprimer un serveur sauvegardé**

### Étapes :
1. **Supprimer le serveur sauvegardé**
   ```bash
   delete-saved-server
   - savedServerId: "server-[ID]"
   ```

2. **Vérifier que le serveur n'existe plus**
   ```bash
   list-saved-servers
   # → Résultat attendu : "No saved servers found"
   ```

### Résultat attendu :
- ✅ Message : "Saved server [ID] deleted from disk"
- ✅ Aucun serveur sauvegardé dans la liste

## ✅ **TEST 5 : Persistence après redémarrage**

### Étapes :
1. **Créer et sauvegarder un serveur**
   ```bash
   create-server-from-template → save-server
   ```

2. **Redémarrer Claude Desktop**
   ```bash
   # Fermer et rouvrir Claude Desktop
   ```

3. **Vérifier que le serveur est toujours sauvegardé**
   ```bash
   list-saved-servers
   # → Résultat attendu : Serveur présent dans la liste
   ```

4. **Charger le serveur**
   ```bash
   load-saved-server
   ```

5. **Tester le serveur chargé**
   ```bash
   execute-tool
   ```

### Résultat attendu :
- ✅ Serveur survit au redémarrage
- ✅ Données persistent dans le volume Docker
- ✅ Serveur fonctionne après chargement

## 🎯 **CRITÈRES DE VALIDATION**

### **Fonctionnalités Core :**
- [ ] Sauvegarder un serveur actif
- [ ] Lister les serveurs sauvegardés
- [ ] Charger un serveur sauvegardé
- [ ] Supprimer un serveur sauvegardé

### **Persistence :**
- [ ] Données survivent au redémarrage
- [ ] Volume Docker `/app/data` fonctionne
- [ ] Format JSON valide dans `saved_servers.json`

### **Validation :**
- [ ] Erreurs claires pour arguments manquants
- [ ] Gestion des serveurs inexistants
- [ ] Nouveaux IDs après chargement

### **Intégration :**
- [ ] Compatible avec serveurs TypeScript et Python
- [ ] Fonctionne avec les outils existants
- [ ] Pas de régression sur les fonctionnalités existantes

## 🚀 **RÉSULTAT ATTENDU**

**✅ SYSTÈME DE PERSISTENCE OPÉRATIONNEL**
- Sauvegarde/restauration complète
- Interface utilisateur claire
- Stockage persistent Docker
- Compatibilité multi-langage
- Gestion d'erreurs robuste

**🎯 OBJECTIF ATTEINT : Les serveurs MCP survivent aux redémarrages !** 