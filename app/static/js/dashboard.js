document.addEventListener('DOMContentLoaded', () => {
    fetchProjects();

    // Drawer Tabs Logic
    document.querySelectorAll('.drawer-tab').forEach(tab => {
        tab.addEventListener('click', (e) => {
            // Remove active from all tabs
            document.querySelectorAll('.drawer-tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            
            // Add active to clicked
            e.target.classList.add('active');
            const targetId = 'tab-' + e.target.getAttribute('data-tab');
            document.getElementById(targetId).classList.add('active');
        });
    });

    // Close Drawer
    document.getElementById('close-drawer-btn').addEventListener('click', closeDrawer);
    document.getElementById('drawer-overlay').addEventListener('click', closeDrawer);
});

let currentProjectId = null;

async function fetchProjects() {
    try {
        const response = await fetch('/api/projects/');
        const data = await response.json();
        const container = document.getElementById('project-container');
        
        if (data.projects && data.projects.length > 0) {
            container.innerHTML = '';
            data.projects.forEach(project => {
                const healthColor = project.health_score === 'Green' ? 'health-green' : (project.health_score === 'Yellow' ? 'health-yellow' : 'health-red');
                const statusClass = `status-${project.status.toLowerCase().replace(' ', '')}`;
                
                // Show up to 3 avatars
                let avatarsHtml = '';
                if (project.assignments && project.assignments.length > 0) {
                    for (let i = 0; i < Math.min(3, project.assigned_count); i++) {
                        avatarsHtml += `<div class="avatar-circle">M</div>`; // Mock initials
                    }
                    if (project.assigned_count > 3) {
                        avatarsHtml += `<div class="avatar-circle">+${project.assigned_count - 3}</div>`;
                    }
                } else {
                    avatarsHtml = `<span style="font-size:11px; color:var(--text-muted);">Unassigned</span>`;
                }

                const cardHtml = `
                    <div class="project-card" onclick="openProjectDrawer(${project.id})">
                        <div class="project-card-header">
                            <div>
                                <h3 class="project-title">${project.name}</h3>
                                <p class="project-meta">Due: ${project.duration}</p>
                            </div>
                            <span class="status-badge ${statusClass}">${project.status}</span>
                        </div>
                        <p style="font-size: 13px; color: var(--text-muted); display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;">
                            ${project.description}
                        </p>
                        <div style="margin-top: auto;">
                            <div style="display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 8px;">
                                <div class="team-avatars">
                                    ${avatarsHtml}
                                </div>
                                <div style="text-align: right;">
                                    <span class="${healthColor}" style="margin-bottom: 2px;">${project.health_score}</span>
                                    <span style="font-size: 11px; color: var(--text-muted);">${project.completed_tasks}/${project.total_tasks} Tasks</span>
                                </div>
                            </div>
                            <div class="progress-container">
                                <div class="progress-bar" style="width: ${project.completion_percentage}%;"></div>
                            </div>
                        </div>
                    </div>
                `;
                container.innerHTML += cardHtml;
            });
        } else {
            container.innerHTML = `
                <div style="grid-column: 1 / -1; text-align: center; padding: 40px; background: var(--bg-card); border: 1px dashed var(--border); border-radius: 12px;">
                    <h4 style="color: var(--text-white); margin-bottom: 8px;">No active projects</h4>
                    <p style="color: var(--text-muted); font-size: 13px; margin-bottom: 16px;">Create your first project to start executing.</p>
                </div>
            `;
        }
    } catch (err) {
        console.error("Failed to fetch projects", err);
    }
}

async function openProjectDrawer(projectId) {
    currentProjectId = projectId;
    document.getElementById('drawer-overlay').classList.add('open');
    document.getElementById('drawer-panel').classList.add('open');
    
    // Reset data
    document.getElementById('drawer-project-title').textContent = "Loading...";
    document.getElementById('ai-insights-container').style.display = 'none';
    
    // Fetch overview
    try {
        const res = await fetch(`/api/projects/${projectId}`);
        const data = await res.json();
        const p = data.project;
        
        document.getElementById('drawer-project-title').textContent = p.name;
        document.getElementById('drawer-project-desc').textContent = p.description;
        document.getElementById('drawer-project-duration').textContent = p.duration;
        
        const statusBadge = document.getElementById('drawer-project-status');
        statusBadge.textContent = p.status;
        statusBadge.className = `status-badge status-${p.status.toLowerCase().replace(' ', '')}`;
        
        // Trigger fetching insights in background
        fetchInsights(projectId);
        // Load Kanban tasks
        if(window.loadKanbanTasks) window.loadKanbanTasks(projectId);
        // Load Team
        loadTeam(projectId);
        // Load Milestones
        loadMilestones(projectId);
    } catch (err) {
        console.error(err);
    }
}

function closeDrawer() {
    document.getElementById('drawer-overlay').classList.remove('open');
    document.getElementById('drawer-panel').classList.remove('open');
    currentProjectId = null;
}

async function fetchInsights(projectId) {
    try {
        const res = await fetch(`/api/projects/${projectId}/insights`);
        const data = await res.json();
        if (data.insights && !data.insights.error) {
            document.getElementById('ai-insights-container').style.display = 'block';
            document.getElementById('insight-summary').textContent = data.insights.health_summary;
            
            let risksHtml = '';
            (data.insights.risks || []).forEach(r => {
                risksHtml += `<div class="action-item"><span style="color:var(--warning-text);">⚠️</span> <span style="font-size:13px; color:var(--text-muted);">${r}</span></div>`;
            });
            document.getElementById('insight-risks').innerHTML = risksHtml;
            
            let actionsHtml = '';
            (data.insights.recommendations || []).forEach(r => {
                actionsHtml += `<div class="action-item"><span style="color:var(--success);">💡</span> <span style="font-size:13px; color:var(--text-muted);">${r}</span></div>`;
            });
            document.getElementById('insight-actions').innerHTML = actionsHtml;
        }
    } catch(err) {
        console.error("AI Insights failed", err);
    }
}

async function loadTeam(projectId) {
    try {
        const res = await fetch(`/api/projects/${projectId}/team`);
        const data = await res.json();
        const tbody = document.getElementById('team-table-body');
        tbody.innerHTML = '';
        
        data.team.forEach(t => {
            const role = t.project_role || t.role;
            const util = t.utilization || 0;
            
            tbody.innerHTML += `
                <tr>
                    <td>
                        <div style="font-weight: 500; color: var(--text-white);">${t.name}</div>
                        <div style="font-size: 11px; color: var(--text-muted);">${t.skills.substring(0, 30)}...</div>
                    </td>
                    <td><span class="badge badge-outline">${role}</span></td>
                    <td>
                        <div style="display: flex; align-items: center; gap: 8px;">
                            <span style="font-size: 12px; width: 30px;">${util}%</span>
                            <div class="progress-container" style="width: 80px; margin-top: 0;">
                                <div class="progress-bar ${util > 80 ? 'bg-danger' : 'bg-success'}" style="width: ${util}%;"></div>
                            </div>
                        </div>
                    </td>
                    <td>-</td>
                </tr>
            `;
        });
    } catch(err) { console.error(err); }
}

async function loadMilestones(projectId) {
    try {
        const res = await fetch(`/api/projects/${projectId}/milestones`);
        const data = await res.json();
        const mContainer = document.getElementById('milestones-container');
        mContainer.innerHTML = '';
        
        if (data.milestones && data.milestones.length > 0) {
            data.milestones.forEach(m => {
                mContainer.innerHTML += `
                    <div style="display: flex; gap: 16px; border-left: 2px solid var(--border); padding-left: 16px; position: relative;">
                        <div style="position: absolute; left: -6px; top: 0; width: 10px; height: 10px; border-radius: 50%; background: ${m.status === 'Completed' ? 'var(--success)' : 'var(--border-hover)'};"></div>
                        <div>
                            <div style="font-size: 13px; font-weight: 500; color: var(--text-white);">${m.title}</div>
                            <div style="font-size: 11px; color: var(--text-muted);">${new Date(m.due_date).toLocaleDateString()} &middot; ${m.status}</div>
                        </div>
                    </div>
                `;
            });
        } else {
            mContainer.innerHTML = `<span style="font-size: 13px; color: var(--text-muted);">No milestones defined.</span>`;
        }
    } catch(err) { console.error(err); }
}
