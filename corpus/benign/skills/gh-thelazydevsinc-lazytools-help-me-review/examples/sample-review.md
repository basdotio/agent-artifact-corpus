# Example: Notely PR #231, shared folder links

Notely is a made-up notes app. PR #231 lets a user share a folder by link. It adds a link endpoint, a permissions check and a new settings screen. Two reviewers split the diff: one reads the server, one reads the screen. The PR author wants a verdict by Wed 7 Oct 2026.

```js
var PREP=[
  {t:'Push the branch and say which commit this guide covers. This guide covers `4f2a9c1`.'},
  {t:'Run the app locally if you want to try the screen:',pre:'npm ci && npm run dev'}
];

var SUMMARY=[
  {title:'What the PR changes',items:[
    {b:'A share link.',t:'`POST /folders/:id/link` makes a link that lets anyone with it read the folder.'},
    {b:'A permissions check.',t:'Every folder read now goes through `canRead()`.'},
    {b:'A settings screen.',t:'Owners can turn a link on, copy it and turn it off.'}
  ]},
  {title:'Left out on purpose',items:[
    {t:'Link expiry. It is tracked in #240, so do not review for it.'}
  ]}
];

var CONTEXT=[
  {h:'Scope',t:'Review the diff against `main`. Files under `generated/` are out of scope.'},
  {h:'How to give a verdict',t:'Mark Looks good only when you read the lines. Mark Question when you cannot tell. A Question is not a rejection.'}
];

var AREAS=[
  {id:'all',icon:'👋',title:'Everyone',mins:10,mine:1},
  {id:'srv',icon:'🖥️',title:'Server',mins:20},
  {id:'ui',icon:'🎨',title:'Settings screen',mins:10}
];

var ITEMS=[
  {id:'r1',n:1,s:'all',title:'The PR does what its description says',iss:'#231',sev:'',
   look:['Read the PR description.','Skim the file list for files the description does not mention.'],
   good:'Every changed file has a reason in the description.',
   raise:'A file changes that the description does not explain.'},
  {id:'r2',n:2,s:'srv',title:'Links cannot be guessed',iss:'#231',ref:'server/link.js:22-48',sev:'blocker',
   look:['Read how the link token is made.','Check its **length** and its source of randomness, for example `crypto.randomBytes`.'],
   good:'The token is at least 128 bits and comes from `crypto.randomBytes`.',
   raise:'The token is short, counted up, or made from the folder id.'},
  {id:'r3',n:3,s:'srv',title:'Every read goes through the check',iss:'#231',ref:'server/folders.js:80-130',sev:'blocker',
   look:['Find every route that reads a folder or its notes.','Check that each one calls `canRead()` before it returns data.'],
   good:'No route returns folder data without `canRead()`.',
   raise:'Any route skips `canRead()`, even a rarely used one.'},
  {id:'r4',n:4,s:'srv',title:'Turning a link off works at once',iss:'',ref:'server/link.js:60-75',sev:'should',
   look:['Read the delete path.','Check that cached links stop working too.'],
   good:'A link stops working on the next request.',
   raise:'A cache can keep an off link alive.'},
  {id:'r5',n:5,s:'ui',title:'The screen explains who can read the link',iss:'',ref:'web/ShareSettings.tsx:12-60',sev:'should',
   look:['Open the settings screen.','Read the text next to the on switch.'],
   good:'It says that anyone with the link can read the folder.',
   raise:'The text hides or softens that fact.'},
  {id:'r6',n:6,s:'ui',title:'Copy button names and spacing',iss:'',ref:'web/ShareSettings.tsx:62-90',sev:'nit',
   look:['Check the button names against the rest of the app.'],
   good:'Names match the rest of the app.',
   raise:'A name or a space looks out of place. This is a nit, so say so.'}
];

var HOWTO=[
  'Your verdicts save on this page as you go. The PR author reads them before the merge.',
  'If you find a security problem, tell the PR author **at once**. Do not wait for the summary.'
];
```
