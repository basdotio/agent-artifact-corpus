// ============================================================
// 钓鱼游戏调度面板 - 前端逻辑
// ============================================================

const API = '';
const RARITY_LABELS = {
    common: '常见', uncommon: '少见', rare: '稀有',
    epic: '史诗', legendary: '传说', mythic: '神话'
};
const SEASON_LABELS = { spring: '春', summer: '夏', autumn: '秋', winter: '冬', all: '全部' };
const ALL_SEASONS = ['spring', 'summer', 'autumn', 'winter'];
const ALL_TAGS = ['freshwater','nocturnal','deepsea','glowing','fire','fantasy','wind','crystal','armored','brackish','swamp','poison','mineral','ancient','shadow','migratory','electric','underwater'];
const TAG_LABELS = {
    freshwater:'淡水', nocturnal:'夜行', deepsea:'深海', glowing:'发光', fire:'火焰',
    fantasy:'幻想', wind:'风系', crystal:'水晶', armored:'甲壳', brackish:'咸淡水',
    swamp:'沼泽', poison:'毒性', mineral:'矿物', ancient:'远古', shadow:'暗影',
    migratory:'洄游', electric:'电击', underwater:'水下'
};

let allFishData = [];
let allLocations = [];
let ws = null;
let highlightBaitId = '';
let highlightLocationId = '';
let highlightFishId = '';
let locSelectedFishIds = new Set();
let locOriginalFishIds = new Set();
let locDiveSelectedFishIds = new Set();
let locDiveOriginalFishIds = new Set();
let locGlobalFish = [];
let probabilityMode = 'cast';

// ============================================================
// Init
// ============================================================

document.addEventListener('DOMContentLoaded', () => {
    lucide.createIcons();
    loadDashboard();
    connectWebSocket();
});

// ============================================================
// Utilities
// ============================================================

function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function generateId() {
    return 'custom_' + Math.random().toString(36).substr(2, 8);
}

// ============================================================
// Custom Dialog System (replaces alert/confirm/prompt)
// ============================================================

function _createDialogOverlay() {
    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay custom-dialog-overlay';
    overlay.style.display = 'flex';
    overlay.style.zIndex = '2000';
    return overlay;
}

function customAlert(message, title = '提示') {
    return new Promise(resolve => {
        const overlay = _createDialogOverlay();
        overlay.innerHTML = `
            <div class="modal" style="max-width:400px;">
                <div class="modal-header">
                    <h3>${escapeHtml(title)}</h3>
                    <button class="btn-icon" onclick="this.closest('.modal-overlay').remove()"><i data-lucide="x"></i></button>
                </div>
                <div class="modal-body">
                    <p style="white-space:pre-wrap;line-height:1.7;color:var(--text-secondary);">${escapeHtml(message)}</p>
                </div>
                <div class="modal-footer">
                    <button class="btn dialog-ok-btn">确定</button>
                </div>
            </div>
        `;
        document.body.appendChild(overlay);
        lucide.createIcons();
        const okBtn = overlay.querySelector('.dialog-ok-btn');
        okBtn.focus();
        okBtn.onclick = () => { overlay.remove(); resolve(); };
        overlay.onclick = (e) => { if (e.target === overlay) { overlay.remove(); resolve(); } };
    });
}

function customConfirm(message, title = '确认') {
    return new Promise(resolve => {
        const overlay = _createDialogOverlay();
        overlay.innerHTML = `
            <div class="modal" style="max-width:420px;">
                <div class="modal-header">
                    <h3>${escapeHtml(title)}</h3>
                    <button class="btn-icon" onclick="this.closest('.modal-overlay').remove()"><i data-lucide="x"></i></button>
                </div>
                <div class="modal-body">
                    <p style="white-space:pre-wrap;line-height:1.7;color:var(--text-secondary);">${escapeHtml(message)}</p>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-ghost dialog-cancel-btn">取消</button>
                    <button class="btn dialog-ok-btn">确定</button>
                </div>
            </div>
        `;
        document.body.appendChild(overlay);
        lucide.createIcons();
        const okBtn = overlay.querySelector('.dialog-ok-btn');
        const cancelBtn = overlay.querySelector('.dialog-cancel-btn');
        const closeIcon = overlay.querySelector('.btn-icon');
        okBtn.focus();
        okBtn.onclick = () => { overlay.remove(); resolve(true); };
        cancelBtn.onclick = () => { overlay.remove(); resolve(false); };
        closeIcon.onclick = () => { overlay.remove(); resolve(false); };
        overlay.onclick = (e) => { if (e.target === overlay) { overlay.remove(); resolve(false); } };
    });
}

function notify(message) {
    customAlert(message);
}

async function parseApiResponse(res) {
    const data = await res.json().catch(() => ({}));
    if (!res.ok || data.error) {
        throw new Error(`${data.error || `请求失败：${res.status}`}\n${res.url || ''}`.trim());
    }
    return data;
}

async function ensureFishData() {
    if (allFishData.length > 0) return;
    const res = await fetch(`${API}/api/fish`);
    const data = await res.json();
    allFishData = data.fish || [];
}

// Multi-select chip renderer
function renderChips(containerId, options, selected = []) {
    const container = document.getElementById(containerId);
    container.innerHTML = options.map(opt => {
        const val = typeof opt === 'object' ? opt.value : opt;
        const label = typeof opt === 'object' ? opt.label : (SEASON_LABELS[opt] || opt);
        const isSelected = selected.includes(val);
        return `<span class="chip chip-option ${isSelected ? 'selected' : ''}" data-value="${val}" onclick="toggleChip(this)">${label}</span>`;
    }).join('');
}

function toggleChip(el) {
    el.classList.toggle('selected');
}

function getSelectedChips(containerId) {
    const chips = document.querySelectorAll(`#${containerId} .chip-option.selected`);
    return Array.from(chips).map(c => c.dataset.value);
}

function linesToText(lines) {
    return Array.isArray(lines) ? lines.join('\n') : '';
}

function textToLines(text) {
    return (text || '').split('\n').map(s => s.trim()).filter(Boolean);
}

// ============================================================
// Custom Dropdown
// ============================================================

function toggleDropdown(id) {
    const dd = document.getElementById(id);
    document.querySelectorAll('.custom-dropdown.open').forEach(d => { if (d.id !== id) d.classList.remove('open'); });
    dd.classList.toggle('open');
}

function selectRarity(value) {
    document.getElementById('fishRarityFilter').value = value;
    const label = value ? (RARITY_LABELS[value] || value) : '全部稀有度';
    document.getElementById('fishRarityLabel').textContent = label;
    // Update active state
    document.querySelectorAll('#fishRarityDropdown .custom-dropdown-item').forEach(item => {
        item.classList.toggle('active', item.dataset.value === value);
    });
    document.getElementById('fishRarityDropdown').classList.remove('open');
    loadFishList();
}

// Close dropdowns on outside click
document.addEventListener('click', (e) => {
    if (!e.target.closest('.custom-dropdown')) {
        document.querySelectorAll('.custom-dropdown.open').forEach(d => d.classList.remove('open'));
    }
});

// ============================================================
// Tab Navigation
// ============================================================

function switchTab(tabName) {
    document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
    document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
    document.getElementById(`tab-${tabName}`).classList.add('active');

    if (tabName === 'baits') loadBaits();
    if (tabName === 'locations') loadLocations();
    if (tabName === 'fish') loadFishList();
    if (tabName === 'probability') initProbability();
    if (tabName === 'tooldescs') loadToolDescs();
    if (tabName === 'dashboard') loadDashboard();

    lucide.createIcons();
}

// ============================================================
// Dashboard
// ============================================================

async function loadDashboard() {
    try {
        const res = await fetch(`${API}/api/status`);
        const data = await res.json();
        const card = document.getElementById('gameStatusCard');
        const lines = data.game_status.split('\n').slice(0, 8).join('\n');
        card.innerHTML = `<pre class="result-text" style="max-height:180px;">${escapeHtml(lines)}</pre>`;
    } catch (e) {
        document.getElementById('gameStatusCard').innerHTML = '<p class="text-muted">无法连接服务器</p>';
    }
}

async function runCommand(cmd) {
    const res = await fetch(`${API}/api/command`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command: cmd })
    });
    const data = await res.json();
    const el = document.getElementById('commandResult');
    el.style.display = 'block';
    el.textContent = data.result;
}

function runCustomCommand() {
    const input = document.getElementById('commandInput');
    if (input.value.trim()) {
        runCommand(input.value.trim());
        input.value = '';
    }
}

async function newGame() {
    if (!await customConfirm('确定要重开一局吗？当前进度将清空。')) return;
    await fetch(`${API}/api/new_game`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
    });
    await customAlert('已重开一局！');
    loadDashboard();
}

// ============================================================
// Baits
// ============================================================

async function loadBaits() {
    const res = await fetch(`${API}/api/baits`);
    const data = await res.json();
    const grid = document.getElementById('baitsGrid');
    const search = (document.getElementById('baitSearchInput')?.value || '').toLowerCase();

    let baits = data.baits;
    if (search) baits = baits.filter(b => b.name.toLowerCase().includes(search) || b.id.toLowerCase().includes(search));

    grid.innerHTML = baits.map(bait => `
        <div class="card card-hover" style="${bait.id === highlightBaitId ? 'outline:2px solid var(--accent);' : ''}">
            <div class="bait-card">
                <div class="bait-name">${escapeHtml(bait.name)}</div>
                <div class="bait-desc">${escapeHtml(bait.description)}</div>
                <div class="bait-controls">
                    <div class="bait-control-row">
                        <label>价格</label>
                        <input type="number" value="${bait.cost}" style="width:80px"
                            onchange="updateBait('${bait.id}', {cost: parseInt(this.value)})">
                    </div>
                    <div class="bait-control-row">
                        <label>购买上限 (空=不限)</label>
                        <input type="number" value="${bait.limit || ''}" placeholder="不限" style="width:80px"
                            onchange="updateBait('${bait.id}', {limit: this.value ? parseInt(this.value) : null})">
                    </div>
                    <div class="bait-control-row">
                        <label>启用</label>
                        <div class="toggle ${!bait.disabled ? 'active' : ''}"
                            onclick="toggleBait(this, '${bait.id}')"></div>
                    </div>
                    <div style="margin-top:8px;display:flex;gap:6px;">
                        <button class="btn btn-sm btn-ghost" onclick="editBaitEffects('${bait.id}')">编辑</button>
                        <button class="btn btn-sm btn-danger" onclick="deleteBait('${bait.id}','${escapeHtml(bait.name)}')">删除</button>
                    </div>
                </div>
            </div>
        </div>
    `).join('');
}

async function updateBait(id, updates) {
    const res = await fetch(`${API}/api/baits/update`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id, ...updates })
    });
    await parseApiResponse(res);
}

async function toggleBait(el, id) {
    const isActive = el.classList.contains('active');
    el.classList.toggle('active');
    await updateBait(id, { disabled: isActive });
}

async function deleteBait(id, name) {
    if (!await customConfirm(`确定删除鱼饵「${name}」吗？`)) return;
    const res = await fetch(`${API}/api/baits/delete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id })
    });
    await parseApiResponse(res);
    notify(`已删除鱼饵：${name}`);
    loadBaits();
}

let editingBaitId = null;

function showAddBaitPrompt() {
    editingBaitId = null;
    document.getElementById('baitFormName').value = '';
    document.getElementById('baitFormCost').value = '20';
    document.getElementById('baitFormDesc').value = '';
    document.getElementById('baitFormLimit').value = '0';
    document.getElementById('baitFormEnabled').classList.add('active');
    // Show basic fields for new bait
    document.querySelectorAll('#addBaitModal .bait-basic-fields').forEach(el => el.style.display = '');
    clearBaitEffectFields();
    renderBaitTagEffectInputs({});
    document.getElementById('addBaitModal').style.display = 'flex';
    lucide.createIcons();
}

async function editBaitEffects(baitId) {
    editingBaitId = baitId;
    // Fetch current bait effects from server
    const res = await fetch(`${API}/api/baits`);
    const data = await res.json();
    const bait = data.baits.find(b => b.id === baitId);
    if (!bait) return;

    // We need the full bait data with effects - get from custom_config via a dedicated approach
    // The /api/baits doesn't return effects, so let's fetch from engine directly
    // Actually, let's add effects to the baits API response... for now, use update with empty to read
    // Better: open the modal and fill what we can, effects come from engine.BAITS[id].effects
    // The simplest: fetch effects from a new lightweight endpoint or just open the form
    // For now, fill the basic info and let user see/edit effects
    document.getElementById('baitFormName').value = bait.name;
    document.getElementById('baitFormCost').value = bait.cost;
    document.getElementById('baitFormDesc').value = bait.description || '';
    document.getElementById('baitFormLimit').value = bait.limit || '0';
    if (bait.disabled) {
        document.getElementById('baitFormEnabled').classList.remove('active');
    } else {
        document.getElementById('baitFormEnabled').classList.add('active');
    }

    // Clear and render effects - we'll try to load from API
    clearBaitEffectFields();
    try {
        const effRes = await fetch(`${API}/api/baits/effects/${baitId}`);
        if (effRes.ok) {
            const effData = await effRes.json();
            fillBaitEffectFields(effData.effects || {});
        } else {
            renderBaitTagEffectInputs({});
        }
    } catch(e) {
        renderBaitTagEffectInputs({});
    }

    document.getElementById('addBaitModal').style.display = 'flex';
    lucide.createIcons();
}

function clearBaitEffectFields() {
    ['Common','Uncommon','Rare','Epic','Legendary','Mythic'].forEach(r => {
        const el = document.getElementById('baitEffRarity' + r);
        if (el) el.value = '';
    });
    const junkEl = document.getElementById('baitEffJunk');
    const eventEl = document.getElementById('baitEffEvent');
    if (junkEl) junkEl.value = '';
    if (eventEl) eventEl.value = '';
    renderBaitTagEffectInputs({});
}

function renderBaitTagEffectInputs(tagWeights) {
    const tagsContainer = document.getElementById('baitEffectTags');
    if (tagsContainer) {
        tagsContainer.innerHTML = ALL_TAGS.map(tag => {
            const val = tagWeights[tag] || '';
            return `<div class="bait-effect-row"><span>${TAG_LABELS[tag] || tag}</span><input type="number" step="0.1" min="0" data-tag="${tag}" placeholder="1.0" value="${val && val !== 1 ? val : ''}"></div>`;
        }).join('');
    }
}

function fillBaitEffectFields(effects) {
    const rarityMap = {common:'Common',uncommon:'Uncommon',rare:'Rare',epic:'Epic',legendary:'Legendary',mythic:'Mythic'};
    const rwm = effects.rarity_weight_mult || {};
    for (const [key, suffix] of Object.entries(rarityMap)) {
        const el = document.getElementById('baitEffRarity' + suffix);
        if (el) el.value = rwm[key] || '';
    }
    const junkEl = document.getElementById('baitEffJunk');
    if (junkEl) junkEl.value = effects.junk_chance_mult || '';
    const eventEl = document.getElementById('baitEffEvent');
    if (eventEl) eventEl.value = effects.event_chance_add || '';
    renderBaitTagEffectInputs(effects.tag_weight_mult || {});
}

function collectBaitEffects() {
    const effects = {};
    // Rarity weight mult
    const rarityMap = {common:'Common',uncommon:'Uncommon',rare:'Rare',epic:'Epic',legendary:'Legendary',mythic:'Mythic'};
    const rarity_weight_mult = {};
    for (const [key, suffix] of Object.entries(rarityMap)) {
        const el = document.getElementById('baitEffRarity' + suffix);
        if (el && el.value && parseFloat(el.value) !== 1.0) {
            rarity_weight_mult[key] = parseFloat(el.value);
        }
    }
    if (Object.keys(rarity_weight_mult).length > 0) effects.rarity_weight_mult = rarity_weight_mult;
    // Tag weight mult
    const tag_weight_mult = {};
    document.querySelectorAll('#baitEffectTags input[data-tag]').forEach(input => {
        if (input.value && parseFloat(input.value) !== 1.0) {
            tag_weight_mult[input.dataset.tag] = parseFloat(input.value);
        }
    });
    if (Object.keys(tag_weight_mult).length > 0) effects.tag_weight_mult = tag_weight_mult;
    // Junk chance
    const junkEl = document.getElementById('baitEffJunk');
    if (junkEl && junkEl.value) effects.junk_chance_mult = parseFloat(junkEl.value);
    // Event chance
    const eventEl = document.getElementById('baitEffEvent');
    if (eventEl && eventEl.value) effects.event_chance_add = parseFloat(eventEl.value);
    return effects;
}

async function submitBaitForm() {
    const name = document.getElementById('baitFormName').value.trim();
    if (!name) { customAlert('请填写鱼饵名称'); return; }

    const cost = parseInt(document.getElementById('baitFormCost').value) || 20;
    const desc = document.getElementById('baitFormDesc').value.trim() || '自定义鱼饵';
    const limit = parseInt(document.getElementById('baitFormLimit').value) || 0;
    const enabled = document.getElementById('baitFormEnabled').classList.contains('active');
    const effects = collectBaitEffects();

    if (editingBaitId) {
        // Edit mode: update existing bait
        const res = await fetch(`${API}/api/baits/update`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                id: editingBaitId,
                name, cost, description: desc, effects,
                limit: limit > 0 ? limit : null,
                disabled: !enabled
            })
        });
        try {
            await parseApiResponse(res);
        } catch (e) {
            customAlert(e.message);
            return;
        }
        closeModal('addBaitModal');
        highlightBaitId = editingBaitId;
        editingBaitId = null;
        loadBaits();
        notify(`已保存鱼饵效果：${name}`);
    } else {
        // Add mode
        const res = await fetch(`${API}/api/baits/add`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, cost, description: desc, effects })
        });
        let data;
        try {
            data = await parseApiResponse(res);
        } catch (e) {
            customAlert(e.message);
            return;
        }

        // Apply limit and disabled state if set
        if (data.bait && (limit > 0 || !enabled)) {
            const updateRes = await fetch(`${API}/api/baits/update`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    id: data.bait.id,
                    limit: limit > 0 ? limit : null,
                    disabled: !enabled
                })
            });
            await parseApiResponse(updateRes);
        }

        closeModal('addBaitModal');
        highlightBaitId = data.bait.id;
        loadBaits();
        notify(`已添加鱼饵：${data.bait.name}\nMCP 的 shop/buy 已可使用。`);
    }
}

// ============================================================
// Locations
// ============================================================

function selectLocSeasonFilter(value) {
    document.getElementById('locSeasonFilter').value = value;
    const label = value ? (SEASON_LABELS[value] || value) : '全部季节';
    document.getElementById('locSeasonFilterLabel').textContent = label;
    document.querySelectorAll('#locSeasonFilterDropdown .custom-dropdown-item').forEach(item => {
        item.classList.toggle('active', item.dataset.value === value);
    });
    document.getElementById('locSeasonFilterDropdown').classList.remove('open');
    loadLocations();
}

async function loadLocations() {
    const res = await fetch(`${API}/api/locations`);
    const data = await res.json();
    allLocations = data.locations;
    const grid = document.getElementById('locationsGrid');
    const search = (document.getElementById('locSearchInput')?.value || '').toLowerCase();
    const seasonFilter = document.getElementById('locSeasonFilter')?.value || '';

    let locs = data.locations;
    if (search) locs = locs.filter(l => l.name.toLowerCase().includes(search) || l.id.toLowerCase().includes(search));
    if (seasonFilter) locs = locs.filter(l => l.available_seasons.includes(seasonFilter));

    const cards = await Promise.all(locs.map(async loc => {
        const fishRes = await fetch(`${API}/api/locations/${loc.id}/fish`);
        const fishData = await fishRes.json();
        const explicitFish = (fishData.fish || []).filter(f => f.explicit && !f.global);
        const surfaceCount = explicitFish.filter(f => !f.dive).length;
        const diveCount = explicitFish.filter(f => f.dive).length;
        const globalCount = (fishData.fish || []).filter(f => f.global).length;
        const seasons = loc.available_seasons.map(s => SEASON_LABELS[s] || s).join(' ');
        const diveBadge = loc.dive_enabled ? `<span class="location-tag">深水 ${diveCount}</span>` : `<span class="location-tag">深水关闭</span>`;

        return `
            <div class="card card-hover" style="${loc.id === highlightLocationId ? 'outline:2px solid var(--accent);' : ''}">
                <div class="location-card">
                    <div class="location-name">${escapeHtml(loc.name)}</div>
                    <div class="location-desc">${escapeHtml(loc.description)}</div>
                    <div class="location-meta">
                        <span class="location-tag">${loc.unlock_cost ? loc.unlock_cost + ' 点解锁' : '免费'}</span>
                        <span class="location-tag">${seasons}</span>
                        ${diveBadge}
                    </div>
                    <div class="location-fish-count">本地点：水面 ${surfaceCount} 种｜深水 ${diveCount} 种${globalCount ? `｜另有全域自动 ${globalCount} 种` : ''}</div>
                    <div style="margin-top:10px;display:flex;gap:6px;">
                        <button class="btn btn-sm btn-ghost" onclick="editLocation('${loc.id}')">编辑</button>
                        <button class="btn btn-sm btn-danger" onclick="deleteLocation('${loc.id}')">删除</button>
                    </div>
                </div>
            </div>
        `;
    }));

    grid.innerHTML = cards.join('');
    lucide.createIcons();
}

async function showAddLocationModal() {
    await ensureFishData();
    switchLocationFormPage('surface');
    document.getElementById('locEditMode').value = 'add';
    document.getElementById('locModalTitle').textContent = '新增地点';
    document.getElementById('locFormId').value = '';
    document.getElementById('locFormName').value = '';
    document.getElementById('locFormCost').value = '0';
    document.getElementById('locFormDesc').value = '';
    renderChips('locFormSeasonsContainer', ALL_SEASONS.map(s => ({value: s, label: SEASON_LABELS[s]})), ALL_SEASONS);
    document.getElementById('locDiveEnabled').classList.add('active');
    document.getElementById('locDiveDesc').value = '';
    document.getElementById('locDiveNotes').value = '';
    ['Spring','Summer','Autumn','Winter'].forEach(s => document.getElementById('locDiveAmb' + s).value = '');
    renderChips('locDiveSeasonsContainer', ALL_SEASONS.map(s => ({value: s, label: SEASON_LABELS[s]})), ALL_SEASONS);
    locSelectedFishIds = new Set();
    locOriginalFishIds = new Set();
    locDiveSelectedFishIds = new Set();
    locDiveOriginalFishIds = new Set();
    locGlobalFish = allFishData.filter(fish => fish.locations && fish.locations.includes('all'));
    document.getElementById('locFishSearchInput').value = '';
    document.getElementById('locDiveFishSearchInput').value = '';
    updateLocationDivePlaceholders(null);
    renderLocationFishPicker('surface');
    renderLocationFishPicker('dive');
    document.getElementById('addLocationModal').style.display = 'flex';
    lucide.createIcons();
}

async function editLocation(locId) {
    await ensureFishData();
    switchLocationFormPage('surface');
    const loc = allLocations.find(l => l.id === locId);
    if (!loc) return;
    const fishRes = await fetch(`${API}/api/locations/${locId}/fish`);
    const fishData = await fishRes.json();
    const explicitFish = (fishData.fish || []).filter(f => f.explicit && !f.global);
    locSelectedFishIds = new Set(explicitFish.filter(f => !f.dive).map(f => f.id));
    locDiveSelectedFishIds = new Set(explicitFish.filter(f => f.dive).map(f => f.id));
    locOriginalFishIds = new Set(locSelectedFishIds);
    locDiveOriginalFishIds = new Set(locDiveSelectedFishIds);
    locGlobalFish = (fishData.fish || []).filter(f => f.global);
    document.getElementById('locEditMode').value = 'edit';
    document.getElementById('locModalTitle').textContent = '编辑地点';
    document.getElementById('locFormId').value = loc.id;
    document.getElementById('locFormName').value = loc.name;
    document.getElementById('locFormCost').value = loc.unlock_cost;
    document.getElementById('locFormDesc').value = loc.description;
    renderChips('locFormSeasonsContainer', ALL_SEASONS.map(s => ({value: s, label: SEASON_LABELS[s]})), loc.available_seasons);
    document.getElementById('locDiveEnabled').classList.toggle('active', loc.dive_enabled !== false);
    document.getElementById('locDiveDesc').value = getDiveDescriptionText(loc);
    document.getElementById('locDiveNotes').value = getDiveNotesText(loc);
    renderChips('locDiveSeasonsContainer', ALL_SEASONS.map(s => ({value: s, label: SEASON_LABELS[s]})), loc.dive_available_seasons || loc.available_seasons || ALL_SEASONS);
    const amb = loc.dive_ambience || {};
    document.getElementById('locDiveAmbSpring').value = linesToText(getDiveAmbienceLines(loc, 'spring'));
    document.getElementById('locDiveAmbSummer').value = linesToText(getDiveAmbienceLines(loc, 'summer'));
    document.getElementById('locDiveAmbAutumn').value = linesToText(getDiveAmbienceLines(loc, 'autumn'));
    document.getElementById('locDiveAmbWinter').value = linesToText(getDiveAmbienceLines(loc, 'winter'));
    updateLocationDivePlaceholders(loc);
    document.getElementById('locFishSearchInput').value = '';
    document.getElementById('locDiveFishSearchInput').value = '';
    renderLocationFishPicker('surface');
    renderLocationFishPicker('dive');
    document.getElementById('addLocationModal').style.display = 'flex';
    lucide.createIcons();
}

function getFishById(fishId) {
    return allFishData.find(f => f.id === fishId);
}

function countLinesForSeason(ambience, season) {
    return Array.isArray(ambience?.[season]) ? ambience[season].length : 0;
}

function getAllDiveAmbienceLines(loc) {
    const amb = loc?.dive_ambience || {};
    return ALL_SEASONS.flatMap(season => Array.isArray(amb[season]) ? amb[season] : []).filter(Boolean);
}

function getDiveAmbienceLines(loc, season) {
    const amb = loc?.dive_ambience || {};
    if (Array.isArray(amb[season]) && amb[season].length) return amb[season];
    const anyLine = getAllDiveAmbienceLines(loc)[0];
    if (anyLine) return [`${SEASON_LABELS[season]}季的${loc.name}深水也延续着相近的潜水氛围：${anyLine}`];
    if (loc?.description) return [`你潜入${loc.name}的深水区域，${loc.description}`];
    return [`你潜入${loc?.name || '这个地点'}的深水区域，水下细节还没有填写，可以在这里改成这一季的潜水文案。`];
}

function getDiveDescriptionText(loc) {
    if (loc?.dive_description) return loc.dive_description;
    const firstLine = getAllDiveAmbienceLines(loc)[0];
    if (firstLine) return firstLine;
    if (loc?.description) return `深水中的${loc.name}延续着水面特征：${loc.description}`;
    return `${loc?.name || '这个地点'}的深水区域尚未写描述，可在这里补充水下环境。`;
}

function getDiveNotesText(loc) {
    if (loc?.dive_notes) return loc.dive_notes;
    if (loc?.character) return loc.character;
    return `潜水远征会消耗氧气瓶；这里的深水鱼池可在「深水可遇鱼类」中编辑。`;
}

function updateLocationDivePlaceholders(loc) {
    const name = loc?.name || '新地点';
    const hasAnyAmbience = loc && ALL_SEASONS.some(season => countLinesForSeason(loc.dive_ambience || {}, season) > 0);
    const descEl = document.getElementById('locDiveDesc');
    const notesEl = document.getElementById('locDiveNotes');
    if (descEl) {
        descEl.placeholder = loc
            ? `这里编辑「${name}」的深水/潜水说明。若为空，游戏仍会使用下方四季潜水氛围文案。`
            : '描述这个地点水下/深处是什么样；新地点默认没有潜水文案，需要你自己填写。';
    }
    if (notesEl) {
        notesEl.placeholder = loc
            ? '可写危险提示、装备需求、深处传闻等；留空不会覆盖已有四季氛围文案。'
            : '可写危险提示、装备需求、深处传闻等，自定义展示备用。';
    }
    const seasonNames = { spring: '春季', summer: '夏季', autumn: '秋季', winter: '冬季' };
    const suffixMap = { spring: 'Spring', summer: 'Summer', autumn: 'Autumn', winter: 'Winter' };
    ALL_SEASONS.forEach(season => {
        const el = document.getElementById('locDiveAmb' + suffixMap[season]);
        if (!el) return;
        const existingCount = countLinesForSeason(loc?.dive_ambience || {}, season);
        el.placeholder = loc
            ? (existingCount
                ? `${seasonNames[season]}原本有 ${existingCount} 条潜水文案，已显示在这里，可直接编辑。`
                : `${seasonNames[season]}暂无原始潜水文案，可在这里新增（一行一句）。${hasAnyAmbience ? '其他季节已有文案。' : ''}`)
            : `${seasonNames[season]}潜水文案（一行一句，dive 开始时随机出现）。`;
    });
}

function switchLocationFormPage(mode) {
    const target = mode === 'dive' ? 'dive' : 'surface';
    document.querySelectorAll('.location-mode-tab').forEach(tab => tab.classList.toggle('active', tab.dataset.locMode === target));
    const surfacePage = document.getElementById('locPageSurface');
    const divePage = document.getElementById('locPageDive');
    if (surfacePage) {
        surfacePage.classList.toggle('active', target === 'surface');
        surfacePage.style.display = target === 'surface' ? 'block' : 'none';
    }
    if (divePage) {
        divePage.classList.toggle('active', target === 'dive');
        divePage.style.display = target === 'dive' ? 'block' : 'none';
    }
}

function toggleLocationFish(fishId, mode = 'surface') {
    const selectedSet = mode === 'dive' ? locDiveSelectedFishIds : locSelectedFishIds;
    const otherSet = mode === 'dive' ? locSelectedFishIds : locDiveSelectedFishIds;
    if (selectedSet.has(fishId)) selectedSet.delete(fishId);
    else {
        selectedSet.add(fishId);
        otherSet.delete(fishId);
    }
    renderLocationFishPicker('surface');
    renderLocationFishPicker('dive');
}

function removeLocationFish(fishId, mode = 'surface') {
    (mode === 'dive' ? locDiveSelectedFishIds : locSelectedFishIds).delete(fishId);
    renderLocationFishPicker(mode);
}

function renderGlobalFishNote(mode) {
    const filtered = locGlobalFish.filter(f => mode === 'dive' ? f.dive : !f.dive);
    if (!filtered.length) return '';
    return `<div class="global-fish-note">
        <strong>全域自动出现，不能从单个地点删除：</strong>${filtered.map(f => escapeHtml(f.name)).join('、')}
        <br><span>这些鱼的出没地点包含 all，所以每个新地点都会看到它们。要移除请去「渔获编辑」把鱼的出没地点 all 改掉，或删除/编辑该鱼种。</span>
    </div>`;
}

function locationFishModeHint(mode, selectedCount, globalCount) {
    const title = mode === 'dive' ? '深水鱼池（潜水玩法）' : '水面鱼池';
    const body = mode === 'dive'
        ? '这里选择 dive 潜水远征会遇到的鱼。加入深水会把该鱼标记为「潜水专属」，水面抛竿不会出现。'
        : '这里选择 cast 水面抛竿会遇到的鱼。加入水面会把该鱼标记为非潜水鱼。';
    return `<div class="location-fish-mode-hint">
        <strong>${title}</strong><span>${body}</span>
        <em>已选 ${selectedCount} 种${globalCount ? `｜另有全域 ${globalCount} 种自动出现` : ''}</em>
    </div>`;
}

function renderLocationFishPicker(mode = 'surface') {
    const selectedEl = document.getElementById(mode === 'dive' ? 'locDiveSelectedFishList' : 'locSelectedFishList');
    const resultsEl = document.getElementById(mode === 'dive' ? 'locDiveFishSearchResults' : 'locFishSearchResults');
    const searchEl = document.getElementById(mode === 'dive' ? 'locDiveFishSearchInput' : 'locFishSearchInput');
    const selectedSet = mode === 'dive' ? locDiveSelectedFishIds : locSelectedFishIds;
    if (!selectedEl || !resultsEl) return;

    const selected = Array.from(selectedSet).map(getFishById).filter(Boolean);
    const globalForMode = locGlobalFish.filter(f => mode === 'dive' ? f.dive : !f.dive);
    selectedEl.innerHTML = locationFishModeHint(mode, selected.length, globalForMode.length) + (selected.length ? selected.map(fish => `
        <span class="selected-fish-chip">
            <span>${escapeHtml(fish.name)}</span>
            <small>${escapeHtml(fish.id)}</small>
            <button type="button" onclick="removeLocationFish('${fish.id}', '${mode}')">×</button>
        </span>
    `).join('') : `<span class="text-muted">还没选择${mode === 'dive' ? '深水' : '水面'}鱼类</span>`) + renderGlobalFishNote(mode);

    const keyword = (searchEl?.value || '').trim().toLowerCase();
    const matched = (keyword
        ? allFishData.filter(fish => fish.name.toLowerCase().includes(keyword) || fish.id.toLowerCase().includes(keyword))
        : allFishData
    )
        .filter(fish => !fish.locations.includes('all'))
        .sort((a, b) => {
            const aMatch = (mode === 'dive') === !!a.dive;
            const bMatch = (mode === 'dive') === !!b.dive;
            if (aMatch !== bMatch) return aMatch ? -1 : 1;
            return (RARITY_LABELS[a.rarity] || a.rarity).localeCompare(RARITY_LABELS[b.rarity] || b.rarity, 'zh-CN') || a.name.localeCompare(b.name, 'zh-CN');
        })
        .slice(0, 30);

    resultsEl.innerHTML = matched.map(fish => {
        const selected = selectedSet.has(fish.id);
        const naturalMode = fish.dive ? '深水鱼' : '水面鱼';
        const willConvert = (mode === 'dive') !== !!fish.dive;
        return `
            <div class="location-fish-result ${selected ? 'selected' : ''} ${willConvert ? 'will-convert' : ''}" onclick="toggleLocationFish('${fish.id}', '${mode}')">
                <div class="location-fish-result-main">
                    <strong>${escapeHtml(fish.name)}</strong>
                    <span>${escapeHtml(fish.id)} · 当前${naturalMode}${willConvert ? ` · 点击后改为${mode === 'dive' ? '深水鱼' : '水面鱼'}` : ''}</span>
                </div>
                <div class="location-fish-result-meta">
                    <span class="rarity-badge rarity-${fish.rarity}">${RARITY_LABELS[fish.rarity] || fish.rarity}</span>
                    <span class="location-fish-check">${selected ? '已加入' : '点击加入'}</span>
                </div>
            </div>
        `;
    }).join('') || '<div class="location-fish-empty">没有找到匹配鱼类</div>';
}

async function syncLocationFish(locationId) {
    const desired = new Map();
    locSelectedFishIds.forEach(id => desired.set(id, false));
    locDiveSelectedFishIds.forEach(id => desired.set(id, true));
    const original = new Set([...locOriginalFishIds, ...locDiveOriginalFishIds]);
    const toRemove = Array.from(original).filter(id => !desired.has(id));
    const errors = [];

    for (const [fishId, isDive] of desired.entries()) {
        const fish = getFishById(fishId);
        const res = await fetch(`${API}/api/fish/add_to_location`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ fish_id: fishId, location_id: locationId, dive: isDive })
        });
        try { await parseApiResponse(res); if (fish) fish.dive = isDive; }
        catch (e) { errors.push(`同步 ${fish?.name || fishId} 失败：${e.message}`); }
    }

    for (const fishId of toRemove) {
        const fish = getFishById(fishId);
        const res = await fetch(`${API}/api/fish/remove_from_location`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ fish_id: fishId, location_id: locationId })
        });
        try { await parseApiResponse(res); }
        catch (e) { errors.push(`移除 ${fish?.name || fishId} 失败：${e.message}`); }
    }

    if (errors.length) throw new Error(errors.join('\n'));
    locOriginalFishIds = new Set(locSelectedFishIds);
    locDiveOriginalFishIds = new Set(locDiveSelectedFishIds);
}

async function submitLocationForm() {
    const mode = document.getElementById('locEditMode').value;
    const payload = {
        id: document.getElementById('locFormId').value || generateId(),
        name: document.getElementById('locFormName').value.trim(),
        unlock_cost: parseInt(document.getElementById('locFormCost').value) || 0,
        description: document.getElementById('locFormDesc').value.trim(),
        available_seasons: getSelectedChips('locFormSeasonsContainer'),
        dive_enabled: document.getElementById('locDiveEnabled').classList.contains('active'),
        dive_description: document.getElementById('locDiveDesc').value.trim(),
        dive_available_seasons: getSelectedChips('locDiveSeasonsContainer'),
        dive_ambience: {
            spring: textToLines(document.getElementById('locDiveAmbSpring').value),
            summer: textToLines(document.getElementById('locDiveAmbSummer').value),
            autumn: textToLines(document.getElementById('locDiveAmbAutumn').value),
            winter: textToLines(document.getElementById('locDiveAmbWinter').value),
        },
        dive_notes: document.getElementById('locDiveNotes').value.trim(),
    };
    if (!payload.name) { alert('请填写地点名称'); return; }

    const url = mode === 'add' ? `${API}/api/locations/add` : `${API}/api/locations/update`;
    const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });
    let data;
    try {
        data = await parseApiResponse(res);
    } catch (e) {
        alert(e.message);
        return;
    }
    closeModal('addLocationModal');
    try {
        await syncLocationFish(payload.id);
    } catch (e) {
        alert(`地点已保存，但鱼类同步有问题：\n${e.message}`);
    }
    highlightLocationId = payload.id;
    loadLocations();
    notify(`${mode === 'add' ? '已添加地点' : '已保存地点'}：${payload.name}\n水面 ${locSelectedFishIds.size} 种｜深水 ${locDiveSelectedFishIds.size} 种，MCP 的 goto/cast/dive/look 已可使用。`);
}

async function deleteLocation(locId) {
    const loc = allLocations.find(l => l.id === locId);
    if (!await customConfirm(`确定删除「${loc?.name || locId}」吗？`)) return;
    const res = await fetch(`${API}/api/locations/delete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: locId })
    });
    try {
        await parseApiResponse(res);
    } catch (e) {
        alert(e.message);
        return;
    }
    notify(`已删除地点：${loc?.name || locId}`);
    loadLocations();
}

// ============================================================
// Fish List
// ============================================================

async function loadFishList() {
    const res = await fetch(`${API}/api/fish`);
    const data = await res.json();
    allFishData = data.fish;

    // Also ensure we have locations
    if (allLocations.length === 0) {
        const lr = await fetch(`${API}/api/locations`);
        const ld = await lr.json();
        allLocations = ld.locations;
    }

    const rarity = document.getElementById('fishRarityFilter').value;
    const search = document.getElementById('fishSearchInput').value.toLowerCase();

    let filtered = allFishData;
    if (rarity) filtered = filtered.filter(f => f.rarity === rarity);
    if (search) filtered = filtered.filter(f => f.name.toLowerCase().includes(search) || f.id.toLowerCase().includes(search));

    const locNames = {};
    allLocations.forEach(l => locNames[l.id] = l.name);

    const tbody = document.getElementById('fishTableBody');
    tbody.innerHTML = filtered.slice(0, 100).map(fish => {
        const locs = fish.locations.slice(0, 2).map(l => locNames[l] || l).join(', ') + (fish.locations.length > 2 ? '...' : '');
        const seasons = fish.seasons.map(s => SEASON_LABELS[s] || s).join(' ');
        return `
            <tr style="${fish.id === highlightFishId ? 'outline:2px solid var(--accent);' : ''}">
                <td><strong>${escapeHtml(fish.name)}</strong>${fish.dive ? ' <span class="location-tag">潜水</span>' : ''}</td>
                <td><span class="rarity-badge rarity-${fish.rarity}">${RARITY_LABELS[fish.rarity]}</span></td>
                <td>${fish.base_value}</td>
                <td style="font-size:11px;">${escapeHtml(locs)}</td>
                <td>${seasons}</td>
                <td>
                    <div class="action-btns">
                        <button class="btn-icon" onclick="editFish('${fish.id}')" title="编辑"><i data-lucide="pencil"></i></button>
                        <button class="btn-icon" onclick="deleteFish('${fish.id}')" title="删除"><i data-lucide="trash-2"></i></button>
                    </div>
                </td>
            </tr>
        `;
    }).join('');

    lucide.createIcons();
}

async function showAddFishModal() {
    if (allLocations.length === 0) {
        const res = await fetch(`${API}/api/locations`);
        const data = await res.json();
        allLocations = data.locations;
    }
    document.getElementById('fishEditMode').value = 'add';
    document.getElementById('fishModalTitle').textContent = '添加鱼种';
    document.getElementById('fishFormId').value = '';
    document.getElementById('fishFormName').value = '';
    document.getElementById('fishFormRarity').value = 'common';
    document.getElementById('fishFormValue').value = '10';
    document.getElementById('fishFormDesc').value = '';
    document.getElementById('fishFormCaptureFeel').value = '';
    document.getElementById('fishFormDive').classList.remove('active');
    toggleFishDiveForm(false);

    const locOpts = allLocations.map(l => ({value: l.id, label: l.name}));
    renderChips('fishFormLocsContainer', locOpts, []);
    renderChips('fishFormSeasonsContainer', [{value:'all',label:'全部'},...ALL_SEASONS.map(s=>({value:s,label:SEASON_LABELS[s]}))], ['all']);
    renderChips('fishFormTagsContainer', ALL_TAGS.map(t => ({value: t, label: TAG_LABELS[t] || t})), []);

    document.getElementById('addFishModal').style.display = 'flex';
    lucide.createIcons();
}

function editFish(fishId) {
    const fish = allFishData.find(f => f.id === fishId);
    if (!fish) return;

    document.getElementById('fishEditMode').value = 'edit';
    document.getElementById('fishModalTitle').textContent = '编辑鱼种';
    document.getElementById('fishFormId').value = fish.id;
    document.getElementById('fishFormName').value = fish.name;
    document.getElementById('fishFormRarity').value = fish.rarity;
    document.getElementById('fishFormValue').value = fish.base_value;
    document.getElementById('fishFormDesc').value = fish.description || '';
    document.getElementById('fishFormCaptureFeel').value = fish.capture_feel || '';
    document.getElementById('fishFormDive').classList.toggle('active', !!fish.dive);
    toggleFishDiveForm(false);

    const locOpts = allLocations.map(l => ({value: l.id, label: l.name}));
    renderChips('fishFormLocsContainer', locOpts, fish.locations);
    renderChips('fishFormSeasonsContainer', [{value:'all',label:'全部'},...ALL_SEASONS.map(s=>({value:s,label:SEASON_LABELS[s]}))], fish.seasons);
    renderChips('fishFormTagsContainer', ALL_TAGS.map(t => ({value: t, label: TAG_LABELS[t] || t})), fish.tags);

    document.getElementById('addFishModal').style.display = 'flex';
    lucide.createIcons();
}

function toggleFishDiveForm(toggle = true) {
    const diveToggle = document.getElementById('fishFormDive');
    if (toggle) diveToggle.classList.toggle('active');
    const isDive = diveToggle.classList.contains('active');
    const feelGroup = document.getElementById('fishCaptureFeelGroup');
    if (feelGroup) feelGroup.style.display = isDive ? '' : 'none';
}

async function submitFishForm() {
    const mode = document.getElementById('fishEditMode').value;
    const payload = {
        id: document.getElementById('fishFormId').value || generateId(),
        name: document.getElementById('fishFormName').value.trim(),
        rarity: document.getElementById('fishFormRarity').value,
        base_value: parseInt(document.getElementById('fishFormValue').value) || 10,
        description: document.getElementById('fishFormDesc').value.trim(),
        locations: getSelectedChips('fishFormLocsContainer'),
        seasons: getSelectedChips('fishFormSeasonsContainer'),
        tags: getSelectedChips('fishFormTagsContainer'),
        dive: document.getElementById('fishFormDive').classList.contains('active'),
        capture_feel: document.getElementById('fishFormCaptureFeel').value.trim(),
    };

    if (payload.dive && !payload.tags.includes('underwater')) payload.tags.push('underwater');

    if (!payload.name) { alert('请填写鱼名'); return; }

    const url = mode === 'add' ? `${API}/api/fish/add` : `${API}/api/fish/update`;
    const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });
    let data;
    try {
        data = await parseApiResponse(res);
    } catch (e) {
        alert(e.message);
        return;
    }

    closeModal('addFishModal');
    highlightFishId = payload.id;
    loadFishList();
    notify(`${mode === 'add' ? '已添加鱼种' : '已保存鱼种'}：${payload.name}\n${payload.dive ? '深水 dive' : '水面 cast'}/look/encyclopedia 已可使用。`);
}

async function deleteFish(fishId) {
    const fish = allFishData.find(f => f.id === fishId);
    if (!await customConfirm(`确定删除「${fish?.name || fishId}」吗？`)) return;
    const res = await fetch(`${API}/api/fish/delete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: fishId })
    });
    try {
        await parseApiResponse(res);
    } catch (e) {
        alert(e.message);
        return;
    }
    notify(`已删除鱼种：${fish?.name || fishId}`);
    loadFishList();
}

function closeModal(id) {
    document.getElementById(id).style.display = 'none';
}

// ============================================================
// Probability
// ============================================================

async function initProbability() {
    const res = await fetch(`${API}/api/locations`);
    const data = await res.json();
    allLocations = data.locations;
    const current = document.getElementById('probLocation').value;
    const menu = document.getElementById('probLocationMenu');
    menu.innerHTML = allLocations.map(l => `
        <div class="custom-dropdown-item ${l.id === current ? 'active' : ''}" data-value="${l.id}" onclick="selectProbLocation('${l.id}')">${escapeHtml(l.name)}</div>
    `).join('');
    // Auto-select first if none selected
    if (!current && allLocations.length > 0) {
        selectProbLocation(allLocations[0].id);
    } else if (current) {
        loadProbability();
    }
}

function selectProbLocation(locId) {
    document.getElementById('probLocation').value = locId;
    const loc = allLocations.find(l => l.id === locId);
    document.getElementById('probLocationLabel').textContent = loc ? loc.name : locId;
    document.querySelectorAll('#probLocationMenu .custom-dropdown-item').forEach(item => {
        item.classList.toggle('active', item.dataset.value === locId);
    });
    document.getElementById('probLocationDropdown').classList.remove('open');
    loadProbability();
}

function selectProbSeason(season) {
    const labels = {spring:'春', summer:'夏', autumn:'秋', winter:'冬'};
    document.getElementById('probSeason').value = season;
    document.getElementById('probSeasonLabel').textContent = labels[season] || season;
    document.querySelectorAll('#probSeasonDropdown .custom-dropdown-item').forEach(item => {
        item.classList.toggle('active', item.dataset.value === season);
    });
    document.getElementById('probSeasonDropdown').classList.remove('open');
    loadProbability();
}

function selectProbabilityMode(mode) {
    probabilityMode = mode === 'dive' ? 'dive' : 'cast';
    document.getElementById('probMode').value = probabilityMode;
    document.getElementById('probModeCast').classList.toggle('active', probabilityMode === 'cast');
    document.getElementById('probModeDive').classList.toggle('active', probabilityMode === 'dive');
    loadProbability();
}

async function loadProbability() {
    const loc = document.getElementById('probLocation').value;
    const season = document.getElementById('probSeason').value;
    const mode = document.getElementById('probMode')?.value || probabilityMode || 'cast';
    if (!loc) return;

    const res = await fetch(`${API}/api/probability/${loc}?season=${season}&mode=${mode}`);
    const data = await res.json();

    if (!data.fish || data.fish.length === 0) {
        const label = mode === 'dive' ? '深水' : '水面';
        document.getElementById('probChart').innerHTML = `<p class="text-muted">这个地点本季没有${label}鱼池数据。</p>`;
        document.getElementById('probList').innerHTML = '';
        return;
    }

    const maxProb = Math.max(...data.fish.map(f => f.probability), 1);
    document.getElementById('probChart').innerHTML = data.fish.slice(0, 25).map(f => `
        <div class="prob-bar-row">
            <div class="prob-bar-label" title="${f.name}">${f.name}</div>
            <div class="prob-bar-track">
                <div class="prob-bar-fill" style="width: ${(f.probability / maxProb * 100).toFixed(1)}%"></div>
            </div>
            <div class="prob-bar-value">${f.probability}%</div>
        </div>
    `).join('');

    document.getElementById('probList').innerHTML = data.fish.map(f => `
        <div class="prob-list-item">
            <span class="prob-list-item-name">
                <span class="rarity-badge rarity-${f.rarity}">${RARITY_LABELS[f.rarity]}</span>
                ${escapeHtml(f.name)}
            </span>
            <span class="prob-list-item-pct">${f.probability}%</span>
        </div>
    `).join('');
}

// ============================================================
// Tool Descriptions
// ============================================================

const DEFAULT_PLAY_DESC = `文字钓鱼游戏。你是玩家，通过 command 参数传入游戏指令来操作。支持用 ; 串联多条指令一次执行（最多8条）。

常用指令：
- help 看规则
- status 看当前状态（点数/地点/季节/图鉴进度）
- shop 看鱼饵商店
- buy <饵id> [数量] 买饵（如 buy basic_worm 10）
- cast [饵id] [次数] [stop=new,rare,event] 抛竿钓鱼
  · cast 10 连钓10竿
  · cast 10 stop=rare 连钓10竿，钓到稀有及以上就停
  · cast glow_bait 5 用夜光饵钓5竿
- goto 列出所有钓点 / goto <地点id> 前往某地
- sell all 卖掉所有渔获换点数
- inventory 查看背包（鱼/物品/宝箱）
- open <宝箱uid> 打开宝箱
- encyclopedia 查看图鉴收集进度
- look <名称或id> 查看鱼/地点/物品详情
- dive [氧气瓶数] [stop=...] 开始潜水远征
- buy oxygen 5 买氧气瓶（潜水用）
- surface 潜水中主动上浮

组合示例：
- buy basic_worm 10; cast 10（买饵再钓一条龙）
- goto reed_river; cast 8 stop=new（换地点再钓到新种就停）

每次返回末尾有 📊 状态栏 JSON，看它即可掌握当前状态。`;

const DEFAULT_NEW_GAME_DESC = `重开一局钓鱼游戏。可选传入 seed 整数作为随机种子，相同种子+相同指令序列=完全相同结果。不传则用默认种子。`;

async function loadToolDescs() {
    const res = await fetch(`${API}/api/tool_descriptions`);
    const data = await res.json();
    const descs = data.tool_descriptions || {};
    document.getElementById('descPlayFishing').value = descs.play_fishing || DEFAULT_PLAY_DESC;
    document.getElementById('descNewGame').value = descs.new_fishing_game || DEFAULT_NEW_GAME_DESC;
}

async function saveToolDescs() {
    const play = document.getElementById('descPlayFishing').value;
    const newGame = document.getElementById('descNewGame').value;
    const res = await fetch(`${API}/api/tool_descriptions/update`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ play_fishing: play, new_fishing_game: newGame })
    });
    const data = await res.json();
    if (data.ok) customAlert('工具描述已保存！Claude 下次连接时将使用新描述。');
}

// ============================================================
// WebSocket Logs
// ============================================================

function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/logs`;
    try {
        ws = new WebSocket(wsUrl);
        ws.onopen = () => {
            document.getElementById('mcpStatus').style.background = 'var(--accent)';
            document.getElementById('mcpStatus').style.boxShadow = '0 0 10px rgba(184, 164, 200, 0.65)';
            document.getElementById('mcpStatusText').textContent = 'MCP 已连接';
        };
        ws.onmessage = (event) => appendLog(JSON.parse(event.data));
        ws.onclose = () => {
            document.getElementById('mcpStatus').style.background = '#d47070';
            document.getElementById('mcpStatusText').textContent = 'MCP 断开';
            setTimeout(connectWebSocket, 3000);
        };
        ws.onerror = () => ws.close();
    } catch (e) { setTimeout(connectWebSocket, 3000); }
}

function appendLog(entry) {
    const container = document.getElementById('logContainer');
    const placeholder = container.querySelector('.text-muted');
    if (placeholder) placeholder.remove();

    const div = document.createElement('div');
    div.className = 'log-entry';
    div.innerHTML = `
        <div class="log-entry-time">${entry.time}</div>
        <div class="log-entry-cmd">${escapeHtml(entry.command)}</div>
        <div class="log-entry-result">${escapeHtml(entry.result)}</div>
    `;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
    while (container.children.length > 100) container.removeChild(container.firstChild);
}

// ============================================================
// Import / Export
// ============================================================

async function exportData() {
    const resultEl = document.getElementById('exportResult');
    resultEl.style.display = 'block';
    resultEl.textContent = '正在导出...';

    try {
        const res = await fetch(`${API}/api/export`);
        const data = await res.json();
        if (!data.ok) throw new Error(data.error || '导出失败');

        // Download as file
        const blob = new Blob([data.data], { type: 'application/octet-stream' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `fishing-save-${new Date().toISOString().slice(0,10)}.fish-save`;
        a.click();
        URL.revokeObjectURL(url);

        const ratio = ((data.size_compressed / data.size_original) * 100).toFixed(1);
        resultEl.textContent = `导出成功！原始 ${(data.size_original / 1024).toFixed(1)}KB → 压缩后 ${(data.size_compressed / 1024).toFixed(1)}KB（${ratio}%）`;
    } catch (e) {
        resultEl.textContent = '导出失败：' + e.message;
    }
}

async function importData(fileInput) {
    const resultEl = document.getElementById('importResult');
    resultEl.style.display = 'block';

    const file = fileInput.files[0];
    if (!file) return;

    resultEl.textContent = '正在读取文件...';

    try {
        const text = await file.text();
        if (!text.trim()) throw new Error('文件为空');

        if (!await customConfirm('导入将覆盖当前所有配置和游戏进度，确定继续？')) {
            resultEl.textContent = '已取消导入';
            fileInput.value = '';
            return;
        }

        resultEl.textContent = '正在导入...';
        const res = await fetch(`${API}/api/import`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ data: text.trim() })
        });
        const data = await res.json();
        if (!data.ok) throw new Error(data.error || '导入失败');

        resultEl.textContent = '导入成功！页面将在 2 秒后刷新...';
        setTimeout(() => location.reload(), 2000);
    } catch (e) {
        resultEl.textContent = '导入失败：' + e.message;
    }

    fileInput.value = '';
}
