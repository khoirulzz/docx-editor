/**
 * AI DOCX Academic Editor — Studio Revisi & Sitasi
 * Vanilla JavaScript Single-Page Application (Cloudflare Pages compatible)
 */

document.addEventListener("DOMContentLoaded", () => {
    // --- State Management ---
    let apiBaseUrl = localStorage.getItem("docx_api_base") || "https://docx-editor-8v0s.onrender.com";
    let currentSessionId = null;
    let currentProposalId = null;
    let currentVersion = 1;
    let activeOperations = [];

    // --- DOM Elements ---
    const serverHealthBadge = document.getElementById("serverHealthBadge");
    const settingsBtn = document.getElementById("settingsBtn");
    const settingsModal = document.getElementById("settingsModal");
    const closeSettingsBtn = document.getElementById("closeSettingsBtn");
    const saveSettingsBtn = document.getElementById("saveSettingsBtn");
    const resetApiBtn = document.getElementById("resetApiBtn");
    const apiBaseInput = document.getElementById("apiBaseInput");

    const dropzone = document.getElementById("dropzone");
    const docxFileInput = document.getElementById("docxFileInput");
    const uploadProgress = document.getElementById("uploadProgress");
    const progressFill = document.getElementById("progressFill");
    const progressText = document.getElementById("progressText");
    const activeDocCard = document.getElementById("activeDocCard");
    const docFileName = document.getElementById("docFileName");
    const docStats = document.getElementById("docStats");
    const newUploadBtn = document.getElementById("newUploadBtn");
    const sessionBadge = document.getElementById("sessionBadge");

    const outlineTree = document.getElementById("outlineTree");
    const chatMessages = document.getElementById("chatMessages");
    const chatForm = document.getElementById("chatForm");
    const instructionInput = document.getElementById("instructionInput");
    const targetScope = document.getElementById("targetScope");
    const citationStyle = document.getElementById("citationStyle");
    const sendBtn = document.getElementById("sendBtn");

    const proposalBadge = document.getElementById("proposalBadge");
    const proposalContainer = document.getElementById("proposalContainer");
    const proposalFooter = document.getElementById("proposalFooter");
    const commitProposalBtn = document.getElementById("commitProposalBtn");
    const rejectProposalBtn = document.getElementById("rejectProposalBtn");
    const downloadCard = document.getElementById("downloadCard");
    const downloadBtn = document.getElementById("downloadBtn");
    const newVersionNum = document.getElementById("newVersionNum");
    const toastContainer = document.getElementById("toastContainer");

    // Initialize API Base Input
    apiBaseInput.value = apiBaseUrl;

    // --- Toast Notification Helper ---
    function showToast(message, type = "info") {
        const toast = document.createElement("div");
        toast.className = `toast toast-${type}`;
        const icons = { info: "ℹ️", success: "✔", error: "⚠" };
        toast.innerHTML = `<span>${icons[type] || ""}</span> <span>${message}</span>`;
        toastContainer.appendChild(toast);
        setTimeout(() => {
            toast.style.opacity = "0";
            toast.style.transform = "translateX(100%)";
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    }

    // --- Server Health Monitor ---
    async function checkHealth() {
        serverHealthBadge.className = "health-badge status-checking";
        serverHealthBadge.innerHTML = `<span class="pulse-dot"></span><span class="health-label">Memeriksa Server...</span>`;
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 12000);
            const res = await fetch(`${apiBaseUrl.rstrip("/")}/health`, { signal: controller.signal });
            clearTimeout(timeoutId);
            if (res.ok) {
                const data = await res.json();
                serverHealthBadge.className = "health-badge status-online";
                serverHealthBadge.innerHTML = `<span class="pulse-dot"></span><span class="health-label">🟢 Server Render Aktif (${data.version || "1.0.0"})</span>`;
            } else {
                throw new Error("HTTP non-ok");
            }
        } catch (err) {
            serverHealthBadge.className = "health-badge status-offline";
            serverHealthBadge.innerHTML = `<span class="pulse-dot"></span><span class="health-label">🟡 Server Sedang Bangun / Tidur...</span>`;
        }
    }

    String.prototype.rstrip = function (chars) {
        let str = this;
        while (str.endsWith(chars)) str = str.slice(0, -1);
        return str;
    };

    checkHealth();
    setInterval(checkHealth, 25000);

    // --- Settings Modal Events ---
    settingsBtn.addEventListener("click", () => settingsModal.classList.remove("hidden"));
    closeSettingsBtn.addEventListener("click", () => settingsModal.classList.add("hidden"));
    resetApiBtn.addEventListener("click", () => {
        apiBaseInput.value = "https://docx-editor-8v0s.onrender.com";
    });
    saveSettingsBtn.addEventListener("click", () => {
        let url = apiBaseInput.value.trim().rstrip("/");
        if (!url) url = "https://docx-editor-8v0s.onrender.com";
        apiBaseUrl = url;
        localStorage.setItem("docx_api_base", apiBaseUrl);
        settingsModal.classList.add("hidden");
        showToast("Konfigurasi API berhasil disimpan!", "success");
        checkHealth();
    });

    // --- File Upload & Drag-and-Drop ---
    dropzone.addEventListener("click", () => docxFileInput.click());
    dropzone.addEventListener("dragover", (e) => {
        e.preventDefault();
        dropzone.classList.add("drag-over");
    });
    dropzone.addEventListener("dragleave", () => dropzone.classList.remove("drag-over"));
    dropzone.addEventListener("drop", (e) => {
        e.preventDefault();
        dropzone.classList.remove("drag-over");
        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            handleFileUpload(e.dataTransfer.files[0]);
        }
    });
    docxFileInput.addEventListener("change", () => {
        if (docxFileInput.files && docxFileInput.files[0]) {
            handleFileUpload(docxFileInput.files[0]);
        }
    });

    newUploadBtn.addEventListener("click", () => {
        currentSessionId = null;
        currentProposalId = null;
        activeOperations = [];
        activeDocCard.classList.add("hidden");
        dropzone.classList.remove("hidden");
        outlineTree.innerHTML = `<div class="empty-state"><span>Belum ada dokumen yang diunggah. Unggah file .docx untuk melihat struktur bab.</span></div>`;
        sessionBadge.classList.add("hidden");
        instructionInput.disabled = true;
        sendBtn.disabled = true;
        proposalContainer.innerHTML = `<div class="empty-state"><div class="shield-icon">🔐</div><h3>Belum ada proposal aktif</h3><p>Unggah dokumen dan kirim instruksi chat untuk menyusun revisi L1-L5.</p></div>`;
        proposalFooter.classList.add("hidden");
        downloadCard.classList.add("hidden");
    });

    async function handleFileUpload(file) {
        if (!file.name.endsWith(".docx")) {
            showToast("Harap pilih file dokumen berformat .docx", "error");
            return;
        }
        if (file.size > 52428800) {
            showToast("Ukuran file melebihi batas maksimal 50 MB", "error");
            return;
        }

        dropzone.classList.add("hidden");
        uploadProgress.classList.remove("hidden");
        progressFill.style.width = "30%";
        progressText.innerText = "Mengunggah paket Office Open XML...";

        const formData = new FormData();
        formData.append("file", file);

        try {
            progressFill.style.width = "65%";
            progressText.innerText = "Menginspeksi struktur OPC & mengekstrak bab...";

            const res = await fetch(`${apiBaseUrl.rstrip("/")}/v1/sessions`, {
                method: "POST",
                body: formData
            });

            if (!res.ok) {
                const errData = await res.json().catch(() => ({}));
                throw new Error(errData.detail || `Upload gagal dengan status HTTP ${res.status}`);
            }

            const data = await res.json();
            currentSessionId = data.session_id;
            currentVersion = 1;

            progressFill.style.width = "100%";
            setTimeout(() => {
                uploadProgress.classList.add("hidden");
                activeDocCard.classList.remove("hidden");
                docFileName.innerText = file.name;
                docStats.innerText = `Sesi Aktif: ${currentSessionId.slice(0, 8)}... • Siap Direvisi`;
                sessionBadge.innerText = `Sesi: ${currentSessionId.slice(0, 8)}`;
                sessionBadge.classList.remove("hidden");
                instructionInput.disabled = false;
                sendBtn.disabled = false;
                showToast("Dokumen berhasil diunggah dan diinspeksi!", "success");
                loadDocumentGraph();
            }, 600);

        } catch (err) {
            uploadProgress.classList.add("hidden");
            dropzone.classList.remove("hidden");
            showToast(`Gagal mengunggah: ${err.message}`, "error");
        }
    }

    async function loadDocumentGraph() {
        if (!currentSessionId) return;
        try {
            const res = await fetch(`${apiBaseUrl.rstrip("/")}/v1/sessions/${currentSessionId}/graph`);
            if (!res.ok) return;
            const graph = await res.json();

            // Populate outline tree and target scope options
            if (graph.nodes && graph.nodes.length > 0) {
                outlineTree.innerHTML = "";
                targetScope.innerHTML = `<option value="all">Seluruh Dokumen (Otomatis deteksi bab)</option>`;

                graph.nodes.forEach((node, idx) => {
                    const item = document.createElement("div");
                    item.className = "outline-item";
                    item.innerHTML = `
                        <span><strong>#${idx + 1}</strong> ${node.text ? node.text.slice(0, 32) + (node.text.length > 32 ? "..." : "") : "Paragraf / Heading"}</span>
                        <span class="para-count">${node.type || "para"}</span>
                    `;
                    item.addEventListener("click", () => {
                        instructionInput.value = `Tolong perbaiki paragraf ke-${idx + 1}: "${node.text ? node.text.slice(0, 40) : ""}"`;
                        instructionInput.focus();
                    });
                    outlineTree.appendChild(item);

                    // Add to dropdown
                    const opt = document.createElement("option");
                    opt.value = node.node_id;
                    opt.innerText = `Paragraf #${idx + 1}: ${node.text ? node.text.slice(0, 25) : "Section"}`;
                    targetScope.appendChild(opt);
                });
            } else {
                outlineTree.innerHTML = `<div class="empty-state"><span>Struktur paragraf telah diindeks dalam memori.</span></div>`;
            }
        } catch (e) {
            console.error("Graph fetch err:", e);
        }
    }

    // --- Chat & Planning Events ---
    chatForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const text = instructionInput.value.trim();
        if (!text || !currentSessionId) return;

        appendChatMessage("user", text);
        instructionInput.value = "";
        instructionInput.disabled = true;
        sendBtn.disabled = true;

        const loadingId = appendChatMessage("assistant", "⏳ <em>Menganalisis instruksi & menyusun rencana revisi deterministik (L1-L5)...</em>");

        try {
            const scopeVal = targetScope.value;
            const payload = {
                instruction: `${text} (Format Sitasi yang diinginkan: ${citationStyle.value})`,
                target_scope: scopeVal === "all" ? null : scopeVal
            };

            const res = await fetch(`${apiBaseUrl.rstrip("/")}/v1/sessions/${currentSessionId}/chat`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });

            if (!res.ok) {
                const errData = await res.json().catch(() => ({}));
                throw new Error(errData.detail || `Chat API returned status ${res.status}`);
            }

            const data = await res.json();
            currentProposalId = data.proposal_id;
            activeOperations = (data.plan && data.plan.operations) || [];

            // Remove loading msg
            const lNode = document.getElementById(loadingId);
            if (lNode) lNode.remove();

            appendChatMessage("assistant", `
                <h4>Rencana Revisi Selesai Disusun!</h4>
                <p>AI telah mengolah instruksi Anda menjadi <code>${activeOperations.length} operasi edit deterministik</code> dengan ringkasan: <strong>"${(data.plan && data.plan.instruction_summary) || text}"</strong>.</p>
                <p>Silakan tinjau perbandingan (*Before / After diff*) pada panel kanan sebelum menyetujui perubahan.</p>
            `);

            renderProposalReview(data.plan);

        } catch (err) {
            const lNode = document.getElementById(loadingId);
            if (lNode) lNode.remove();
            appendChatMessage("assistant", `⚠ <strong>Gagal memproses instruksi:</strong> ${err.message}. Pastikan API Key Blackbox telah terpasang di server Render Anda.`);
            showToast(`Error: ${err.message}`, "error");
        } finally {
            instructionInput.disabled = false;
            sendBtn.disabled = false;
            instructionInput.focus();
        }
    });

    function appendChatMessage(role, htmlOrText) {
        const id = "msg_" + Math.random().toString(36).substr(2, 9);
        const msgDiv = document.createElement("div");
        msgDiv.id = id;
        msgDiv.className = `message ${role === "user" ? "user-msg" : "assistant-msg"}`;
        msgDiv.innerHTML = `
            <div class="msg-avatar">${role === "user" ? "👤" : "🤖"}</div>
            <div class="msg-content">${role === "user" ? `<p>${htmlOrText}</p>` : htmlOrText}</div>
        `;
        chatMessages.appendChild(msgDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        return id;
    }

    // --- Proposal & Diff Rendering ---
    function renderProposalReview(plan) {
        proposalContainer.innerHTML = "";
        proposalBadge.innerText = `${activeOperations.length} Operasi Tertunda`;
        proposalBadge.className = "badge badge-version";
        downloadCard.classList.add("hidden");

        if (!activeOperations || activeOperations.length === 0) {
            proposalContainer.innerHTML = `<div class="empty-state"><span>Tidak ada operasi modifikasi yang diperlukan berdasarkan instruksi Anda.</span></div>`;
            proposalFooter.classList.add("hidden");
            return;
        }

        activeOperations.forEach((op, idx) => {
            const card = document.createElement("div");
            card.className = "proposal-card";
            
            let diffHtml = "";
            if (op.type === "replace_text_span") {
                diffHtml = `
                    <div class="diff-box">
                        <div class="diff-old">- ${op.original_span || "Teks lama..."}</div>
                        <div class="diff-new">+ ${op.new_span || "Teks baru..."}</div>
                    </div>
                `;
            } else if (op.type === "insert_paragraph") {
                diffHtml = `
                    <div class="diff-box">
                        <div class="diff-new">+ [Paragraf Baru] ${op.text || op.content || ""}</div>
                    </div>
                `;
            } else {
                diffHtml = `<div class="diff-box"><div class="diff-new">Operasi: ${op.type}</div></div>`;
            }

            card.innerHTML = `
                <div class="proposal-card-header">
                    <strong>#${idx + 1} Target: <code>${op.target_node_id || "document"}</code></strong>
                    <span class="op-type-badge">${op.type}</span>
                </div>
                ${diffHtml}
            `;
            proposalContainer.appendChild(card);
        });

        proposalFooter.classList.remove("hidden");
    }

    rejectProposalBtn.addEventListener("click", () => {
        currentProposalId = null;
        activeOperations = [];
        proposalContainer.innerHTML = `<div class="empty-state"><div class="shield-icon">✕</div><h3>Proposal Ditolak</h3><p>Anda dapat memberikan instruksi chat baru untuk menghasilkan revisi lain.</p></div>`;
        proposalFooter.classList.add("hidden");
        proposalBadge.innerText = "Ditolak";
        proposalBadge.className = "badge badge-neutral";
        showToast("Proposal perubahan dibatalkan", "info");
    });

    commitProposalBtn.addEventListener("click", async () => {
        if (!currentSessionId || !currentProposalId) return;
        commitProposalBtn.disabled = true;
        commitProposalBtn.innerText = "⏳ Menerapkan & Memverifikasi XML...";

        try {
            const res = await fetch(`${apiBaseUrl.rstrip("/")}/v1/sessions/${currentSessionId}/proposals/${currentProposalId}/commit`, {
                method: "POST"
            });

            if (!res.ok) {
                const errData = await res.json().catch(() => ({}));
                throw new Error(errData.detail || `Commit gagal dengan status ${res.status}`);
            }

            const data = await res.json();
            currentVersion = (data.new_version || data.version || currentVersion + 1);

            proposalFooter.classList.add("hidden");
            proposalBadge.innerText = `Lolos L1-L5 (v${currentVersion})`;
            proposalBadge.className = "badge badge-version";
            
            // Show download card
            newVersionNum.innerText = currentVersion;
            downloadBtn.href = `${apiBaseUrl.rstrip("/")}/v1/sessions/${currentSessionId}/versions/v${currentVersion}/export`;
            downloadCard.classList.remove("hidden");

            appendChatMessage("assistant", `
                <h4>🎉 Revisi Berhasil Diterapkan ke Dokumen!</h4>
                <p>Dokumen Anda telah diperbarui ke <strong>Versi v${currentVersion}</strong>. Seluruh sitasi Mendeley, tabel, dan struktur dokumen telah terverifikasi aman 100%.</p>
                <p>Klik tombol <strong>Download DOCX Hasil Revisi</strong> di panel kanan untuk mengunduh file baru Anda.</p>
            `);

            showToast("Perubahan berhasil diterapkan ke file .docx!", "success");

        } catch (err) {
            showToast(`Gagal menerapkan perubahan: ${err.message}`, "error");
        } finally {
            commitProposalBtn.disabled = false;
            commitProposalBtn.innerText = "✔ Setujui & Terapkan Perubahan";
        }
    });
});
