// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------
let token = localStorage.getItem("taskboard_token") || null;
let username = localStorage.getItem("taskboard_username") || null;
let tasks = [];
let draggedTaskId = null;

// ---------------------------------------------------------------------------
// Element references
// ---------------------------------------------------------------------------
const authScreen = document.getElementById("auth-screen");
const appScreen = document.getElementById("app-screen");
const authError = document.getElementById("auth-error");

const loginForm = document.getElementById("login-form");
const registerForm = document.getElementById("register-form");
const showRegister = document.getElementById("show-register");
const showLogin = document.getElementById("show-login");

const usernameDisplay = document.getElementById("username-display");
const logoutBtn = document.getElementById("logout-btn");
const newTaskBtn = document.getElementById("new-task-btn");

const taskModal = document.getElementById("task-modal");
const taskForm = document.getElementById("task-form");
const modalTitle = document.getElementById("modal-title");
const cancelTaskBtn = document.getElementById("cancel-task-btn");
const deleteTaskBtn = document.getElementById("delete-task-btn");

// ---------------------------------------------------------------------------
// API helper
// ---------------------------------------------------------------------------
async function api(path, options = {}) {
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(path, { ...options, headers });
  const data = await res.json().catch(() => ({}));

  if (!res.ok) {
    throw new Error(data.error || "Something went wrong");
  }
  return data;
}

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------
function showApp() {
  authScreen.classList.add("hidden");
  appScreen.classList.remove("hidden");
  usernameDisplay.textContent = username;
  loadTasks();
}

function showAuth() {
  appScreen.classList.add("hidden");
  authScreen.classList.remove("hidden");
}

showRegister.addEventListener("click", () => {
  loginForm.classList.add("hidden");
  registerForm.classList.remove("hidden");
  showRegister.classList.add("hidden");
  showLogin.classList.remove("hidden");
  authError.textContent = "";
});

showLogin.addEventListener("click", () => {
  registerForm.classList.add("hidden");
  loginForm.classList.remove("hidden");
  showLogin.classList.add("hidden");
  showRegister.classList.remove("hidden");
  authError.textContent = "";
});

loginForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  authError.textContent = "";
  const u = document.getElementById("login-username").value.trim();
  const p = document.getElementById("login-password").value;

  try {
    const data = await api("/api/login", { method: "POST", body: JSON.stringify({ username: u, password: p }) });
    token = data.token;
    username = data.username;
    localStorage.setItem("taskboard_token", token);
    localStorage.setItem("taskboard_username", username);
    showApp();
  } catch (err) {
    authError.textContent = err.message;
  }
});

registerForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  authError.textContent = "";
  const u = document.getElementById("register-username").value.trim();
  const p = document.getElementById("register-password").value;

  try {
    const data = await api("/api/register", { method: "POST", body: JSON.stringify({ username: u, password: p }) });
    token = data.token;
    username = data.username;
    localStorage.setItem("taskboard_token", token);
    localStorage.setItem("taskboard_username", username);
    showApp();
  } catch (err) {
    authError.textContent = err.message;
  }
});

logoutBtn.addEventListener("click", () => {
  token = null;
  username = null;
  localStorage.removeItem("taskboard_token");
  localStorage.removeItem("taskboard_username");
  showAuth();
});

// ---------------------------------------------------------------------------
// Task rendering
// ---------------------------------------------------------------------------
async function loadTasks() {
  try {
    tasks = await api("/api/tasks");
    renderBoard();
  } catch (err) {
    if (err.message.includes("Token") || err.message.includes("Authorization")) {
      logoutBtn.click();
    }
  }
}

function renderBoard() {
  const columns = { todo: [], in_progress: [], done: [] };
  tasks.forEach((t) => columns[t.status].push(t));

  Object.keys(columns).forEach((status) => {
    const list = document.getElementById(`list-${status}`);
    list.innerHTML = "";
    document.getElementById(`count-${status}`).textContent = columns[status].length;

    columns[status].forEach((task) => {
      list.appendChild(renderTaskCard(task));
    });
  });
}

function renderTaskCard(task) {
  const card = document.createElement("div");
  card.className = `task-card priority-${task.priority}`;
  card.draggable = true;
  card.dataset.taskId = task.id;

  const dueText = task.due_date ? new Date(task.due_date + "T00:00:00").toLocaleDateString() : "";

  card.innerHTML = `
    <div class="task-card-title">${escapeHtml(task.title)}</div>
    ${task.description ? `<div class="task-card-desc">${escapeHtml(task.description)}</div>` : ""}
    <div class="task-card-meta">
      <span>${task.priority}</span>
      <span>${dueText}</span>
    </div>
  `;

  card.addEventListener("click", () => openTaskModal(task));

  card.addEventListener("dragstart", () => {
    draggedTaskId = task.id;
    card.classList.add("dragging");
  });
  card.addEventListener("dragend", () => card.classList.remove("dragging"));

  return card;
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

// ---------------------------------------------------------------------------
// Drag and drop between columns
// ---------------------------------------------------------------------------
document.querySelectorAll(".task-list").forEach((list) => {
  list.addEventListener("dragover", (e) => {
    e.preventDefault();
    list.classList.add("drag-over");
  });
  list.addEventListener("dragleave", () => list.classList.remove("drag-over"));

  list.addEventListener("drop", async (e) => {
    e.preventDefault();
    list.classList.remove("drag-over");
    const newStatus = list.parentElement.dataset.status;
    if (draggedTaskId == null) return;

    try {
      await api(`/api/tasks/${draggedTaskId}`, {
        method: "PUT",
        body: JSON.stringify({ status: newStatus }),
      });
      await loadTasks();
    } catch (err) {
      alert(err.message);
    }
    draggedTaskId = null;
  });
});

// ---------------------------------------------------------------------------
// Task modal (create / edit / delete)
// ---------------------------------------------------------------------------
function openTaskModal(task = null) {
  taskForm.reset();
  document.getElementById("task-id").value = task ? task.id : "";
  modalTitle.textContent = task ? "Edit Task" : "New Task";
  deleteTaskBtn.classList.toggle("hidden", !task);

  if (task) {
    document.getElementById("task-title").value = task.title;
    document.getElementById("task-description").value = task.description || "";
    document.getElementById("task-priority").value = task.priority;
    document.getElementById("task-due-date").value = task.due_date || "";
  }

  taskModal.classList.remove("hidden");
}

function closeTaskModal() {
  taskModal.classList.add("hidden");
}

newTaskBtn.addEventListener("click", () => openTaskModal());
cancelTaskBtn.addEventListener("click", closeTaskModal);
taskModal.addEventListener("click", (e) => {
  if (e.target === taskModal) closeTaskModal();
});

taskForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const id = document.getElementById("task-id").value;

  const payload = {
    title: document.getElementById("task-title").value.trim(),
    description: document.getElementById("task-description").value.trim(),
    priority: document.getElementById("task-priority").value,
    due_date: document.getElementById("task-due-date").value || null,
  };

  try {
    if (id) {
      await api(`/api/tasks/${id}`, { method: "PUT", body: JSON.stringify(payload) });
    } else {
      payload.status = "todo";
      await api("/api/tasks", { method: "POST", body: JSON.stringify(payload) });
    }
    closeTaskModal();
    await loadTasks();
  } catch (err) {
    alert(err.message);
  }
});

deleteTaskBtn.addEventListener("click", async () => {
  const id = document.getElementById("task-id").value;
  if (!id || !confirm("Delete this task?")) return;

  try {
    await api(`/api/tasks/${id}`, { method: "DELETE" });
    closeTaskModal();
    await loadTasks();
  } catch (err) {
    alert(err.message);
  }
});

// ---------------------------------------------------------------------------
// Init
// ---------------------------------------------------------------------------
if (token && username) {
  showApp();
} else {
  showAuth();
}
