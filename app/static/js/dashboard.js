let currentReport = null;
let activeTab = "team";
let currentProjectId = null;
let employeesCache = [];
let projectsCache = [];
let generatedBreakdownTasks = [];
let currentView = "dashboard";

const employeeCards = document.getElementById("employeeCards");
const uploadSummary = document.getElementById("uploadSummary");
const dashboardMessage = document.getElementById("dashboardMessage");
const resultContent = document.getElementById("resultContent");
const loadingState = document.getElementById("loadingState");
const projectCards = document.getElementById("projectCards");
const kanbanBoard = document.getElementById("kanbanBoard");
const analyticsPanel = document.getElementById("analyticsPanel");
const workloadPanel = document.getElementById("workloadPanel");
const riskPanel = document.getElementById("riskPanel");
const forecastPanel = document.getElementById("forecastPanel");
const notificationList = document.getElementById("notificationList");
const commentList = document.getElementById("commentList");
const activityTimeline = document.getElementById("activityTimeline");
const fileList = document.getElementById("fileList");
const assistantResponse = document.getElementById("assistantResponse");
const projectDrawer = document.getElementById("projectDrawer");
const projectDrawerBackdrop = document.getElementById("projectDrawerBackdrop");
const projectDrawerContent = document.getElementById("projectDrawerContent");
const projectDrawerTitle = document.getElementById("projectDrawerTitle");
const closeProjectDrawerButton = document.getElementById("closeProjectDrawer");
const teamUtilizationDonut = document.getElementById("teamUtilizationDonut");

function qs(id) {
    return document.getElementById(id);
}

function setMessage(text, type = "info") {
    dashboardMessage.textContent = text;
    dashboardMessage.className = `form-message ${type}`;
}

function initViewNavigation() {
    document.querySelectorAll("[data-view-link]").forEach((link) => {
        link.addEventListener("click", (event) => {
            event.preventDefault();
            switchView(link.dataset.viewLink);
        });
    });
    switchView("dashboard");
}

function switchView(viewName) {
    currentView = viewName || "dashboard";
    document.querySelectorAll("[data-view-link]").forEach((link) => {
        link.classList.toggle("active", link.dataset.viewLink === currentView);
    });
    document.querySelectorAll("[data-view-section]").forEach((section) => {
        const views = section.dataset.viewSection.split(/\s+/);
        section.classList.toggle("view-hidden", !views.includes(currentView));
    });
    document.querySelectorAll("[data-view-group]").forEach((group) => {
        const visibleChildren = Array.from(group.children).some((child) => !child.classList.contains("view-hidden"));
        group.classList.toggle("view-hidden", !visibleChildren);
    });
    window.scrollTo({top: 0, behavior: "smooth"});
}

async function loadEmployees() {
    const params = new URLSearchParams({
        search: qs("searchEmployee").value,
        role: qs("roleFilter").value,
        availability: qs("availabilityFilter").value,
        sort: qs("sortFilter").value,
    });
    const response = await fetch(`/employees?${params.toString()}`);
    const data = await response.json();
    if (!response.ok) {
        employeeCards.innerHTML = `<p class="empty-state">${data.error || "Unable to load employees."}</p>`;
        return;
    }
    employeesCache = data.employees;
    renderEmployees(data.employees);
    refreshRoleOptions(data.roles);
    refreshAssigneeOptions(data.employees);
}

function refreshRoleOptions(roles) {
    const select = qs("roleFilter");
    const selected = select.value;
    const options = ['<option value="">All roles</option>'].concat(
        roles.map((role) => `<option value="${escapeHtml(role)}">${escapeHtml(role)}</option>`)
    );
    select.innerHTML = options.join("");
    select.value = selected;
}

function refreshAssigneeOptions(employees) {
    const select = qs("taskAssignee");
    if (!select) return;
    const selected = select.value;
    select.innerHTML = '<option value="">Unassigned</option>' + employees.map((employee) => (
        `<option value="${escapeHtml(employee.employee_id)}">${escapeHtml(employee.name)} - ${escapeHtml(employee.role)}</option>`
    )).join("");
    select.value = selected;
}

function renderEmployees(employees) {
    if (!employees.length) {
        employeeCards.innerHTML = '<div class="empty-state"><strong>No employees found</strong><span>Try changing search, role, availability, or sort filters.</span></div>';
        return;
    }
    employeeCards.innerHTML = employees.map((employee) => `
        <article class="talent-card">
            <div class="talent-card-top">
                <div class="person-lockup">
                    <span class="person-avatar">${initials(employee.name)}</span>
                    <div>
                        <h3>${escapeHtml(employee.name)}</h3>
                        <p class="employee-id">${escapeHtml(employee.employee_id)}</p>
                    </div>
                </div>
                <span class="status-pill ${employee.availability === "Available" ? "is-ready" : "is-busy"}">${employee.availability}</span>
            </div>
            <div class="role-band">${escapeHtml(employee.role)}</div>
            <p class="skill-line">${escapeHtml(employee.skills)}</p>
            <div class="talent-metrics">
                <div><span>Experience</span><strong>${Number(employee.experience).toFixed(1)}y</strong></div>
                <div><span>Performance</span><strong>${Number(employee.performance_score).toFixed(0)}</strong></div>
            </div>
        </article>
    `).join("");
}

document.getElementById("uploadForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const button = form.querySelector("button");
    button.disabled = true;
    uploadSummary.innerHTML = '<div class="loading">Uploading and validating CSV...</div>';

    try {
        const response = await fetch("/upload-csv", {
            method: "POST",
            body: new FormData(form),
        });
        const data = await response.json();
        if (!response.ok) {
            uploadSummary.innerHTML = `<div class="form-message error">${escapeHtml(data.error || "Upload failed.")}</div>`;
            return;
        }
        renderUploadSummary(data.result);
        await loadEmployees();
    } catch (error) {
        uploadSummary.innerHTML = '<div class="form-message error">Upload failed. Please try again.</div>';
    } finally {
        button.disabled = false;
    }
});

function renderUploadSummary(result) {
    const stats = [
        ["Total uploaded", result.total_uploaded],
        ["Added", result.added],
        ["Duplicates", result.duplicates],
        ["Validation failures", result.validation_failures],
    ];
    uploadSummary.innerHTML = stats.map(([label, value]) => `
        <div class="upload-stat">
            <span>${label}</span>
            <strong>${value}</strong>
        </div>
    `).join("") + renderErrors(result.errors || []);
}

function renderErrors(errors) {
    if (!errors.length) return "";
    return `<div class="error-list">${errors.map((error) => `<p>${escapeHtml(error)}</p>`).join("")}</div>`;
}

document.getElementById("projectForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const button = qs("generateBtn");
    const formData = new FormData(form);
    const payload = Object.fromEntries(formData.entries());
    payload.preferred_roles = formData.getAll("preferred_roles");

    button.disabled = true;
    loadingState.classList.remove("hidden");
    setMessage("", "info");

    try {
        const response = await fetch("/generate-plan", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify(payload),
        });
        const data = await response.json();
        if (!response.ok) {
            setMessage(data.error || "Unable to generate plan.", "error");
            return;
        }
        currentReport = data;
        activeTab = "team";
        activateTab("team");
        renderActiveTab();
        const source = data.ai_plan.source === "groq" ? "Groq recommendations added." : "Local fallback recommendations added.";
        setMessage(`Assignment generated. ${source}`, "success");
    } catch (error) {
        setMessage("Generation failed. Please try again.", "error");
    } finally {
        loadingState.classList.add("hidden");
        button.disabled = false;
    }
});

document.getElementById("createProjectBtn").addEventListener("click", async () => {
    const form = document.getElementById("projectForm");
    const formData = new FormData(form);
    const selectedTeam = currentReport?.deterministic?.selected_team?.map((member) => member.employee_id) || [];
    const payload = {
        name: formData.get("project_name"),
        description: formData.get("description"),
        priority: "High",
        status: "Planning",
        deadline: "",
        team_member_ids: selectedTeam,
    };
    if (!payload.name) {
        setMessage("Project name is required before saving an execution project.", "error");
        return;
    }
    const response = await fetch("/projects", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) {
        setMessage(data.error || "Unable to create project.", "error");
        return;
    }
    currentProjectId = data.project.id;
    setMessage("Execution project created.", "success");
    await refreshWorkspace();
});

document.getElementById("taskForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!currentProjectId) {
        setMessage("Create or select a project before adding tasks.", "error");
        return;
    }
    const form = event.currentTarget;
    const formData = new FormData(form);
    const payload = Object.fromEntries(formData.entries());
    payload.project_id = currentProjectId;
    const response = await fetch("/tasks", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) {
        setMessage(data.error || "Unable to create task.", "error");
        return;
    }
    form.reset();
    setMessage("Task created.", "success");
    await refreshWorkspace();
});

document.getElementById("breakdownForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const requirements = new FormData(form).get("requirements");
    const response = await fetch("/tasks/breakdown", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({requirements}),
    });
    const data = await response.json();
    if (!response.ok) {
        setMessage(data.error || "Unable to generate task breakdown.", "error");
        return;
    }
    generatedBreakdownTasks = data.breakdown.tasks || [];
    renderBreakdown(generatedBreakdownTasks);
});

function renderBreakdown(tasks) {
    const container = document.getElementById("breakdownList");
    if (!tasks.length) {
        container.innerHTML = "";
        return;
    }
    container.innerHTML = tasks.map((task, index) => `
        <article class="approval-card">
            <strong>${escapeHtml(task.title)}</strong>
            <p>${escapeHtml(task.description)}</p>
            <span>${escapeHtml(task.story_points || 3)} pts - ${escapeHtml(task.suggested_owner || "Unassigned")}</span>
            <button type="button" class="secondary-action compact" data-approve-task="${index}">Approve</button>
        </article>
    `).join("");
}

document.getElementById("breakdownList").addEventListener("click", async (event) => {
    const button = event.target.closest("[data-approve-task]");
    if (!button) return;
    if (!currentProjectId) {
        setMessage("Create or select a project before approving AI tasks.", "error");
        return;
    }
    const task = generatedBreakdownTasks[Number(button.dataset.approveTask)];
    const owner = findEmployeeByName(task.suggested_owner);
    const response = await fetch("/tasks", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
            project_id: currentProjectId,
            title: task.title,
            description: task.description,
            story_points: task.story_points || 3,
            estimated_hours: (Number(task.story_points) || 3) * 3,
            assignee_employee_id: owner?.employee_id || "",
            priority: "Medium",
            status: "To Do",
        }),
    });
    const data = await response.json();
    if (!response.ok) {
        setMessage(data.error || "Unable to approve task.", "error");
        return;
    }
    button.closest(".approval-card").remove();
    setMessage("AI task approved and added to Kanban.", "success");
    await refreshWorkspace();
});

function findEmployeeByName(name) {
    if (!name) return null;
    const query = String(name).toLowerCase();
    return employeesCache.find((employee) => employee.name.toLowerCase() === query || query.includes(employee.name.toLowerCase()));
}

document.querySelectorAll(".tab").forEach((tab) => {
    tab.addEventListener("click", () => {
        activeTab = tab.dataset.tab;
        activateTab(activeTab);
        renderActiveTab();
    });
});

function activateTab(tabName) {
    document.querySelectorAll(".tab").forEach((tab) => {
        tab.classList.toggle("is-active", tab.dataset.tab === tabName);
    });
}

function renderActiveTab() {
    if (!currentReport) {
        resultContent.innerHTML = '<p class="empty-state">No assignment generated yet.</p>';
        return;
    }
    const deterministic = currentReport.deterministic;
    const aiPlan = currentReport.ai_plan;
    const renderers = {
        team: () => renderTeam(deterministic.selected_team),
        scores: () => renderScores(deterministic.selected_team),
        structure: () => renderList(aiPlan.team_structure, (item) => `<strong>${escapeHtml(item.role)}</strong><span>${escapeHtml(item.responsibility)}</span>`),
        stack: () => renderSimpleList(aiPlan.technology_stack),
        timeline: () => renderList(aiPlan.timeline, (item) => `<strong>${escapeHtml(item.phase)}</strong><span>${escapeHtml(item.duration)} - ${escapeHtml(item.notes)}</span>`),
        risks: () => renderList(aiPlan.risks, (item) => `<strong>${escapeHtml(item.risk)}</strong><span>${escapeHtml(item.mitigation)}</span>`),
        recommendations: () => renderSimpleList(aiPlan.final_recommendations),
    };
    resultContent.innerHTML = renderers[activeTab]();
}

async function refreshWorkspace() {
    await Promise.all([
        loadProjects(),
        loadTasks(),
        loadAnalytics(),
        loadWorkload(),
        loadRisks(),
        loadForecast(),
        loadNotifications(),
        loadComments(),
        loadActivity(),
        loadFiles(),
    ]);
}

async function loadRisks() {
    const url = currentProjectId ? `/risks?project_id=${currentProjectId}` : "/risks";
    const response = await fetch(url);
    const data = await response.json();
    if (!response.ok || !riskPanel) return;
    renderRisks(data.risks || []);
}

async function loadProjects() {
    const response = await fetch("/projects");
    const data = await response.json();
    if (!response.ok) return;
    projectsCache = data.projects || [];
    if (!currentProjectId && data.projects.length) {
        currentProjectId = data.projects[0].id;
    }
    renderProjects(projectsCache);
}

function renderProjects(projects) {
    if (!projects.length) {
        projectCards.innerHTML = '<div class="empty-state compact-empty"><strong>No projects yet</strong><span>Create an execution project from Planner to begin tracking delivery.</span></div>';
        return;
    }
    projectCards.innerHTML = projects.map((project, index) => {
        const totalTasks = Number(project.task_count || 0);
        const completedTasks = Number(project.completed_tasks || 0);
        const openTasks = Math.max(totalTasks - completedTasks, 0);
        const progress = clampScore(project.progress);
        const members = project.team_members || [];
        return `
        <article class="project-command-card ${String(project.id) === String(currentProjectId) ? "is-selected" : ""}" data-project-id="${project.id}">
            <div class="project-card-topline">
                <span class="project-color color-${index % 4}"></span>
                <span class="project-status ${statusClass(project.status)}">${escapeHtml(project.status || "Planning")}</span>
            </div>
            <div class="project-card-main">
                <div>
                    <h3>${escapeHtml(project.name)}</h3>
                    <p>${escapeHtml(project.description || "No description added yet.")}</p>
                </div>
                <b class="project-score ${healthClass(project.health_score)}"><span>Health</span>${Number(project.health_score || 0).toFixed(0)}</b>
            </div>
            <div class="project-card-progress">
                <div>
                    <span>${progress}% complete</span>
                    <strong>${completedTasks}/${totalTasks} tasks</strong>
                </div>
                <div class="project-progress"><span style="width: ${progress}%"></span></div>
            </div>
            <div class="project-card-team">
                <div class="avatar-stack" aria-label="${members.length} team members">
                    ${members.slice(0, 5).map((member) => `<span title="${escapeHtml(member.name)}">${initials(member.name)}</span>`).join("")}
                    ${members.length > 5 ? `<span>+${members.length - 5}</span>` : ""}
                </div>
                <span>${members.length || 0} members</span>
            </div>
            <div class="project-card-meta">
                <span>Due ${escapeHtml(project.deadline || "Not set")}</span>
                <span>${openTasks} open</span>
                <span class="${Number(project.open_risks || 0) ? "risk-count" : ""}">${Number(project.open_risks || 0)} risks</span>
            </div>
        </article>`;
    }).join("");
}

projectCards.addEventListener("click", async (event) => {
    const card = event.target.closest("[data-project-id]");
    if (!card) return;
    currentProjectId = card.dataset.projectId;
    await refreshWorkspace();
    await openProjectDrawer(currentProjectId);
});

closeProjectDrawerButton.addEventListener("click", closeProjectDrawer);
projectDrawerBackdrop.addEventListener("click", closeProjectDrawer);
document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && projectDrawer.classList.contains("is-open")) {
        closeProjectDrawer();
    }
});

async function openProjectDrawer(projectId) {
    if (!projectId) return;
    projectDrawer.classList.add("is-open");
    projectDrawerBackdrop.classList.add("is-open");
    projectDrawer.setAttribute("aria-hidden", "false");
    projectDrawerBackdrop.setAttribute("aria-hidden", "false");
    projectDrawerTitle.textContent = "Loading project...";
    projectDrawerContent.innerHTML = '<div class="loading">Loading project command data...</div>';

    try {
        const [tasksData, workloadData, risksData, forecastData] = await Promise.all([
            fetchJson(`/tasks?project_id=${projectId}`),
            fetchJson(`/workload?project_id=${projectId}`),
            fetchJson(`/risks?project_id=${projectId}`),
            fetchJson(`/forecast?project_id=${projectId}`),
        ]);
        const project = projectsCache.find((item) => String(item.id) === String(projectId)) || {};
        projectDrawerTitle.textContent = project.name || "Project overview";
        renderProjectDrawer(project, tasksData.tasks || [], workloadData.workload || [], risksData.risks || [], forecastData.forecast || {});
    } catch (error) {
        projectDrawerTitle.textContent = "Project overview";
        projectDrawerContent.innerHTML = '<div class="empty-state compact-empty"><strong>Unable to load project details</strong><span>Please refresh and try again.</span></div>';
    }
}

function closeProjectDrawer() {
    projectDrawer.classList.remove("is-open");
    projectDrawerBackdrop.classList.remove("is-open");
    projectDrawer.setAttribute("aria-hidden", "true");
    projectDrawerBackdrop.setAttribute("aria-hidden", "true");
}

function renderProjectDrawer(project, tasks, workload, risks, forecast) {
    const progress = clampScore(project.progress);
    const statusCounts = groupTasksByStatus(tasks);
    const memberStats = buildDrawerMembers(project, tasks, workload);
    const openTasks = tasks.filter((task) => task.status !== "Completed").length;
    projectDrawerContent.innerHTML = `
        <section class="drawer-overview">
            <div>
                <span class="project-status ${statusClass(project.status)}">${escapeHtml(project.status || "Planning")}</span>
                <h3>${escapeHtml(project.name || "Untitled project")}</h3>
                <p>${escapeHtml(project.description || "No project description has been added.")}</p>
                <div class="drawer-meta-grid">
                    <span><strong>${escapeHtml(project.deadline || "Not set")}</strong>Due date</span>
                    <span><strong>${openTasks}</strong>Open tasks</span>
                    <span><strong>${Number(project.open_risks || risks.length || 0)}</strong>Risks</span>
                    <span><strong>${escapeHtml(project.priority || "Medium")}</strong>Priority</span>
                </div>
            </div>
            <div class="completion-ring" style="--progress: ${progress * 3.6}deg">
                <strong>${progress}%</strong>
                <span>complete</span>
            </div>
        </section>

        <section class="drawer-section">
            <div class="drawer-section-heading">
                <h3>Team workload</h3>
                <span>${memberStats.length} people</span>
            </div>
            <div class="drawer-team-list">
                ${memberStats.map(renderDrawerMember).join("") || '<div class="empty-state compact-empty"><strong>No team members</strong><span>Add people to the project to see utilization.</span></div>'}
            </div>
        </section>

        <section class="drawer-section">
            <div class="drawer-section-heading">
                <h3>Task breakdown</h3>
                <span>${tasks.length} tasks</span>
            </div>
            <div class="drawer-task-grid">
                ${["To Do", "In Progress", "Review", "Blocked", "Completed"].map((status) => renderStatusGroup(status, statusCounts[status] || [])).join("")}
            </div>
        </section>

        <section class="drawer-section">
            <div class="drawer-section-heading">
                <h3>AI insights and risks</h3>
                <span>${risks.length} saved risks</span>
            </div>
            <div class="drawer-insight-grid">
                ${renderForecastInsight(forecast)}
                ${renderDrawerRisks(risks)}
            </div>
        </section>
    `;
}

function buildDrawerMembers(project, tasks, workload) {
    const workloadById = new Map(workload.map((item) => [String(item.employee_id), item]));
    const tasksByAssignee = tasks.reduce((acc, task) => {
        const id = task.assignee_employee_id;
        if (!id || task.status === "Completed") return acc;
        acc[String(id)] = (acc[String(id)] || 0) + 1;
        return acc;
    }, {});
    const members = project.team_members && project.team_members.length
        ? project.team_members
        : workload.filter((item) => Number(item.assigned_hours || 0) > 0);

    return members.map((member) => {
        const metric = workloadById.get(String(member.employee_id)) || {};
        return {
            employee_id: member.employee_id,
            name: member.name,
            role: member.role,
            utilization: Number(metric.utilization || 0),
            indicator: metric.indicator || "Green",
            performance_score: Number(member.performance_score || 0),
            task_count: tasksByAssignee[String(member.employee_id)] || 0,
        };
    });
}

function renderDrawerMember(member) {
    return `
        <article class="drawer-team-member">
            <div class="person-lockup">
                <span class="person-avatar">${initials(member.name)}</span>
                <div>
                    <strong>${escapeHtml(member.name)}</strong>
                    <small>${escapeHtml(member.role)}</small>
                </div>
            </div>
            <div class="drawer-member-metrics">
                <span class="traffic ${String(member.indicator).toLowerCase()}">${Math.round(member.utilization)}%</span>
                <span>${Math.round(member.performance_score)} perf.</span>
                <span>${member.task_count} tasks</span>
            </div>
        </article>
    `;
}

function groupTasksByStatus(tasks) {
    return tasks.reduce((groups, task) => {
        groups[task.status] = groups[task.status] || [];
        groups[task.status].push(task);
        return groups;
    }, {});
}

// Fixed selector helper for the quick-status update
function renderStatusGroup(status, tasks) {
    return `
        <article class="drawer-task-status">
            <header>
                <strong>${escapeHtml(status)}</strong>
                <span>${tasks.length}</span>
            </header>
            <div>
                ${tasks.slice(0, 5).map((task) => `
                    <p>
                        <strong>${escapeHtml(task.title)}</strong>
                        <span>${escapeHtml(task.assignee?.name || "Unassigned")} - ${escapeHtml(task.due_date || "No due date")}</span>
                    </p>
                `).join("") || '<p><span>No tasks</span></p>'}
                ${tasks.length > 5 ? `<small>+${tasks.length - 5} more</small>` : ""}
            </div>
        </article>
    `;
}

function renderForecastInsight(forecast) {
    if (!forecast || !forecast.completion_date) {
        return '<article class="drawer-ai-card"><strong>Forecast pending</strong><span>Add tasks and run planning to calculate completion signals.</span></article>';
    }
    return `
        <article class="drawer-ai-card">
            <strong>Forecast completion: ${escapeHtml(forecast.completion_date)}</strong>
            <span>${Number(forecast.delay_probability || 0)}% delay probability - ${escapeHtml(forecast.velocity_trend || "Velocity trend unavailable")}</span>
            ${(forecast.recommendations || []).slice(0, 3).map((item) => `<small>${escapeHtml(item)}</small>`).join("")}
        </article>
    `;
}

function renderDrawerRisks(risks) {
    if (!risks.length) {
        return '<article class="drawer-ai-card is-clear"><strong>No stored risks</strong><span>Run Risk Analyzer to generate project-specific execution risks.</span></article>';
    }
    return risks.slice(0, 5).map((risk) => `
        <article class="drawer-ai-card ${risk.impact === "High" || risk.impact === "Critical" ? "is-risk" : ""}">
            <strong>${escapeHtml(risk.risk)}</strong>
            <span>${escapeHtml(risk.probability)} probability - ${escapeHtml(risk.impact)} impact</span>
            <small>${escapeHtml(risk.mitigation)}</small>
        </article>
    `).join("");
}

async function fetchJson(url) {
    const response = await fetch(url);
    const data = await response.json();
    if (!response.ok) {
        throw new Error(data.error || "Request failed");
    }
    return data;
}

async function loadTasks() {
    const url = currentProjectId ? `/tasks?project_id=${currentProjectId}` : "/tasks";
    const response = await fetch(url);
    const data = await response.json();
    if (!response.ok) return;
    renderKanban(data.tasks, data.statuses);
}

function renderKanban(tasks, statuses) {
    kanbanBoard.innerHTML = statuses.map((status) => {
        const statusTasks = tasks.filter((task) => task.status === status);
        return `
            <section class="kanban-column" data-status="${escapeHtml(status)}">
                <header>
                    <strong>${escapeHtml(status)}</strong>
                    <span>${statusTasks.length}</span>
                </header>
                <div class="kanban-dropzone" data-status="${escapeHtml(status)}">
                    ${statusTasks.map(renderKanbanTask).join("")}
                </div>
            </section>
        `;
    }).join("");
    bindKanbanDrag();
}

function renderKanbanTask(task) {
    return `
        <article class="kanban-card" draggable="true" data-task-id="${task.id}">
            <div class="kanban-card-top">
                <strong>${escapeHtml(task.title)}</strong>
                <span class="priority ${priorityClass(task.priority)}">${escapeHtml(task.priority)}</span>
            </div>
            <p>${escapeHtml(task.description || "No description")}</p>
            <div class="kanban-meta">
                <span>${escapeHtml(task.assignee?.name || "Unassigned")}</span>
                <span>${escapeHtml(task.due_date || "No due date")}</span>
                <span>${Number(task.estimated_hours || 0)}h</span>
            </div>
            <select class="quick-status" data-task-status="${task.id}">
                ${["To Do", "In Progress", "Review", "Blocked", "Completed"].map((status) => (
                    `<option value="${status}" ${task.status === status ? "selected" : ""}>${status}</option>`
                )).join("")}
            </select>
        </article>
    `;
}

function bindKanbanDrag() {
    document.querySelectorAll(".kanban-card").forEach((card) => {
        card.addEventListener("dragstart", (event) => {
            event.dataTransfer.setData("text/plain", card.dataset.taskId);
        });
    });
    document.querySelectorAll(".kanban-dropzone").forEach((zone) => {
        zone.addEventListener("dragover", (event) => event.preventDefault());
        zone.addEventListener("drop", async (event) => {
            event.preventDefault();
            const taskId = event.dataTransfer.getData("text/plain");
            await updateTask(taskId, {status: zone.dataset.status});
        });
    });
}

kanbanBoard.addEventListener("change", async (event) => {
    const select = event.target.closest("[data-task-status]");
    if (!select) return;
    await updateTask(select.dataset.taskStatus, {status: select.value});
});

async function updateTask(id, patch) {
    const response = await fetch("/tasks", {
        method: "PATCH",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({id, ...patch}),
    });
    const data = await response.json();
    if (!response.ok) {
        setMessage(data.error || "Unable to update task.", "error");
        return;
    }
    await refreshWorkspace();
}

async function loadAnalytics() {
    const url = currentProjectId && currentView !== "dashboard" ? `/analytics?project_id=${currentProjectId}` : "/analytics";
    const response = await fetch(url);
    const data = await response.json();
    if (!response.ok) return;
    const metrics = data.analytics.project_metrics;
    analyticsPanel.innerHTML = [
        ["P", "Total Projects", metrics.total_projects || 0, "Live workspace"],
        ["T", "Active Assignments", metrics.open_tasks, "Open execution work"],
        ["%", "Completion Rate", `${Math.round(metrics.completion_rate || 0)}%`, "Completed delivery work"],
        ["H", "Avg. Project Score", metrics.team_health || 0, "Health score"],
    ].map(([icon, label, value, note]) => `
        <article class="kpi-card">
            <span class="kpi-icon">${icon}</span>
            <div>
                <span>${label}</span>
                <strong>${value}</strong>
                <small class="trend-up">${note}</small>
            </div>
        </article>
    `).join("");
}

async function loadWorkload() {
    const url = currentProjectId ? `/workload?project_id=${currentProjectId}` : "/workload";
    const response = await fetch(url);
    const data = await response.json();
    if (!response.ok) return;
    const avgUtilization = data.workload.length
        ? Math.round(data.workload.reduce((sum, item) => sum + Number(item.utilization || 0), 0) / data.workload.length)
        : 0;
    if (teamUtilizationDonut) {
        teamUtilizationDonut.textContent = `${Math.min(100, avgUtilization)}%`;
    }
    workloadPanel.innerHTML = data.workload.map((item) => `
        <div class="workload-row">
            <div>
                <strong>${escapeHtml(item.name)}</strong>
                <span>${escapeHtml(item.role)} - ${item.assigned_hours}/${item.capacity_hours}h</span>
            </div>
            <span class="traffic ${item.indicator.toLowerCase()}">${item.utilization}%</span>
        </div>
    `).join("") || '<div class="empty-state compact-empty"><strong>No workload</strong><span>Add tasks to calculate utilization.</span></div>';
}

async function loadForecast() {
    const url = currentProjectId ? `/forecast?project_id=${currentProjectId}` : "/forecast";
    const response = await fetch(url);
    const data = await response.json();
    if (!response.ok) return;
    const forecast = data.forecast || {};
    forecastPanel.innerHTML = forecast.completion_date ? `
        <div class="forecast-card">
            <span>Forecast completion</span>
            <strong>${escapeHtml(forecast.completion_date)}</strong>
            <p>${forecast.delay_probability}% delay probability - ${escapeHtml(forecast.velocity_trend)}</p>
            ${(forecast.recommendations || []).map((item) => `<small>${escapeHtml(item)}</small>`).join("")}
        </div>
    ` : "";
}

document.getElementById("analyzeRisksBtn").addEventListener("click", async () => {
    if (!currentProjectId) {
        setMessage("Select a project before analyzing risks.", "error");
        return;
    }
    const response = await fetch("/risks/analyze", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({project_id: currentProjectId}),
    });
    const data = await response.json();
    if (!response.ok) {
        setMessage(data.error || "Unable to analyze risks.", "error");
        return;
    }
    renderRisks(data.risks);
    await refreshWorkspace();
});

function renderRisks(risks) {
    riskPanel.innerHTML = risks.map((risk) => `
        <article class="insight-card ${risk.impact === "High" || risk.impact === "Critical" ? "danger" : "info"}">
            <strong>${escapeHtml(risk.risk)}</strong>
            <span>${escapeHtml(risk.probability)} probability - ${escapeHtml(risk.impact)} impact</span>
            <span>${escapeHtml(risk.mitigation)}</span>
            <button type="button">Review</button>
        </article>
    `).join("") || '<article class="insight-card success"><strong>No risks detected</strong><span>Current project signals look stable.</span></article>';
}

document.getElementById("generateSprintBtn").addEventListener("click", async () => {
    if (!currentProjectId) {
        setMessage("Select a project before generating a sprint.", "error");
        return;
    }
    const response = await fetch("/sprints/generate", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({project_id: currentProjectId, capacity_hours: 120}),
    });
    const data = await response.json();
    if (!response.ok) {
        setMessage(data.error || "Unable to generate sprint.", "error");
        return;
    }
    setMessage(data.plan.summary || "Sprint generated.", "success");
    await refreshWorkspace();
});

async function loadNotifications() {
    const filter = document.getElementById("notificationFilter").value;
    const response = await fetch(`/notifications?status=${filter}`);
    const data = await response.json();
    if (!response.ok) return;
    notificationList.innerHTML = data.notifications.map((item) => `
        <article class="notification-card ${item.is_read ? "" : "is-unread"}">
            <strong>${escapeHtml(item.title)}</strong>
            <span>${escapeHtml(item.message)}</span>
            <small>${escapeHtml(item.type)} - ${escapeHtml(item.created_at)}</small>
        </article>
    `).join("") || '<div class="empty-state compact-empty"><strong>No notifications</strong><span>You are caught up.</span></div>';
}

document.getElementById("notificationFilter").addEventListener("change", loadNotifications);
document.getElementById("markNotificationsRead").addEventListener("click", async () => {
    await fetch("/notifications/read", {
        method: "PATCH",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({}),
    });
    await loadNotifications();
});

document.getElementById("commentForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const body = new FormData(event.currentTarget).get("body");
    if (!body) return;
    const response = await fetch("/comments", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({project_id: currentProjectId, body}),
    });
    if (response.ok) {
        event.currentTarget.reset();
        await Promise.all([loadComments(), loadActivity(), loadNotifications()]);
    }
});

async function loadComments() {
    const url = currentProjectId ? `/comments?project_id=${currentProjectId}` : "/comments";
    const response = await fetch(url);
    const data = await response.json();
    if (!response.ok) return;
    commentList.innerHTML = data.comments.slice(0, 6).map((comment) => `
        <article class="comment-card">
            <strong>${escapeHtml(comment.user_name)}</strong>
            <p>${escapeHtml(comment.body)}</p>
            <small>${escapeHtml(comment.created_at)}</small>
        </article>
    `).join("");
}

async function loadActivity() {
    const url = currentProjectId ? `/activity?project_id=${currentProjectId}` : "/activity";
    const response = await fetch(url);
    const data = await response.json();
    if (!response.ok) return;
    activityTimeline.innerHTML = data.activity.slice(0, 8).map((item) => `
        <article class="timeline-item">
            <strong>${escapeHtml(item.action)}</strong>
            <span>${escapeHtml(item.details || "")}</span>
            <small>${escapeHtml(item.created_at)}</small>
        </article>
    `).join("");
}

document.getElementById("fileForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    if (currentProjectId) formData.append("project_id", currentProjectId);
    const response = await fetch("/files/upload", {method: "POST", body: formData});
    const data = await response.json();
    if (!response.ok) {
        setMessage(data.error || "Unable to upload file.", "error");
        return;
    }
    event.currentTarget.reset();
    await Promise.all([loadFiles(), loadActivity(), loadNotifications()]);
});

document.getElementById("fileSearch").addEventListener("input", debounce(loadFiles, 250));

async function loadFiles() {
    const params = new URLSearchParams();
    if (currentProjectId) params.set("project_id", currentProjectId);
    const search = document.getElementById("fileSearch").value;
    if (search) params.set("search", search);
    const response = await fetch(`/files?${params.toString()}`);
    const data = await response.json();
    if (!response.ok) return;
    fileList.innerHTML = data.files.map((file) => `
        <article class="file-card">
            <strong>${escapeHtml(file.original_name)}</strong>
            <span>v${file.version} - ${escapeHtml(file.file_type.toUpperCase())}</span>
            <a href="/files/${file.id}/download">Download</a>
        </article>
    `).join("") || '<div class="empty-state compact-empty"><strong>No documents</strong><span>Upload PDFs, docs, sheets, or images.</span></div>';
}

document.getElementById("assistantForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const message = new FormData(event.currentTarget).get("message");
    assistantResponse.innerHTML = '<div class="loading-state"><span></span>Thinking with project context...</div>';
    const response = await fetch("/assistant/chat", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({project_id: currentProjectId, message}),
    });
    const data = await response.json();
    if (!response.ok) {
        assistantResponse.innerHTML = `<div class="form-message error">${escapeHtml(data.error || "Assistant failed.")}</div>`;
        return;
    }
    assistantResponse.innerHTML = `
        <article class="assistant-card">
            <p>${escapeHtml(data.response.answer || "No answer generated.")}</p>
            ${(data.response.recommendations || []).map((item) => `<span>${escapeHtml(item)}</span>`).join("")}
        </article>
    `;
});

document.getElementById("refreshWorkspace").addEventListener("click", refreshWorkspace);

function renderTeam(team) {
    return `<div class="assignment-grid">${team.map((member, index) => `
        <article class="assignment-card">
            <div class="assignment-rank">#${index + 1}</div>
            <div class="assignment-header">
                <div class="person-lockup">
                    <span class="person-avatar score-avatar">${initials(member.name)}</span>
                    <div>
                        <h3>${escapeHtml(member.name)}</h3>
                        <p class="employee-id">${escapeHtml(member.assigned_role)}</p>
                    </div>
                </div>
                <strong class="score-number">${member.final_score}</strong>
            </div>
            <div class="score-track"><span style="width: ${clampScore(member.final_score)}%"></span></div>
            <dl class="score-breakdown">
                <div><dt>Skills</dt><dd>${member.skills_match}%</dd></div>
                <div><dt>Role</dt><dd>${member.role_match}%</dd></div>
                <div><dt>Avail.</dt><dd>${member.availability_score}%</dd></div>
            </dl>
            <p class="reason-text">${escapeHtml(member.reason)}</p>
        </article>
    `).join("")}</div>`;
}

function renderScores(team) {
    return `
        <div class="table-wrap">
            <table class="score-table">
                <thead>
                    <tr>
                        <th>Name</th>
                        <th>Role</th>
                        <th>Final</th>
                        <th>Skills</th>
                        <th>Role</th>
                        <th>Performance</th>
                        <th>Experience</th>
                        <th>Availability</th>
                        <th>Weakness</th>
                    </tr>
                </thead>
                <tbody>
                    ${team.map((member) => `
                        <tr>
                            <td>${escapeHtml(member.name)}</td>
                            <td>${escapeHtml(member.assigned_role)}</td>
                            <td>${member.final_score}</td>
                            <td>${member.skills_match}%</td>
                            <td>${member.role_match}%</td>
                            <td>${member.performance_score}</td>
                            <td>${member.experience_score}%</td>
                            <td>${member.availability_score}%</td>
                            <td>${escapeHtml(member.weakness)}</td>
                        </tr>
                    `).join("")}
                </tbody>
            </table>
        </div>`;
}

function renderList(items, template) {
    if (!items || !items.length) return '<div class="empty-state"><strong>No items available</strong><span>Generate an assignment to populate this section.</span></div>';
    return `<div class="insight-list">${items.map((item) => `<div>${template(item)}</div>`).join("")}</div>`;
}

function renderSimpleList(items) {
    if (!items || !items.length) return '<div class="empty-state"><strong>No items available</strong><span>Generate an assignment to populate this section.</span></div>';
    return `<div class="insight-list">${items.map((item) => `<div><span>${escapeHtml(String(item))}</span></div>`).join("")}</div>`;
}

function initials(name) {
    return String(name || "")
        .split(/\s+/)
        .filter(Boolean)
        .slice(0, 2)
        .map((part) => part[0].toUpperCase())
        .join("") || "PA";
}

function clampScore(score) {
    const value = Number(score);
    if (Number.isNaN(value)) return 0;
    return Math.max(0, Math.min(100, value));
}

document.getElementById("copyReport").addEventListener("click", async () => {
    if (!currentReport) {
        setMessage("Generate a report before copying.", "error");
        return;
    }
    const text = buildReportText(currentReport);
    try {
        await navigator.clipboard.writeText(text);
        setMessage("Report copied to clipboard.", "success");
    } catch (error) {
        setMessage("Clipboard access failed.", "error");
    }
});

function buildReportText(report) {
    const lines = [`Project: ${report.project.project_name}`, "", "Selected Team:"];
    report.deterministic.selected_team.forEach((member) => {
        lines.push(`${member.name} - ${member.assigned_role} - Score ${member.final_score}`);
        lines.push(`Reason: ${member.reason}`);
        lines.push(`Weakness: ${member.weakness}`);
    });
    lines.push("", "Recommendations:");
    (report.ai_plan.final_recommendations || []).forEach((item) => lines.push(`- ${item}`));
    return lines.join("\n");
}

function escapeHtml(value) {
    return String(value ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function healthClass(score) {
    if (Number(score) >= 80) return "green";
    if (Number(score) >= 60) return "yellow";
    return "red";
}

function statusClass(status) {
    const value = String(status || "").toLowerCase().replace(/\s+/g, "-");
    return `status-${value || "planning"}`;
}

function priorityClass(priority) {
    const value = String(priority || "").toLowerCase();
    if (value === "critical" || value === "high") return "hot";
    if (value === "medium") return "warm";
    return "cool";
}

["searchEmployee", "roleFilter", "availabilityFilter", "sortFilter"].forEach((id) => {
    qs(id).addEventListener("input", debounce(loadEmployees, 250));
    qs(id).addEventListener("change", loadEmployees);
});
qs("refreshEmployees").addEventListener("click", loadEmployees);

function debounce(callback, delay) {
    let timeout;
    return (...args) => {
        window.clearTimeout(timeout);
        timeout = window.setTimeout(() => callback(...args), delay);
    };
}

loadEmployees();
refreshWorkspace();
initViewNavigation();
