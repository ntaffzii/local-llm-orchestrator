from __future__ import annotations


def admin_ui_html() -> str:
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Local LLM Orchestrator</title>
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
      --accent-strong: #075b57;
      --accent-soft: #dff5f2;
      --blue: #2f6fed;
      --blue-soft: #e8efff;
      --warn: #a15c13;
      --warn-soft: #fff2d8;
      --danger: #a13b3b;
      --danger-soft: #fff3f3;
      --ok: #1e7a4f;
      --ok-soft: #f0fbf5;
      --radius: 10px;
      --shadow: 0 1px 2px rgba(15, 23, 42, 0.08);
      --shadow-hover: 0 4px 14px rgba(15, 23, 42, 0.12);
      --header-bg: rgba(255, 255, 255, 0.9);
    }
    @media (prefers-color-scheme: dark) {
      :root {
        --bg: #08090c;
        --panel: #0f1216;
        --panel-soft: #161a20;
        --text: #e8edf4;
        --muted: #8b95a5;
        --line: #232a33;
        --accent: #3ad4c6;
        --accent-strong: #2ab5a8;
        --accent-soft: #0e2f2b;
        --blue: #6ea0ff;
        --blue-soft: #14223a;
        --warn: #e5b968;
        --warn-soft: #2f2711;
        --danger: #f28b8b;
        --danger-soft: #2c1414;
        --ok: #5fce93;
        --ok-soft: #10281b;
        --shadow: 0 1px 3px rgba(0, 0, 0, 0.55);
        --shadow-hover: 0 6px 20px rgba(0, 0, 0, 0.6);
        --header-bg: rgba(10, 12, 16, 0.85);
      }
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
      background: var(--header-bg);
      backdrop-filter: blur(12px);
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
      width: 40px;
      height: 40px;
      display: grid;
      place-items: center;
      border-radius: 11px;
      background: linear-gradient(145deg, var(--accent), var(--accent-strong));
      color: #ffffff;
      font-weight: 800;
      font-size: 15px;
      letter-spacing: 0.5px;
      box-shadow: 0 3px 10px rgba(11, 122, 117, 0.35);
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
      border-radius: var(--radius);
      box-shadow: var(--shadow);
    }
    .metric {
      transition: border-color 0.15s ease, box-shadow 0.15s ease, transform 0.15s ease;
    }
    .metric:hover {
      border-color: var(--accent);
      box-shadow: var(--shadow-hover);
      transform: translateY(-1px);
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
      font-variant-numeric: tabular-nums;
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
      min-height: 38px;
      justify-content: flex-start;
      gap: 10px;
      background: transparent;
      color: var(--muted);
      border-color: transparent;
      font-weight: 600;
    }
    .tab::before {
      content: "";
      width: 3px;
      height: 16px;
      border-radius: 2px;
      background: transparent;
    }
    .tab:hover:not(.active) { background: var(--panel-soft); color: var(--text); filter: none; box-shadow: none; }
    .tab.active:hover { filter: none; box-shadow: none; }
    .tab.active {
      background: var(--accent-soft);
      color: var(--accent);
      border-color: transparent;
    }
    .tab.active::before { background: var(--accent); }
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
      border-radius: 8px;
      background: var(--panel);
      color: var(--text);
      padding: 8px 10px;
      font: inherit;
      font-size: 14px;
      transition: border-color 0.15s ease, box-shadow 0.15s ease;
    }
    input::placeholder, textarea::placeholder { color: var(--muted); opacity: 0.7; }
    textarea {
      resize: vertical;
      min-height: 118px;
      line-height: 1.45;
    }
    input:focus, select:focus, textarea:focus {
      outline: 2px solid rgba(11, 122, 117, 0.18);
      border-color: var(--accent);
    }
    button:focus-visible, .tab:focus-visible {
      outline: 2px solid var(--accent);
      outline-offset: 2px;
    }
    .field-error {
      border-color: var(--danger) !important;
      outline: 2px solid rgba(161, 59, 59, 0.25);
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
      border-radius: 8px;
      background: var(--accent);
      color: #fff;
      padding: 8px 12px;
      font: inherit;
      font-size: 14px;
      font-weight: 650;
      cursor: pointer;
      transition: filter 0.15s ease, background-color 0.15s ease, border-color 0.15s ease, box-shadow 0.15s ease;
    }
    button:hover:not(:disabled) {
      filter: brightness(1.08);
      box-shadow: var(--shadow-hover);
    }
    button:active:not(:disabled) { filter: brightness(0.96); box-shadow: none; }
    button.secondary {
      background: var(--panel);
      color: var(--accent);
    }
    button.blue {
      border-color: var(--blue);
      background: var(--blue);
      color: #fff;
    }
    button.ghost {
      border-color: var(--line);
      background: var(--panel);
      color: var(--text);
    }
    button.secondary:hover:not(:disabled),
    button.ghost:hover:not(:disabled) {
      filter: none;
      border-color: var(--accent);
      color: var(--accent);
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
    .status.ok { border-color: var(--ok); color: var(--ok); background: var(--ok-soft); }
    .status.err { border-color: var(--danger); color: var(--danger); background: var(--danger-soft); }
    .status.warn { border-color: var(--warn); color: var(--warn); background: var(--warn-soft); }
    .badge {
      display: inline-flex;
      align-items: center;
      min-height: 24px;
      padding: 3px 8px;
      border-radius: 999px;
      background: var(--blue-soft);
      color: var(--blue);
      font-size: 12px;
      font-weight: 700;
      white-space: nowrap;
    }
    .badge.ok { background: var(--ok-soft); color: var(--ok); }
    .badge.warn { background: var(--warn-soft); color: var(--warn); }
    .badge.muted { background: var(--panel-soft); color: var(--muted); border: 1px solid var(--line); }
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
      background: var(--panel);
      transition: border-color 0.15s ease, background-color 0.15s ease;
    }
    .tool-item:hover { border-color: var(--accent); }
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
      font-variant-numeric: tabular-nums;
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
    .tr:not(.th):hover { background: var(--panel-soft); }
    .tr.routes { grid-template-columns: 170px 120px minmax(180px, 1fr) 96px 86px; }
    .tr.models { grid-template-columns: 190px 150px minmax(180px, 1fr) 96px; }
    .tr.providers { grid-template-columns: 140px minmax(230px, 1fr) 150px; }
    .tr.audit { grid-template-columns: 160px 150px minmax(180px, 1fr) 120px; }
    .tr.keys { grid-template-columns: minmax(120px, 1.2fr) minmax(90px, 1fr) 72px 78px 130px 130px 92px; }
    .key-code {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 8px;
      margin-top: 6px;
    }
    .key-code code {
      flex: 1;
      min-width: 0;
      padding: 8px 10px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: var(--panel);
      font: 12px/1.5 Consolas, "SFMono-Regular", monospace;
      overflow-wrap: anywhere;
    }
    .th {
      background: var(--panel-soft);
      color: var(--muted);
      font-size: 12px;
      font-weight: 750;
      text-transform: uppercase;
    }
    .th:hover { background: var(--panel-soft); }
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
    .pipeline {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
      align-items: stretch;
    }
    .stage {
      position: relative;
      border: 1px solid var(--line);
      border-radius: 10px;
      background: var(--panel-soft);
      padding: 12px;
      display: grid;
      gap: 9px;
      align-content: start;
      transition: border-color 0.15s ease, box-shadow 0.15s ease;
    }
    .stage:hover { border-color: var(--accent); box-shadow: var(--shadow-hover); }
    .stage:not(:last-child)::after {
      content: "";
      position: absolute;
      right: -8px;
      top: 24px;
      width: 8px;
      height: 1px;
      background: var(--line);
    }
    .stage-head { display: flex; align-items: center; gap: 8px; }
    .stage-num {
      width: 22px;
      height: 22px;
      border-radius: 6px;
      display: grid;
      place-items: center;
      background: var(--accent-soft);
      color: var(--accent);
      font-size: 11px;
      font-weight: 800;
    }
    .stage-title {
      font-size: 12px;
      font-weight: 750;
      text-transform: uppercase;
      letter-spacing: 0.4px;
      color: var(--muted);
    }
    .stage-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      font-size: 12px;
    }
    .stage-row .k { color: var(--muted); }
    .chip {
      display: inline-flex;
      align-items: center;
      min-height: 22px;
      padding: 2px 8px;
      border-radius: 6px;
      background: var(--panel);
      border: 1px solid var(--line);
      color: var(--text);
      font-size: 12px;
      font-weight: 650;
      white-space: nowrap;
      overflow-wrap: anywhere;
    }
    .chip.on { border-color: var(--ok); color: var(--ok); }
    .chip.off { border-color: var(--line); color: var(--muted); }
    .chip.accent { border-color: var(--accent); color: var(--accent); }
    @media (max-width: 900px) { .pipeline { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
    @media (max-width: 560px) { .pipeline { grid-template-columns: 1fr; } .stage:not(:last-child)::after { display: none; } }
    .tab-ico { display: inline-flex; }
    .tab-ico svg { width: 17px; height: 17px; }
    .m-ico { display: inline-flex; color: var(--accent); }
    .m-ico svg { width: 15px; height: 15px; }
    .metric-title { display: flex; align-items: center; justify-content: space-between; gap: 6px; }
    .metric-title .mt-left { display: inline-flex; align-items: center; gap: 6px; }
    .metric-badge {
      padding: 2px 8px;
      border-radius: 999px;
      font-size: 11px;
      font-weight: 700;
      background: var(--panel-soft);
      color: var(--muted);
      border: 1px solid var(--line);
      white-space: nowrap;
    }
    .metric-badge.ok { background: var(--ok-soft); color: var(--ok); border-color: var(--ok); }
    .metric-badge.err { background: var(--danger-soft); color: var(--danger); border-color: var(--danger); }
    .metric-badge:empty { display: none; }
    .content.disconnected .quick,
    .content.disconnected .view { display: none; }
    .content:not(.disconnected) #emptyState { display: none; }
    .empty {
      display: grid;
      justify-items: center;
      text-align: center;
      gap: 12px;
      padding: 56px 20px;
    }
    .empty-mark {
      width: 64px;
      height: 64px;
      display: grid;
      place-items: center;
      border-radius: 18px;
      background: linear-gradient(145deg, var(--accent), var(--accent-strong));
      color: #fff;
      box-shadow: 0 6px 20px rgba(11, 122, 117, 0.35);
    }
    .empty-mark svg { width: 34px; height: 34px; }
    .empty h2 { font-size: 18px; }
    .empty p { margin: 0; color: var(--muted); max-width: 420px; line-height: 1.5; }
    .empty-hint {
      display: inline-flex;
      align-items: center;
      gap: 7px;
      color: var(--accent);
      font-size: 13px;
      font-weight: 650;
    }
    .empty-hint svg { width: 16px; height: 16px; }
    .endpoints {
      display: grid;
      grid-template-columns: auto auto minmax(0, 1fr);
      gap: 12px;
      align-items: center;
    }
    .ep-node {
      border: 1px solid var(--line);
      border-radius: 10px;
      background: var(--panel-soft);
      padding: 11px 13px;
      display: grid;
      gap: 3px;
      min-width: 120px;
    }
    .ep-node.gateway { border-color: var(--accent); background: var(--accent-soft); }
    .ep-name { display: flex; align-items: center; gap: 7px; font-weight: 700; font-size: 13px; }
    .ep-name svg { width: 15px; height: 15px; color: var(--accent); }
    .ep-sub { color: var(--muted); font-size: 12px; }
    .ep-arrow {
      width: 26px;
      height: 1px;
      background: linear-gradient(90deg, var(--line), var(--accent));
      position: relative;
    }
    .ep-arrow::after {
      content: "";
      position: absolute;
      right: 0;
      top: -3px;
      border: 3px solid transparent;
      border-left-color: var(--accent);
    }
    .ep-providers { display: grid; gap: 8px; }
    .ep-provider {
      border: 1px solid var(--line);
      border-radius: 10px;
      background: var(--panel);
      padding: 10px 12px;
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 8px;
      transition: border-color 0.15s ease;
    }
    .ep-provider:hover { border-color: var(--accent); }
    .ep-models { display: flex; flex-wrap: wrap; gap: 6px; margin-left: auto; }
    .dot { width: 8px; height: 8px; border-radius: 50%; flex: none; }
    .dot.ok { background: var(--ok); }
    .dot.down { background: var(--danger); }
    .dot.muted { background: var(--muted); }
    @media (max-width: 760px) {
      .endpoints { grid-template-columns: 1fr; }
      .ep-arrow { display: none; }
      .ep-models { margin-left: 0; }
    }
    .traffic {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr)) 1.3fr;
      gap: 12px;
      align-items: stretch;
    }
    .stat {
      border: 1px solid var(--line);
      border-radius: 10px;
      background: var(--panel-soft);
      padding: 12px;
      display: grid;
      gap: 8px;
      align-content: space-between;
      transition: border-color 0.15s ease;
    }
    .stat:hover { border-color: var(--accent); }
    .stat-label { color: var(--muted); font-size: 12px; font-weight: 650; }
    .stat-row { display: flex; align-items: baseline; gap: 8px; flex-wrap: wrap; }
    .stat-value { font-size: 22px; font-weight: 750; font-variant-numeric: tabular-nums; }
    .delta {
      display: inline-flex;
      align-items: center;
      gap: 3px;
      font-size: 12px;
      font-weight: 700;
      padding: 2px 7px;
      border-radius: 999px;
      white-space: nowrap;
    }
    .delta.up { background: var(--ok-soft); color: var(--ok); }
    .delta.down { background: var(--danger-soft); color: var(--danger); }
    .delta.flat { background: var(--panel); color: var(--muted); border: 1px solid var(--line); }
    .spark {
      border: 1px solid var(--line);
      border-radius: 10px;
      background: var(--panel-soft);
      padding: 12px;
      display: grid;
      gap: 8px;
      align-content: start;
    }
    .spark svg { width: 100%; height: 52px; }
    @media (max-width: 900px) { .traffic { grid-template-columns: repeat(2, minmax(0, 1fr)); } .spark { grid-column: 1 / -1; } }
    @media (max-width: 560px) { .traffic { grid-template-columns: 1fr; } }
    .services { display: grid; gap: 8px; }
    .service-row {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 10px;
      border: 1px solid var(--line);
      border-radius: 10px;
      background: var(--panel);
      padding: 10px 12px;
    }
    .service-name { font-weight: 700; font-size: 13px; }
    .service-actions { margin-left: auto; display: flex; gap: 8px; }
    .toggle-btn { min-height: 32px; padding: 5px 12px; }
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
    @media (prefers-reduced-motion: reduce) {
      * { transition: none !important; }
      .metric:hover { transform: none; }
    }
  </style>
</head>
<body>
  <!-- Local LLM Orchestrator admin console -->
  <header>
    <div class="wrap topbar">
      <div class="brand">
        <div class="mark" aria-hidden="true">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="4.5" cy="12" r="2.1"/>
            <circle cx="19.5" cy="5" r="2.1"/>
            <circle cx="19.5" cy="12" r="2.1"/>
            <circle cx="19.5" cy="19" r="2.1"/>
            <path d="M6.6 12h4.4M11 12l6.4-6.4M11 12h6.4M11 12l6.4 6.4"/>
          </svg>
        </div>
        <div>
          <h1>Local LLM Orchestrator</h1>
          <div class="subtitle">OpenAI-compatible gateway for local llama.cpp models — routing, prompt improvement, and MCP tools</div>
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
          <button class="tab active" data-view="overview" role="tab" aria-selected="true" aria-controls="overview">
            <span class="tab-ico" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/></svg></span>Overview</button>
          <button class="tab" data-view="routing" role="tab" aria-selected="false" aria-controls="routing" tabindex="-1">
            <span class="tab-ico" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><circle cx="6" cy="6" r="2.4"/><circle cx="6" cy="18" r="2.4"/><circle cx="18" cy="12" r="2.4"/><path d="M8.4 6H13a2.6 2.6 0 0 1 2.6 2.6v.9M8.4 18H13a2.6 2.6 0 0 0 2.6-2.6v-.9"/></svg></span>Routing</button>
          <button class="tab" data-view="playground" role="tab" aria-selected="false" aria-controls="playground" tabindex="-1">
            <span class="tab-ico" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M7 5.5v13l11-6.5-11-6.5Z"/></svg></span>Playground</button>
          <button class="tab" data-view="tools" role="tab" aria-selected="false" aria-controls="tools" tabindex="-1">
            <span class="tab-ico" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M9 3v5M15 3v5M8 8h8v3a4 4 0 0 1-8 0V8ZM12 15v6"/></svg></span>Tools</button>
          <button class="tab" data-view="api" role="tab" aria-selected="false" aria-controls="api" tabindex="-1">
            <span class="tab-ico" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M9 8l-4 4 4 4M15 8l4 4-4 4"/></svg></span>API</button>
          <button class="tab" data-view="access" role="tab" aria-selected="false" aria-controls="access" tabindex="-1">
            <span class="tab-ico" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><circle cx="8" cy="15" r="4"/><path d="M10.8 12.2 20 3M17 6l2 2M14 9l2 2"/></svg></span>Access</button>
        </nav>
      </aside>

      <div class="content disconnected">
        <section id="emptyState" class="empty">
          <div class="empty-mark" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="4.5" cy="12" r="2.1"/>
              <circle cx="19.5" cy="5" r="2.1"/>
              <circle cx="19.5" cy="12" r="2.1"/>
              <circle cx="19.5" cy="19" r="2.1"/>
              <path d="M6.6 12h4.4M11 12l6.4-6.4M11 12h6.4M11 12l6.4 6.4"/>
            </svg>
          </div>
          <h2>Connect to your orchestrator</h2>
          <p>Enter your API key above and click Connect to load the gateway pipeline, routing, models, and MCP tools. If a separate admin key is set, add it too.</p>
          <span class="empty-hint">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 19V5M6 11l6-6 6 6"/></svg>
            Enter your key in the top bar
          </span>
        </section>
        <div class="quick">
          <section class="metric">
            <div class="metric-title"><span class="mt-left"><span class="m-ico" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="7" rx="2"/><rect x="3" y="13" width="18" height="7" rx="2"/><path d="M7 7.5h.01M7 16.5h.01"/></svg></span>Orchestrator</span><span class="metric-badge" id="badgeApi"></span></div>
            <div class="metric-value" id="metricApi">--</div>
            <div class="metric-note" id="metricApiNote">/health</div>
          </section>
          <section class="metric">
            <div class="metric-title"><span class="mt-left"><span class="m-ico" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><rect x="7" y="7" width="10" height="10" rx="1.5"/><path d="M10 3v2M14 3v2M10 19v2M14 19v2M3 10h2M3 14h2M19 10h2M19 14h2"/></svg></span>llama.cpp</span><span class="metric-badge" id="badgeLlama"></span></div>
            <div class="metric-value" id="metricLlama">--</div>
            <div class="metric-note" id="metricLlamaNote">/ready</div>
          </section>
          <section class="metric">
            <div class="metric-title"><span class="mt-left"><span class="m-ico" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3l8 4.5-8 4.5-8-4.5L12 3ZM4 12l8 4.5L20 12M4 16.5L12 21l8-4.5"/></svg></span>Models</span><span class="metric-badge" id="badgeModels"></span></div>
            <div class="metric-value" id="metricModels">--</div>
            <div class="metric-note" id="metricModelsNote">physical + virtual</div>
          </section>
          <section class="metric">
            <div class="metric-title"><span class="mt-left"><span class="m-ico" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M9 3v5M15 3v5M8 8h8v3a4 4 0 0 1-8 0V8ZM12 15v6"/></svg></span>MCP</span><span class="metric-badge" id="badgeMcp"></span></div>
            <div class="metric-value" id="metricMcp">--</div>
            <div class="metric-note" id="metricMcpNote">tool allowlist</div>
          </section>
        </div>

        <div id="overview" class="view active">
          <section>
            <div class="section-head">
              <h2>Gateway Pipeline</h2>
              <span class="hint">Request path from client to model</span>
            </div>
            <div id="pipeline" class="pipeline"></div>
          </section>
          <section>
            <div class="section-head">
              <h2>Endpoint Health</h2>
              <span class="hint">Gateway to provider routing and reachability</span>
            </div>
            <div id="endpoints" class="endpoints"></div>
          </section>
          <section>
            <div class="section-head">
              <h2>Model Services</h2>
              <span class="hint">Start/stop model containers (opt-in Docker control)</span>
            </div>
            <div id="services" class="services"></div>
          </section>
          <section>
            <div class="section-head">
              <h2>Traffic</h2>
              <span class="hint">Inference requests, last hour vs the hour before</span>
            </div>
            <div id="traffic" class="traffic"></div>
          </section>
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
          <section>
            <div class="section-head">
              <h2>Recent Activity</h2>
              <span class="hint">Config changes made through the admin API (resets on restart)</span>
            </div>
            <div id="auditLog" class="table"></div>
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
              <div class="hint" style="margin-top:8px">Saving applies immediately and reloads the running service.</div>
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
              <div class="hint" style="margin-top:8px">Saving applies immediately and reloads the running service.</div>
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
              <div class="hint" style="margin-top:8px">Saving applies immediately and reloads the running service.</div>
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
              <h2>Request body <span class="hint">save as request.json (UTF-8)</span></h2>
              <button id="copyBodyBtn" class="secondary">Copy</button>
            </div>
            <pre id="bodySnippet"></pre>
          </section>
          <section>
            <div class="section-head">
              <h2>cURL <span class="hint">any shell — sends request.json</span></h2>
              <button id="copyCurlBtn" class="secondary">Copy</button>
            </div>
            <pre id="curlSnippet"></pre>
          </section>
          <section>
            <div class="section-head">
              <h2>PowerShell <span class="hint">Windows, self-contained</span></h2>
              <button id="copyPsBtn" class="secondary">Copy</button>
            </div>
            <pre id="psSnippet"></pre>
          </section>
        </div>

        <div id="access" class="view">
          <section>
            <div class="section-head">
              <h2>API Keys</h2>
              <span class="hint">Issue inference keys to other people; revoke any time</span>
            </div>
            <div class="row three">
              <div>
                <label for="newKeyLabel">Label</label>
                <input id="newKeyLabel" maxlength="80" placeholder="team-member-a">
              </div>
              <div>
                <label for="newKeyModels">Allowed models <span class="hint">leave empty for all — do not type "all"</span></label>
                <input id="newKeyModels" placeholder="Leave empty for all models · e.g. main-llm, coding">
              </div>
              <div>
                <label for="newKeyRate">Rate limit / min</label>
                <input id="newKeyRate" type="number" min="0" step="1" value="0" placeholder="0 = unlimited">
              </div>
            </div>
            <div class="row three">
              <div>
                <label for="newKeyExpires">Expires in days <span class="hint">0 = never</span></label>
                <input id="newKeyExpires" type="number" min="0" max="3650" step="1" value="0" placeholder="0 = never expires">
              </div>
              <div>
                <label for="newKeyToolsMode">MCP tools</label>
                <select id="newKeyToolsMode">
                  <option value="all">All tools</option>
                  <option value="none">No tools</option>
                  <option value="list">Specific tools</option>
                </select>
              </div>
              <div>
                <label for="newKeyTools">Tool names (when specific)</label>
                <input id="newKeyTools" placeholder="route_request, load_skill">
              </div>
            </div>
            <div class="actions">
              <button id="createKeyBtn">Create key</button>
            </div>
            <div id="newKeyReveal" class="status" style="display:none"></div>
            <div class="hint" style="margin-top:8px">Keys grant inference access only, never admin. Scope limits which models the key may call. An expiring key stops working on its own — prefer it for temporary access. The full key is shown once and stored as a hash.</div>
          </section>
          <section>
            <div class="section-head">
              <h2>Issued Keys</h2>
              <span class="hint">Label, prefix, and usage — the secret is never shown again</span>
            </div>
            <div id="apiKeys" class="table"></div>
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

    const IDLE_TIMEOUT_MIN = 30;
    function key() { return $("apiKey").value.trim(); }
    function adminKey() { return $("adminKey").value.trim() || key(); }
    function hasStoredKeys() {
      // The admin key alone is enough to keep a session alive: it is the more
      // sensitive of the two, and gating on the API key would leave it stored
      // forever whenever only the admin field was filled in.
      return !!(sessionStorage.getItem("orchestratorApiKey") || sessionStorage.getItem("orchestratorAdminKey"));
    }
    function sessionAgeMin() {
      const at = Number(sessionStorage.getItem("orchestratorKeysAt") || 0);
      // Stored keys with no timestamp (written by an older build, or by a path that
      // skipped touchSession) must count as stale rather than brand new -- treating
      // "unknown age" as zero would disable the timeout for that tab entirely.
      if (!at) return hasStoredKeys() ? Infinity : 0;
      return (Date.now() - at) / 60000;
    }
    function touchSession() {
      if (hasStoredKeys()) {
        sessionStorage.setItem("orchestratorKeysAt", String(Date.now()));
      }
    }
    function clearSession() {
      sessionStorage.removeItem("orchestratorApiKey");
      sessionStorage.removeItem("orchestratorAdminKey");
      sessionStorage.removeItem("orchestratorKeysAt");
      $("apiKey").value = "";
      $("adminKey").value = "";
    }
    function expireSessionIfIdle() {
      if (!hasStoredKeys() || sessionAgeMin() <= IDLE_TIMEOUT_MIN) return;
      clearSession();
      document.querySelector(".content").classList.add("disconnected");
      setStatus(`Session expired after ${IDLE_TIMEOUT_MIN} minutes idle. Enter your key to reconnect.`, "warn");
    }
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
    function esc(value) {
      return String(value).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
    }
    function chip(text, kind) {
      return `<span class="chip ${kind || ""}">${esc(text)}</span>`;
    }
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
      // Honest status badges (real state, not fabricated trend deltas).
      setBadge("badgeApi", "healthy", "ok");
      if (state.ready?.status === "ready") setBadge("badgeLlama", "ready", "ok");
      else if (state.ready?.status === "unavailable") setBadge("badgeLlama", "down", "err");
      else setBadge("badgeLlama", "checking", "");
      setBadge("badgeModels", `${virtualNames().length} virtual`, "");
      setBadge("badgeMcp", mcp.enabled ? "on" : "off", mcp.enabled ? "ok" : "");
    }
    function setBadge(id, text, kind) {
      const el = $(id);
      if (!el) return;
      el.textContent = text;
      el.className = "metric-badge" + (kind ? " " + kind : "");
    }
    function renderPipeline() {
      const el = $("pipeline");
      if (!el) return;
      const cfg = state.config || {};
      const routing = cfg.routing || {};
      const improver = cfg.prompt_improver || {};
      const mcp = cfg.mcp || {};
      const orchestration = cfg.orchestration || {};
      const providerCount = Object.keys(cfg.providers || {}).length;
      const llamaReady = state.ready?.status === "ready";
      const stages = [
        { n: "1", title: "Ingress", rows: [
          ["Endpoint", chip("/v1/chat/completions", "accent")],
          ["Auth", chip("API key", "on")],
          ["Providers", chip(providerCount)],
        ]},
        { n: "2", title: "Prompt improve", rows: [
          ["Model", chip(improver.model || "prompt", "accent")],
          ["Provider", chip(improver.provider || "local")],
          ["Temp", chip(improver.temperature ?? "default")],
        ]},
        { n: "3", title: "Router", rows: [
          ["Default", chip(routing.default_model || "-", "accent")],
          ["Coding", chip(routing.coding_model || "-")],
          ["Vision", chip(routing.vision_model || "-")],
        ]},
        { n: "4", title: "MCP tools", rows: [
          ["Status", mcp.enabled ? chip("enabled", "on") : chip("disabled", "off")],
          ["Allowed", chip((mcp.tool_allowlist || []).length)],
          ["Max rounds", chip(orchestration.max_tool_rounds ?? "-")],
        ]},
      ];
      el.innerHTML = stages.map(stage => `
        <div class="stage">
          <div class="stage-head"><span class="stage-num">${stage.n}</span><span class="stage-title">${esc(stage.title)}</span></div>
          ${stage.rows.map(row => `<div class="stage-row"><span class="k">${esc(row[0])}</span>${row[1]}</div>`).join("")}
        </div>`).join("");
    }
    function fmtTime(seconds) {
      if (!seconds) return "-";
      const d = new Date(seconds * 1000);
      return d.toLocaleString([], { month: "short", day: "2-digit", hour: "2-digit", minute: "2-digit", second: "2-digit" });
    }
    function fmtAuditFields(fields) {
      const entries = Object.entries(fields || {});
      if (!entries.length) return "-";
      return entries.map(([k, v]) => `${k}=${v}`).join(", ");
    }
    async function renderAudit() {
      const table = $("auditLog");
      if (!table) return;
      let entries = [];
      try {
        entries = (await api("/admin/audit", { admin: true })).entries || [];
      } catch (err) {
        table.innerHTML = `<div class="status">Could not load activity: ${esc(err.message)}</div>`;
        return;
      }
      table.innerHTML = `<div class="tr audit th"><span>Time</span><span>Action</span><span>Details</span><span>By</span></div>`;
      if (!entries.length) {
        const empty = document.createElement("div");
        empty.className = "status";
        empty.textContent = "No config changes recorded yet.";
        table.appendChild(empty);
        return;
      }
      for (const entry of entries) {
        const row = document.createElement("div");
        row.className = "tr audit";
        row.innerHTML = `
          <div class="td" data-label="Time">${esc(fmtTime(entry.at))}</div>
          <div class="td" data-label="Action"><span class="badge">${esc(entry.action || "-")}</span></div>
          <div class="td" data-label="Details">${esc(fmtAuditFields(entry.fields))}</div>
          <div class="td" data-label="By">${esc(entry.ip || "-")}</div>
        `;
        table.appendChild(row);
      }
    }
    function deltaChip(delta, higherIsBetter) {
      if (delta === null || delta === undefined) return `<span class="delta flat">no baseline</span>`;
      if (delta === 0) return `<span class="delta flat">0%</span>`;
      const up = delta > 0;
      const good = up === higherIsBetter;
      return `<span class="delta ${good ? "up" : "down"}">${up ? "▲" : "▼"} ${esc(Math.abs(delta))}%</span>`;
    }
    function sparkline(series) {
      const values = series && series.length ? series : [0];
      const max = Math.max(1, ...values);
      const n = values.length;
      const w = 200, h = 48;
      const points = values.map((v, i) => `${(n > 1 ? (i / (n - 1)) * w : 0).toFixed(1)},${(h - (v / max) * h).toFixed(1)}`).join(" ");
      return `<svg viewBox="0 0 ${w} ${h}" preserveAspectRatio="none" fill="none" stroke="var(--accent)" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"><polyline points="${points}"/></svg>`;
    }
    async function renderTraffic() {
      const el = $("traffic");
      if (!el) return;
      let m;
      try {
        m = await api("/admin/metrics", { admin: true });
      } catch (err) {
        el.innerHTML = `<div class="status">Could not load metrics: ${esc(err.message)}</div>`;
        return;
      }
      const cur = m.current || {};
      const d = m.delta_pct || {};
      const tiles = [
        { label: "Requests", value: cur.requests ?? 0, delta: d.requests, higherIsBetter: true },
        { label: "Avg latency", value: `${cur.avg_latency_ms ?? 0} ms`, delta: d.avg_latency_ms, higherIsBetter: false },
        { label: "p95 latency", value: `${cur.p95_latency_ms ?? 0} ms`, delta: null, higherIsBetter: false },
        { label: "Error rate", value: `${((cur.error_rate ?? 0) * 100).toFixed(1)}%`, delta: d.error_rate, higherIsBetter: false },
      ];
      const tileHtml = tiles.map(t => `
        <div class="stat">
          <div class="stat-label">${esc(t.label)}</div>
          <div class="stat-row"><span class="stat-value">${esc(t.value)}</span>${deltaChip(t.delta, t.higherIsBetter)}</div>
        </div>`).join("");
      el.innerHTML = tileHtml + `<div class="spark"><div class="stat-label">Requests / 5 min</div>${sparkline(m.series)}</div>`;
    }
    async function renderApiKeys() {
      const table = $("apiKeys");
      if (!table) return;
      let keys = [];
      let byKey = {};
      try {
        keys = (await api("/admin/api-keys", { admin: true })).keys || [];
      } catch (err) {
        table.innerHTML = `<div class="status err">Could not load keys: ${esc(err.message)}</div>`;
        return;
      }
      try { byKey = (await api("/admin/metrics", { admin: true })).by_key || {}; } catch { byKey = {}; }
      table.innerHTML = `<div class="tr keys th"><span>Label</span><span>Scope</span><span>Rate</span><span>Req 1h</span><span>Expires</span><span>Last used</span><span>Action</span></div>`;
      const active = keys.filter(k => !k.revoked && !k.expired);
      if (!active.length) {
        const empty = document.createElement("div");
        empty.className = "status";
        empty.textContent = "No active keys. Create one above to share access.";
        table.appendChild(empty);
        return;
      }
      for (const k of active) {
        const scopeModels = (k.scopes && k.scopes.models) || [];
        const modelsText = scopeModels.length ? scopeModels.join(", ") : "all models";
        const toolsScope = k.scopes ? k.scopes.tools : null;
        const toolsText = (toolsScope === null || toolsScope === undefined)
          ? "all tools"
          : (toolsScope.length ? `tools: ${toolsScope.join(", ")}` : "no tools");
        const scopeText = `${modelsText} · ${toolsText}`;
        const rateText = k.rate_limit_per_min ? `${k.rate_limit_per_min}/min` : "∞";
        const reqCount = byKey[k.label] || 0;
        const expiresText = k.expires_at ? fmtTime(k.expires_at) : "never";
        const row = document.createElement("div");
        row.className = "tr keys";
        row.innerHTML = `
          <div class="td" data-label="Label"><span class="badge">${esc(k.label)}</span> <code style="font-size:11px">${esc(k.prefix)}…</code></div>
          <div class="td" data-label="Scope">${esc(scopeText)}</div>
          <div class="td" data-label="Rate">${esc(rateText)}</div>
          <div class="td" data-label="Req 1h">${esc(reqCount)}</div>
          <div class="td" data-label="Expires">${esc(expiresText)}</div>
          <div class="td" data-label="Last used">${esc(k.last_used_at ? fmtTime(k.last_used_at) : "never")}</div>
          <div class="td" data-label="Action"><button class="ghost toggle-btn" data-id="${esc(k.id)}">Revoke</button></div>
        `;
        row.querySelector("button").addEventListener("click", () => revokeKey(k.id, k.label));
        table.appendChild(row);
      }
    }
    async function createKey() {
      const label = $("newKeyLabel").value.trim() || "unnamed";
      const wildcardWords = new Set(["all", "*", "any"]);
      let models = $("newKeyModels").value.split(",").map(x => x.trim()).filter(Boolean);
      // Typing "all" is a natural mistake -- treat it as "leave empty" instead of a
      // literal (nonexistent) model name that would silently lock the key out of
      // everything. The server applies the same rule as a backstop.
      if (models.some(m => wildcardWords.has(m.toLowerCase()))) models = [];
      const rate = Number($("newKeyRate").value || 0);
      const expiresInDays = Number($("newKeyExpires").value || 0);
      const toolsMode = $("newKeyToolsMode").value;
      let tools = null; // all
      if (toolsMode === "none") tools = [];
      else if (toolsMode === "list") tools = $("newKeyTools").value.split(",").map(x => x.trim()).filter(Boolean);
      setStatus("Creating key...");
      const data = await api("/admin/api-keys", {
        method: "POST", admin: true,
        body: JSON.stringify({ label, models, rate_limit_per_min: rate, tools, expires_in_days: expiresInDays })
      });
      const reveal = $("newKeyReveal");
      reveal.style.display = "block";
      reveal.className = "status ok";
      reveal.innerHTML = `Copy this key now — it will not be shown again:
        <div class="key-code"><code id="newKeyValue">${esc(data.key)}</code><button id="copyNewKeyBtn" class="secondary">Copy</button></div>`;
      $("copyNewKeyBtn").addEventListener("click", () => copyText(data.key));
      $("newKeyLabel").value = "";
      $("newKeyModels").value = "";
      $("newKeyRate").value = "0";
      $("newKeyExpires").value = "0";
      $("newKeyToolsMode").value = "all";
      $("newKeyTools").value = "";
      await renderApiKeys();
      renderAudit();
      setStatus(`Key "${esc(data.record.label)}" created.`, "ok");
    }
    async function revokeKey(id, label) {
      if (!confirm(`Revoke key "${label}"? Clients using it will stop working immediately.`)) return;
      setStatus("Revoking key...");
      await api(`/admin/api-keys/${encodeURIComponent(id)}`, { method: "DELETE", admin: true });
      await renderApiKeys();
      renderAudit();
      setStatus("Key revoked.", "ok");
    }
    async function renderServices() {
      const el = $("services");
      if (!el) return;
      let data;
      try {
        data = await api("/admin/services", { admin: true });
      } catch (err) {
        el.innerHTML = `<div class="status err">Could not load services: ${esc(err.message)}</div>`;
        return;
      }
      if (!data.enabled) {
        el.innerHTML = `<div class="status">Docker control is disabled. Enable the compose.docker-control.yaml overlay and set DOCKER_CONTROL_ENABLED=true to start/stop model containers here.</div>`;
        return;
      }
      if (data.error) {
        el.innerHTML = `<div class="status err">Docker unavailable: ${esc(data.error)}</div>`;
        return;
      }
      el.innerHTML = "";
      for (const svc of data.services || []) {
        const running = !!svc.running;
        const dotKind = running ? "ok" : (svc.exists ? "down" : "muted");
        const stateText = running ? "running" : (svc.exists ? "stopped" : "not created");
        const row = document.createElement("div");
        row.className = "service-row";
        row.innerHTML = `
          <span class="dot ${dotKind}"></span>
          <span class="service-name">${esc(svc.name)}</span>
          <span class="chip ${running ? "on" : "off"}">${esc(stateText)}</span>
          <span class="hint">${esc(svc.status || "")}</span>
          <span class="service-actions">
            <button class="toggle-btn ${running ? "ghost" : ""}" data-svc="${esc(svc.name)}" data-action="${running ? "stop" : "start"}" ${svc.exists ? "" : "disabled"}>${running ? "Stop" : "Start"}</button>
          </span>`;
        const button = row.querySelector("button");
        if (button && svc.exists) {
          button.addEventListener("click", async () => {
            const action = button.dataset.action;
            const name = button.dataset.svc;
            button.disabled = true;
            setStatus(`${action === "start" ? "Starting" : "Stopping"} ${name}...`);
            try {
              await api(`/admin/services/${encodeURIComponent(name)}/${action}`, { method: "POST", admin: true });
              setStatus(`${name} ${action === "start" ? "started" : "stopped"}.`, "ok");
            } catch (err) {
              setStatus(err.message, "err");
            }
            await renderServices();
            renderAudit();
          });
        }
        el.appendChild(row);
      }
    }
    function renderEndpoints() {
      const el = $("endpoints");
      if (!el) return;
      const cfg = state.config || {};
      const providers = cfg.providers || {};
      const models = cfg.models || {};
      const ready = state.ready;
      const health = ready?.providers || {};
      const gatewaySvg = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><circle cx="4.5" cy="12" r="2"/><circle cx="19.5" cy="6" r="2"/><circle cx="19.5" cy="18" r="2"/><path d="M6.5 12h5M11.5 12l6-6M11.5 12l6 6"/></svg>`;
      const providerRows = Object.keys(providers).map(name => {
        const modelChips = Object.entries(models)
          .filter(([, m]) => (m.provider || "local") === name && m.enabled !== false)
          .map(([id]) => chip(id))
          .join("");
        let dot = "muted", label = "configured";
        if (!ready) { dot = "muted"; label = "checking"; }
        else if (health[name]) { dot = health[name].ok ? "ok" : "down"; label = health[name].ok ? "reachable" : "unreachable"; }
        return `<div class="ep-provider">
          <span class="dot ${dot}"></span>
          <span class="ep-name">${esc(name)}</span>
          <span class="chip ${dot === "ok" ? "on" : dot === "down" ? "off" : ""}">${esc(label)}</span>
          <span class="ep-models">${modelChips || chip("no models", "off")}</span>
        </div>`;
      }).join("");
      el.innerHTML = `
        <div class="ep-node gateway">
          <span class="ep-name">${gatewaySvg}Gateway</span>
          <span class="ep-sub">127.0.0.1:8090 · /v1</span>
        </div>
        <div class="ep-arrow"></div>
        <div class="ep-providers">${providerRows}</div>`;
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
      $("bodySnippet").textContent = JSON.stringify(sample, null, 2);
      $("curlSnippet").textContent = `curl http://127.0.0.1:8090/v1/chat/completions -H "Authorization: Bearer ${key() || "<ORCHESTRATOR_API_KEY>"}" -H "Content-Type: application/json" -d "@request.json"`;
      $("psSnippet").textContent = `$headers = @{ Authorization = "Bearer ${key() || "<ORCHESTRATOR_API_KEY>"}" }
$body = @'
${JSON.stringify(sample)}
'@
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8090/v1/chat/completions" -Headers $headers -ContentType "application/json; charset=utf-8" -Body ([System.Text.Encoding]::UTF8.GetBytes($body))`;
    }
    function markFieldError(id, on) {
      const el = $(id);
      if (el) el.classList.toggle("field-error", on);
    }
    async function probeReady() {
      // Backend health is secondary to the admin config, and can be slow/unreachable,
      // so probe it after the console has already painted.
      try {
        state.ready = await api("/ready");
      } catch (err) {
        state.ready = { status: "unavailable", error: err.message };
      }
      updateMetrics();
      renderEndpoints();
      if (state.ready?.status !== "ready") {
        setStatus(`Connected. Note: llama.cpp is not reachable (${state.ready?.error || "unknown"}). Admin settings still work.`, "warn");
      }
    }
    async function loadAll() {
      markFieldError("apiKey", false);
      markFieldError("adminKey", false);
      if (!key()) {
        markFieldError("apiKey", true);
        $("apiKey").focus();
        setStatus("API key is required.", "err");
        return;
      }
      setStatus("Connecting...");

      let health;
      try {
        health = await publicApi("/health");
      } catch (err) {
        setStatus("Cannot reach the orchestrator: " + err.message, "err");
        return;
      }

      // Inference key unlocks the model list.
      try {
        state.models = await api("/v1/models");
      } catch (err) {
        markFieldError("apiKey", true);
        $("apiKey").focus();
        setStatus("API key rejected (" + err.message + "). Check the API key field.", "err");
        return;
      }

      // The console itself is an admin surface, so it needs the admin key. When a
      // separate ORCHESTRATOR_ADMIN_API_KEY is set, point the user at the Admin field
      // instead of failing with a cryptic error and a blank page.
      try {
        state.config = await api("/admin/config", { admin: true });
      } catch (err) {
        markFieldError("adminKey", true);
        $("adminKey").focus();
        updateMetrics();
        renderModels();
        setStatus("Admin access denied (" + err.message + "). Fill the Admin key field (it can differ from the API key), then Connect.", "err");
        return;
      }

      fillSelect($("promptProvider"), providerNames());
      fillSelect($("mainProvider"), providerNames());
      fillSelect($("virtualModel"), virtualNames());
      loadRouteForm();
      loadPromptForm();
      loadMcpForm();
      loadPlaygroundSelects();
      document.querySelector(".content").classList.remove("disconnected");
      updateMetrics();
      renderPipeline();
      renderEndpoints();
      renderProviders();
      renderModels();
      renderRoutes();
      renderSnippets();
      renderAudit();
      renderTraffic();
      renderServices();
      renderApiKeys();
      setStatus(`Connected: ${health.service} ${health.version}`, "ok");

      // Secondary data loads in the background so the console paints immediately.
      probeReady();
      listMcpTools(false).catch(err => {
        $("mcpOutput").textContent = pretty({ error: err.message });
        renderMcpTools();
      });
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
      renderPipeline();
      updateMetrics();
      renderAudit();
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
      touchSession();
      setStatus(`Keys remembered for this browser tab (cleared after ${IDLE_TIMEOUT_MIN} min idle).`, "ok");
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
    $("createKeyBtn").addEventListener("click", () => createKey().catch(err => setStatus(err.message, "err")));
    $("runPlayBtn").addEventListener("click", runPlayground);
    $("copyPlayBtn").addEventListener("click", () => copyText(pretty(playgroundPayload())));
    $("copyRouteBtn").addEventListener("click", () => copyText(pretty(state.config?.virtual_models?.[$("virtualModel").value] || {})));
    $("copyBodyBtn").addEventListener("click", () => copyText($("bodySnippet").textContent));
    $("copyCurlBtn").addEventListener("click", () => copyText($("curlSnippet").textContent));
    $("copyPsBtn").addEventListener("click", () => copyText($("psSnippet").textContent));
    $("apiKey").addEventListener("input", () => markFieldError("apiKey", false));
    $("adminKey").addEventListener("input", () => markFieldError("adminKey", false));
    // Remembered keys are cleared after a period of inactivity so an unattended
    // browser tab does not keep an admin credential usable indefinitely. Activity in
    // the console refreshes the deadline; a reload past it starts from an empty form.
    if (sessionAgeMin() > IDLE_TIMEOUT_MIN) {
      clearSession();
    } else {
      $("apiKey").value = sessionStorage.getItem("orchestratorApiKey") || "";
      $("adminKey").value = sessionStorage.getItem("orchestratorAdminKey") || "";
    }
    ["click", "keydown"].forEach(evt => document.addEventListener(evt, touchSession, { passive: true }));
    setInterval(expireSessionIfIdle, 30000);
    renderSnippets();
  </script>
</body>
</html>"""
