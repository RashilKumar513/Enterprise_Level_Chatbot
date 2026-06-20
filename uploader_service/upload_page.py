UPLOAD_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DocumentBrain — Upload</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: 'Segoe UI', system-ui, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 24px;
        }
        .container {
            background: #fff;
            border-radius: 20px;
            padding: 40px;
            max-width: 520px;
            width: 100%;
            box-shadow: 0 20px 60px rgba(0,0,0,0.2);
        }
        .logo { font-size: 2.5rem; text-align: center; margin-bottom: 8px; }
        h1 { text-align: center; font-size: 1.5rem; color: #1f2937; margin-bottom: 6px; }
        .tagline { text-align: center; color: #6b7280; font-size: 0.9rem; margin-bottom: 24px; }
        label { display: block; font-size: 0.85rem; color: #374151; margin-bottom: 6px; font-weight: 600; }
        input[type="text"], input[type="password"] {
            width: 100%; padding: 12px; border: 1px solid #e5e7eb;
            border-radius: 10px; margin-bottom: 14px; font-size: 0.95rem;
        }
        .drop-zone {
            border: 2px dashed #c4b5fd; border-radius: 16px; padding: 32px 20px;
            text-align: center; background: #faf5ff; cursor: pointer; margin-bottom: 16px;
        }
        .drop-zone:hover, .drop-zone.dragover { border-color: #7c3aed; background: #f3e8ff; }
        .drop-zone .icon { font-size: 2rem; margin-bottom: 8px; }
        .drop-zone p { color: #6b7280; font-size: 0.9rem; }
        .filename { color: #7c3aed; font-weight: 600; margin-top: 8px; font-size: 0.9rem; }
        #fileInput { display: none; }
        .btn {
            width: 100%; padding: 13px; background: #7c3aed; color: white;
            border: none; border-radius: 12px; font-size: 1rem; font-weight: 600;
            cursor: pointer; margin-top: 4px;
        }
        .btn:hover { background: #6d28d9; }
        .btn:disabled { background: #d1d5db; cursor: not-allowed; }
        .btn-secondary { background: #f3f4f6; color: #374151; margin-top: 10px; }
        .btn-secondary:hover { background: #e5e7eb; }
        .btn-danger { background: #ef4444; padding: 6px 12px; width: auto; font-size: 0.8rem; margin: 0; }
        .btn-danger:hover { background: #dc2626; }
        .result { margin-top: 16px; padding: 14px; border-radius: 12px; display: none; font-size: 0.9rem; }
        .result.success { display: block; background: #ecfdf5; border: 1px solid #6ee7b7; color: #065f46; }
        .result.error { display: block; background: #fef2f2; border: 1px solid #fca5a5; color: #991b1b; }
        .hidden { display: none; }
        .user-bar {
            display: flex; justify-content: space-between; align-items: center;
            background: #f9fafb; padding: 10px 14px; border-radius: 10px;
            margin-bottom: 20px; font-size: 0.85rem; color: #4b5563;
        }
        .docs-list { margin-top: 20px; border-top: 1px solid #f3f4f6; padding-top: 16px; }
        .docs-list h3 { font-size: 0.9rem; color: #374151; margin-bottom: 10px; }
        .doc-item {
            display: flex; justify-content: space-between; align-items: center;
            padding: 10px 0; border-bottom: 1px solid #f9fafb; font-size: 0.9rem;
        }
        .footer { margin-top: 24px; text-align: center; font-size: 0.85rem; color: #9ca3af; }
        .footer a { color: #7c3aed; text-decoration: none; font-weight: 500; }
        .hint { font-size: 0.78rem; color: #9ca3af; text-align: center; margin-top: 10px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="logo">📤</div>
        <h1>DocumentBrain Upload</h1>
        <p class="tagline">Admin login required to upload or manage documents</p>

        <!-- Login -->
        <div id="loginSection">
            <label>Username</label>
            <input type="text" id="username" placeholder="admin" autocomplete="username">
            <label>Password</label>
            <input type="password" id="password" placeholder="password" autocomplete="current-password">
            <button class="btn" id="loginBtn" onclick="login()">Sign In</button>
            <div id="loginError" class="result error hidden"></div>
        </div>

        <!-- Upload (after login) -->
        <div id="uploadSection" class="hidden">
            <div class="user-bar">
                <span>Signed in as <strong id="userLabel"></strong></span>
                <button class="btn btn-secondary" style="width:auto;padding:6px 14px;font-size:0.8rem;" onclick="logout()">Logout</button>
            </div>

            <div class="drop-zone" id="dropZone" onclick="document.getElementById('fileInput').click()">
                <div class="icon">📁</div>
                <p>Click to browse or drag & drop your file</p>
                <p class="filename" id="fileName"></p>
            </div>
            <input type="file" id="fileInput" accept=".pdf,.docx,.png,.jpg,.jpeg">
            <button class="btn" id="uploadBtn" disabled onclick="uploadFile()">Upload & Index Document</button>
            <p class="hint">Supported: PDF · DOCX · PNG · JPG · JPEG</p>
            <div id="result" class="result"></div>

            <div class="docs-list" id="docsList" style="display:none">
                <h3>Indexed Documents</h3>
                <div id="docsItems"></div>
            </div>
        </div>

        <div class="footer">
            After uploading, open the <a href="http://localhost:8501" target="_blank">Chatbot App →</a>
        </div>
    </div>

    <script>
        let selectedFile = null;
        let authHeader = "";

        const loginSection = document.getElementById("loginSection");
        const uploadSection = document.getElementById("uploadSection");
        const dropZone = document.getElementById("dropZone");
        const fileInput = document.getElementById("fileInput");
        const uploadBtn = document.getElementById("uploadBtn");
        const fileName = document.getElementById("fileName");
        const result = document.getElementById("result");

        function showLogin() {
            loginSection.classList.remove("hidden");
            uploadSection.classList.add("hidden");
        }

        function showUpload(username) {
            loginSection.classList.add("hidden");
            uploadSection.classList.remove("hidden");
            document.getElementById("userLabel").textContent = username;
            loadDocuments();
        }

        async function login() {
            const user = document.getElementById("username").value.trim();
            const pass = document.getElementById("password").value;
            const err = document.getElementById("loginError");
            const loginBtn = document.getElementById("loginBtn");
            err.classList.add("hidden");

            if (!user || !pass) {
                err.textContent = "Please enter username and password.";
                err.classList.remove("hidden");
                return;
            }

            loginBtn.disabled = true;
            loginBtn.textContent = "Signing in...";

            try {
                const res = await fetch("/auth/login", {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({username: user, password: pass}),
                });
                const data = await res.json();
                if (!res.ok) {
                    throw new Error(data.detail || "Invalid username or password");
                }
                authHeader = "Basic " + btoa(user + ":" + pass);
                sessionStorage.setItem("db_auth", authHeader);
                sessionStorage.setItem("db_user", user);
                showUpload(user);
            } catch (e) {
                err.textContent = e.message;
                err.classList.remove("hidden");
            }

            loginBtn.disabled = false;
            loginBtn.textContent = "Sign In";
        }

        function logout() {
            authHeader = "";
            sessionStorage.removeItem("db_auth");
            sessionStorage.removeItem("db_user");
            selectedFile = null;
            fileName.textContent = "";
            showLogin();
        }

        function authFetch(url, options = {}) {
            options.headers = options.headers || {};
            options.headers["Authorization"] = authHeader;
            return fetch(url, options);
        }

        function escHtml(text) {
            const d = document.createElement("div");
            d.textContent = text;
            return d.innerHTML;
        }

        fileInput.addEventListener("change", (e) => {
            if (e.target.files[0]) setFile(e.target.files[0]);
        });

        dropZone.addEventListener("dragover", (e) => { e.preventDefault(); dropZone.classList.add("dragover"); });
        dropZone.addEventListener("dragleave", () => dropZone.classList.remove("dragover"));
        dropZone.addEventListener("drop", (e) => {
            e.preventDefault();
            dropZone.classList.remove("dragover");
            if (e.dataTransfer.files[0]) setFile(e.dataTransfer.files[0]);
        });

        function setFile(file) {
            selectedFile = file;
            fileName.textContent = file.name;
            uploadBtn.disabled = false;
            result.className = "result";
            result.textContent = "";
        }

        async function uploadFile() {
            if (!selectedFile) return;
            uploadBtn.disabled = true;
            uploadBtn.textContent = "Processing...";
            result.className = "result";
            result.textContent = "Uploading and indexing...";

            const formData = new FormData();
            formData.append("file", selectedFile);

            try {
                const response = await authFetch("/upload", { method: "POST", body: formData });
                const data = await response.json();
                if (response.status === 401) { logout(); throw new Error("Session expired. Please sign in again."); }
                if (!response.ok) throw new Error(data.detail || "Upload failed");

                result.className = "result success";
                result.innerHTML = "<strong>Upload successful!</strong> File: <strong>" + selectedFile.name + "</strong>";
                selectedFile = null;
                fileName.textContent = "";
                fileInput.value = "";
                loadDocuments();
            } catch (err) {
                result.className = "result error";
                result.textContent = err.message;
            }

            uploadBtn.disabled = false;
            uploadBtn.textContent = "Upload & Index Document";
        }

        async function deleteDoc(id, name) {
            if (!confirm("Delete '" + name + "' from the database?")) return;
            try {
                const response = await authFetch("/documents/" + id, { method: "DELETE" });
                const data = await response.json();
                if (response.status === 401) { logout(); throw new Error("Session expired."); }
                if (!response.ok) throw new Error(data.detail || "Delete failed");
                loadDocuments();
            } catch (err) {
                alert(err.message);
            }
        }

        async function loadDocuments() {
            try {
                const res = await fetch("/documents");
                const data = await res.json();
                const docs = data.documents || [];
                const list = document.getElementById("docsList");
                const items = document.getElementById("docsItems");

                if (docs.length === 0) {
                    list.style.display = "none";
                    return;
                }

                list.style.display = "block";
                items.innerHTML = docs.map(d =>
                    '<div class="doc-item"><span>📄 ' + escHtml(d.filename) + '</span>' +
                    '<button class="btn btn-danger" data-id="' + d.document_id +
                    '" data-name="' + escHtml(d.filename) + '">Delete</button></div>'
                ).join("");

                items.querySelectorAll(".btn-danger").forEach(btn => {
                    btn.addEventListener("click", () =>
                        deleteDoc(btn.dataset.id, btn.dataset.name));
                });
            } catch (_) {}
        }

        async function verifyStoredSession() {
            const saved = sessionStorage.getItem("db_auth");
            const savedUser = sessionStorage.getItem("db_user");
            if (!saved || !savedUser) return;

            authHeader = saved;
            try {
                const res = await fetch("/auth/verify", {
                    headers: {"Authorization": authHeader},
                });
                if (res.ok) {
                    showUpload(savedUser);
                } else {
                    logout();
                }
            } catch (_) {
                logout();
            }
        }

        verifyStoredSession();

        document.getElementById("password").addEventListener("keydown", (e) => {
            if (e.key === "Enter") login();
        });
    </script>
</body>
</html>
"""
