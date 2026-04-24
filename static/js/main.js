document.addEventListener('DOMContentLoaded', () => {
    // --- GLOBAL UTILS ---
    const setupCamera = async (videoId) => {
        const video = document.getElementById(videoId);
        if (!video) return null;
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ video: true });
            video.srcObject = stream;
            return stream;
        } catch (err) {
            console.error("Camera error:", err);
            return null;
        }
    };

    // --- STUDENT ENROLLMENT (registration.html) ---
    const regVideo = document.getElementById('video-reg');
    const captureBtn = document.getElementById('capture-btn');
    const openCamBtn = document.getElementById('open-camera-btn');
    const roleSelect = document.getElementById('reg-role');
    const passwordGroup = document.getElementById('password-group');

    if (roleSelect && passwordGroup) {
        roleSelect.addEventListener('change', () => {
            passwordGroup.style.display = roleSelect.value === 'Faculty' ? 'block' : 'none';
        });
    }

    if (openCamBtn) {
        openCamBtn.addEventListener('click', async () => {
            openCamBtn.disabled = true;
            openCamBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Starting...';
            const stream = await setupCamera('video-reg');
            if (stream) {
                document.getElementById('camera-placeholder').style.display = 'none';
                document.getElementById('capture-container').style.display = 'block';
                document.getElementById('capture-controls').style.display = 'flex';
            } else {
                alert("Could not access camera.");
                openCamBtn.disabled = false;
                openCamBtn.innerHTML = '<i class="fas fa-play"></i> Initialize Camera';
            }
        });
    }

    if (regVideo && captureBtn) {
        captureBtn.addEventListener('click', async () => {
            const name = document.getElementById('reg-name').value;
            const roll = document.getElementById('reg-roll').value;
            const course = document.getElementById('reg-course').value;
            const phone = document.getElementById('reg-phone').value;
            const dob = document.getElementById('reg-dob').value;
            const email = document.getElementById('reg-email').value;
            const role = document.getElementById('reg-role').value;
            const password = document.getElementById('reg-password').value;

            if (!name || !roll) {
                alert("Please enter Name and Roll Number");
                return;
            }

            if (role === 'Faculty' && !password) {
                alert("Password is required for Faculty/Staff login access");
                return;
            }

            const canvas = document.getElementById('canvas-reg');
            canvas.width = regVideo.videoWidth;
            canvas.height = regVideo.videoHeight;
            canvas.getContext('2d').drawImage(regVideo, 0, 0);
            const imageData = canvas.toDataURL('image/jpeg');

            const statusEl = document.getElementById('reg-status');
            statusEl.innerText = "Processing Enrollment... Please wait.";
            statusEl.style.color = "var(--primary)";

            try {
                const response = await fetch('/register', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ name, roll, course, phone, dob, email, role, password, image: imageData })
                });
                const result = await response.json();

                if (result.success) {
                    statusEl.innerHTML = `<span style="color:var(--success)"><i class="fas fa-check-circle"></i> ${result.message}</span>`;
                    setTimeout(() => window.location.reload(), 2000);
                } else {
                    statusEl.innerHTML = `<span style="color:var(--danger)"><i class="fas fa-times-circle"></i> ${result.message}</span>`;
                }
            } catch (err) {
                statusEl.innerText = "Error saving data.";
            }
        });
    }

    // --- LIVE ATTENDANCE (attendance.html) ---
    const startBtn = document.getElementById('start-btn');
    const stopBtn = document.getElementById('stop-btn');
    const statusMsg = document.getElementById('status-msg');
    let recognitionInterval = null;
    let mainStream = null;

    if (startBtn) {
        startBtn.addEventListener('click', async () => {
            mainStream = await setupCamera('video');
            if (!mainStream) {
                statusMsg.innerText = "Error: Camera access denied.";
                statusMsg.style.color = "var(--danger)";
                return;
            }

            startBtn.style.display = 'none';
            stopBtn.style.display = 'inline-flex';
            document.getElementById('scan-line').style.display = 'block';
            statusMsg.innerText = "System Active: Scanning for attendees...";
            statusMsg.style.color = "var(--primary)";

            recognitionInterval = setInterval(async () => {
                const video = document.getElementById('video');
                const canvas = document.createElement('canvas');
                canvas.width = video.videoWidth;
                canvas.height = video.videoHeight;
                canvas.getContext('2d').drawImage(video, 0, 0);
                const imageData = canvas.toDataURL('image/jpeg');

                try {
                    const response = await fetch('/mark_attendance', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ image: imageData })
                    });
                    const result = await response.json();

                    if (result.success && result.marked.length > 0) {
                        statusMsg.innerHTML = `<span style="color:var(--success)"><i class="fas fa-user-check"></i> Verified: ${result.marked.join(', ')}</span>`;
                        const scanLine = document.getElementById('scan-line');
                        scanLine.style.background = "var(--success)";
                        setTimeout(() => scanLine.style.background = "var(--primary)", 500);
                    } else if (result.success === false) {
                        // Handle Proxy Blocking
                        statusMsg.innerHTML = `<span style="color:var(--danger)"><i class="fas fa-shield-alt"></i> ${result.message}</span>`;
                        const scanLine = document.getElementById('scan-line');
                        scanLine.style.background = "var(--danger)";
                    }
                } catch (err) {
                    console.error("Loop Error:", err);
                }
            }, 3000);
        });

        stopBtn.addEventListener('click', () => {
            clearInterval(recognitionInterval);
            if (mainStream) {
                mainStream.getTracks().forEach(track => track.stop());
            }
            startBtn.style.display = 'inline-flex';
            stopBtn.style.display = 'none';
            document.getElementById('scan-line').style.display = 'none';
            statusMsg.innerText = "System Paused.";
            statusMsg.style.color = "var(--text-muted)";
        });
    }

    // --- ABSENTEE ALERTS ---
    const alertBtn = document.getElementById('alert-btn');
    if (alertBtn) {
        alertBtn.addEventListener('click', async () => {
            alertBtn.disabled = true;
            alertBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Sending...';

            try {
                const response = await fetch('/api/send_absent_alerts', { method: 'POST' });
                const result = await response.json();
                alert(result.message);
            } catch (err) {
                alert("Error sending alerts.");
            } finally {
                alertBtn.disabled = false;
                alertBtn.innerHTML = '<i class="fas fa-paper-plane"></i> Alert Absentees';
            }
        });
    }

    // --- MANAGEMENT ACTIONS (registration.html) ---
    window.openEditModal = async (sid) => {
        console.log("Opening edit modal for ID:", sid);
        try {
            const response = await fetch(`/api/student/${sid}`);
            const data = await response.json();
            console.log("Fetched data:", data);

            document.getElementById('edit-id').value = data.id;
            document.getElementById('edit-name').value = data.name;
            document.getElementById('edit-roll').value = data.roll;
            document.getElementById('edit-course').value = data.course;
            document.getElementById('edit-phone').value = data.phone || '';
            document.getElementById('edit-dob').value = data.dob || '';
            document.getElementById('edit-email').value = data.email || '';
            document.getElementById('edit-role').value = data.role;
            document.getElementById('edit-password').value = '';

            document.getElementById('edit-password-group').style.display = data.role === 'Faculty' ? 'block' : 'none';
            document.getElementById('edit-modal').style.display = 'flex';
        } catch (err) {
            console.error("Fetch error:", err);
            alert("Error fetching data.");
        }
    };

    window.closeEditModal = () => {
        document.getElementById('edit-modal').style.display = 'none';
    };

    const editRole = document.getElementById('edit-role');
    if (editRole) {
        editRole.addEventListener('change', (e) => {
            document.getElementById('edit-password-group').style.display = e.target.value === 'Faculty' ? 'block' : 'none';
        });
    }

    const updateBtn = document.getElementById('update-btn');
    if (updateBtn) {
        updateBtn.addEventListener('click', async () => {
            const sid = document.getElementById('edit-id').value;
            console.log("Updating record ID:", sid);
            const payload = {
                name: document.getElementById('edit-name').value,
                roll: document.getElementById('edit-roll').value,
                course: document.getElementById('edit-course').value,
                phone: document.getElementById('edit-phone').value,
                dob: document.getElementById('edit-dob').value,
                email: document.getElementById('edit-email').value,
                role: document.getElementById('edit-role').value,
                password: document.getElementById('edit-password').value
            };

            updateBtn.disabled = true;
            updateBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Updating...';

            try {
                const response = await fetch(`/api/student/update/${sid}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const result = await response.json();
                console.log("Update result:", result);
                if (result.success) {
                    window.location.reload();
                } else {
                    alert("Update failed: " + result.message);
                }
            } catch (err) {
                console.error("Update error:", err);
                alert("Error connecting to server.");
            } finally {
                updateBtn.disabled = false;
                updateBtn.innerHTML = '<i class="fas fa-check-circle"></i> Update Information';
            }
        });
    }

    window.deleteRecord = async (sid) => {
        if (!confirm("Are you sure? This will permanently delete the record and the associated face data.")) return;

        try {
            const response = await fetch(`/api/student/delete/${sid}`, { method: 'POST' });
            const result = await response.json();
            
            if (result.success) {
                window.location.reload();
            } else {
                alert(result.message || "Delete failed.");
            }
        } catch (err) {
            console.error("Delete error:", err);
            alert("Delete failed: Error connecting to server.");
        }
    };
});
