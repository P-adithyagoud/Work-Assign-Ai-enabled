let draggedTask = null;

document.addEventListener('DOMContentLoaded', () => {
    setupKanbanDragAndDrop();
    
    document.getElementById('add-task-btn').addEventListener('click', () => {
        const title = prompt("Enter task title:");
        if (title && currentProjectId) {
            createTask(currentProjectId, title);
        }
    });
});

window.loadKanbanTasks = async function(projectId) {
    try {
        const res = await fetch(`/api/projects/${projectId}/tasks`);
        const data = await res.json();
        
        // Clear columns
        document.querySelectorAll('.kanban-column-content').forEach(c => c.innerHTML = '');
        document.querySelectorAll('.kanban-header .badge').forEach(b => b.textContent = '0');
        
        if (data.tasks) {
            data.tasks.forEach(task => {
                let status = task.status;
                let colId = '';
                if (status === 'To Do') colId = 'column-todo';
                else if (status === 'In Progress') colId = 'column-progress';
                else if (status === 'Review') colId = 'column-review';
                else if (status === 'Completed') colId = 'column-completed';
                else colId = 'column-todo'; // default
                
                const col = document.querySelector(`#${colId} .kanban-column-content`);
                if (col) {
                    const assignee = task.employees ? task.employees.name : 'Unassigned';
                    col.innerHTML += `
                        <div class="kanban-task" draggable="true" data-id="${task.id}">
                            <div class="task-title">${task.title}</div>
                            <div class="task-meta">
                                <span>${assignee}</span>
                                <span class="badge badge-outline">${task.story_points} pt</span>
                            </div>
                        </div>
                    `;
                }
            });
            
            // Update counts
            document.querySelectorAll('.kanban-column').forEach(col => {
                const count = col.querySelectorAll('.kanban-task').length;
                col.querySelector('.badge').textContent = count;
            });
            
            attachDragEvents();
        }
    } catch(err) {
        console.error("Failed to load tasks", err);
    }
}

async function createTask(projectId, title) {
    try {
        const res = await fetch('/api/tasks/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ project_id: projectId, title: title, status: 'To Do', story_points: 1 })
        });
        if (res.ok) {
            window.loadKanbanTasks(projectId);
        }
    } catch (err) { console.error(err); }
}

function attachDragEvents() {
    document.querySelectorAll('.kanban-task').forEach(task => {
        task.addEventListener('dragstart', () => {
            draggedTask = task;
            setTimeout(() => task.classList.add('dragging'), 0);
        });
        
        task.addEventListener('dragend', () => {
            task.classList.remove('dragging');
            draggedTask = null;
        });
    });
}

function setupKanbanDragAndDrop() {
    document.querySelectorAll('.kanban-column-content').forEach(container => {
        container.addEventListener('dragover', e => {
            e.preventDefault();
            const afterElement = getDragAfterElement(container, e.clientY);
            if (draggedTask) {
                if (afterElement == null) {
                    container.appendChild(draggedTask);
                } else {
                    container.insertBefore(draggedTask, afterElement);
                }
            }
        });
        
        container.addEventListener('drop', async e => {
            e.preventDefault();
            if (draggedTask) {
                const newStatus = container.parentElement.getAttribute('data-status');
                const taskId = draggedTask.getAttribute('data-id');
                
                // Update counts visually immediately
                document.querySelectorAll('.kanban-column').forEach(col => {
                    const count = col.querySelectorAll('.kanban-task').length;
                    col.querySelector('.badge').textContent = count;
                });
                
                // Persist status change
                try {
                    await fetch(`/api/tasks/${taskId}`, {
                        method: 'PUT',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ status: newStatus })
                    });
                } catch(err) { console.error("Failed to update status", err); }
            }
        });
    });
}

function getDragAfterElement(container, y) {
    const draggableElements = [...container.querySelectorAll('.kanban-task:not(.dragging)')];
    
    return draggableElements.reduce((closest, child) => {
        const box = child.getBoundingClientRect();
        const offset = y - box.top - box.height / 2;
        if (offset < 0 && offset > closest.offset) {
            return { offset: offset, element: child };
        } else {
            return closest;
        }
    }, { offset: Number.NEGATIVE_INFINITY }).element;
}
