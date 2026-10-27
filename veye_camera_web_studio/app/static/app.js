/**
 * VEYE Camera Web Studio - Frontend Application
 */
(function () {
    "use strict";

    // ========== State ==========
    const state = {
        lang: "en",
        i18n: {},
        groups: [],
        commands: [],
        currentGroup: null,
        currentCommand: null,
        view: "welcome",
        cameras: [],
        selectedCamera: null,
        platform: "jetson",
        commandRequestCounter: 0, // Track selectCommand requests to prevent race conditions
    };

    // ========== DOM Cache ==========
    const $ = (sel) => document.querySelector(sel);
    const $$ = (sel) => document.querySelectorAll(sel);

    const dom = {};
    function cacheDom() {
        [
            "systemInfo", "infoOS", "infoKernel",
            "cameraList", "cameraSelectorWrap", "cameraDetail",
            "cameraSelect", "platformSelect",
            "camModel", "camVerC", "camVerL", "camSerial", "camI2cBus", "camI2cAddr",
            "camVideoNode", "camMediaNode", "camEntityName",
            "btnRescan",
            "searchInput", "groupsList",
            "welcomeScreen", "splitView", "searchResultsView",
            "groupTitle", "groupDescription", "commandCards",
            "opPlaceholder", "opPanel", "opTitle", "opMode", "opRisk",
            "opRegSection", "opRegAddr", "opRegType",
            "opDescription", "opParamsSection", "paramForm", "noParamsMsg",
            "opActions", "btnRead", "btnWrite",
            "opResult", "opNotesSection", "opNotes",
            "confirmModal", "btnConfirmYes", "btnConfirmCancel",
            "searchTitle", "searchResults", "btnClearSearch",
            "statusIndicator", "btnThemeToggle",
        ].forEach((id) => { dom[id] = $("#" + id); });
    }

    // ========== Theme Toggle ==========
    function getPreferredTheme() {
        const saved = localStorage.getItem("veye-theme");
        if (saved) return saved;
        return window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
    }

    function applyTheme(theme) {
        document.documentElement.setAttribute("data-theme", theme);
        dom.btnThemeToggle.textContent = theme === "light" ? "☀️" : "🌙";
        dom.btnThemeToggle.title = theme === "light" ? "Switch to dark" : "Switch to light";
        localStorage.setItem("veye-theme", theme);
    }

    function toggleTheme() {
        const current = document.documentElement.getAttribute("data-theme") || "dark";
        applyTheme(current === "dark" ? "light" : "dark");
    }

    // ========== i18n ==========
    function t(key) {
        const parts = key.split(".");
        let obj = state.i18n;
        for (const p of parts) {
            if (obj && typeof obj === "object") obj = obj[p];
            else return key;
        }
        if (obj && typeof obj === "object") return obj[state.lang] || obj["en"] || key;
        return obj || key;
    }

    function applyI18n() {
        $$("[data-i18n]").forEach((el) => {
            const key = el.getAttribute("data-i18n");
            el.textContent = t(key);
        });
        $$("[data-i18n-placeholder]").forEach((el) => {
            el.placeholder = t(el.getAttribute("data-i18n-placeholder"));
        });
        $$("[data-i18n-title]").forEach((el) => {
            el.title = t(el.getAttribute("data-i18n-title"));
        });
        document.documentElement.setAttribute("data-lang", state.lang);
    }

    async function loadI18n() {
        try {
            const res = await fetch("/api/i18n");
            state.i18n = await res.json();
        } catch (e) {
            console.warn("Failed to load i18n:", e);
        }
    }

    // ========== API Helpers ==========
    async function apiGet(url) {
        const res = await fetch(url);
        if (!res.ok) throw new Error(`API error: ${res.status}`);
        return res.json();
    }

    async function apiPost(url, body) {
        const res = await fetch(url, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
        });
        if (!res.ok) throw new Error(`API error: ${res.status}`);
        return res.json();
    }

    async function apiDelete(url) {
        const res = await fetch(url, { method: "DELETE" });
        if (!res.ok) throw new Error(`API error: ${res.status}`);
        return res.json();
    }

    // ========== System Info ==========
    async function loadSystemInfo() {
        try {
            const info = await apiGet("/api/system/info");
            dom.infoOS.textContent = info.os_pretty_name || info.os || "—";
            dom.infoKernel.textContent = info.os_release || "—";
            setStatus("online");
        } catch (e) {
            console.warn("System info error:", e);
            dom.infoOS.textContent = "error";
            setStatus("error");
        }
    }

    // ========== Camera Probe ==========
    async function probeCameras() {
        const platform = dom.platformSelect.value;
        state.platform = platform;
        localStorage.setItem("veye-platform", platform);

        // Show loading
        dom.cameraSelectorWrap.style.display = "none";
        dom.cameraDetail.style.display = "none";
        dom.cameraList.style.display = "";
        dom.cameraList.innerHTML = `<span class="placeholder">${t("device.scanning")}</span>`;

        try {
            const data = await apiPost("/api/devices/probe", { platform });
            state.cameras = data.cameras || [];

            if (state.cameras.length === 0) {
                dom.cameraList.innerHTML = `<span class="placeholder">${t("device.no_camera")}</span>`;
                return;
            }

            // Populate camera selector
            dom.cameraList.style.display = "none";
            dom.cameraSelectorWrap.style.display = "";
            dom.cameraSelect.innerHTML = state.cameras
                .map((cam, i) => {
                    const bus = cam.i2c_bus || "?";
                    const model = cam.model || `Camera #${i + 1}`;
                    const label = `I2C-${bus} ${model}`;
                    return `<option value="${i}">${label}</option>`;
                })
                .join("");

            // Select first camera
            selectCamera(0);
        } catch (e) {
            dom.cameraList.innerHTML = `<span class="placeholder">Probe failed: ${escapeHtml(e.message)}</span>`;
        }
    }

    function selectCamera(index) {
        const cam = state.cameras[index];
        if (!cam) return;
        state.selectedCamera = cam;

        // Show camera detail
        dom.cameraDetail.style.display = "";
        dom.camModel.textContent = cam.model || "—";
        dom.camVerC.textContent = cam.version_c || "—";
        dom.camVerL.textContent = cam.version_l || "—";
        dom.camSerial.textContent = cam.serial || "—";
        dom.camI2cBus.textContent = cam.i2c_bus || "—";
        dom.camI2cAddr.textContent = cam.i2c_addr || "0x3b";
        dom.camVideoNode.textContent = cam.video_node || "—";
        dom.camMediaNode.textContent = cam.media_node || "—";
        dom.camEntityName.textContent = cam.media_entity_name || "—";
    }

    function setStatus(s) {
        const dot = dom.statusIndicator.querySelector(".status-dot");
        const txt = dom.statusIndicator.querySelector(".status-text");
        dot.className = "status-dot " + s;
        txt.removeAttribute("data-i18n");
        txt.textContent = s === "online" ? "Online" : s === "error" ? "Error" : "Loading...";
    }

    // ========== Command Groups ==========
    async function loadGroups() {
        try {
            const data = await apiGet("/api/commands/groups");
            state.groups = (data.groups || []).sort((a, b) => a.order - b.order);
            renderGroups();
        } catch (e) {
            console.error("Failed to load groups:", e);
        }
    }

    function renderGroups() {
        const iconMap = {
            info: "ℹ️", list: "📋", video: "🎬", dashboard: "📊",
            sun: "☀️", palette: "🎨", image: "🖼️", zap: "⚡",
            moon: "🌙", cpu: "🔌", settings: "⚙️", power: "🔋", tool: "🔧",
        };
        dom.groupsList.innerHTML = state.groups
            .map(
                (g) => `
            <button class="group-item" data-group="${g.id}">
                <span class="group-icon">${iconMap[g.icon] || ""}</span>
                <span class="group-name">${g.name[state.lang] || g.name.en}</span>
            </button>`
            )
            .join("");

        dom.groupsList.querySelectorAll(".group-item").forEach((btn) => {
            btn.addEventListener("click", () => selectGroup(btn.dataset.group));
        });
    }

    // ========== Command List ==========
    async function selectGroup(groupId) {
        state.currentGroup = groupId;
        dom.groupsList.querySelectorAll(".group-item").forEach((btn) => {
            btn.classList.toggle("active", btn.dataset.group === groupId);
        });
        try {
            let url = `/api/commands?group=${groupId}&lang=${state.lang}`;
            // For video_modes group, pass I2C info for capability-based filtering
            if (groupId === "video_modes" && state.selectedCamera) {
                const bus = parseInt(state.selectedCamera.i2c_bus) || 10;
                const addr = state.selectedCamera.i2c_addr || "0x3b";
                url += `&i2c_bus=${bus}&i2c_addr=${encodeURIComponent(addr)}`;
            }
            const data = await apiGet(url);
            state.commands = data.commands || [];
            const group = state.groups.find((g) => g.id === groupId);
            showView("list");
            dom.groupTitle.textContent = group ? group.name[state.lang] || group.name.en : groupId;
            dom.groupDescription.textContent = group ? group.description[state.lang] || group.description.en : "";

            // Render video mode summary if available
            const oldSummary = document.querySelector(".video-mode-summary");
            if (data.video_mode_info) {
                renderVideoModeSummary(data.video_mode_info);
            } else if (oldSummary) {
                oldSummary.remove();
            }

            renderCommandCards(state.commands, dom.commandCards);
        } catch (e) {
            console.error("Failed to load commands:", e);
        }
    }

    function renderVideoModeSummary(info) {
        // Remove any existing summary
        const oldSummary = document.querySelector(".video-mode-summary");
        if (oldSummary) oldSummary.remove();

        const summaryEl = document.createElement("div");
        summaryEl.className = "video-mode-summary";

        const capLabel = info.cap_label[state.lang] || info.cap_label.en;
        const capClass = info.cap_mode === 1 ? "cap-roi" : "cap-preset";

        let html = `<div class="video-mode-cap-badge ${capClass}">${capLabel}</div>`;

        if (info.cap_mode === 2 && info.preset_modes && info.preset_modes.length > 0) {
            // Preset mode: show current resolution/framerate from camera data + preset mode grid
            const cam = state.selectedCamera || {};
            const curW = cam.width || "";
            const curH = cam.height || "";
            const curFps = cam.fps || "";

            if (curW && curH) {
                html += `<div class="video-mode-current">`;
                html += `<span class="vmc-label">${state.lang === 'zh' ? '当前分辨率' : 'Current Resolution'}:</span> `;
                html += `<span class="vmc-value">${curW} × ${curH}</span>`;
                if (curFps) {
                    html += ` &nbsp;|&nbsp; <span class="vmc-label">${state.lang === 'zh' ? '帧率' : 'Framerate'}:</span> `;
                    html += `<span class="vmc-value">${curFps} fps</span>`;
                }
                html += `</div>`;
            }

            html += `<div class="video-mode-grid">`;
            info.preset_modes.forEach((m) => {
                html += `<div class="vmode-card" data-mode="${m.mode}" title="${state.lang === 'zh' ? '点击选择此模式' : 'Click to select this mode'}">`;
                html += `<div class="vmode-num">${state.lang === 'zh' ? '模式' : 'Mode'} ${m.mode}</div>`;
                html += `<div class="vmode-res">${m.width} × ${m.height}</div>`;
                html += `<div class="vmode-fps">${m.fps} fps</div>`;
                html += `<div class="vmode-rm">${m.read_mode_name}</div>`;
                html += `</div>`;
            });
            html += `</div>`;
        } else if (info.cap_mode === 1) {
            // ROI mode
            html += `<p class="video-mode-hint">${state.lang === 'zh' ? '当前相机支持 ROI 模式，可在下方配置感兴趣区域和帧率。' : 'This camera supports ROI mode. Configure Region of Interest and framerate below.'}</p>`;
        }

        summaryEl.innerHTML = html;

        // Insert after group description
        dom.groupDescription.insertAdjacentElement("afterend", summaryEl);

        // Bind click on preset mode cards to set videomode
        summaryEl.querySelectorAll(".vmode-card").forEach((card) => {
            card.addEventListener("click", () => {
                const mode = parseInt(card.dataset.mode);
                setPresetMode(mode);
            });
        });
    }

    async function setPresetMode(mode) {
        // Execute the videomode command to switch preset mode
        const cam = state.selectedCamera || {};
        const body = {
            command_id: "videomode",
            i2c_bus: parseInt(cam.i2c_bus) || 10,
            i2c_addr: cam.i2c_addr || "0x3b",
            params: [mode],
            timeout: 5,
        };
        try {
            const data = await apiPost(`/api/commands/videomode/execute`, body);
            if (data.success) {
                // Refresh the video_modes group to update the display
                if (state.currentGroup === "video_modes") {
                    selectGroup("video_modes");
                }
            } else {
                console.error("Failed to set video mode:", data.stderr || data.error);
            }
        } catch (e) {
            console.error("Failed to set video mode:", e);
        }
    }

    function renderCommandCards(commands, container) {
        if (!commands.length) {
            container.innerHTML = `<p class="placeholder">No commands found</p>`;
            return;
        }
        container.innerHTML = commands
            .map((cmd) => {
                const modeClass = cmd.mode === "read" ? "badge-read" : cmd.mode === "write" ? "badge-write" : "badge-rw";
                const modeLabel = cmd.mode === "read" ? "R" : cmd.mode === "write" ? "W" : "RW";
                const riskClass = "badge-risk-" + (cmd.risk_level || "none");
                return `
                <div class="cmd-card fade-in" data-cmd="${cmd.id}">
                    <div class="cmd-card-info">
                        <div class="cmd-card-name">${cmd.name[state.lang] || cmd.name.en}</div>
                        <div class="cmd-card-desc">${cmd.description[state.lang] || cmd.description.en}</div>
                    </div>
                    <div class="cmd-card-badges">
                        <span class="badge ${modeClass}">${modeLabel}</span>
                        <span class="badge ${riskClass}">${(cmd.risk_level || "none").toUpperCase()}</span>
                    </div>
                </div>`;
            })
            .join("");

        // Bind click to select command
        container.querySelectorAll(".cmd-card").forEach((card) => {
            card.addEventListener("click", () => {
                console.log(`Card clicked: ${card.dataset.cmd}`);
                selectCommand(card.dataset.cmd);
            });
        });
    }

    // ========== Operation Panel (right side) ==========
    async function selectCommand(commandId) {
        // Increment request counter to track this request
        const requestId = ++state.commandRequestCounter;
        console.log(`selectCommand: loading ${commandId} (requestId=${requestId})`);

        // Disable read/write buttons while loading
        dom.btnRead.disabled = true;
        dom.btnWrite.disabled = true;

        try {
            const cmd = await apiGet(`/api/commands/${commandId}`);

            // Only proceed if this is still the latest request
            if (requestId !== state.commandRequestCounter) {
                console.log(`selectCommand: discarding stale request for ${commandId} (current=${state.commandRequestCounter})`);
                return; // Stale request, ignore
            }

            console.log(`selectCommand: loaded ${commandId}, register=${cmd.register?.address || 'N/A'}`);
            state.currentCommand = cmd;

            // Highlight active card
            document.querySelectorAll(".cmd-card").forEach((c) => c.classList.remove("active"));
            const activeCard = document.querySelector(`.cmd-card[data-cmd="${commandId}"]`);
            if (activeCard) activeCard.classList.add("active");

            // If in search mode, switch to split view
            if (state.view === "search") {
                showView("list");
            }

            // Show operation panel
            dom.opPlaceholder.style.display = "none";
            dom.opPanel.style.display = "";
            renderOpPanel(cmd);
        } catch (e) {
            console.error("Failed to load command:", e);
        } finally {
            // Re-enable buttons only if this is the latest request
            if (requestId === state.commandRequestCounter) {
                dom.btnRead.disabled = false;
                dom.btnWrite.disabled = false;
            }
        }
    }

    function renderOpPanel(cmd) {
        // Reset result
        dom.opResult.style.display = "none";
        dom.opResult.innerHTML = `<div class="op-result-placeholder">Execute a command to see results here</div>`;

        // Title with debug info
        const debugInfo = cmd.register?.address ? ` [${cmd.register.address}]` : "";
        dom.opTitle.textContent = (cmd.name[state.lang] || cmd.name.en) + debugInfo;

        // Mode badge
        const modeClass = cmd.mode === "read" ? "badge-read" : cmd.mode === "write" ? "badge-write" : "badge-rw";
        const modeLabel = cmd.mode === "read" ? t("command.mode_read") : cmd.mode === "write" ? t("command.mode_write") : t("command.mode_rw");
        dom.opMode.className = "badge " + modeClass;
        dom.opMode.textContent = modeLabel;

        // Risk badge
        const riskClass = "badge-risk-" + (cmd.risk_level || "none");
        dom.opRisk.className = "badge " + riskClass;
        dom.opRisk.textContent = t("command.risk_" + (cmd.risk_level || "low"));

        // Description
        dom.opDescription.textContent = cmd.description[state.lang] || cmd.description.en;

        // Register info
        if (cmd.register && cmd.register.address) {
            dom.opRegSection.style.display = "";
            dom.opRegAddr.textContent = cmd.register.address;
        } else {
            dom.opRegSection.style.display = "none";
        }

        // Parameters form
        const params = cmd.parameters || [];
        if (params.length > 0) {
            dom.opParamsSection.style.display = "";
            dom.noParamsMsg.style.display = "none";
            dom.paramForm.style.display = "";
            dom.paramForm.innerHTML = params
                .map((p, i) => {
                    const label = p.label[state.lang] || p.label.en;
                    if (p.type === "enum") {
                        const opts = p.options
                            .map((o) => {
                                const lbl = typeof o.label === "object" ? o.label[state.lang] || o.label.en : o.label;
                                return `<option value="${o.value}">${lbl}</option>`;
                            })
                            .join("");
                        return `
                        <div class="param-field">
                            <label>${label}</label>
                            <select name="param_${i}" data-index="${i}">${opts}</select>
                        </div>`;
                    } else {
                        const def = p.default !== null && p.default !== undefined ? p.default : "";
                        const unit = p.unit ? ` (${p.unit})` : "";
                        const placeholder = `十进制或 0x 十六进制`;
                        return `
                        <div class="param-field">
                            <label>${label}${unit}</label>
                            <input type="text" name="param_${i}" data-index="${i}"
                                   value="${def}" placeholder="${placeholder}"
                                   autocomplete="off">
                        </div>`;
                    }
                })
                .join("");
        } else {
            dom.opParamsSection.style.display = "none";
            dom.noParamsMsg.style.display = "";
            dom.paramForm.style.display = "none";
        }

        // Notes
        if (cmd.notes && (cmd.notes[state.lang] || cmd.notes.en)) {
            dom.opNotesSection.style.display = "";
            dom.opNotes.textContent = cmd.notes[state.lang] || cmd.notes.en;
        } else {
            dom.opNotesSection.style.display = "none";
        }

        // Button visibility based on mode
        dom.btnRead.style.display = "none";
        dom.btnWrite.style.display = "none";

        if (cmd.mode === "read") {
            dom.btnRead.style.display = "";
            dom.btnRead.textContent = "▶ " + t("command.read_btn");
        } else if (cmd.mode === "write") {
            dom.btnWrite.style.display = "";
            dom.btnWrite.textContent = "▶ " + t("command.write_btn");
        } else {
            // RW: show both Read and Write
            dom.btnRead.style.display = "";
            dom.btnWrite.style.display = "";
            dom.btnRead.textContent = "▶ " + t("command.read_btn");
            dom.btnWrite.textContent = "▶ " + t("command.write_btn");
        }
    }

    // ========== Execution ==========
    function collectParams() {
        const params = [];
        dom.paramForm.querySelectorAll("input, select").forEach((el) => {
            let val = el.value.trim();
            if (val !== "" && val !== null) {
                // Parse hex (0x prefix) or decimal
                if (val.startsWith("0x") || val.startsWith("0X")) {
                    const parsed = parseInt(val, 16);
                    params.push(isNaN(parsed) ? val : parsed);
                } else {
                    params.push(isNaN(val) ? val : Number(val));
                }
            }
        });
        return params;
    }

    async function executeRead() {
        const cmd = state.currentCommand;
        if (!cmd) {
            console.warn("executeRead: no current command");
            return;
        }
        console.log(`executeRead: command_id=${cmd.id}, register=${cmd.register?.address || 'N/A'}`);
        if (cmd.risk_level === "high" || cmd.requires_confirmation) {
            if (!(await showConfirmModal())) return;
        }
        const cam = state.selectedCamera || {};
        const body = {
            command_id: cmd.id,
            i2c_bus: parseInt(cam.i2c_bus) || 10,
            i2c_addr: cam.i2c_addr || "0x3b",
            params: collectParams(),
            timeout: 5,
        };
        await doExecute(body, dom.btnRead);
    }

    async function executeWrite() {
        const cmd = state.currentCommand;
        if (!cmd) return;
        if (cmd.risk_level === "high" || cmd.requires_confirmation) {
            if (!(await showConfirmModal())) return;
        }
        const cam = state.selectedCamera || {};
        const body = {
            command_id: cmd.id,
            i2c_bus: parseInt(cam.i2c_bus) || 10,
            i2c_addr: cam.i2c_addr || "0x3b",
            params: collectParams(),
            timeout: 5,
        };
        await doExecute(body, dom.btnWrite);
    }

    async function doExecute(body, btnEl) {
        btnEl.disabled = true;
        const origText = btnEl.textContent;
        btnEl.textContent = "⏳";
        dom.opResult.style.display = "";
        dom.opResult.innerHTML = `<div class="op-result-placeholder">⏳ ${t("command.executing")}</div>`;

        try {
            const data = await apiPost(`/api/commands/${body.command_id}/execute`, body);
            console.log(`doExecute response:`, data);
            showResult(data);

            // For RW commands: after read, populate parameter fields with read values
            const cmd = state.currentCommand;
            if (data.success && cmd && cmd.mode === "rw" && data.read_values && data.read_values.length > 0) {
                populateParamsFromRead(data.read_values, cmd);
            }

        } catch (e) {
            dom.opResult.innerHTML = `<div class="result-error">❌ ${e.message}</div>`;
        } finally {
            btnEl.disabled = false;
            btnEl.textContent = origText;
        }
    }

    function populateParamsFromRead(readValues, cmd) {
        const params = cmd.parameters || [];
        if (params.length === 0) return;

        // For single-param commands, set the first param from the first read value
        readValues.forEach((val, i) => {
            if (i >= params.length) return;
            const p = params[i];
            const el = dom.paramForm.querySelector(`[data-index="${i}"]`);
            if (!el) return;

            if (p.type === "enum") {
                // Try to match the value to an option
                const num = typeof val === "number" ? val : parseInt(val, 10);
                const match = p.options.find((o) => o.value === num || o.value === String(num));
                if (match) {
                    el.value = String(match.value);
                }
            } else {
                // Numeric: set the input value
                const num = typeof val === "number" ? val : parseInt(val, 10);
                if (!isNaN(num)) {
                    el.value = String(num);
                }
            }
        });
    }

    function showResult(data) {
        dom.opResult.style.display = "";
        if (data.success) {
            const readValues = data.read_values || [];
            const cmd = state.currentCommand;
            if (readValues.length > 0) {
                let html = '<div class="result-values">';
                readValues.forEach((val, i) => {
                    const label = readValues.length > 1 ? `R${i}` : "Value";
                    const num = typeof val === "number" ? val : parseInt(val, 10);
                    if (isNaN(num)) return;
                    const hex = "0x" + num.toString(16).toUpperCase().padStart(2, "0");
                    const dec = num.toString(10);
                    const bin = "0b" + num.toString(2);
                    html += `
                        <div class="result-value">
                            <span class="result-label">HEX</span>
                            <span class="result-data">${label}: ${hex}</span>
                        </div>
                        <div class="result-value">
                            <span class="result-label">DEC</span>
                            <span class="result-data">${label}: ${dec}</span>
                        </div>
                        <div class="result-value">
                            <span class="result-label">BIN</span>
                            <span class="result-data">${label}: ${bin}</span>
                        </div>`;
                    
                    // Special handling for temperature commands: show Kelvin and Celsius
                    if (cmd && (cmd.id === "sensortemp" || cmd.id === "isptemp")) {
                        const kelvin = num / 100;
                        const celsius = kelvin - 273.15;
                        html += `
                        <div class="result-value">
                            <span class="result-label">K</span>
                            <span class="result-data">${label}: ${kelvin.toFixed(2)} K</span>
                        </div>
                        <div class="result-value">
                            <span class="result-label">°C</span>
                            <span class="result-data">${label}: ${celsius.toFixed(2)} °C</span>
                        </div>`;
                    }
                });
                html += "</div>";
                dom.opResult.innerHTML = html;
            } else {
                dom.opResult.innerHTML = `<div class="result-success">✅ ${t("command.success")}</div>`;
            }
        } else {
            const errMsg = data.stderr || data.stdout || data.error || "Unknown error";
            dom.opResult.innerHTML = `<div class="result-error">❌ ${errMsg}</div>`;
        }
    }

    // ========== Logs ==========
    async function loadLogs() {
        try {
            const data = await apiGet("/api/logs?limit=50");
            renderLogs(data.logs || []);
        } catch (e) {
            // silent
        }
    }

    function renderLogs(logs) {
        if (!logs.length) {
            dom.logArea.innerHTML = `<div class="log-placeholder">${t("log.no_logs")}</div>`;
            return;
        }
        dom.logArea.innerHTML = logs
            .map((log) => {
                const time = log.timestamp ? new Date(log.timestamp).toLocaleTimeString() : "";
                const statusClass = log.success ? "success" : "failed";
                const statusText = log.success ? "✓" : "";
                const output = log.stdout ? log.stdout.substring(0, 80) : (log.stderr || "").substring(0, 80);
                return `
                <div class="log-entry">
                    <div class="log-entry-header">
                        <span class="log-time">${time}</span>
                        <span class="log-status ${statusClass}">${statusText}</span>
                    </div>
                    <div class="log-cmd">${escapeHtml(log.command_id)} ${log.params && log.params.length ? "(" + log.params.join(", ") + ")" : ""}</div>
                    ${output ? `<div class="log-detail">${escapeHtml(output)}</div>` : ""}
                </div>`;
            })
            .join("");
    }

    // ========== Search ==========
    let searchTimer = null;
    function onSearchInput() {
        clearTimeout(searchTimer);
        searchTimer = setTimeout(async () => {
            const q = dom.searchInput.value.trim();
            if (q.length < 2) {
                if (state.currentGroup) {
                    selectGroup(state.currentGroup);
                } else {
                    showView("welcome");
                }
                return;
            }
            try {
                const data = await apiGet(`/api/commands?search=${encodeURIComponent(q)}&lang=${state.lang}`);
                showView("search");
                dom.searchTitle.textContent = `"${q}" — ${data.count} results`;
                renderCommandCards(data.commands || [], dom.searchResults);
            } catch (e) {
                console.error("Search error:", e);
            }
        }, 300);
    }

    // ========== View Management ==========
    function showView(view) {
        state.view = view;
        dom.welcomeScreen.style.display = view === "welcome" ? "" : "none";
        dom.splitView.style.display = view === "list" ? "" : "none";
        dom.searchResultsView.style.display = view === "search" ? "" : "none";
    }

    // ========== Modal ==========
    function showConfirmModal() {
        return new Promise((resolve) => {
            dom.confirmModal.style.display = "";
            const cleanup = (val) => {
                dom.confirmModal.style.display = "none";
                dom.btnConfirmYes.removeEventListener("click", onYes);
                dom.btnConfirmCancel.removeEventListener("click", onNo);
                dom.confirmModal.querySelector(".modal-overlay").removeEventListener("click", onNo);
                resolve(val);
            };
            const onYes = () => cleanup(true);
            const onNo = () => cleanup(false);
            dom.btnConfirmYes.addEventListener("click", onYes);
            dom.btnConfirmCancel.addEventListener("click", onNo);
            dom.confirmModal.querySelector(".modal-overlay").addEventListener("click", onNo);
        });
    }

    // ========== Utilities ==========
    function escapeHtml(str) {
        if (!str) return "";
        return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
    }

    // ========== Event Binding ==========
    function bindEvents() {
        // Theme toggle
        dom.btnThemeToggle.addEventListener("click", toggleTheme);

        // Platform change → re-probe
        dom.platformSelect.addEventListener("change", () => {
            probeCameras();
        });

        // Camera selection change
        dom.cameraSelect.addEventListener("change", () => {
            selectCamera(parseInt(dom.cameraSelect.value));
        });

        // Rescan
        dom.btnRescan.addEventListener("click", () => {
            probeCameras();
        });

        // Language switch
        $$(".lang-btn").forEach((btn) => {
            btn.addEventListener("click", () => {
                state.lang = btn.dataset.lang;
                $$(".lang-btn").forEach((b) => b.classList.toggle("active", b === btn));
                applyI18n();
                if (state.currentGroup && state.view === "list") selectGroup(state.currentGroup);
                if (state.currentCommand) renderOpPanel(state.currentCommand);
                renderGroups();
            });
        });

        // Read / Write buttons
        dom.btnRead.addEventListener("click", executeRead);
        dom.btnWrite.addEventListener("click", executeWrite);

        // Search
        dom.searchInput.addEventListener("input", onSearchInput);
        dom.btnClearSearch.addEventListener("click", () => {
            dom.searchInput.value = "";
            if (state.currentGroup) selectGroup(state.currentGroup);
            else showView("welcome");
        });
    }

    // ========== Init ==========
    async function init() {
        cacheDom();
        bindEvents();
        applyTheme(getPreferredTheme());

        // Restore saved platform
        const savedPlatform = localStorage.getItem("veye-platform");
        if (savedPlatform) {
            dom.platformSelect.value = savedPlatform;
            state.platform = savedPlatform;
        }

        await loadI18n();
        applyI18n();
        await loadSystemInfo();
        await probeCameras();
        await loadGroups();
        showView("welcome");
    }

    // Start
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
