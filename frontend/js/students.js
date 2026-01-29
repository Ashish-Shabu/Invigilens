const API_BASE = 'http://localhost:5000/api/students';
const PHOTO_BASE = 'http://localhost:5000/student-photos/';

// State
let currentView = 'classes'; // 'classes' or 'students'
let activeClass = null;

document.addEventListener('DOMContentLoaded', () => {
    loadClassesView();

    // Modal Logic
    const modal = document.getElementById('addModal');
    const btn = document.getElementById('add-student-btn');
    const span = document.getElementsByClassName('close-btn')[0];
    const form = document.getElementById('addStudentForm');

    btn.onclick = () => {
        modal.style.display = 'block';
        // Auto-fill class if we are actively viewing a class
        const classInput = document.getElementById('modalClassName');
        if (activeClass) {
            classInput.value = activeClass;
            // Optional: make it readonly if you want to force it
            // classInput.readOnly = true; 
        } else {
            classInput.value = '';
        }
    }

    span.onclick = () => modal.style.display = 'none';

    window.onclick = (event) => {
        if (event.target == modal) {
            modal.style.display = 'none';
        }
    }

    // Form Submit
    form.onsubmit = async (e) => {
        e.preventDefault();
        const submitBtn = form.querySelector('button[type="submit"]');
        const originalText = submitBtn.innerText;
        submitBtn.innerText = "Uploading...";
        submitBtn.disabled = true;

        try {
            const formData = new FormData(form);

            const res = await fetch(API_BASE, {
                method: 'POST',
                body: formData
            });

            const data = await res.json();

            if (!res.ok) {
                throw new Error(data.message || 'Failed to add student');
            }

            // Success
            modal.style.display = 'none';
            form.reset();
            alert('Student added successfully!');

            // Refresh logic
            if (activeClass) {
                // If we added a student to the current class, refresh students
                // If we added to a different class, well, just refresh the list
                if (data.className === activeClass) {
                    loadStudentsView(activeClass);
                }
            } else {
                loadClassesView();
            }

        } catch (err) {
            console.error(err);
            alert('Error: ' + err.message);
        } finally {
            submitBtn.innerText = originalText;
            submitBtn.disabled = false;
        }
    }
});

async function loadClassesView() {
    currentView = 'classes';
    activeClass = null;

    document.getElementById('classes-view').style.display = 'block';
    document.getElementById('students-view').style.display = 'none';
    document.getElementById('breadcrumb').style.display = 'none';

    const container = document.getElementById('classes-container');
    container.innerHTML = '<div style="grid-column:1/-1; text-align:center; color:var(--text-secondary);">Loading...</div>';

    try {
        const res = await fetch(`${API_BASE}/classes`);
        const classes = await res.json();

        if (classes.length === 0) {
            container.innerHTML = `
                <div style="grid-column:1/-1; text-align:center; padding: 40px; color:var(--text-secondary);">
                    <ion-icon name="folder-open-outline" style="font-size: 3rem; margin-bottom:10px;"></ion-icon><br>
                    No classes found. <br>Click "Add Student" to create your first class.
                </div>
            `;
            return;
        }

        container.innerHTML = classes.map(cls => `
            <div class="class-card" onclick="loadStudentsView('${cls.name}')">
                <div class="class-icon"><ion-icon name="easel-outline"></ion-icon></div>
                <div class="class-name">${cls.name}</div>
                <div class="student-count">${cls.count} Students</div>
            </div>
        `).join('');

    } catch (err) {
        container.innerHTML = `<div style="color:red;">Failed to load classes: ${err.message}</div>`;
    }
}

async function loadStudentsView(className) {
    currentView = 'students';
    activeClass = className;

    document.getElementById('classes-view').style.display = 'none';
    document.getElementById('students-view').style.display = 'block';

    // Setup Breadcrumb
    const breadcrumb = document.getElementById('breadcrumb');
    breadcrumb.style.display = 'flex';
    document.getElementById('current-class-name').innerText = className;

    const container = document.getElementById('students-container');
    container.innerHTML = '<div style="grid-column:1/-1; text-align:center; color:var(--text-secondary);">Loading students...</div>';

    try {
        const res = await fetch(`${API_BASE}?class=${encodeURIComponent(className)}`);
        const students = await res.json();

        if (students.length === 0) {
            container.innerHTML = '<div style="grid-column:1/-1; text-align:center;">No students in this class yet.</div>';
            return;
        }

        container.innerHTML = students.map(s => `
            <div class="student-card">
                <img src="${PHOTO_BASE}${s.photoPath}" class="student-photo" alt="${s.name}" onerror="this.src='https://via.placeholder.com/200?text=No+Photo'">
                <div class="student-info">
                    <div class="student-name" title="${s.name}">${s.name}</div>
                    <div class="student-roll">Roll: ${s.rollNo}</div>
                </div>
            </div>
        `).join('');

    } catch (err) {
        container.innerHTML = `<div style="color:red;">Failed to load students.</div>`;
    }
}
