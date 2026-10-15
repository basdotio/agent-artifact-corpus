const toolList = document.querySelector("#tool-list");
const toolName = document.querySelector("#tool-name");
const toolForm = document.querySelector("#tool-form");
const refreshButton = document.querySelector("#refresh-tools");
const result = document.querySelector("#result");

function showResult(payload) {
  result.textContent = JSON.stringify(payload, null, 2);
}

function renderTools(tools) {
  toolList.innerHTML = "";
  toolName.innerHTML = "";

  for (const tool of tools) {
    const option = document.createElement("option");
    option.value = tool.name;
    option.textContent = tool.name;
    toolName.append(option);

    const item = document.createElement("li");
    item.innerHTML = `<strong>${tool.name}</strong><span>${tool.description ?? ""}</span>`;
    toolList.append(item);
  }
}

async function loadTools() {
  result.textContent = "Loading tools...";

  const response = await fetch("/api/tools");
  const payload = await response.json();

  if (!response.ok) {
    throw new Error(payload.detail ?? "Could not load tools.");
  }

  renderTools(payload.tools);
  result.textContent = "Tools loaded. Pick one and call it.";
}

async function callTool(event) {
  event.preventDefault();

  const body = {
    name: toolName.value,
    arguments: {
      a: Number(document.querySelector("#value-a").value),
      b: Number(document.querySelector("#value-b").value),
    },
  };

  result.textContent = "Calling tool...";

  const response = await fetch("/api/call", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });
  const payload = await response.json();

  if (!response.ok) {
    throw new Error(payload.detail ?? "Tool call failed.");
  }

  showResult(payload);
}

refreshButton.addEventListener("click", async () => {
  try {
    await loadTools();
  } catch (error) {
    result.textContent = error.message;
  }
});

toolForm.addEventListener("submit", async (event) => {
  try {
    await callTool(event);
  } catch (error) {
    result.textContent = error.message;
  }
});

loadTools().catch((error) => {
  result.textContent = error.message;
});
