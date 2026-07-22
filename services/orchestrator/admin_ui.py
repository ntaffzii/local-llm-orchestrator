from __future__ import annotations


def admin_ui_html() -> str:
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>GoModel Local LLM Console</title>
  <style>
    :root {
      color-scheme: light dark;
      --bg: #f4f6f8;
      --panel: #ffffff;
      --panel-soft: #f9fafb;
      --text: #17202e;
      --muted: #647082;
      --line: #d8dee7;
      --accent: #0b7a75;
      --accent-soft: #dff5f2;
      --blue: #2f6fed;
      --blue-soft: #e8efff;
      --warn: #a15c13;
      --warn-soft: #fff2d8;
      --danger: #a13b3b;
      --ok: #1e7a4f;
      --shadow: 0 1px 2px rgba(15, 23, 42, 0.08);
    }
    @media (prefers-color-scheme: dark) {
      :root {
        --bg: #0e141b;
        --panel: #171f28;
        --panel-soft: #1d2731;
        --text: #e6edf3;
        --muted: #93a1b0;
        --line: #2b3743;
        --accent: #4bd0c6;
        --accent-soft: #123833;
        --blue: #6ea0ff;
        --blue-soft: #16263f;
        --warn: #e0b35c;
        --warn-soft: #3a2e14;
        --danger: #f08a8a;
        --ok: #5fce93;
        --shadow: 0 1px 2px rgba(0, 0, 0, 0.4);
      }
      header { background: rgba(23, 31, 40, 0.96); }
      input, select, textarea { background: #0f1720; color: var(--text); }
      button.secondary, button.ghost { background: var(--panel); }
      .th { background: #1d2731; }
      .tab.active { color: var(--accent); }
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: "Segoe UI", system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
      font-size: 14px;
    }
    header {
      position: sticky;
      top: 0;
      z-index: 10;
      border-bottom: 1px solid var(--line);
      background: rgba(255, 255, 255, 0.96);
      backdrop-filter: blur(10px);
    }
    .wrap {
      width: min(1440px, calc(100vw - 32px));
      margin: 0 auto;
    }
    .topbar {
      min-height: 70px;
      display: grid;
      grid-template-columns: minmax(240px, 1fr) minmax(300px, 440px);
      gap: 18px;
      align-items: center;
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 12px;
      min-width: 0;
    }
    .mark {
      width: 38px;
      height: 38px;
      display: grid;
      place-items: center;
      border: 1px solid #8fd8d0;
      border-radius: 8px;
      background: linear-gradient(145deg, #e8fbf8, #ffffff);
      color: var(--accent);
      font-weight: 800;
    }
    h1 {
      margin: 0;
      font-size: 20px;
      line-height: 1.2;
      letter-spacing: 0;
    }
    .subtitle {
      margin-top: 3px;
      color: var(--muted);
      font-size: 12px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    main { padding: 18px 0 36px; }
    .layout {
      display: grid;
      grid-template-columns: 260px minmax(0, 1fr);
      gap: 16px;
      align-items: start;
    }
    .sidebar {
      position: sticky;
      top: 88px;
      display: grid;
      gap: 10px;
    }
    section, .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: var(--shadow);
    }
    section { padding: 16px; }
    .content {
      display: grid;
      gap: 16px;
    }
    .quick {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
    }
    .metric {
      min-height: 86px;
      padding: 13px;
      display: grid;
      align-content: space-between;
      gap: 8px;
    }
    .metric-title {
      color: var(--muted);
      font-size: 12px;
      font-weight: 650;
    }
    .metric-value {
      font-size: 22px;
      font-weight: 750;
      letter-spacing: 0;
    }
    .metric-note {
      color: var(--muted);
      font-size: 12px;
      overflow-wrap: anywhere;
    }
    .tabs {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      padding: 8px;
    }
    .tab {
      width: 100%;
      min-height: 36px;
      justify-content: flex-start;
      background: transparent;
      color: var(--text);
      border-color: transparent;
    }
    .tab.active {
      background: var(--accent-soft);
      color: #075b57;
      border-color: #b8e7e1;
    }
    .view { display: none; }
    .view.active { display: grid; gap: 16px; }
    .section-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 14px;
    }
    h2 {
      margin: 0;
      font-size: 16px;
      line-height: 1.2;
      font-weight: 700;
      letter-spacing: 0;
    }
    .hint {
      color: var(--muted);
      font-size: 12px;
    }
    label {
      display: block;
      margin: 12px 0 6px;
      color: var(--muted);
      font-size: 12px;
      font-weight: 650;
    }
    input, select, textarea {
      width: 100%;
      min-height: 38px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #fff;
      color: var(--text);
      padding: 8px 10px;
      font: inherit;
      font-size: 14px;
    }
    textarea {
      resize: vertical;
      min-height: 118px;
      line-height: 1.45;
    }
    input:focus, select:focus, textarea:focus {
      outline: 2px solid rgba(11, 122, 117, 0.18);
      border-color: var(--accent);
    }
    .row {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
    }
    .row.three {
      grid-template-columns: repeat(3, minmax(0, 1fr));
    }
    .actions {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 14px;
    }
    button {
      min-height: 38px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 7px;
      border: 1px solid var(--accent);
      border-radius: 6px;
      background: var(--accent);
      color: #fff;
      padding: 8px 12px;
      font: inherit;
      font-size: 14px;
      font-weight: 650;
      cursor: pointer;
    }
    button.secondary {
      background: #fff;
      color: #075b57;
    }
    button.blue {
      border-color: var(--blue);
      background: var(--blue);
    }
    button.ghost {
      border-color: var(--line);
      background: #fff;
      color: var(--text);
    }
    button:disabled {
      opacity: 0.55;
      cursor: not-allowed;
    }
    .status {
      min-height: 38px;
      padding: 9px 10px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: var(--panel-soft);
      color: var(--muted);
      font-size: 13px;
      overflow-wrap: anywhere;
    }
    .status.ok { border-color: rgba(30, 122, 79, 0.35); color: var(--ok); background: #f0fbf5; }
    .status.err { border-color: rgba(161, 59, 59, 0.35); color: var(--danger); background: #fff3f3; }
    .status.warn { border-color: rgba(161, 92, 19, 0.35); color: var(--warn); background: var(--warn-soft); }
    .badge {
      display: inline-flex;
      align-items: center;
      min-height: 24px;
      padding: 3px 8px;
      border-radius: 999px;
      background: var(--blue-soft);
      color: #244f9f;
      font-size: 12px;
      font-weight: 700;
      white-space: nowrap;
    }
    .badge.ok { background: #dff8ea; color: var(--ok); }
    .badge.warn { background: var(--warn-soft); color: var(--warn); }
    .badge.muted { background: #eef1f5; color: var(--muted); }
    .toolbar {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
      justify-content: space-between;
      margin: 12px 0;
    }
    .preset-row {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 10px;
    }
    .tool-list {
      display: grid;
      gap: 8px;
      max-height: 520px;
      overflow: auto;
      padding-right: 4px;
    }
    .tool-item {
      display: grid;
      grid-template-columns: auto minmax(0, 1fr) auto;
      gap: 10px;
      align-items: start;
      padding: 11px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
    }
    .tool-item.disabled {
      background: var(--panel-soft);
      color: var(--muted);
    }
    .tool-item input {
      width: 18px;
      height: 18px;
      min-height: 18px;
      margin-top: 2px;
      accent-color: var(--accent);
    }
    .tool-name {
      font-weight: 750;
      overflow-wrap: anywhere;
    }
    .tool-desc {
      margin-top: 4px;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.4;
      overflow-wrap: anywhere;
    }
    .tool-summary {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 8px;
    }
    .mini-stat {
      padding: 10px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel-soft);
    }
    .mini-stat strong {
      display: block;
      margin-bottom: 2px;
      font-size: 18px;
    }
    .table {
      display: grid;
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow: hidden;
    }
    .tr {
      display: grid;
      min-height: 44px;
      border-top: 1px solid var(--line);
      align-items: center;
    }
    .tr:first-child { border-top: 0; }
    .tr.routes { grid-template-columns: 170px 120px minmax(180px, 1fr) 96px 86px; }
    .tr.models { grid-template-columns: 190px 150px minmax(180px, 1fr) 96px; }
    .tr.providers { grid-template-columns: 140px minmax(230px, 1fr) 150px; }
    .th {
      background: #eef2f5;
      color: var(--muted);
      font-size: 12px;
      font-weight: 750;
      text-transform: uppercase;
    }
    .td, .th span {
      padding: 10px 12px;
      min-width: 0;
      overflow-wrap: anywhere;
      font-size: 13px;
    }
    .split {
      display: grid;
      grid-template-columns: minmax(340px, 0.82fr) minmax(360px, 1.18fr);
      gap: 16px;
      align-items: start;
    }
    pre {
      margin: 0;
      max-height: 360px;
      overflow: auto;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #101826;
      color: #d9e7ff;
      padding: 12px;
      font: 12px/1.5 Consolas, "SFMono-Regular", monospace;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
    }
    .output {
      min-height: 220px;
    }
    .api-key-box {
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) auto auto;
      gap: 8px;
      align-items: end;
    }
    .api-key-box label { margin-top: 0; }
    @media (max-width: 1100px) {
      .layout, .split { grid-template-columns: 1fr; }
      .sidebar { position: static; }
      .quick { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .topbar { grid-template-columns: 1fr; padding: 12px 0; }
      .subtitle { white-space: normal; }
    }
    @media (max-width: 760px) {
      .wrap { width: min(100vw - 20px, 1440px); }
      .quick, .row, .row.three, .api-key-box, .tool-summary { grid-template-columns: 1fr; }
      .tr { grid-template-columns: 1fr !important; padding: 8px 0; }
      .th { display: none; }
      .td { padding: 5px 12px; }
      .td::before {
        content: attr(data-label);
        display: block;
        margin-bottom: 2px;
        color: var(--muted);
        font-size: 11px;
        font-weight: 750;
        text-transform: uppercase;
      }
    }
  </style>
</head>
<body>
  <!-- Local LLM Admin -->
  <header>
    <div class="wrap topbar">
      <div class="brand">
        <div class="mark">GM</div>
        <div>
          <h1>GoModel Local LLM Console</h1>
          <div class="subtitle">OpenAI-compatible bot API gateway for local llama.cpp models, prompt routing, and MCP tools</div>
        </div>
      </div>
      <div class="api-key-box">
        <div>
          <label for="apiKey">API key</label>
          <input id="apiKey" type="password" autocomplete="off" placeholder="ORCHESTRATOR_API_KEY">
        </div>
        <div title="Only needed if ORCHESTRATOR_ADMIN_API_KEY is set to a different value than the API key. Leave empty to reuse the API key for admin actions.">
          <label for="adminKey">Admin key <span class="hint">optional</span></label>
          <input id="adminKey" type="password" autocomplete="off" placeholder="ORCHESTRATOR_ADMIN_API_KEY"
                 aria-label="Admin API key, optional, only if different from the API key">
        </div>
        <button id="rememberBtn" class="ghost">Remember</button>
        <button id="loadBtn">Connect</button>
      </div>
    </div>
  </header>

  <main class="wrap">
    <div class="layout">
      <aside class="sidebar">
        <section>
          <div class="status" id="status">Connect with an API key to load the console.</div>
          <div class="actions">
            <button id="refreshBtn" class="secondary">Refresh</button>
            <button id="reloadBtn" class="ghost">Reload</button>
          </div>
        </section>
        <nav class="panel tabs" aria-label="Console sections" role="tablist">
          <button class="tab active" data-view="overview" role="tab" aria-selected="true" aria-controls="overview">Overview</button>
          <button class="tab" data-view="routing" role="tab" aria-selected="false" aria-controls="routing" tabindex="-1">Routing</button>
          <button class="tab" data-view="playground" role="tab" aria-selected="false" aria-controls="playground" tabindex="-1">Playground</button>
          <button class="tab" data-view="tools" role="tab" aria-selected="false" aria-controls="tools" tabindex="-1">Tools</button>
          <button class="tab" data-view="api" role="tab" aria-selected="false" aria-controls="api" tabindex="-1">API</button>
        </nav>
      </aside>

      <div class="content">
        <div class="quick">
          <section class="metric">
            <div class="metric-title">Orchestrator</div>
            <div class="metric-value" id="metricApi">--</div>
            <div class="metric-note" id="metricApiNote">/health</div>
          </section>
          <section class="metric">
            <div class="metric-title">llama.cpp</div>
            <div class="metric-value" id="metricLlama">--</div>
            <div class="metric-note" id="metricLlamaNote">/ready</div>
          </section>
          <section class="metric">
            <div class="metric-title">Models</div>
            <div class="metric-value" id="metricModels">--</div>
            <div class="metric-note" id="metricModelsNote">physical + virtual</div>
          </section>
          <section class="metric">
            <div class="metric-title">MCP</div>
            <div class="metric-value" id="metricMcp">--</div>
            <div class="metric-note" id="metricMcpNote">tool allowlist</div>
          </section>
        </div>

        <div id="overview" class="view active">
          <section>
            <div class="section-head">
              <h2>Provider Map</h2>
              <span class="hint">Base URLs used by virtual models</span>
            </div>
            <div id="providers" class="table"></div>
          </section>
          <section>
            <div class="section-head">
              <h2>Model Inventory</h2>
              <span class="hint">Physical and virtual model IDs exposed to OpenAI clients</span>
            </div>
            <div id="modelInventory" class="table"></div>
          </section>
        </div>

        <div id="routing" class="view">
          <div class="split">
            <section>
              <div class="section-head">
                <h2>Route Editor</h2>
                <span class="badge">virtual model</span>
              </div>
              <div class="row">
                <div>
                  <label for="virtualModel">Virtual model</label>
                  <select id="virtualModel"></select>
                </div>
                <div>
                  <label for="mainProvider">Provider</label>
                  <select id="mainProvider"></select>
                </div>
              </div>
              <label for="mainModel">Target model ID</label>
              <input id="mainModel" placeholder="gemma4-e2b">
              <div class="row">
                <div>
                  <label for="improvePolicy">Improve prompt</label>
                  <select id="improvePolicy">
                    <option value="true">true</option>
                    <option value="false">false</option>
                    <option value="auto">auto</option>
                  </select>
                </div>
                <div>
                  <label for="toolsPolicy">Tools</label>
                  <select id="toolsPolicy">
                    <option value="false">false</option>
                    <option value="true">true</option>
                    <option value="auto">auto</option>
                  </select>
                </div>
              </div>
              <div class="actions">
                <button id="saveVirtualBtn">Save Route</button>
                <button id="copyRouteBtn" class="secondary">Copy JSON</button>
              </div>
            </section>

            <section>
              <div class="section-head">
                <h2>Prompt Improver</h2>
                <span class="badge ok">LFM2.5</span>
              </div>
              <div class="row">
                <div>
                  <label for="promptProvider">Provider</label>
                  <select id="promptProvider"></select>
                </div>
                <div>
                  <label for="promptModel">Model</label>
                  <input id="promptModel" placeholder="prompt">
                </div>
              </div>
              <div class="row">
                <div>
                  <label for="promptTemperature">Temperature</label>
                  <input id="promptTemperature" type="number" step="0.01" min="0" max="2">
                </div>
                <div>
                  <label for="promptMaxTokens">Max tokens</label>
                  <input id="promptMaxTokens" type="number" step="1" min="1">
                </div>
              </div>
              <label for="promptSystem">System prompt</label>
              <textarea id="promptSystem" spellcheck="false"></textarea>
              <div class="actions">
                <button id="savePromptBtn">Save Improver</button>
              </div>
            </section>
          </div>

          <section>
            <div class="section-head">
              <h2>Current Routes</h2>
              <span class="hint">Client-visible model names</span>
            </div>
            <div id="routes" class="table"></div>
          </section>
        </div>

        <div id="playground" class="view">
          <div class="split">
            <section>
              <div class="section-head">
                <h2>Request</h2>
                <span class="badge">bot API</span>
              </div>
              <div class="row three">
                <div>
                  <label for="playMode">Mode</label>
                  <select id="playMode">
                    <option value="chat">Chat completion</option>
                    <option value="improve">Prompt improve</option>
                    <option value="orchestrate">Orchestrate chat</option>
                  </select>
                </div>
                <div>
                  <label for="playModel">Model</label>
                  <select id="playModel"></select>
                </div>
                <div>
                  <label for="playMaxTokens">Max tokens</label>
                  <input id="playMaxTokens" type="number" min="1" step="1" value="256">
                </div>
              </div>
              <label for="playPrompt">Prompt</label>
              <textarea id="playPrompt" spellcheck="false">ช่วยเขียน api ง่ายๆ สำหรับเช็คสถานะ server</textarea>
              <div class="row">
                <div>
                  <label for="playImprove">Improve prompt</label>
                  <select id="playImprove">
                    <option value="">model default</option>
                    <option value="true">true</option>
                    <option value="false">false</option>
                    <option value="auto">auto</option>
                  </select>
                </div>
                <div>
                  <label for="playTools">Use tools</label>
                  <select id="playTools">
                    <option value="">model default</option>
                    <option value="true">true</option>
                    <option value="false">false</option>
                    <option value="auto">auto</option>
                  </select>
                </div>
              </div>
              <div class="actions">
                <button id="runPlayBtn" class="blue">Run</button>
                <button id="copyPlayBtn" class="secondary">Copy Payload</button>
              </div>
            </section>
            <section>
              <div class="section-head">
                <h2>Response</h2>
                <span class="hint" id="playTiming">idle</span>
              </div>
              <pre id="playOutput" class="output">{}</pre>
            </section>
          </div>
        </div>

        <div id="tools" class="view">
          <div class="split">
            <section>
              <div class="section-head">
                <h2>MCP Tool Manager</h2>
                <span id="mcpState" class="badge muted">unknown</span>
              </div>
              <div class="tool-summary">
                <div class="mini-stat"><strong id="mcpAvailableCount">--</strong><span class="hint">available</span></div>
                <div class="mini-stat"><strong id="mcpAllowedCount">--</strong><span class="hint">enabled tools</span></div>
                <div class="mini-stat"><strong id="mcpHiddenCount">--</strong><span class="hint">disabled tools</span></div>
              </div>
              <div class="toolbar">
                <div>
                  <label for="mcpEnabled">MCP enabled</label>
                  <select id="mcpEnabled">
                    <option value="true">On</option>
                    <option value="false">Off</option>
                  </select>
                </div>
                <div>
                  <label for="mcpSearch">Search tools</label>
                  <input id="mcpSearch" placeholder="prompt, skill, file, route">
                </div>
              </div>
              <label>Presets</label>
              <div class="preset-row">
                <button class="secondary" data-preset="prompt">Prompt workflow</button>
                <button class="secondary" data-preset="skill">Skill routing</button>
                <button class="secondary" data-preset="files">Read-only files</button>
                <button class="secondary" data-preset="recommended">Recommended core</button>
                <button class="ghost" data-preset="none">Disable all</button>
              </div>
              <label for="mcpAllowlist">Tool allowlist</label>
              <textarea id="mcpAllowlist" spellcheck="false" placeholder="one_tool_per_line"></textarea>
              <div class="actions">
                <button id="saveMcpBtn">Save selection</button>
                <button id="loadMcpBtn" class="secondary">Refresh tools</button>
              </div>
            </section>
            <section>
              <div class="section-head">
                <h2>Available Tools</h2>
                <span class="hint">toggle tools used by tool-enabled models</span>
              </div>
              <div id="mcpToolList" class="tool-list"></div>
              <label for="mcpOutput">Raw schema</label>
              <pre id="mcpOutput" class="output">[]</pre>
            </section>
          </div>
        </div>

        <div id="api" class="view">
          <section>
            <div class="section-head">
              <h2>Client Settings</h2>
              <span class="badge">OpenAI-compatible</span>
            </div>
            <div class="row three">
              <div>
                <label>Base URL</label>
                <input readonly value="http://127.0.0.1:8090/v1">
              </div>
              <div>
                <label>Docker client URL</label>
                <input readonly value="http://host.docker.internal:8090/v1">
              </div>
              <div>
                <label>Default model</label>
                <input readonly value="main-llm-improved">
              </div>
            </div>
          </section>
          <section>
            <div class="section-head">
              <h2>cURL</h2>
              <button id="copyCurlBtn" class="secondary">Copy</button>
            </div>
            <pre id="curlSnippet"></pre>
          </section>
          <section>
            <div class="section-head">
              <h2>PowerShell</h2>
              <button id="copyPsBtn" class="secondary">Copy</button>
            </div>
            <pre id="psSnippet"></pre>
          </section>
        </div>
      </div>
    </div>
  </main>

  <script>
    const state = { config: null, ready: null, models: null, mcpTools: null };
    const $ = (id) => document.getElementById(id);
    const views = [...document.querySelectorAll(".view")];
    const tabs = [...document.querySelectorAll(".tab")];

    function key() { return $("apiKey").value.trim(); }
    function adminKey() { return $("adminKey").value.trim() || key(); }
    function authHeaders() {
      return { "Authorization": "Bearer " + key(), "Content-Type": "application/json; charset=utf-8" };
    }
    function adminAuthHeaders() {
      return { "Authorization": "Bearer " + adminKey(), "Content-Type": "application/json; charset=utf-8" };
    }
    function setStatus(text, kind = "") {
      const el = $("status");
      el.textContent = text;
      el.className = "status" + (kind ? " " + kind : "");
    }
    function pretty(value) { return JSON.stringify(value, null, 2); }
    function parsePolicy(value) {
      if (value === "true") return true;
      if (value === "false") return false;
      if (value === "") return null;
      return "auto";
    }
    function policyValue(value) {
      if (value === true) return "true";
      if (value === false) return "false";
      return value || "false";
    }
    async function api(path, options = {}) {
      const baseHeaders = options.admin ? adminAuthHeaders() : authHeaders();
      const response = await fetch(path, { ...options, headers: { ...baseHeaders, ...(options.headers || {}) } });
      const text = await response.text();
      let data = {};
      try { data = text ? JSON.parse(text) : {}; } catch { data = { raw: text }; }
      if (!response.ok) {
        throw new Error(data.detail?.message || data.detail?.code || response.statusText);
      }
      return data;
    }
    async function publicApi(path) {
      const response = await fetch(path);
      return response.json();
    }
    function fillSelect(select, values) {
      select.innerHTML = "";
      for (const value of values) {
        const option = document.createElement("option");
        option.value = value;
        option.textContent = value;
        select.appendChild(option);
      }
    }
    function toolName(tool) { return tool?.function?.name || tool?.name || ""; }
    function toolDescription(tool) { return tool?.function?.description || tool?.description || ""; }
    const recommendedMcpTools = [
      "build_agent_context",
      "get_toolset",
      "list_files",
      "list_toolsets",
      "load_skill",
      "load_workflow",
      "prompt_analyze",
      "prompt_consult",
      "prompt_history_export_markdown",
      "prompt_history_save",
      "prompt_history_search",
      "prompt_history_stats",
      "prompt_improve_rule_based",
      "read_file",
      "route_request"
    ];
    function currentMcpAllowlist() {
      return $("mcpAllowlist").value.split(/\\r?\\n/).map(x => x.trim()).filter(Boolean);
    }
    function mcpAvailableTools() {
      const map = new Map();
      for (const tool of state.mcpTools?.available_tools || state.mcpTools?.tools || []) {
        const name = toolName(tool);
        if (name) map.set(name, tool);
      }
      for (const name of state.config?.mcp?.tool_allowlist || []) {
        if (!map.has(name)) {
          map.set(name, { type: "function", function: { name, description: "Configured allowlist entry", parameters: {} } });
        }
      }
      return [...map.values()].sort((a, b) => toolName(a).localeCompare(toolName(b)));
    }
    function toolCategory(name) {
      if (name.startsWith("prompt_")) return "prompt";
      if (["route_request", "build_agent_context", "get_toolset", "list_toolsets", "load_skill", "load_workflow"].includes(name)) return "skill";
      if (["list_files", "read_file"].includes(name)) return "files";
      return "general";
    }
    function setMcpAllowlist(names) {
      $("mcpAllowlist").value = [...new Set(names.filter(Boolean))].sort().join("\\n");
      renderMcpTools();
    }
    function applyMcpPreset(kind) {
      const names = mcpAvailableTools().map(toolName).filter(Boolean);
      if (kind === "recommended") {
        const known = new Set(names);
        const next = recommendedMcpTools.filter(name => !known.size || known.has(name));
        return setMcpAllowlist(next);
      }
      if (kind === "none") return setMcpAllowlist([]);
      setMcpAllowlist(names.filter(name => toolCategory(name) === kind));
    }
    function providerNames() { return Object.keys(state.config?.providers || { local: {} }); }
    function virtualNames() { return Object.keys(state.config?.virtual_models || {}); }
    function inferProvider(model) {
      if (model === "auto") return "auto";
      return state.config?.models?.[model]?.provider || "local";
    }
    function updateMetrics() {
      $("metricApi").textContent = "OK";
      $("metricApiNote").textContent = "local-llm-orchestrator";
      $("metricLlama").textContent = state.ready?.status === "ready" ? "Ready" : (state.ready?.status === "unavailable" ? "Down" : "--");
      $("metricLlamaNote").textContent = state.ready?.status === "ready" ? (state.ready?.llama_cpp?.status || "ok") : (state.ready?.error || "/ready");
      const allModels = state.models?.data || [];
      $("metricModels").textContent = String(allModels.length || "--");
      $("metricModelsNote").textContent = `${Object.keys(state.config?.models || {}).length} physical, ${virtualNames().length} virtual`;
      const mcp = state.config?.mcp || {};
      $("metricMcp").textContent = mcp.enabled ? "On" : "Off";
      $("metricMcpNote").textContent = `${(mcp.tool_allowlist || []).length} allowed tools`;
      $("mcpState").textContent = mcp.enabled ? "enabled" : "disabled";
      $("mcpState").className = "badge " + (mcp.enabled ? "ok" : "muted");
    }
    function renderProviders() {
      const providers = state.config?.providers || {};
      const table = $("providers");
      table.innerHTML = `<div class="tr providers th"><span>Name</span><span>Base URL</span><span>Key Env</span></div>`;
      for (const [name, details] of Object.entries(providers)) {
        const row = document.createElement("div");
        row.className = "tr providers";
        row.innerHTML = `
          <div class="td" data-label="Name"><span class="badge">${name}</span></div>
          <div class="td" data-label="Base URL">${details.base_url || ""}</div>
          <div class="td" data-label="Key Env">${details.api_key_env || "<none>"}</div>
        `;
        table.appendChild(row);
      }
    }
    function renderModels() {
      const table = $("modelInventory");
      table.innerHTML = `<div class="tr models th"><span>ID</span><span>Type</span><span>Name</span><span>Status</span></div>`;
      for (const item of state.models?.data || []) {
        const row = document.createElement("div");
        row.className = "tr models";
        row.innerHTML = `
          <div class="td" data-label="ID">${item.id}</div>
          <div class="td" data-label="Type"><span class="badge ${item.virtual ? "warn" : "ok"}">${item.virtual ? "virtual" : "physical"}</span></div>
          <div class="td" data-label="Name">${item.name || item.id}</div>
          <div class="td" data-label="Status">enabled</div>
        `;
        table.appendChild(row);
      }
    }
    function renderRoutes() {
      const table = $("routes");
      table.innerHTML = `<div class="tr routes th"><span>Virtual</span><span>Provider</span><span>Target</span><span>Improve</span><span>Tools</span></div>`;
      for (const [name, policy] of Object.entries(state.config?.virtual_models || {})) {
        const model = policy.model || policy.route || "";
        const provider = policy.provider || inferProvider(model);
        const row = document.createElement("div");
        row.className = "tr routes";
        row.innerHTML = `
          <div class="td" data-label="Virtual"><span class="badge">${name}</span></div>
          <div class="td" data-label="Provider">${provider}</div>
          <div class="td" data-label="Target">${model}</div>
          <div class="td" data-label="Improve">${policy.improve_prompt}</div>
          <div class="td" data-label="Tools">${policy.tools}</div>
        `;
        table.appendChild(row);
      }
    }
    function loadRouteForm() {
      const name = $("virtualModel").value;
      const policy = state.config?.virtual_models?.[name] || {};
      const model = policy.model || policy.route || "";
      $("mainProvider").value = policy.provider || inferProvider(model);
      $("mainModel").value = model;
      $("improvePolicy").value = policyValue(policy.improve_prompt);
      $("toolsPolicy").value = policyValue(policy.tools);
    }
    function loadPromptForm() {
      const prompt = state.config?.prompt_improver || {};
      $("promptProvider").value = prompt.provider || "local";
      $("promptModel").value = prompt.model || "prompt";
      $("promptTemperature").value = prompt.temperature ?? "";
      $("promptMaxTokens").value = prompt.max_tokens ?? "";
      $("promptSystem").value = prompt.system_prompt || "";
    }
    function loadMcpForm() {
      const mcp = state.config?.mcp || {};
      $("mcpEnabled").value = String(Boolean(mcp.enabled));
      $("mcpAllowlist").value = (mcp.tool_allowlist || []).join("\\n");
      renderMcpTools();
    }
    function renderMcpTools() {
      if (!$("mcpToolList")) return;
      const mcp = state.config?.mcp || {};
      const tools = mcpAvailableTools();
      const allowed = new Set(currentMcpAllowlist());
      const query = ($("mcpSearch").value || "").trim().toLowerCase();
      $("mcpState").textContent = mcp.enabled ? "enabled" : "disabled";
      $("mcpState").className = "badge " + (mcp.enabled ? "ok" : "muted");
      $("mcpAvailableCount").textContent = String(tools.length);
      $("mcpAllowedCount").textContent = String(allowed.size);
      $("mcpHiddenCount").textContent = String(Math.max(0, tools.length - allowed.size));
      const list = $("mcpToolList");
      list.innerHTML = "";
      const filtered = tools.filter(tool => {
        const name = toolName(tool);
        const haystack = `${name} ${toolDescription(tool)} ${toolCategory(name)}`.toLowerCase();
        return !query || haystack.includes(query);
      });
      if (!filtered.length) {
        const empty = document.createElement("div");
        empty.className = "status";
        empty.textContent = tools.length ? "No tools match the search." : "Click Refresh tools to load MCP tools.";
        list.appendChild(empty);
        return;
      }
      for (const tool of filtered) {
        const name = toolName(tool);
        const enabled = allowed.has(name);
        const row = document.createElement("label");
        row.className = "tool-item" + (enabled ? "" : " disabled");
        row.innerHTML = `
          <input type="checkbox" ${enabled ? "checked" : ""} data-tool="${name}">
          <div>
            <div class="tool-name">${name}</div>
            <div class="tool-desc">${toolDescription(tool) || "No description provided."}</div>
          </div>
          <span class="badge muted">${toolCategory(name)}</span>
        `;
        row.querySelector("input").addEventListener("change", (event) => {
          const next = new Set(currentMcpAllowlist());
          if (event.target.checked) next.add(name);
          else next.delete(name);
          setMcpAllowlist([...next]);
          setStatus("Tool selection changed. Click Save selection to apply.", "ok");
        });
        list.appendChild(row);
      }
    }
    function loadPlaygroundSelects() {
      fillSelect($("playModel"), virtualNames());
      if (virtualNames().includes("main-llm-improved")) $("playModel").value = "main-llm-improved";
    }
    function renderSnippets() {
      const sample = {
        model: "main-llm-improved",
        messages: [{ role: "user", content: "ช่วยเขียน api ง่ายๆ สำหรับเช็คสถานะ server" }],
        stream: false
      };
      $("curlSnippet").textContent = `curl http://127.0.0.1:8090/v1/chat/completions \\
  -H "Authorization: Bearer ${key() || "<ORCHESTRATOR_API_KEY>"}" \\
  -H "Content-Type: application/json" \\
  -d '${JSON.stringify(sample)}'`;
      $("psSnippet").textContent = `$headers = @{ Authorization = "Bearer ${key() || "<ORCHESTRATOR_API_KEY>"}"; "Content-Type" = "application/json" }
$body = ${JSON.stringify(sample, null, 2)} | ConvertTo-Json -Depth 10
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8090/v1/chat/completions" -Headers $headers -Body $body`;
    }
    async function loadAll() {
      if (!key()) {
        setStatus("API key is required.", "err");
        return;
      }
      setStatus("Connecting...");
      const health = await publicApi("/health");
      try {
        state.ready = await api("/ready");
      } catch (err) {
        // llama.cpp being unreachable must not block the admin console, which is
        // independent of the inference backend.
        state.ready = { status: "unavailable", error: err.message };
      }
      state.models = await api("/v1/models");
      state.config = await api("/admin/config", { admin: true });
      fillSelect($("promptProvider"), providerNames());
      fillSelect($("mainProvider"), providerNames());
      fillSelect($("virtualModel"), virtualNames());
      loadRouteForm();
      loadPromptForm();
      loadMcpForm();
      loadPlaygroundSelects();
      try {
        await listMcpTools(false);
      } catch (err) {
        $("mcpOutput").textContent = pretty({ error: err.message });
        renderMcpTools();
      }
      updateMetrics();
      renderProviders();
      renderModels();
      renderRoutes();
      renderSnippets();
      if (state.ready?.status === "ready") {
        setStatus(`Connected: ${health.service} ${health.version}`, "ok");
      } else {
        setStatus(`Console loaded, but llama.cpp is not reachable (${state.ready?.error || "unknown"}). Admin settings still work.`, "warn");
      }
    }
    async function saveRoute() {
      const body = {
        virtual_model: $("virtualModel").value,
        provider: $("mainProvider").value,
        model: $("mainModel").value.trim(),
        improve_prompt: parsePolicy($("improvePolicy").value),
        tools: parsePolicy($("toolsPolicy").value)
      };
      setStatus("Saving route...");
      state.config = await api("/admin/config/virtual-model", { method: "POST", admin: true, body: JSON.stringify(body) });
      loadRouteForm();
      renderRoutes();
      updateMetrics();
      setStatus("Route saved and reloaded.", "ok");
    }
    async function savePrompt() {
      const updated = structuredClone(state.config);
      updated.prompt_improver = {
        ...(updated.prompt_improver || {}),
        provider: $("promptProvider").value,
        model: $("promptModel").value.trim(),
        system_prompt: $("promptSystem").value.trim(),
        temperature: $("promptTemperature").value ? Number($("promptTemperature").value) : null,
        max_tokens: $("promptMaxTokens").value ? Number($("promptMaxTokens").value) : null
      };
      if (updated.prompt_improver.temperature === null) delete updated.prompt_improver.temperature;
      if (updated.prompt_improver.max_tokens === null) delete updated.prompt_improver.max_tokens;
      setStatus("Saving prompt improver...");
      await api("/admin/config", { method: "PUT", admin: true, body: JSON.stringify(updated) });
      await loadAll();
      setStatus("Prompt improver saved and reloaded.", "ok");
    }
    async function saveMcp() {
      const next = currentMcpAllowlist();
      setStatus("Saving MCP tools...");
      await api("/admin/mcp/tools", {
        method: "PATCH",
        admin: true,
        body: JSON.stringify({ enabled: $("mcpEnabled").value === "true", set_tools: next })
      });
      await loadAll();
      setStatus("MCP tools saved and reloaded.", "ok");
    }
    function playgroundPayload() {
      const prompt = $("playPrompt").value;
      const maxTokens = Number($("playMaxTokens").value || 256);
      const model = $("playModel").value;
      if ($("playMode").value === "improve") {
        return { prompt, model: "prompt", temperature: 0.05, max_tokens: maxTokens };
      }
      const payload = { model, messages: [{ role: "user", content: prompt }], stream: false, max_tokens: maxTokens };
      if ($("playMode").value === "orchestrate") {
        const improve = parsePolicy($("playImprove").value);
        const tools = parsePolicy($("playTools").value);
        if (improve !== null) payload.improve_prompt = improve;
        if (tools !== null) payload.use_tools = tools;
      }
      return payload;
    }
    async function runPlayground() {
      const payload = playgroundPayload();
      const mode = $("playMode").value;
      const path = mode === "improve" ? "/prompt/improve" : mode === "orchestrate" ? "/orchestrate/chat" : "/v1/chat/completions";
      $("playOutput").textContent = pretty({ running: true, path, payload });
      $("playTiming").textContent = "running";
      const started = performance.now();
      try {
        const data = await api(path, { method: "POST", body: JSON.stringify(payload) });
        $("playTiming").textContent = `${((performance.now() - started) / 1000).toFixed(1)}s`;
        $("playOutput").textContent = pretty(data);
      } catch (error) {
        $("playTiming").textContent = "failed";
        $("playOutput").textContent = pretty({ error: error.message });
      }
    }
    async function listMcpTools(showStatus = true) {
      const data = await api("/mcp/tools");
      state.mcpTools = data;
      $("mcpOutput").textContent = pretty(data);
      renderMcpTools();
      if (showStatus) setStatus("MCP tools loaded.", "ok");
    }
    async function reloadConfig() {
      setStatus("Reloading components...");
      await api("/admin/reload", { method: "POST", admin: true, body: "{}" });
      await loadAll();
      setStatus("Components reloaded.", "ok");
    }
    async function copyText(text) {
      await navigator.clipboard.writeText(text);
      setStatus("Copied to clipboard.", "ok");
    }
    function activateTab(tab, focus = false) {
      tabs.forEach(x => {
        const on = x === tab;
        x.classList.toggle("active", on);
        x.setAttribute("aria-selected", on ? "true" : "false");
        x.tabIndex = on ? 0 : -1;
      });
      views.forEach(x => x.classList.remove("active"));
      $(tab.dataset.view).classList.add("active");
      if (focus) tab.focus();
    }
    tabs.forEach((tab, index) => {
      tab.addEventListener("click", () => activateTab(tab));
      tab.addEventListener("keydown", (event) => {
        let next = null;
        if (event.key === "ArrowRight" || event.key === "ArrowDown") next = tabs[(index + 1) % tabs.length];
        else if (event.key === "ArrowLeft" || event.key === "ArrowUp") next = tabs[(index - 1 + tabs.length) % tabs.length];
        else if (event.key === "Home") next = tabs[0];
        else if (event.key === "End") next = tabs[tabs.length - 1];
        if (next) { event.preventDefault(); activateTab(next, true); }
      });
    });
    $("loadBtn").addEventListener("click", () => loadAll().catch(err => setStatus(err.message, "err")));
    $("refreshBtn").addEventListener("click", () => loadAll().catch(err => setStatus(err.message, "err")));
    $("reloadBtn").addEventListener("click", () => reloadConfig().catch(err => setStatus(err.message, "err")));
    $("rememberBtn").addEventListener("click", () => {
      sessionStorage.setItem("orchestratorApiKey", key());
      sessionStorage.setItem("orchestratorAdminKey", $("adminKey").value.trim());
      setStatus("Keys remembered for this browser tab.", "ok");
    });
    $("virtualModel").addEventListener("change", loadRouteForm);
    $("saveVirtualBtn").addEventListener("click", () => saveRoute().catch(err => setStatus(err.message, "err")));
    $("savePromptBtn").addEventListener("click", () => savePrompt().catch(err => setStatus(err.message, "err")));
    $("saveMcpBtn").addEventListener("click", () => saveMcp().catch(err => setStatus(err.message, "err")));
    $("loadMcpBtn").addEventListener("click", () => listMcpTools().catch(err => setStatus(err.message, "err")));
    $("mcpSearch").addEventListener("input", renderMcpTools);
    $("mcpAllowlist").addEventListener("input", renderMcpTools);
    $("mcpEnabled").addEventListener("change", () => setStatus("MCP state changed. Click Save selection to apply.", "ok"));
    document.querySelectorAll("[data-preset]").forEach(button => {
      button.addEventListener("click", () => {
        applyMcpPreset(button.dataset.preset);
        setStatus("Preset applied. Click Save selection to apply.", "ok");
      });
    });
    $("runPlayBtn").addEventListener("click", runPlayground);
    $("copyPlayBtn").addEventListener("click", () => copyText(pretty(playgroundPayload())));
    $("copyRouteBtn").addEventListener("click", () => copyText(pretty(state.config?.virtual_models?.[$("virtualModel").value] || {})));
    $("copyCurlBtn").addEventListener("click", () => copyText($("curlSnippet").textContent));
    $("copyPsBtn").addEventListener("click", () => copyText($("psSnippet").textContent));
    $("apiKey").value = sessionStorage.getItem("orchestratorApiKey") || "";
    $("adminKey").value = sessionStorage.getItem("orchestratorAdminKey") || "";
    renderSnippets();
  </script>
</body>
</html>"""
