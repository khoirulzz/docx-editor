/**
 * AI DOCX Academic Editor — Pro Studio Logic
 * Vanilla JavaScript Single-Page Application (Cloudflare Pages / Light Studio UI)
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
    if (apiBaseInput) apiBaseInput.value = apiBaseUrl;

    // --- Helper for Rstrip ---
    String.prototype.rstrip = function (chars) {
        let str = this;
        while (str.endsWith(chars)) str = str.slice(0, -1);
        return str;
    };

    // --- Toast Notification ---
    function showToast(message, type = "info") {
        const toast = document.createElement("div");
        toast.className = `toast toast-${type}`;
        const icons = { info: "ℹ️", success: "✔", error: "⚠" };
        toast.innerHTML = `<span>${icons[type] || ""}</span> <span>${message}</span>`;
        toastContainer.appendChild(toast);
        setTimeout(() => {
            toast.style.opacity = "0";
            toast.style.transform = "translateX(100%)";
            setTimeout(() => toast.remove(), 250);
        }, 4000);
    }

    // --- Server Health Check ---
    async function checkHealth() {
        if (!serverHealthBadge) return;
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

    checkHealth();
    setInterval(checkHealth, 25000);

    // --- Settings Modal ---
    if (settingsBtn) settingsBtn.addEventListener("click", () => settingsModal.classList.remove("hidden"));
    if (closeSettingsBtn) closeSettingsBtn.addEventListener("click", () => settingsModal.classList.add("hidden"));
    if (resetApiBtn) resetApiBtn.addEventListener("click", () => {
        apiBaseInput.value = "https://docx-editor-8v0s.onrender.com";
    });
    if (saveSettingsBtn) saveSettingsBtn.addEventListener("click", () => {
        let url = apiBaseInput.value.trim().rstrip("/");
        if (!url) url = "https://docx-editor-8v0s.onrender.com";
        apiBaseUrl = url;
        localStorage.setItem("docx_api_base", apiBaseUrl);
        settingsModal.classList.add("hidden");
        showToast("Konfigurasi API berhasil disimpan!", "success");
        checkHealth();
    });

    // --- File Upload & Drag-and-Drop ---
    if (dropzone) {
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
    }

    if (docxFileInput) {
        docxFileInput.addEventListener("change", () => {
            if (docxFileInput.files && docxFileInput.files[0]) {
                handleFileUpload(docxFileInput.files[0]);
            }
        });
    }

    if (newUploadBtn) {
        newUploadBtn.addEventListener("click", () => {
            currentSessionId = null;
            currentProposalId = null;
            activeOperations = [];
            activeDocCard.classList.add("hidden");
            dropzone.classList.remove("hidden");
            outlineTree.innerHTML = `<div class="empty-state"><span>Belum ada dokumen. Unggah file .docx untuk menguraikan struktur bab dan paragraf.</span></div>`;
            sessionBadge.classList.add("hidden");
            instructionInput.disabled = true;
            sendBtn.disabled = true;
            proposalContainer.innerHTML = `<div class="empty-state"><div class="shield-graphic">🔐</div><h3>Belum ada proposal aktif</h3><p>Unggah dokumen dan kirim instruksi chat untuk menyusun revisi L1-L5.</p></div>`;
            proposalFooter.classList.add("hidden");
            downloadCard.classList.add("hidden");
        });
    }

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
                const errMsg = (errData.error && errData.error.message) || errData.detail || errData.message || `Upload gagal dengan status HTTP ${res.status}`;
                throw new Error(errMsg);
            }

            const data = await res.json();
            currentSessionId = data.session_id;
            currentVersion = 1;

            progressFill.style.width = "100%";
            setTimeout(() => {
                uploadProgress.classList.add("hidden");
                activeDocCard.classList.remove("hidden");
                docFileName.innerText = file.name;
                docFileName.title = file.name;
                docStats.innerText = `Sesi Aktif (${currentSessionId.slice(0, 8)}) • Siap Direvisi`;
                sessionBadge.innerText = `Sesi: ${currentSessionId.slice(0, 8)}`;
                sessionBadge.classList.remove("hidden");
                instructionInput.disabled = false;
                sendBtn.disabled = false;
                showToast("Dokumen berhasil diunggah dan diinspeksi!", "success");
                loadDocumentGraph();
            }, 500);

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

            if (graph.nodes && graph.nodes.length > 0) {
                outlineTree.innerHTML = "";
                targetScope.innerHTML = `<option value="all">Seluruh Dokumen (Otomatis deteksi bab)</option>`;

                graph.nodes.forEach((node, idx) => {
                    const item = document.createElement("div");
                    item.className = "outline-item";
                    item.innerHTML = `
                        <span><strong>#${idx + 1}</strong> ${node.text ? node.text.slice(0, 32) + (node.text.length > 32 ? "..." : "") : "Paragraf / Heading"}</span>
                        <span class="para-badge">${node.type || "para"}</span>
                    `;
                    item.addEventListener("click", () => {
                        instructionInput.value = `Tolong perbaiki paragraf ke-${idx + 1}: "${node.text ? node.text.slice(0, 45) : ""}"`;
                        instructionInput.focus();
                    });
                    outlineTree.appendChild(item);

                    const opt = document.createElement("option");
                    opt.value = node.node_id;
                    opt.innerText = `Paragraf #${idx + 1}: ${node.text ? node.text.slice(0, 28) : "Section"}`;
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
    if (chatForm) {
        chatForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const text = instructionInput.value.trim();
            if (!text || !currentSessionId) return;

            appendChatMessage("user", text);
            instructionInput.value = "";
            instructionInput.disabled = true;
            sendBtn.disabled = true;

            const accordionId = "thinking_" + Math.random().toString(36).substr(2, 9);
            const startTimestamp = Date.now();
            appendChatMessage("assistant", `
                <div class="thinking-accordion" id="${accordionId}">
                    <div class="thinking-header" onclick="this.parentElement.classList.toggle('collapsed')">
                        <div class="thinking-header-left">
                            <span class="thinking-pulse-icon"></span>
                            <span class="thinking-title">🧠 AI sedang menganalisis & menyusun strategi...</span>
                        </div>
                        <span class="thinking-toggle-btn">[Klik untuk melihat/sembunyikan log]</span>
                    </div>
                    <div class="thinking-body" id="${accordionId}_body">
                        <div class="thinking-log-line">
                            <span class="thinking-log-time">[00.0s]</span>
                            <span class="thinking-log-text">Memulai alur kerja perencanaan & mutasi dokumen...</span>
                        </div>
                    </div>
                </div>
                <div id="${accordionId}_summary"></div>
            `);

            try {
                const scopeVal = targetScope.value;
                const payload = {
                    instruction: `${text} (Format Sitasi yang diinginkan: ${citationStyle.value})`,
                    target_scope: scopeVal === "all" ? null : scopeVal
                };

                const res = await fetch(`${apiBaseUrl.rstrip("/")}/v1/sessions/${currentSessionId}/chat/stream`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload)
                });

                if (!res.ok) {
                    const errData = await res.json().catch(() => ({}));
                    const errMsg = (errData.error && errData.error.message) || errData.detail || errData.message || `Chat API returned status ${res.status}`;
                    throw new Error(errMsg);
                }

                const reader = res.body.getReader();
                const decoder = new TextDecoder("utf-8");
                let buffer = "";

                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;
                    buffer += decoder.decode(value, { stream: true });

                    const lines = buffer.split("\n\n");
                    buffer = lines.pop() || ""; // keep remainder

                    for (const chunk of lines) {
                        const chunkLines = chunk.split("\n");
                        let eventType = "message";
                        let dataStr = "";

                        for (const l of chunkLines) {
                            if (l.startsWith("event: ")) {
                                eventType = l.substring(7).trim();
                            } else if (l.startsWith("data: ")) {
                                dataStr = l.substring(6).trim();
                            }
                        }

                        if (!dataStr) continue;
                        let dataObj = {};
                        try { dataObj = JSON.parse(dataStr); } catch (err) { continue; }

                        const elapsed = ((Date.now() - startTimestamp) / 1000).toFixed(1) + "s";
                        const bodyEl = document.getElementById(`${accordionId}_body`);

                        if (eventType === "thinking" || eventType === "tool_call") {
                            if (bodyEl) {
                                const line = document.createElement("div");
                                line.className = "thinking-log-line";
                                const textSpanClass = eventType === "tool_call" ? "thinking-log-text tool-call" : "thinking-log-text";
                                const iconPrefix = eventType === "tool_call" ? "⚙️ " : "💭 ";
                                const messageText = dataObj.text || dataObj.message || "";
                                line.innerHTML = `<span class="thinking-log-time">[${elapsed}]</span><span class="${textSpanClass}">${iconPrefix}${messageText}</span>`;
                                bodyEl.appendChild(line);
                                bodyEl.scrollTop = bodyEl.scrollHeight;
                            }
                        } else if (eventType === "proposal_ready") {
                            const elapsedTotal = ((Date.now() - startTimestamp) / 1000).toFixed(1) + "s";
                            const accEl = document.getElementById(accordionId);
                            if (accEl) {
                                accEl.classList.add("completed", "collapsed");
                                const titleEl = accEl.querySelector(".thinking-title");
                                if (titleEl) titleEl.innerText = `✔️ Selesai menganalisis & menyusun proposal (${elapsedTotal})`;
                            }

                            currentProposalId = (dataObj.proposal && dataObj.proposal.proposal_id) || "";
                            activeOperations = (dataObj.plan && dataObj.plan.operations) || [];

                            const summaryEl = document.getElementById(`${accordionId}_summary`);
                            if (summaryEl) {
                                summaryEl.innerHTML = `
                                    <h4>✔ Rencana Revisi Selesai Disusun!</h4>
                                    <p>AI telah mengolah instruksi Anda menjadi <code>${activeOperations.length} operasi edit deterministik</code> dengan ringkasan: <strong>"${(dataObj.plan && dataObj.plan.instruction_summary) || text}"</strong>.</p>
                                    <p>Silakan tinjau perbandingan (*Before / After diff*) pada panel kanan sebelum menyetujui perubahan.</p>
                                `;
                            }
                            renderProposalReview(dataObj.plan);
                        } else if (eventType === "error") {
                            throw new Error(dataObj.message || "Unknown streaming error.");
                        }
                    }
                }

            } catch (err) {
                const accEl = document.getElementById(accordionId);
                if (accEl) {
                    accEl.classList.add("collapsed");
                    const titleEl = accEl.querySelector(".thinking-title");
                    if (titleEl) titleEl.innerText = `⚠ Gagal: ${err.message}`;
                }
                appendChatMessage("assistant", `⚠ <strong>Gagal memproses instruksi:</strong> ${err.message}. Pastikan API Key Blackbox telah terpasang dengan benar di server Render Anda.`);
                showToast(`Error: ${err.message}`, "error");
            } finally {
                instructionInput.disabled = false;
                sendBtn.disabled = false;
                instructionInput.focus();
            }
        });
    }

    function appendChatMessage(role, htmlOrText) {
        const id = "msg_" + Math.random().toString(36).substr(2, 9);
        const msgDiv = document.createElement("div");
        msgDiv.id = id;
        msgDiv.className = `message ${role === "user" ? "user-msg" : "assistant-msg"}`;
        msgDiv.innerHTML = `
            <div class="msg-avatar ${role === "assistant" ? "assistant-avatar" : ""}">${role === "user" ? "👤" : "✨"}</div>
            <div class="msg-bubble">${role === "user" ? `<p>${htmlOrText}</p>` : htmlOrText}</div>
        `;
        chatMessages.appendChild(msgDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        return id;
    }

    // --- Proposal & Diff Rendering ---
    function renderProposalReview(plan) {
        proposalContainer.innerHTML = "";
        proposalBadge.innerText = `${activeOperations.length} Operasi Tertunda`;
        proposalBadge.className = "badge badge-pro";
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
                <div class="proposal-card-top">
                    <strong>#${idx + 1} Target: <code>${op.target_node_id || "document"}</code></strong>
                    <span class="op-type-tag">${op.type}</span>
                </div>
                ${diffHtml}
            `;
            proposalContainer.appendChild(card);
        });

        proposalFooter.classList.remove("hidden");
    }

    if (rejectProposalBtn) {
        rejectProposalBtn.addEventListener("click", () => {
            currentProposalId = null;
            activeOperations = [];
            proposalContainer.innerHTML = `<div class="empty-state"><div class="shield-graphic">✕</div><h3>Proposal Ditolak</h3><p>Anda dapat memberikan instruksi chat baru untuk menghasilkan revisi lain.</p></div>`;
            proposalFooter.classList.add("hidden");
            proposalBadge.innerText = "Ditolak";
            proposalBadge.className = "badge badge-light";
            showToast("Proposal perubahan dibatalkan", "info");
        });
    }

    if (commitProposalBtn) {
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
                    const errMsg = (errData.error && errData.error.message) || errData.detail || errData.message || `Commit gagal dengan status ${res.status}`;
                    throw new Error(errMsg);
                }

                const data = await res.json();
                currentVersion = (data.new_version || data.version || currentVersion + 1);

                proposalFooter.classList.add("hidden");
                proposalBadge.innerText = `Lolos L1-L5 (v${currentVersion})`;
                proposalBadge.className = "badge badge-pro";
                
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
                commitProposalBtn.innerText = "✔ Setujui & Terapkan";
            }
        });
    }
});
