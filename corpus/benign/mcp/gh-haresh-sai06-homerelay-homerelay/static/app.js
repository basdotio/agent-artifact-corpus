'use strict';
let board = {members: [], tasks: [], history: []};
let filter = 'open';
let accessToken = '';
let summary = '';
const $ = id => document.getElementById(id);
const notice = message => { $('notice').textContent = message; };

async function api(path, body) {
  const response = await fetch('/api' + path, {
    method: body === undefined ? 'GET' : 'POST',
    headers: {'Content-Type': 'application/json', ...(accessToken ? {Authorization: 'Bearer ' + accessToken} : {})},
    ...(body === undefined ? {} : {body: JSON.stringify(body)})
  });
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Please check the form values.');
  return data;
}
function el(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}
function date(value) { return new Date(value).toLocaleString([], {month:'short', day:'numeric', hour:'numeric', minute:'2-digit'}); }
function memberOptions(select, exclude) {
  const previous = select.value;
  select.replaceChildren();
  for (const member of board.members.filter(m => m.id !== exclude)) {
    const option = el('option', member.name); option.value = member.id; select.append(option);
  }
  if (board.members.some(m => m.id === previous && m.id !== exclude)) select.value = previous;
}
function button(text, action, secondary = false) {
  const b = el('button', text, secondary ? 'secondary' : '');
  b.type = 'button'; b.addEventListener('click', () => run(action)); return b;
}
async function run(action) {
  try { notice(''); await action(); } catch (error) { notice(error.message); }
}
async function confirm(text) {
  $('confirm-text').textContent = text;
  $('confirm').returnValue = 'cancel';
  $('confirm').showModal();
  return new Promise(resolve => $('confirm').addEventListener('close', () => resolve($('confirm').returnValue === 'confirm'), {once:true}));
}
async function change(task, action, target) {
  const actor = board.members.find(m => m.id === $('actor').value);
  const recipient = board.members.find(m => m.id === target);
  const label = action === 'propose' ? `Propose handing “${task.title}” from ${actor.name} to ${recipient.name}? It remains with ${actor.name} until accepted.` : `${actor.name}: ${action} “${task.title}”?`;
  if (!await confirm(label)) return;
  await api('/tasks/' + task.id + '/change', {actor_id:actor.id, version:task.version, action, target_id:target || null});
  await load();
}
function renderTasks() {
  const actor = $('actor').value;
  const tasks = board.tasks.filter(t => filter === 'done' ? t.status === 'done' : t.status === 'open' && (filter === 'mine' ? t.owner_id === actor : filter === 'handoffs' ? t.proposed_owner === actor : true));
  $('tasks').replaceChildren();
  $('count').textContent = board.tasks.filter(t => t.status === 'open').length + ' open';
  if (!tasks.length) $('tasks').append(el('div', board.members.length ? 'Nothing here right now. A little breathing room.' : 'Add your people, then give the small things a place to land.', 'empty'));
  for (const task of tasks) {
    const card = el('article', undefined, 'task');
    const top = el('div', undefined, 'task-top'); top.append(el('h3',task.title), el('span', ['','Flexible','Normal','Important'][task.priority], 'pill')); card.append(top);
    const overdue = task.status === 'open' && new Date(task.due_at) < new Date();
    card.append(el('p', `${task.owner_name} · ${date(task.due_at)}${overdue ? ' · Overdue' : ''}${task.status === 'done' ? ' · Completed' : ''}`, 'meta' + (overdue ? ' overdue' : '')));
    if (task.proposed_owner) card.append(el('div', `${task.owner_name} asked ${task.proposed_owner_name} to take this. Waiting for a response.`, 'pending'));
    const actions = el('div', undefined, 'actions');
    if (task.status === 'open' && actor === task.proposed_owner) {
      actions.append(button('Accept handoff', () => change(task,'accept')), button('Decline', () => change(task,'decline'),true));
    }
    if (task.status === 'open' && actor === task.owner_id) {
      actions.append(button('Mark complete', () => change(task,'complete')));
      if (board.members.length > 1) {
        const select = el('select'); select.setAttribute('aria-label', 'Handoff recipient for ' + task.title); memberOptions(select,actor);
        actions.append(select, button('Ask to hand off', () => change(task,'propose',select.value),true));
      }
    }
    card.append(actions); $('tasks').append(card);
  }
}
async function renderBriefing() {
  if (!$('actor').value) { summary = 'Add yourself to get started.'; }
  else summary = (await api('/briefing/' + $('actor').value)).spoken_summary;
  $('briefing').textContent = summary;
}
async function load() {
  board = await api('/board'); memberOptions($('actor')); memberOptions($('owner')); renderTasks();
  $('history').replaceChildren();
  const names = {created:'added a task',propose:'proposed a handoff',accept:'accepted a handoff',decline:'declined a handoff',complete:'completed a task'};
  for (const event of board.history.slice(0,8)) {
    const item = el('li'); const title = board.tasks.find(t => t.id === event.task_id)?.title || 'Task';
    item.append(el('span',`${event.actor_name} ${names[event.action]} · ${title}`));
    const stamp = el('time',date(event.at)); stamp.dateTime = event.at; item.append(stamp); $('history').append(item);
  }
  await renderBriefing();
}
$('member-form').addEventListener('submit', event => {
  event.preventDefault(); run(async () => { const member = await api('/members',{name:$('member').value}); await load(); $('actor').value = member.id; $('member').value = ''; renderTasks(); await renderBriefing(); });
});
$('task-form').addEventListener('submit', event => {
  event.preventDefault(); run(async () => {
    const title = $('title').value.trim(); const owner = board.members.find(m => m.id === $('owner').value);
    if (!owner) throw new Error('Add a household member first.');
    const due = new Date($('due').value).toISOString();
    if (!await confirm(`Add “${title}” for ${owner.name}, due ${date(due)}?`)) return;
    await api('/tasks',{title,owner_id:owner.id,due_at:due,priority:Number($('priority').value),request_id:crypto.randomUUID()});
    $('title').value = ''; await load();
  });
});
$('actor').addEventListener('change', () => run(async () => {renderTasks(); await renderBriefing();}));
$('refresh').addEventListener('click', () => run(load));
$('connect').addEventListener('click', () => run(async () => {accessToken = $('token').value; $('token').value = ''; await load(); notice('Connected.');}));
$('speak').addEventListener('click', () => {
  if (!('speechSynthesis' in window)) { notice('Read aloud is unavailable in this browser. Your written briefing is above.'); return; }
  speechSynthesis.cancel(); speechSynthesis.speak(new SpeechSynthesisUtterance(summary));
});
document.querySelectorAll('[data-filter]').forEach(b => b.addEventListener('click', () => {
  filter = b.dataset.filter; document.querySelectorAll('[data-filter]').forEach(x => x.setAttribute('aria-pressed',String(x === b))); renderTasks();
}));
const initialDue = new Date(Date.now() + 3600000); initialDue.setMinutes(initialDue.getMinutes() - initialDue.getTimezoneOffset());
$('due').value = initialDue.toISOString().slice(0,16);
run(load);
