/**
 * ZhuShou Web Interface — Client-side JavaScript
 *
 * Pure vanilla JS (no build step).  Connects to the FastAPI backend
 * via WebSocket for real-time pipeline event streaming.
 */

(function () {
    "use strict";

    // ── DOM references ────────────────────────────────────────────

    const requestInput = document.getElementById("requestInput");
    const runBtn = document.getElementById("runBtn");
    const stopBtn = document.getElementById("stopBtn");
    const providerLabel = document.getElementById("providerLabel");
    const timerLabel = document.getElementById("timerLabel");
    const stageList = document.getElementById("stageList");
    const progressLabel = document.getElementById("progressLabel");
    const fileList = document.getElementById("fileList");
    const fileCount = document.getElementById("fileCount");
    const filePathLabel = document.getElementById("filePathLabel");
    const codeViewer = document.getElementById("codeViewer");
    const thinkingLog = document.getElementById("thinkingLog");
    const clearThinkingBtn = document.getElementById("clearThinking");
    const toast = document.getElementById("toast");

    // ── State ─────────────────────────────────────────────────────

    let ws = null;
    let timerInterval = null;
    let startTime = 0;
    let running = false;
    const files = {};       // path -> content
    let activeFile = null;
    const stages = {};      // stage_num -> DOM element

    // ── Init ──────────────────────────────────────────────────────

    async function init() {
        // Load config
        try {
            const res = await fetch("/api/config");
            const cfg = await res.json();
            providerLabel.textContent = cfg.provider || "--";
        } catch (e) {
            providerLabel.textContent = "--";
        }

        runBtn.addEventListener("click", startPipeline);
        stopBtn.addEventListener("click", stopPipeline);
        requestInput.addEventListener("keydown", (e) => {
            if (e.key === "Enter") startPipeline();
        });
        clearThinkingBtn.addEventListener("click", () => {
            thinkingLog.innerHTML = "";
        });
    }

    // ── Pipeline control ──────────────────────────────────────────

    async function startPipeline() {
        const request = requestInput.value.trim();
        if (!request || running) return;

        // Clear UI
        clearOutput();
        setRunning(true);

        try {
            const res = await fetch("/api/pipeline", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ request }),
            });
            const data = await res.json();

            if (!res.ok) {
                showToast(data.error || "Failed to start pipeline", "error");
                setRunning(false);
                return;
            }

            // Connect WebSocket
            connectWebSocket();
        } catch (e) {
            showToast("Connection error: " + e.message, "error");
            setRunning(false);
        }
    }

    function stopPipeline() {
        if (ws) {
            ws.close();
            ws = null;
        }
        setRunning(false);
        showToast("Pipeline stopped", "error");
    }

    function setRunning(state) {
        running = state;
        runBtn.style.display = state ? "none" : "";
        stopBtn.style.display = state ? "" : "none";
        requestInput.readOnly = state;

        if (state) {
            startTime = Date.now();
            timerInterval = setInterval(updateTimer, 1000);
        } else {
            clearInterval(timerInterval);
        }
    }

    function updateTimer() {
        const elapsed = Math.floor((Date.now() - startTime) / 1000);
        const m = Math.floor(elapsed / 60);
        const s = elapsed % 60;
        timerLabel.textContent =
            String(m).padStart(2, "0") + ":" + String(s).padStart(2, "0");
    }

    // ── WebSocket ─────────────────────────────────────────────────

    function connectWebSocket() {
        const proto = location.protocol === "https:" ? "wss:" : "ws:";
        ws = new WebSocket(proto + "//" + location.host + "/ws");

        ws.onopen = () => {
            showToast("Connected", "success");
        };

        ws.onmessage = (evt) => {
            try {
                const event = JSON.parse(evt.data);
                handleEvent(event);
            } catch (e) {
                console.warn("Bad event:", evt.data);
            }
        };

        ws.onclose = () => {
            if (running) {
                showToast("Connection lost", "error");
                setRunning(false);
            }
        };

        ws.onerror = () => {
            showToast("WebSocket error", "error");
        };
    }

    // ── Event dispatch ────────────────────────────────────────────

    function handleEvent(ev) {
        switch (ev.event_type) {
            case "stage_start":
                onStageStart(ev);
                break;
            case "stage_complete":
                onStageComplete(ev);
                break;
            case "thinking":
                onThinking(ev);
                break;
            case "code_output":
                onCodeOutput(ev);
                break;
            case "tool_call":
                onToolCall(ev);
                break;
            case "tool_result":
                onToolResult(ev);
                break;
            case "test_result":
                onTestResult(ev);
                break;
            case "debug_attempt":
                onDebugAttempt(ev);
                break;
            case "pipeline_complete":
                onPipelineComplete(ev);
                break;
            case "info":
                onInfo(ev);
                break;
            case "error":
                onError(ev);
                break;
        }
    }

    // ── Event handlers ────────────────────────────────────────────

    function onStageStart(ev) {
        const num = ev.stage_num;
        const name = ev.stage_name;
        const total = ev.total_stages;

        // Mark previous stages as not running
        Object.values(stages).forEach((el) => el.classList.remove("running"));

        // Create or update stage item
        if (!stages[num]) {
            const item = document.createElement("div");
            item.className = "stage-item";
            item.innerHTML =
                '<span class="stage-indicator pending">&#9675;</span>' +
                '<span class="stage-name pending"></span>' +
                '<span class="stage-duration"></span>';
            stageList.appendChild(item);
            stages[num] = item;
        }

        const item = stages[num];
        item.className = "stage-item running";
        item.querySelector(".stage-indicator").className =
            "stage-indicator running";
        item.querySelector(".stage-indicator").innerHTML = "&#9679;";
        item.querySelector(".stage-name").className = "stage-name running";
        item.querySelector(".stage-name").textContent = num + ". " + name;

        progressLabel.textContent =
            "Stage " + num + "/" + total + ": " + name;
    }

    function onStageComplete(ev) {
        const num = ev.stage_num;
        const dur = ev.duration_seconds;

        if (stages[num]) {
            const item = stages[num];
            item.classList.remove("running");
            item.querySelector(".stage-indicator").className =
                "stage-indicator complete";
            item.querySelector(".stage-indicator").innerHTML = "&#10003;";
            item.querySelector(".stage-name").className =
                "stage-name complete";
            if (dur > 0) {
                item.querySelector(".stage-duration").textContent =
                    dur.toFixed(1) + "s";
            }
        }
    }

    function onThinking(ev) {
        if (!ev.content || !ev.content.trim()) return;
        const div = document.createElement("div");
        div.className = "thinking-block";
        div.textContent = ev.content;
        thinkingLog.appendChild(div);
        thinkingLog.scrollTop = thinkingLog.scrollHeight;
    }

    function onCodeOutput(ev) {
        const path = ev.file_path;
        const action = ev.action;

        // Store placeholder
        if (!files[path]) {
            files[path] = "";
            const li = document.createElement("li");
            li.textContent = path;
            li.className = action === "create" ? "created" : "edited";
            li.addEventListener("click", () => selectFile(path, li));
            fileList.appendChild(li);
        }

        fileCount.textContent = Object.keys(files).length + " files";

        // Auto-select latest
        const items = fileList.querySelectorAll("li");
        if (items.length > 0) {
            selectFile(path, items[items.length - 1]);
        }
    }

    function onToolCall(ev) {
        const div = document.createElement("div");
        div.className = "tool-call";

        let argSummary = "";
        const args = ev.arguments || {};
        for (const key of ["path", "file_path", "command", "pattern"]) {
            if (args[key]) {
                argSummary = String(args[key]).substring(0, 80);
                break;
            }
        }

        div.innerHTML =
            "&gt;&gt; " +
            escapeHtml(ev.tool_name) +
            (argSummary
                ? ' <span class="args">(' + escapeHtml(argSummary) + ")</span>"
                : "");
        thinkingLog.appendChild(div);
        thinkingLog.scrollTop = thinkingLog.scrollHeight;
    }

    function onToolResult(ev) {
        const div = document.createElement("div");
        const ok = ev.success;
        div.className = "tool-result " + (ok ? "success" : "fail");

        const label = ok ? "OK" : "FAIL";
        const short =
            ev.output.length > 200
                ? ev.output.substring(0, 200) + "..."
                : ev.output;
        div.innerHTML =
            "<strong>" +
            label +
            "</strong> " +
            '<span class="output">' +
            escapeHtml(short) +
            "</span>";
        thinkingLog.appendChild(div);
        thinkingLog.scrollTop = thinkingLog.scrollHeight;

        // If file was written, try to fetch updated content
        if (
            ev.tool_name === "write_file" ||
            ev.tool_name === "edit_file"
        ) {
            // Content will be refreshed when the file is selected
        }
    }

    function onTestResult(ev) {
        const div = document.createElement("div");
        div.className =
            "test-result " + (ev.passed ? "passed" : "failed");
        const label = ev.passed ? "Tests PASSED" : "Tests FAILED";
        const short =
            ev.output.length > 300
                ? ev.output.substring(0, 300) + "..."
                : ev.output;
        div.innerHTML =
            "<strong>" +
            label +
            "</strong>" +
            '<span class="output">' +
            escapeHtml(short) +
            "</span>";
        thinkingLog.appendChild(div);
        thinkingLog.scrollTop = thinkingLog.scrollHeight;
    }

    function onDebugAttempt(ev) {
        const div = document.createElement("div");
        div.className =
            "debug-attempt " + (ev.passed ? "passed" : "");
        const status = ev.passed ? "PASSED" : "retrying...";
        div.textContent =
            "Debug attempt " +
            ev.attempt +
            "/" +
            ev.max_retries +
            ": " +
            status;
        thinkingLog.appendChild(div);
        thinkingLog.scrollTop = thinkingLog.scrollHeight;
    }

    function onPipelineComplete(ev) {
        setRunning(false);
        const stats = ev.stats || {};
        progressLabel.textContent =
            "Done: " +
            (stats.stages_completed || 0) +
            " stages | Tests: " +
            (stats.tests_passed || "N/A") +
            " | " +
            (stats.total_time || "");
        showToast("Pipeline complete", "success");

        if (ws) {
            ws.close();
            ws = null;
        }
    }

    function onInfo(ev) {
        const div = document.createElement("div");
        div.className = "info-msg";
        div.textContent = ev.message;
        thinkingLog.appendChild(div);
        thinkingLog.scrollTop = thinkingLog.scrollHeight;
    }

    function onError(ev) {
        const div = document.createElement("div");
        div.className = "error-msg";
        div.textContent = "Error: " + ev.message;
        thinkingLog.appendChild(div);
        thinkingLog.scrollTop = thinkingLog.scrollHeight;
    }

    // ── File viewer ───────────────────────────────────────────────

    function selectFile(path, liElement) {
        // Highlight active
        fileList.querySelectorAll("li").forEach((el) =>
            el.classList.remove("active")
        );
        if (liElement) liElement.classList.add("active");

        activeFile = path;
        filePathLabel.textContent = path;
        codeViewer.textContent = files[path] || "(file content loading...)";
    }

    // ── Helpers ───────────────────────────────────────────────────

    function clearOutput() {
        stageList.innerHTML = "";
        fileList.innerHTML = "";
        codeViewer.textContent = "";
        thinkingLog.innerHTML = "";
        filePathLabel.textContent = "Select a file to view";
        fileCount.textContent = "0 files";
        progressLabel.textContent = "Waiting to start...";
        timerLabel.textContent = "00:00";

        Object.keys(files).forEach((k) => delete files[k]);
        Object.keys(stages).forEach((k) => delete stages[k]);
        activeFile = null;
    }

    function showToast(msg, type) {
        toast.textContent = msg;
        toast.className = "toast " + (type || "");
        clearTimeout(toast._timeout);
        toast._timeout = setTimeout(() => {
            toast.className = "toast hidden";
        }, 3000);
    }

    function escapeHtml(text) {
        const div = document.createElement("div");
        div.appendChild(document.createTextNode(text));
        return div.innerHTML;
    }

    // ── Boot ──────────────────────────────────────────────────────

    init();
})();
