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
        // One entry per running pipeline: streamId -> {streamId, videoNode, label,
        // series, playbackUrl, encoder, params, popup, watchTimer, inlineFpsTimer,
        // inlineZeroTicks}.  Keyed by id so switching the selected camera never
        // disturbs a stream another camera is still running.
        streams: new Map(),
        // The inline <img> can only ever read one stream (a second consumer on the
        // same gst stdout would split the multipart frames).
        inlineStreamId: null,
        streamCap: null,           // detected VideoModeCap: 1=ROI, 2=Preset, null=unknown
        streamPresetModes: [],     // preset modes read from the camera (cap_mode==2)
        streamListTimer: null,     // polls /api/stream/status for the running list
        maxStreams: 4,             // server-reported concurrency cap (for the hint)
        platform: "jetson",
        cameraSeries: "gx",  // "gx" or "mv"
        supportedSeries: [],
        commandRequestCounter: 0, // Track selectCommand requests to prevent race conditions
        defaultConfig: {
            i2c_bus: 10,
            i2c_addr: "0x3b",
        },
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
            "streamSection", "streamHint", "streamControls", "streamPreviewWrap", "mjpegView", "streamStatus",
            "streamCapRow",
            "streamWidth", "streamHeight", "streamFps", "streamRoiWrap", "streamRoiX", "streamRoiY",
            "streamPresetWrap", "streamPresetMode", "streamQuality",
            "streamCapBadge", "streamCapText", "btnStreamRedetect",
            "btnStartStream", "btnOpenPreview", "btnStopStream", "streamPopupHint", "streamLiveFps",
            "mjpegCaption",
            "streamListWrap", "streamListCount", "streamList", "btnStopAllStreams",
            "defaultI2cInfo", "manualSeries", "manualI2cBus", "manualI2cAddr", "btnApplyManual",
            "btnRescan",
            "cameraSeriesDisplay", "camSeries",
            "searchInput", "groupsList",
            "welcomeScreen", "splitView", "searchResultsView",
            "groupTitle", "groupDescription", "commandCards",
            "opPlaceholder", "opPanel", "opTitle", "opMode", "opRisk",
            "opRegSection", "opRegAddr", "opRegType",
            "opScriptFuncsSection", "opScriptFuncs",
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

    // Translate one subtree. Dynamically rendered rows use this instead of a full
    // applyI18n(), which would walk the whole document on every status poll.
    function applyI18nAttributes(root) {
        const scope = root || document;
        scope.querySelectorAll("[data-i18n]").forEach((el) => {
            el.textContent = t(el.getAttribute("data-i18n"));
        });
        scope.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
            el.placeholder = t(el.getAttribute("data-i18n-placeholder"));
        });
        scope.querySelectorAll("[data-i18n-title]").forEach((el) => {
            el.title = t(el.getAttribute("data-i18n-title"));
        });
    }

    function applyI18n() {
        applyI18nAttributes(document);
        // Both attributes matter: ``data-lang`` drives the CSS that picks which
        // embedded label to show, while ``lang`` is what screen readers and any
        // ``[lang]`` selector in the browser use.
        document.documentElement.setAttribute("data-lang", state.lang);
        document.documentElement.lang = state.lang;
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

    // ========== Default Config ==========
    async function loadDefaultConfig() {
        try {
            const config = await apiGet("/api/config");
            state.defaultConfig.i2c_bus = config.default_i2c_bus || 10;
            state.defaultConfig.i2c_addr = config.default_i2c_addr || "0x3b";
            // Load supported series (for reference, no longer user-selectable)
            if (config.supported_series) {
                state.supportedSeries = config.supported_series;
            }
            // Default series (used until a camera is selected and auto-detected)
            if (config.default_series) {
                state.cameraSeries = config.default_series;
            }
        } catch (e) {
            console.warn("Failed to load default config:", e);
        }
    }

    function updateDefaultI2cDisplay() {
        if (dom.manualSeries) dom.manualSeries.value = state.cameraSeries || "gx";
        if (dom.manualI2cBus) dom.manualI2cBus.value = state.defaultConfig.i2c_bus;
        if (dom.manualI2cAddr) dom.manualI2cAddr.value = state.defaultConfig.i2c_addr;
    }

    function applyManualSettings() {
        if (!dom.manualSeries || !dom.manualI2cBus || !dom.manualI2cAddr) return;
        
        const newSeries = dom.manualSeries.value;
        const newBus = parseInt(dom.manualI2cBus.value) || 10;
        const newAddr = dom.manualI2cAddr.value.trim() || "0x3b";
        
        // Validate I2C address format
        let addr = newAddr;
        if (!addr.startsWith("0x") && !addr.startsWith("0X")) {
            addr = "0x" + addr;
        }
        
        // Update state
        state.cameraSeries = newSeries;
        state.defaultConfig.i2c_bus = newBus;
        state.defaultConfig.i2c_addr = addr;
        
        // Reload groups/commands for the new series
        state.currentGroup = null;
        state.currentCommand = null;
        state.commands = [];
        loadGroups();
        showView("welcome");
        dom.opPanel.style.display = "none";
        dom.opPlaceholder.style.display = "";
        
        // Show success feedback
        const btnText = dom.btnApplyManual.textContent;
        dom.btnApplyManual.textContent = "✓";
        dom.btnApplyManual.disabled = true;
        setTimeout(() => {
            dom.btnApplyManual.textContent = btnText;
            dom.btnApplyManual.disabled = false;
        }, 1000);
        
        console.log(`Manual settings applied: series=${newSeries}, bus=${newBus}, addr=${addr}`);
    }

    /**
     * Get effective I2C bus/addr - from selected camera or defaults
     */
    function getEffectiveI2c() {
        if (state.selectedCamera) {
            return {
                bus: parseInt(state.selectedCamera.i2c_bus) || state.defaultConfig.i2c_bus,
                addr: state.selectedCamera.i2c_addr || state.defaultConfig.i2c_addr,
            };
        }
        return {
            bus: state.defaultConfig.i2c_bus,
            addr: state.defaultConfig.i2c_addr,
        };
    }

    // ========== Camera Probe ==========
    async function probeCameras() {
        const platform = dom.platformSelect.value;
        state.platform = platform;
        localStorage.setItem("veye-platform", platform);

        // Show loading
        dom.cameraSelectorWrap.style.display = "none";
        dom.cameraSeriesDisplay.style.display = "none";
        dom.cameraDetail.style.display = "none";
        dom.defaultI2cInfo.style.display = "none";
        dom.cameraList.style.display = "";
        dom.cameraList.innerHTML = `<span class="placeholder">${t("device.scanning")}</span>`;

        try {
            const data = await apiPost("/api/devices/probe", { platform });
            state.cameras = data.cameras || [];

            if (state.cameras.length === 0) {
                dom.cameraList.innerHTML = `<span class="placeholder">${t("device.no_camera")}</span>`;
                // Show default I2C info
                updateDefaultI2cDisplay();
                dom.defaultI2cInfo.style.display = "";
                refreshStreamCaps();
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
        // Deliberately does NOT stop the previous camera's preview: each running
        // pipeline is tracked in state.streams and keeps its own popup and lock.
        state.selectedCamera = cam;
        // Show what this camera's pipeline is actually capturing, if it has one;
        // refreshStreamCaps() would otherwise overwrite it with live register values.
        const running = streamFor(cam.video_node);
        if (running) applyStreamParams(running); else syncStreamPanel();

        // Auto-switch camera series if detected from sysfs
        if (cam.series && cam.series !== state.cameraSeries) {
            console.log(`Auto-detected camera series: ${cam.series} (switching from ${state.cameraSeries})`);
            state.cameraSeries = cam.series;
            // Reload groups/commands for the new series
            state.currentGroup = null;
            state.currentCommand = null;
            state.commands = [];
            loadGroups();
            showView("welcome");
            dom.opPanel.style.display = "none";
            dom.opPlaceholder.style.display = "";
        } else if (cam.series) {
            // Same series, just update display
            state.cameraSeries = cam.series;
        }

        // Update series display (read-only badge)
        if (dom.cameraSeriesDisplay && dom.camSeries) {
            const seriesLabels = { gx: "GX Series", mv: "MV/RAW Series" };
            dom.camSeries.textContent = cam.series ? (seriesLabels[cam.series] || cam.series.toUpperCase()) : "—";
            dom.cameraSeriesDisplay.style.display = "";
        }

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
        refreshStreamCaps();
    }

    function setStatus(s) {
        const dot = dom.statusIndicator.querySelector(".status-dot");
        const txt = dom.statusIndicator.querySelector(".status-text");
        dot.className = "status-dot " + s;
        txt.removeAttribute("data-i18n");
        txt.textContent = s === "online" ? "Online" : s === "error" ? "Error" : "Loading...";
    }

    // ========== Camera Series ==========
    // Series is now auto-detected from sysfs when a camera is selected.
    // No manual series change handler needed.

    // ========== Command Groups ==========
    async function loadGroups() {
        try {
            const data = await apiGet(`/api/commands/groups?series=${state.cameraSeries}`);
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
            let url = `/api/commands?group=${groupId}&lang=${state.lang}&series=${state.cameraSeries}`;
            // For video_modes group, pass I2C info for capability-based filtering
            if (groupId === "video_modes") {
                const i2c = getEffectiveI2c();
                url += `&i2c_bus=${i2c.bus}&i2c_addr=${encodeURIComponent(i2c.addr)}`;
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

            // For trigger_sync group: read current workmode and filter commands
            if (groupId === "trigger_sync") {
                await filterTriggerSyncByWorkmode();
            } else {
                renderCommandCards(state.commands, dom.commandCards);
            }
        } catch (e) {
            console.error("Failed to load commands:", e);
        }
    }

    // ========== Trigger & Sync workmode filtering ==========
    async function readCurrentWorkmode() {
        const i2c = getEffectiveI2c();
        // GX uses "workmode", MV uses "trgmode"
        const cmdId = state.cameraSeries === "mv" ? "trgmode" : "workmode";
        const body = {
            command_id: cmdId,
            i2c_bus: i2c.bus,
            i2c_addr: i2c.addr,
            params: [],
            timeout: 5,
            action: "read",
            series: state.cameraSeries,
        };
        try {
            const data = await apiPost(`/api/commands/${cmdId}/execute`, body);
            if (data.success && data.read_values && data.read_values.length > 0) {
                return data.read_values[0];
            }
        } catch (e) {
            console.warn("Failed to read workmode:", e);
        }
        return null;
    }

    function filterTriggerSyncCommands(commands, workmode) {
        if (workmode === null || workmode === undefined) return commands;

        if (state.cameraSeries === "mv") {
            // MV series: 0=Stream, 1=Normal trigger, 2=Rolling shutter multi-frame, 3=Pulse/Level trigger
            switch (workmode) {
                case 0: // Video streaming - hide all except trgmode
                    return commands.filter(c => c.id === "trgmode");
                case 3: // Level trigger - hide slavemode, trgdelay, trginterval, trgnum
                    return commands.filter(c => !["slavemode", "trgdelay", "trginterval", "trgnum"].includes(c.id));
                default: // Normal trigger (1), Rolling shutter (2) - hide slavemode
                    return commands.filter(c => c.id !== "slavemode");
            }
        } else {
            // GX series: 0=Stream, 1=Trigger, 3=Level trigger, 4=Multi-camera sync
            switch (workmode) {
                case 0: // Video streaming - hide all except workmode
                    return commands.filter(c => c.id === "workmode");
                case 4: // Multi-camera sync - only show workmode + slavemode
                    return commands.filter(c => ["workmode", "slavemode"].includes(c.id));
                case 3: // Level trigger - hide slavemode, trgdelay, trginterval, trgnum
                    return commands.filter(c => !["slavemode", "trgdelay", "trginterval", "trgnum"].includes(c.id));
                case 1: // Normal trigger - hide slavemode
                default:
                    return commands.filter(c => c.id !== "slavemode");
            }
        }
    }

    function getWorkmodeLabel(workmode) {
        const lang = state.lang || 'en';
        if (state.cameraSeries === "mv") {
            const labels = {
                0: lang === 'zh' ? '视频流' : 'Video Streaming',
                1: lang === 'zh' ? '普通触发' : 'Normal Trigger',
                2: lang === 'zh' ? '卷帘多帧' : 'Rolling Shutter Multi-frame',
                3: lang === 'zh' ? '电平触发' : 'Pulse Trigger Mode',
            };
            return labels[workmode] || `Mode ${workmode}`;
        } else {
            const labels = {
                0: lang === 'zh' ? '视频流' : 'Video Streaming',
                1: lang === 'zh' ? '触发' : 'Trigger',
                3: lang === 'zh' ? '电平触发' : 'Pulse Trigger Mode',
                4: lang === 'zh' ? '多机同步' : 'Multi-camera Sync',
            };
            return labels[workmode] || `Mode ${workmode}`;
        }
    }

    function renderWorkmodeBanner(workmode) {
        // Remove existing banner
        const oldBanner = document.querySelector(".workmode-banner");
        if (oldBanner) oldBanner.remove();

        if (workmode === null) return;

        const lang = state.lang || 'en';
        const modeLabel = lang === 'zh' ? '当前工作模式' : 'Current Work Mode';
        const modeName = getWorkmodeLabel(workmode);

        const banner = document.createElement("div");
        banner.className = "workmode-banner";
        banner.innerHTML = `<span class="workmode-banner-label">${modeLabel}:</span> <span class="workmode-banner-value">${modeName}</span>`;

        // Insert after group description
        dom.groupDescription.insertAdjacentElement("afterend", banner);
    }

    async function filterTriggerSyncByWorkmode() {
        // Remove old banner
        const oldBanner = document.querySelector(".workmode-banner");
        if (oldBanner) oldBanner.remove();

        const workmode = await readCurrentWorkmode();
        renderWorkmodeBanner(workmode);

        const filtered = filterTriggerSyncCommands(state.commands, workmode);
        renderCommandCards(filtered, dom.commandCards);
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
        const i2c = getEffectiveI2c();
        const body = {
            command_id: "videomode",
            i2c_bus: i2c.bus,
            i2c_addr: i2c.addr,
            params: [mode],
            timeout: 5,
            series: state.cameraSeries,
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
                const scriptFuncs = cmd.script_functions || [];
                const scriptFuncsHtml = scriptFuncs.length > 0
                    ? `<div class="cmd-card-script-funcs">${scriptFuncs.map(f => `<code>${f}</code>`).join(' ')}</div>`
                    : '';
                return `
                <div class="cmd-card fade-in" data-cmd="${cmd.id}">
                    <div class="cmd-card-info">
                        <div class="cmd-card-name">${cmd.name[state.lang] || cmd.name.en}</div>
                        <div class="cmd-card-desc">${cmd.description[state.lang] || cmd.description.en}</div>
                        ${scriptFuncsHtml}
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
            const cmd = await apiGet(`/api/commands/${commandId}?series=${state.cameraSeries}`);

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
            await renderOpPanel(cmd);
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

    async function renderOpPanel(cmd) {
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

        // Script functions
        const scriptFuncs = cmd.script_functions || [];
        if (scriptFuncs.length > 0) {
            dom.opScriptFuncsSection.style.display = "";
            dom.opScriptFuncs.innerHTML = scriptFuncs.map(f => `<code class="script-func">${f}</code>`).join(' ');
        } else {
            dom.opScriptFuncsSection.style.display = "none";
        }

        // Parameters form
        const params = cmd.parameters || [];
        if (params.length > 0) {
            dom.opParamsSection.style.display = "";
            dom.noParamsMsg.style.display = "none";
            dom.paramForm.style.display = "";

            // Check for capability filters and fetch capabilities first
            const capFilters = params
                .map((p, i) => ({ param: p, index: i, filter: p.capability_filter }))
                .filter(x => x.filter);

            // Fetch all capability values in parallel
            const capValues = {};
            if (capFilters.length > 0) {
                console.log('Capability filters found:', capFilters);
                const i2c = getEffectiveI2c();
                console.log('I2C config:', i2c);
                const uniqueCapCmds = [...new Set(capFilters.map(f => f.filter.command_id))];
                console.log('Unique capability commands:', uniqueCapCmds);
                await Promise.all(uniqueCapCmds.map(async (capCmdId) => {
                    try {
                        const result = await apiPost(`/api/commands/${capCmdId}/execute`, {
                            series: state.cameraSeries,
                            command_id: capCmdId,
                            params: [],
                            i2c_bus: i2c.bus,
                            i2c_addr: i2c.addr
                        });
                        console.log(`Capability ${capCmdId} result:`, result);
                        if (result.success && result.read_values && result.read_values.length > 0) {
                            capValues[capCmdId] = result.read_values[0];
                        }
                    } catch (e) {
                        console.warn(`Failed to read capability ${capCmdId}:`, e);
                    }
                }));
                console.log('Final capability values:', capValues);
            }

            dom.paramForm.innerHTML = params
                .map((p, i) => {
                    const label = p.label[state.lang] || p.label.en;
                    if (p.type === "enum") {
                        let options = p.options;

                        // Apply capability filter if present
                        if (p.capability_filter) {
                            const capCmdId = p.capability_filter.command_id;
                            const capValue = capValues[capCmdId];
                            const bitMapping = p.capability_filter.bit_mapping;
                            console.log(`Filtering options for ${p.name}:`, { capCmdId, capValue, bitMapping, originalOptions: options });

                            if (capValue !== undefined) {
                                options = options.filter(o => {
                                    const bit = bitMapping[String(o.value)] ?? bitMapping[o.value];
                                    const keep = bit !== undefined && (capValue & (1 << bit)) !== 0;
                                    console.log(`  Option ${o.value}: bit=${bit}, keep=${keep}`);
                                    return keep;
                                });
                                console.log(`Filtered options:`, options);
                            }
                        }

                        const opts = options
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
        const i2c = getEffectiveI2c();
        const body = {
            command_id: cmd.id,
            i2c_bus: i2c.bus,
            i2c_addr: i2c.addr,
            params: collectParams(),
            timeout: 5,
            action: "read",
            series: state.cameraSeries,
        };
        await doExecute(body, dom.btnRead);
    }

    async function executeWrite() {
        const cmd = state.currentCommand;
        if (!cmd) return;
        if (cmd.risk_level === "high" || cmd.requires_confirmation) {
            if (!(await showConfirmModal())) return;
        }
        const i2c = getEffectiveI2c();
        const body = {
            command_id: cmd.id,
            i2c_bus: i2c.bus,
            i2c_addr: i2c.addr,
            params: collectParams(),
            timeout: 5,
            action: "write",
            series: state.cameraSeries,
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

            // After workmode/trgmode write: refresh trigger_sync group to re-filter commands
            if (data.success && body.action === "write" && (body.command_id === "workmode" || body.command_id === "trgmode")) {
                if (state.currentGroup === "trigger_sync") {
                    await filterTriggerSyncByWorkmode();
                }
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

        // Get inverse transform to convert register values to user-facing values
        const writeTransform = cmd.register?.value_transform?.write || null;
        const readTransform = cmd.register?.value_transform?.read || null;

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
                // Numeric: apply inverse transform to get user-facing value
                let num = typeof val === "number" ? val : parseInt(val, 10);
                if (!isNaN(num)) {
                    // Special handling for slowshutter: second param is gain threshold * 10
                    if (cmd.id === "slowshutter" && i === 1) {
                        num = num / 10;
                    }
                    // If there's a read transform, use it; otherwise invert the write transform
                    else if (readTransform) {
                        num = applyTransform(num, readTransform);
                    } else if (writeTransform) {
                        num = applyInverseTransform(num, writeTransform);
                    }
                    // Round to reasonable precision for float types
                    if (p.type === "float") {
                        num = Math.round(num * 10000) / 10000;
                    }
                    el.value = String(num);
                }
            }
        });
    }

    // Apply a transform expression like "value / 10000" to a number
    function applyTransform(value, expr) {
        try {
            // Replace 'value' with the actual number and evaluate safely
            const sanitized = expr.replace(/value/g, String(value));
            // Only allow safe math expressions
            if (/^[\d\s+\-*/().]+$/.test(sanitized)) {
                return Function('"use strict"; return (' + sanitized + ')')();
            }
        } catch (e) {
            console.warn("applyTransform failed:", expr, e);
        }
        return value;
    }

    // Compute inverse of a transform expression (e.g., "value * 10000" -> "value / 10000")
    function applyInverseTransform(registerValue, expr) {
        // Parse simple patterns: "value * N", "value / N", "value + N", "value - N"
        const match = expr.match(/value\s*([*/+\-])\s*([\d.]+)/);
        if (match) {
            const op = match[1];
            const operand = parseFloat(match[2]);
            switch (op) {
                case '*': return registerValue / operand;
                case '/': return registerValue * operand;
                case '+': return registerValue - operand;
                case '-': return registerValue + operand;
            }
        }
        return registerValue;
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
                    // Special handling for exposure time range command
                    else if (cmd && cmd.id === "exptime_range") {
                        const lang = state.lang || 'en';
                        const maxLabel = lang === 'zh' ? '最大曝光时间' : 'Max Exposure Time';
                        const minLabel = lang === 'zh' ? '最小曝光时间' : 'Min Exposure Time';
                        if (i === 0) {
                            // R0 = 0x0C8C = Max exposure time (unit: us)
                            const us = num;
                            const ms = us / 1000;
                            html += `
                            <div class="result-value">
                                <span class="result-label">Max</span>
                                <span class="result-data">${maxLabel}: ${us} μs${us >= 1000 ? ` (${ms.toFixed(3)} ms)` : ''}</span>
                            </div>`;
                        } else if (i === 1) {
                            // R1 = 0x0C90 = Min exposure time (unit: 0.1us)
                            const unit01us = num;
                            const us = num / 10;
                            html += `
                            <div class="result-value">
                                <span class="result-label">Min</span>
                                <span class="result-data">${minLabel}: ${us} μs${us >= 1000 ? ` (${(us/1000).toFixed(3)} ms)` : ''}</span>
                            </div>`;
                        }
                    }
                    // Special handling for slow shutter command
                    else if (cmd && cmd.id === "slowshutter") {
                        const lang = state.lang || 'en';
                        const modeLabel = lang === 'zh' ? '模式' : 'Mode';
                        const gainLabel = lang === 'zh' ? '增益阈值' : 'Gain Threshold';
                        const modeNames = {
                            0: lang === 'zh' ? '固定帧率模式' : 'Fixed frame rate mode',
                            1: lang === 'zh' ? '自动降帧模式' : 'Auto frame reduction mode'
                        };
                        if (i === 0) {
                            // R0 = 0x0CBC = Mode (0 or 1)
                            const modeName = modeNames[num] || String(num);
                            html += `
                            <div class="result-value">
                                <span class="result-label">${modeLabel}</span>
                                <span class="result-data">${modeName} (${num})</span>
                            </div>`;
                        } else if (i === 1) {
                            // R1 = 0x0CC0 = Gain threshold * 10 (unit: 0.1 dB)
                            const gainDb = num / 10;
                            html += `
                            <div class="result-value">
                                <span class="result-label">${gainLabel}</span>
                                <span class="result-data">${gainDb} dB (raw: ${num})</span>
                            </div>`;
                        }
                    }
                    // Special handling for sensor register indirect read
                    else if (cmd && cmd.id === "snsreg") {
                        const lang = state.lang || 'en';
                        const statusLabel = lang === 'zh' ? '状态' : 'Status';
                        const regValueLabel = lang === 'zh' ? '传感器寄存器值' : 'Sensor Register Value';

                        let ready, actualValue;
                        if (state.cameraSeries === 'mv') {
                            // MV/RAW series: indirect access (write addr to 0x0450, read from 0x0454).
                            // Bit 31 of the read value is the read-completion flag; mask it out for the value.
                            ready = (num & 0x80000000) !== 0;
                            actualValue = num & 0x7FFFFFFF;
                        } else {
                            // GX series: the sensor register is read directly (reg_type=sensor) and the
                            // returned value is the raw register value with no completion-flag bit, so a
                            // successful read is always complete.
                            ready = true;
                            actualValue = num >>> 0;
                        }

                        const hex = "0x" + actualValue.toString(16).toUpperCase().padStart(8, "0");
                        const dec = actualValue.toString(10);
                        const readyText = lang === 'zh' ? (ready ? '✅ 读取完成' : '⏳ 读取未完成') : (ready ? '✅ Read Complete' : '⏳ Read Incomplete');
                        
                        html += `
                        <div class="result-value">
                            <span class="result-label">${statusLabel}</span>
                            <span class="result-data">${readyText}</span>
                        </div>
                        <div class="result-value">
                            <span class="result-label">HEX</span>
                            <span class="result-data">${regValueLabel}: ${hex}</span>
                        </div>
                        <div class="result-value">
                            <span class="result-label">DEC</span>
                            <span class="result-data">${regValueLabel}: ${dec}</span>
                        </div>`;
                    }
                    // Show transformed value if value_transform.read is defined (skip for temp commands - already handled above)
                    else if (cmd && cmd.register?.value_transform?.read) {
                        const transformed = applyTransform(num, cmd.register.value_transform.read);
                        const unit = cmd.register.value_transform.unit || "";
                        const displayVal = Number.isInteger(transformed) ? transformed : transformed.toFixed(4).replace(/\.?0+$/, '');
                        html += `
                        <div class="result-value">
                            <span class="result-label">${unit}</span>
                            <span class="result-data">${label}: ${displayVal}${unit ? ' ' + unit : ''}</span>
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
                const data = await apiGet(`/api/commands?search=${encodeURIComponent(q)}&lang=${state.lang}&series=${state.cameraSeries}`);
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

        // Apply manual settings (when no camera detected)
        if (dom.btnApplyManual) {
            dom.btnApplyManual.addEventListener("click", applyManualSettings);
        }

        // Language switch
        $$(".lang-btn").forEach((btn) => {
            btn.addEventListener("click", () => {
                state.lang = btn.dataset.lang;
                $$(".lang-btn").forEach((b) => b.classList.toggle("active", b === btn));
                applyI18n();
                if (state.currentGroup && state.view === "list") selectGroup(state.currentGroup);
                if (state.currentCommand) renderOpPanel(state.currentCommand);
                renderGroups();
                // The Live Preview panel builds its strings from t() at render time
                // instead of through data-i18n attributes, so applyI18n() alone cannot
                // reach it: without this the capability badge/hint and the preset
                // option labels kept whichever language was active when the camera was
                // probed. Both calls reuse cached state, so no I2C read is repeated.
                updateStreamGate();
                populateStreamPresetSelect();
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

        // Live Preview (multi-camera)
        if (dom.btnStartStream) dom.btnStartStream.addEventListener("click", startStream);
        // Stop/Open act on the *selected* camera's stream, never on some global one.
        if (dom.btnStopStream) dom.btnStopStream.addEventListener("click", () => {
            const rec = streamForSelectedCamera();
            if (rec) stopStream(rec.streamId);
        });
        if (dom.streamPresetMode) dom.streamPresetMode.addEventListener("change", applyStreamPreset);
        if (dom.btnStreamRedetect) dom.btnStreamRedetect.addEventListener("click", refreshStreamCaps);
        if (dom.btnOpenPreview) dom.btnOpenPreview.addEventListener("click", () => {
            const rec = streamForSelectedCamera();
            if (rec) openPreviewWindow(rec.streamId);
        });
        if (dom.btnStopAllStreams) dom.btnStopAllStreams.addEventListener("click", stopAllStreams);
        // One delegated listener serves every row, so re-rendering the list does not
        // leak a listener per row.
        if (dom.streamList) dom.streamList.addEventListener("click", (ev) => {
            const btn = ev.target.closest("button[data-act]");
            if (!btn) return;
            const row = btn.closest("[data-stream-id]");
            if (!row) return;
            const sid = row.getAttribute("data-stream-id");
            if (btn.getAttribute("data-act") === "reopen") openPreviewWindow(sid);
            else stopStream(sid);
        });
    }

    // ========== Live Preview (multi-camera) ==========

    // ---- Stream registry -------------------------------------------------
    // Every running pipeline lives in state.streams, keyed by stream_id. The
    // panel edits the *selected* camera's entry, so looking a stream up by
    // video_node is what lets several cameras preview at the same time.
    function streamFor(videoNode) {
        if (!videoNode) return null;
        for (const rec of state.streams.values()) {
            if (rec.videoNode === videoNode) return rec;
        }
        return null;
    }

    function streamForSelectedCamera() {
        return streamFor((state.selectedCamera || {}).video_node);
    }

    // Deterministic popup name per camera: re-opening the same camera focuses its
    // existing window instead of stealing a different camera's popup. It must not
    // use the stream_id, because the window is pre-opened (inside the click
    // gesture, to beat the popup blocker) before the id is known.
    function popupNameFor(videoNode) {
        return "veyePreview_" + String(videoNode || "x").replace(/\W+/g, "");
    }

    function popupUrl(streamId) {
        return "/preview?stream_id=" + encodeURIComponent(streamId)
            + "&lang=" + encodeURIComponent(state.lang);
    }

    function popupSpecs() {
        return "width=1040,height=760,menubar=no,toolbar=no,location=no,status=no,resizable=yes";
    }

    function clearStreamTimers(rec) {
        if (!rec) return;
        if (rec.watchTimer) { clearInterval(rec.watchTimer); rec.watchTimer = null; }
        if (rec.inlineFpsTimer) { clearInterval(rec.inlineFpsTimer); rec.inlineFpsTimer = null; }
    }

    function closeStreamPopup(rec) {
        if (!rec || !rec.popup) return;
        try { rec.popup.close(); } catch (e) { /* ignore */ }
        rec.popup = null;
    }

    function forgetStream(streamId) {
        const rec = state.streams.get(streamId);
        if (!rec) return false;
        clearStreamTimers(rec);
        if (state.inlineStreamId === streamId) {
            state.inlineStreamId = null;
            try { dom.mjpegView.removeAttribute("src"); } catch (e) { /* ignore */ }
        }
        state.streams.delete(streamId);
        return true;
    }

    async function streamPost(url, body) {
        const res = await fetch(url, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body || {}),
        });
        let payload = null;
        try { payload = await res.json(); } catch (e) { /* no body */ }
        if (!res.ok) {
            let msg = "HTTP " + res.status;
            if (payload) {
                const d = payload.detail || payload.error;
                msg = (typeof d === "string") ? d : JSON.stringify(d || payload);
            }
            const err = new Error(msg);
            err.status = res.status;
            err.payload = payload;
            throw err;
        }
        return payload;
    }

    function streamNum(el, def) {
        if (!el) return def;
        const v = parseFloat(el.value);
        return isNaN(v) ? def : v;
    }

    // Inline fallback FPS: read the server-measured rate via the status endpoint
    // (only used when the popup is blocked and the thumbnail <img> is the consumer).
    function resetInlineFps(rec) {
        if (!rec) return;
        rec.inlineZeroTicks = 0;
        if (dom.streamLiveFps && state.inlineStreamId === rec.streamId) {
            dom.streamLiveFps.textContent = "0 fps";
            dom.streamLiveFps.style.display = "";
        }
    }

    // The pipeline is gone - either the server no longer knows the id (404) or it
    // reports the process dead.  Stop polling and surface the recorded reason; a
    // dead id must not be polled forever while the status line keeps saying 0 fps.
    function reportStreamGone(streamId, st) {
        let reason = "";
        if (st) {
            reason = st.error || "";
            if (!reason && st.stderr_tail && st.stderr_tail.length) reason = st.stderr_tail.slice(-2).join(" | ");
            if (!reason && typeof st.exit_code === "number") reason = "gst-launch exit code " + st.exit_code;
        }
        // Captured before the teardown, which drops the record.
        const rec = state.streams.get(streamId);
        handleStreamStopped(streamId);
        // Only narrate the selected camera's fate in the shared status line, so a
        // background camera dying does not silently rewrite what the user is doing.
        if (!rec || rec.videoNode === (state.selectedCamera || {}).video_node) {
            setStreamStatus(t("stream.status_died") + (reason ? ": " + reason : ""), "error");
        }
    }

    // Hook called by a preview popup (same origin) when its pipeline dies, so the
    // main panel stops reporting "Previewing" for a stream that is already gone.
    // The stream id routes it to the right record out of however many are running.
    window.__veyePreviewEnded = function (sid, reasonText) {
        if (!sid || !state.streams.has(sid)) return;
        reportStreamGone(sid, { error: reasonText || "" });
    };

    async function updateInlineFps(streamId) {
        const rec = state.streams.get(streamId);
        if (!rec) return;
        if (state.inlineStreamId !== streamId) {
            if (rec.inlineFpsTimer) { clearInterval(rec.inlineFpsTimer); rec.inlineFpsTimer = null; }
            return;
        }
        try {
            const res = await fetch("/api/stream/" + encodeURIComponent(streamId) + "/status");
            if (res.status === 404) { reportStreamGone(streamId, null); return; }
            if (!res.ok) return;
            const st = await res.json();
            if (!st.alive) { reportStreamGone(streamId, st); return; }
            const v = (typeof st.measured_fps === "number" && st.measured_fps > 0) ? st.measured_fps : 0;
            if (dom.streamLiveFps) dom.streamLiveFps.textContent = (v ? v.toFixed(1) : "0") + " fps";
            // Alive but delivering nothing for ~5s: say so instead of a silent 0 fps.
            if (v <= 0) {
                rec.inlineZeroTicks = (rec.inlineZeroTicks || 0) + 1;
                if (rec.inlineZeroTicks === 5 && rec.videoNode === (state.selectedCamera || {}).video_node) {
                    setStreamStatus(t("stream.status_noframes") + " \u00b7 " + st.width + "\u00d7" + st.height + " @ " + st.fps + " fps", "error");
                }
            } else if (rec.inlineZeroTicks) {
                rec.inlineZeroTicks = 0;
            }
        } catch (e) { /* ignore transient fetch errors */ }
    }

    function buildStreamBody() {
        const cam = state.selectedCamera || {};
        const series = state.cameraSeries || "gx";
        const cap = state.streamCap;   // GX: 1=ROI, 2=Preset, null=auto; MV: n/a
        const width = Math.round(streamNum(dom.streamWidth, 1920));
        const height = Math.round(streamNum(dom.streamHeight, 1080));
        const fps = streamNum(dom.streamFps, 30);
        if (width < 1 || height < 1) throw new Error(t("stream.width") + "/" + t("stream.height") + " invalid");
        return {
            platform: state.platform,
            camera: cam,
            series,
            width,
            height,
            fps,
            roi_x: Math.round(streamNum(dom.streamRoiX, 0)),
            roi_y: Math.round(streamNum(dom.streamRoiY, 0)),
            cap_mode: series === "gx" ? cap : null,
            preset_mode: (series === "gx" && cap === 2) ? Math.round(streamNum(dom.streamPresetMode, 0)) : null,
            transport: "mjpeg",
            jpeg_quality: Math.round(streamNum(dom.streamQuality, 85)),
        };
    }

    // Put a running stream's own parameters back into the inputs. Without this,
    // switching cameras would show values that differ from what that pipeline is
    // actually capturing (register prefill reads the live sensor, not the stream).
    function applyStreamParams(rec) {
        if (!rec || !rec.params) return;
        const p = rec.params;
        if (dom.streamWidth) dom.streamWidth.value = p.width;
        if (dom.streamHeight) dom.streamHeight.value = p.height;
        if (dom.streamFps) dom.streamFps.value = p.fps;
        if (dom.streamRoiX) dom.streamRoiX.value = p.roiX;
        if (dom.streamRoiY) dom.streamRoiY.value = p.roiY;
        if (dom.streamQuality) dom.streamQuality.value = p.quality;
        if (dom.streamPresetMode && p.presetMode != null) dom.streamPresetMode.value = String(p.presetMode);
    }

    function setStreamStatus(msg, kind) {
        if (!dom.streamStatus) return;
        dom.streamStatus.textContent = msg || "";
        dom.streamStatus.className = "stream-status" + (kind ? " " + kind : "");
    }

    // Give the inline <img> one stream to read, and keep it attached even when
    // another camera is selected: hiding it would drop the connection, and the
    // server tears a pipeline down as soon as its only consumer disconnects.
    function attachInline(rec) {
        state.inlineStreamId = rec.streamId;
        dom.mjpegView.src = rec.playbackUrl + "?t=" + Date.now();
        resetInlineFps(rec);
        if (!rec.inlineFpsTimer) {
            rec.inlineFpsTimer = setInterval(() => updateInlineFps(rec.streamId), 1000);
        }
    }

    function detachInline() {
        state.inlineStreamId = null;
        try { dom.mjpegView.removeAttribute("src"); } catch (e) { /* ignore */ }
    }

    async function startStream() {
        const cam = state.selectedCamera;
        if (!cam || !cam.video_node) { setStreamStatus(t("stream.hint_no_camera"), "error"); return; }
        const series = state.cameraSeries || "gx";
        if (series !== "gx" && series !== "mv") return;
        // Already streaming this camera: bring its window back rather than asking
        // for a second pipeline on the same node (the server would reply 409).
        const existing = streamFor(cam.video_node);
        if (existing) { openPreviewWindow(existing.streamId); return; }
        // Client-side pre-check only; the server owns the real limit. The list poll
        // adopts any stream this tab does not know about yet (e.g. after a reload),
        // which is what keeps the pre-opened window below from ever blanking a
        // live preview that shares the same deterministic popup name.
        if (state.streams.size >= state.maxStreams) {
            setStreamStatus(t("stream.limit_reached") + " (" + state.streams.size + "/" + state.maxStreams + ")", "error");
            refreshStreamList(true);
            return;
        }
        // Pre-open the popup synchronously (still inside the click gesture) so it
        // is not blocked; we navigate it to /preview once we know the stream_id.
        const popup = window.open("about:blank", popupNameFor(cam.video_node), popupSpecs());
        const popupBlocked = !popup;
        // The inline thumbnail has exactly one <img>, so it can only ever feed one
        // stream. Re-pointing it at the new camera would disconnect the stream it
        // currently serves, and the server tears a pipeline down as soon as its
        // only viewer leaves - so refuse instead of silently killing a running
        // preview. Multi-camera viewing needs the popup windows.
        if (popupBlocked && state.inlineStreamId && state.streams.has(state.inlineStreamId)) {
            const cur = state.streams.get(state.inlineStreamId);
            setStreamStatus(t("stream.inline_busy") + " (" + cur.label + ")", "error");
            syncStreamPanel();
            return;
        }
        dom.btnStartStream.disabled = true;
        setStreamStatus(t("stream.status_starting"), "loading");
        let body;
        try { body = buildStreamBody(); } catch (e) {
            if (popup) popup.close();
            setStreamStatus(e.message, "error"); dom.btnStartStream.disabled = false; return;
        }
        try {
            const data = await streamPost("/api/stream/start", body);
            state.streams.set(data.stream_id, {
                streamId: data.stream_id,
                videoNode: cam.video_node,
                label: data.label || cam.media_entity_name || cam.video_node,
                series,
                playbackUrl: data.playback_url,
                encoder: data.encoder || "",
                params: {
                    width: body.width, height: body.height, fps: body.fps,
                    roiX: body.roi_x, roiY: body.roi_y, quality: body.jpeg_quality,
                    presetMode: body.preset_mode,
                },
                popup: popupBlocked ? null : popup,
                watchTimer: null,
                inlineFpsTimer: null,
                inlineZeroTicks: 0,
                startedAt: Date.now(),
            });
            const rec = state.streams.get(data.stream_id);
            if (!popupBlocked) {
                // Popup is the sole consumer; the inline <img> stays detached so the
                // stream never has two readers on the same stdout.
                popup.location.href = popupUrl(data.stream_id);
                startStreamWatch(rec);
            } else {
                // Popup blocked -> fall back to the inline thumbnail.
                attachInline(rec);
            }
            syncStreamPanel();
            setStreamStatus(
                t("stream.status_previewing") + " \u00b7 " + rec.label +
                " \u00b7 " + body.width + "\u00d7" + body.height +
                " @ " + body.fps + " fps" + (data.encoder ? " \u00b7 " + data.encoder : ""),
                "ok"
            );
            refreshStreamList(true);
        } catch (e) {
            if (popup) { try { popup.close(); } catch (_) { /* ignore */ } }
            dom.btnStartStream.style.display = "";
            dom.btnStartStream.disabled = false;
            dom.streamPreviewWrap.style.display = "none";
            if (e.status === 429) setStreamStatus(t("stream.limit_reached") + ": " + e.message, "error");
            else if (e.status === 409) setStreamStatus(t("stream.status_busy") + ": " + e.message, "error");
            else setStreamStatus(e.message || t("stream.status_error"), "error");
            refreshStreamList(true);
        }
    }

    async function stopStream(streamId) {
        const rec = state.streams.get(streamId);
        if (!rec) return;
        const wasSelected = rec.videoNode === (state.selectedCamera || {}).video_node;
        // Disconnect every viewer first so the server tears the pipeline down.
        closeStreamPopup(rec);
        clearStreamTimers(rec);
        if (state.inlineStreamId === streamId) detachInline();
        try {
            await streamPost("/api/stream/" + encodeURIComponent(streamId) + "/stop", {});
        } catch (e) { console.warn("stop failed:", e); }
        forgetStream(streamId);
        syncStreamPanel();
        refreshStreamList(true);
        if (wasSelected) setStreamStatus(t("stream.status_stopped"), "");
    }

    async function stopAllStreams() {
        const ids = Array.from(state.streams.keys());
        ids.forEach((id) => {
            const rec = state.streams.get(id);
            closeStreamPopup(rec);
            clearStreamTimers(rec);
        });
        detachInline();
        try {
            await streamPost("/api/stream/stop-all", {});
        } catch (e) { console.warn("stop-all failed:", e); }
        ids.forEach((id) => forgetStream(id));
        syncStreamPanel();
        refreshStreamList(true);
        setStreamStatus(t("stream.status_stopped"), "");
    }

    function updateStreamGate() {
        const cam = state.selectedCamera;
        const series = state.cameraSeries || "gx";
        const isGx = series === "gx";
        const isMv = series === "mv";
        const hasCam = !!(cam && cam.video_node);
        const cap = state.streamCap;   // GX only: 1=ROI, 2=Preset, null=unknown

        // Live preview supports GX (UYVY) and MV/RAW (GREY); hide it otherwise.
        if (dom.streamSection) dom.streamSection.style.display = (isGx || isMv) ? "" : "none";
        if (!isGx && !isMv) return;

        // MV/RAW has no VideoModeCap concept: hide the GX capability row.
        if (dom.streamCapRow) dom.streamCapRow.style.display = isGx ? "" : "none";

        const isPreset = isGx && hasCam && cap === 2;
        const isRoi = hasCam && (isMv || cap === 1 || cap == null);

        if (dom.streamPresetWrap) dom.streamPresetWrap.style.display = isPreset ? "" : "none";
        if (dom.streamRoiWrap) dom.streamRoiWrap.style.display = isRoi ? "" : "none";
        // For preset cameras the resolution is fixed by the selected sensor mode.
        if (dom.streamWidth) dom.streamWidth.readOnly = isPreset;
        if (dom.streamHeight) dom.streamHeight.readOnly = isPreset;

        setStreamCapUI(isGx, hasCam, cap);

        if (dom.streamHint) {
            if (isMv) { dom.streamHint.textContent = t("stream.hint_mv"); dom.streamHint.className = "stream-hint"; }
            else if (!hasCam) { dom.streamHint.textContent = t("stream.hint_no_camera"); dom.streamHint.className = "stream-hint"; }
            else { dom.streamHint.textContent = t("stream.hint"); dom.streamHint.className = "stream-hint"; }
        }
        if (dom.streamControls) dom.streamControls.classList.toggle("stream-disabled", !hasCam);
        // A camera that is already streaming shows Stop, not Start.
        if (dom.btnStartStream && !streamForSelectedCamera()) {
            dom.btnStartStream.disabled = !hasCam;
        }
        syncStreamPanel();
    }

    function setStreamCapUI(isGx, hasCam, cap) {
        const badge = dom.streamCapBadge, text = dom.streamCapText, btn = dom.btnStreamRedetect;
        if (btn) btn.style.display = (isGx && hasCam) ? "" : "none";
        if (!isGx || !hasCam) {
            if (badge) { badge.textContent = "—"; badge.className = "stream-cap-badge cap-unknown"; }
            if (text) text.textContent = "";
            return;
        }
        if (cap === 1) {
            if (badge) { badge.textContent = t("stream.cap_roi"); badge.className = "stream-cap-badge cap-roi"; }
            if (text) text.textContent = t("stream.cap_text_roi");
        } else if (cap === 2) {
            if (badge) { badge.textContent = t("stream.cap_preset"); badge.className = "stream-cap-badge cap-preset"; }
            if (text) text.textContent = t("stream.cap_text_preset");
        } else {
            if (badge) { badge.textContent = t("stream.cap_unknown"); badge.className = "stream-cap-badge cap-unknown"; }
            if (text) text.textContent = t("stream.cap_text_unknown");
        }
    }

    async function refreshStreamCaps() {
        const cam = state.selectedCamera;
        const series = state.cameraSeries || "gx";
        const isGx = series === "gx";
        const isMv = series === "mv";
        const hasCam = !!(cam && cam.video_node);
        state.streamPresetModes = [];
        // Unknown series or no camera selected: nothing to detect or prefill.
        if ((!isGx && !isMv) || !hasCam) {
            state.streamCap = null; populateStreamPresetSelect(); updateStreamGate(); return;
        }
        if (dom.streamCapBadge) { dom.streamCapBadge.className = "stream-cap-badge cap-unknown"; dom.streamCapBadge.textContent = "…"; }
        if (dom.streamCapText) dom.streamCapText.textContent = t("stream.cap_detecting");
        const i2c = getEffectiveI2c();
        let data = {};
        try {
            const url = "/api/stream/capabilities?platform=" + encodeURIComponent(state.platform)
                + "&video_node=" + encodeURIComponent(cam.video_node)
                + "&i2c_bus=" + encodeURIComponent(i2c.bus)
                + "&i2c_addr=" + encodeURIComponent(i2c.addr)
                + "&series=" + encodeURIComponent(series);
            data = await apiGet(url);
            state.streamCap = isGx ? ((data.video_mode_cap === 1 || data.video_mode_cap === 2) ? data.video_mode_cap : null) : null;
            state.streamPresetModes = data.preset_modes || [];
        } catch (e) {
            console.warn("stream caps failed:", e);
            state.streamCap = null;
            state.streamPresetModes = [];
        }
        populateStreamPresetSelect();
        applyStreamCurrent(data.current);
        updateStreamGate();
    }

    // Prefill the Live Preview Width/Height/FPS + ROI offsets from the camera's
    // current picture (read server-side), instead of the static 1920x1080@30
    // defaults.  Preset cameras are driven by the preset selector, so skipped.
    function applyStreamCurrent(cur) {
        if (!cur || typeof cur !== "object") return;
        if (state.streamCap === 2) return;
        // While this camera is streaming, its own pipeline parameters win: overwriting
        // them with live register values would show numbers that differ from what the
        // preview is actually producing.
        const rec = streamForSelectedCamera();
        if (rec) { applyStreamParams(rec); return; }
        if (cur.width  && dom.streamWidth)  dom.streamWidth.value  = cur.width;
        if (cur.height && dom.streamHeight) dom.streamHeight.value = cur.height;
        if (typeof cur.fps === "number" && cur.fps > 0 && dom.streamFps) dom.streamFps.value = cur.fps;
        if (Number.isFinite(cur.roi_x) && dom.streamRoiX) dom.streamRoiX.value = cur.roi_x;
        if (Number.isFinite(cur.roi_y) && dom.streamRoiY) dom.streamRoiY.value = cur.roi_y;
    }

    function populateStreamPresetSelect() {
        const sel = dom.streamPresetMode;
        if (!sel) return;
        const prev = sel.value;
        sel.innerHTML = "";
        const modes = state.streamPresetModes || [];
        if (state.streamCap !== 2 || !modes.length) return;
        // Labels come from t() so a language switch can rebuild them from cache;
        // this function is called again on switch, and must then keep the choice.
        const modeWord = t("stream.mode_word");
        modes.forEach((m) => {
            const opt = document.createElement("option");
            opt.value = String(m.mode);
            opt.textContent = modeWord + " " + m.mode + " · " + m.width + "×" + m.height
                + " @ " + m.fps + "fps" + (m.read_mode_name ? " · " + m.read_mode_name : "");
            sel.appendChild(opt);
        });
        if (prev && Array.prototype.some.call(sel.options, (o) => o.value === prev)) {
            sel.value = prev;
            applyStreamPreset();
            return;
        }
        // Preselect the mode that matches the camera's current resolution.
        const cam = state.selectedCamera || {};
        let idx = 0;
        for (let i = 0; i < modes.length; i++) {
            if (cam.width && modes[i].width === cam.width && modes[i].height === cam.height) { idx = i; break; }
        }
        sel.selectedIndex = idx;
        applyStreamPreset();
    }

    function applyStreamPreset() {
        if (state.streamCap !== 2) return;
        const sel = dom.streamPresetMode;
        if (!sel || !sel.options.length) return;
        // Same rule as applyStreamCurrent: a running stream keeps showing the
        // resolution it actually captures, not whatever the selector landed on.
        const rec = streamForSelectedCamera();
        if (rec) { applyStreamParams(rec); return; }
        const mode = parseInt(sel.value, 10);
        const m = (state.streamPresetModes || []).find((x) => x.mode === mode);
        if (!m) return;
        if (dom.streamWidth) dom.streamWidth.value = m.width;
        if (dom.streamHeight) dom.streamHeight.value = m.height;
        if (dom.streamFps && m.fps) dom.streamFps.value = m.fps;
    }

    // Render the panel for the currently selected camera. Two independent things
    // can occupy the preview area at once, because they belong to different
    // streams: the selected camera's popup (hint only) and whichever stream the
    // inline <img> is consuming - the latter may well be another camera, and must
    // stay rendered or its preview would be torn down by the disconnect.
    function syncStreamPanel() {
        const rec = streamForSelectedCamera();
        const inlineRec = state.inlineStreamId ? state.streams.get(state.inlineStreamId) : null;
        const popupOpen = !!(rec && rec.popup && !rec.popup.closed);

        if (dom.btnStartStream) {
            dom.btnStartStream.style.display = rec ? "none" : "";
            if (!rec) dom.btnStartStream.disabled = !((state.selectedCamera || {}).video_node);
        }
        if (dom.btnStopStream) dom.btnStopStream.style.display = rec ? "" : "none";
        if (dom.btnOpenPreview) dom.btnOpenPreview.style.display = (rec && !popupOpen) ? "" : "none";

        if (dom.mjpegView) dom.mjpegView.style.display = inlineRec ? "" : "none";
        if (dom.mjpegCaption) {
            dom.mjpegCaption.textContent = inlineRec ? inlineRec.label : "";
            dom.mjpegCaption.style.display = inlineRec ? "" : "none";
        }
        if (dom.streamLiveFps) dom.streamLiveFps.style.display = inlineRec ? "" : "none";
        if (dom.streamPopupHint) dom.streamPopupHint.style.display = popupOpen ? "" : "none";
        if (dom.streamPreviewWrap) {
            dom.streamPreviewWrap.style.display = (inlineRec || popupOpen) ? "" : "none";
        }
    }

    function openPreviewWindow(streamId) {
        const rec = state.streams.get(streamId);
        if (!rec) return null;
        let w = rec.popup;
        if (w && !w.closed) { try { w.focus(); return w; } catch (e) { /* fallthrough */ } }
        // Deterministic name: after a page reload this re-adopts the window the
        // browser still holds for this camera instead of spawning a duplicate.
        w = window.open(popupUrl(streamId), popupNameFor(rec.videoNode), popupSpecs());
        if (w) {
            rec.popup = w;
            // Promoting to the popup: the inline <img> must stop reading it, or both
            // consumers would split one stdout's multipart frames. Drop it only after
            // the popup is up, so the pipeline is never left without a consumer.
            if (state.inlineStreamId === streamId) {
                detachInline();
                if (rec.inlineFpsTimer) { clearInterval(rec.inlineFpsTimer); rec.inlineFpsTimer = null; }
            }
            startStreamWatch(rec);
            syncStreamPanel();
        }
        return w;
    }

    function startStreamWatch(rec) {
        if (rec.watchTimer) clearInterval(rec.watchTimer);
        rec.watchTimer = setInterval(() => {
            if (rec.popup && rec.popup.closed) {
                rec.popup = null;
                // The popup held the only consumer, so the server already reaped the
                // pipeline when the connection dropped; this is local bookkeeping.
                handleStreamStopped(rec.streamId);
            }
        }, 1000);
    }

    // Local-side teardown of a stream that is no longer running (stopped, died, or
    // its viewer went away). Safe to call twice; only the first call does anything.
    function dropStreamLocally(streamId) {
        const rec = state.streams.get(streamId);
        if (!rec) return false;
        clearStreamTimers(rec);
        closeStreamPopup(rec);
        forgetStream(streamId);
        syncStreamPanel();
        return true;
    }

    function handleStreamStopped(streamId) {
        if (!dropStreamLocally(streamId)) return;
        refreshStreamList(true);
    }

    // ---- Running-previews list ------------------------------------------
    // The server is the source of truth: a stream can end without this tab noticing
    // (popup closed, pipeline crashed), so the list both informs the user and
    // reconciles state.streams. It also adopts streams that exist but are unknown
    // here, which is what makes the concurrency cap honest after a page reload.
    // What the pipeline is actually delivering to a viewer.  ``measured_fps`` is
    // fed by the byte counter in the read loop, so it stays 0 while nobody is
    // watching - say so instead of implying the camera stalled.
    function streamFpsText(s, rec) {
        const v = s.measured_fps || 0;
        if (v > 0) return Math.round(v) + " fps \u2192";
        const viewed = !!(rec && ((rec.popup && !rec.popup.closed)
            || state.inlineStreamId === rec.streamId));
        return viewed ? "0 fps \u2192" : t("stream.no_viewer");
    }

    function streamRowHtml(s, rec) {
        const sid = escapeHtml(s.stream_id);
        const label = escapeHtml(s.label || s.video_node || s.stream_id);
        const res = (s.width && s.height) ? (s.width + "\u00d7" + s.height) : "";
        const parts = [];
        if (res) parts.push(res);
        if (s.fps) parts.push(s.fps + " fps");
        // The encoder name is what reveals a silent fall back to CPU jpegenc.
        if (s.encoder) parts.push(s.encoder);
        parts.push(streamFpsText(s, rec));
        return (
            '<div class="stream-list-row" data-stream-id="' + sid + '">'
            + '<span class="stream-list-label" title="' + escapeHtml(s.video_node || "") + '">' + label + '</span>'
            + '<span class="stream-list-meta">' + escapeHtml(parts.join(" \u00b7 ")) + '</span>'
            + '<button class="btn btn-sm btn-outline" data-act="reopen" data-i18n-title="stream.reopen">\u25a1</button>'
            + '<button class="btn btn-sm btn-outline" data-act="stop" data-i18n-title="stream.stop">\u2715</button>'
            + '</div>'
        );
    }

    async function refreshStreamList(force) {
        if (!dom.streamListWrap) return;
        if (!force && state.streams.size === 0 && dom.streamListWrap.style.display === "none") return;
        let data = null;
        try {
            data = await apiGet("/api/stream/status");
        } catch (e) {
            return;  // transient; keep the current rows
        }
        const streams = (data && data.streams) || [];
        if (typeof data.max_streams === "number") state.maxStreams = data.max_streams;

        const alive = {};
        streams.forEach((s) => {
            alive[s.stream_id] = true;
            // Adopt a stream this tab does not know: after a reload the popups and
            // pipelines survive while state.streams is empty, and without this the
            // camera would offer "Start" for a node that is already capturing.
            if (!state.streams.has(s.stream_id)) {
                state.streams.set(s.stream_id, {
                    streamId: s.stream_id,
                    videoNode: s.video_node,
                    label: s.label || s.video_node || s.stream_id,
                    series: s.series || "gx",
                    playbackUrl: "/api/stream/" + s.stream_id + "/mjpeg",
                    encoder: s.encoder || "",
                    params: null,
                    popup: null,
                    watchTimer: null,
                    inlineFpsTimer: null,
                    inlineZeroTicks: 0,
                    startedAt: Date.now(),
                });
            }
        });
        // Drop local records the server no longer has (their pipeline is gone), except
        // very recent ones: a poll issued just before /start committed its pipeline
        // cannot know about it yet, and must not then delete it. dropStreamLocally
        // (not handleStreamStopped) keeps this single-pass: re-polling per row from
        // inside the poll would cascade.
        Array.from(state.streams.keys()).forEach((id) => {
            if (alive[id]) return;
            const rec = state.streams.get(id);
            if (rec && Date.now() - (rec.startedAt || 0) < 6000) return;
            dropStreamLocally(id);
        });

        if (!streams.length) {
            dom.streamList.innerHTML = "";
            dom.streamListWrap.style.display = "none";
            if (dom.streamListCount) dom.streamListCount.textContent = "0 / " + state.maxStreams;
            return;
        }
        dom.streamList.innerHTML = streams
            .map((s) => streamRowHtml(s, state.streams.get(s.stream_id)))
            .join("");
        if (dom.streamListCount) {
            dom.streamListCount.textContent = streams.length + " / " + state.maxStreams;
        }
        applyI18nAttributes(dom.streamList);
        dom.streamListWrap.style.display = "";
    }

    function startStreamListPoll() {
        if (state.streamListTimer) return;
        // 2s rather than 1s: every row costs one same-origin HTTP request, and each
        // live preview already holds one of the browser's six connections.
        state.streamListTimer = setInterval(() => refreshStreamList(false), 2000);
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
        await loadDefaultConfig();
        await loadSystemInfo();
        await probeCameras();
        await loadGroups();
        showView("welcome");
        updateStreamGate();
        // Adopt streams that outlived a page reload (their popups survive it), so the
        // concurrency budget and the Stop buttons reflect the server, not this tab.
        await refreshStreamList(true);
        startStreamListPoll();
    }

    // Start
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
