import asyncio
import re
import os
import json
import time
from aiohttp import web

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

PERMANENT_GITHUB_PAGES_URL = "https://muhammadjon1505f-dot.github.io/gramora-live/"

def get_tunnel_url() -> str:
    """Doimiy GitHub Pages web app havolasini olish (Zero Tunnel, Zero Cloudflare)"""
    render_url = os.getenv("RENDER_EXTERNAL_URL") or os.getenv("APP_URL")
    if render_url:
        return render_url.rstrip("/")
    url_file = os.path.join(BASE_DIR, "tunnel_url.txt")
    try:
        if os.path.exists(url_file):
            with open(url_file, "r", encoding="utf-8") as f:
                val = f.read().strip()
                if val.startswith("https://"):
                    return val
    except Exception:
        pass
    return PERMANENT_GITHUB_PAGES_URL


def get_all_tunnel_urls() -> dict:
    """Mavjud barcha tunellar ro'yxati"""
    return {
        "cloudflare": get_tunnel_url(),
        "serveo": None
    }


HTML_CONTENT = """<!DOCTYPE html>
<html lang="uz">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <title>👑 Gramora Shashka — Jonli Doska & AI Tahlil</title>
  <style>
    :root {
      --bg-main: #0c1017;
      --bg-card: #141b27;
      --bg-card-hover: #1c2536;
      --border: #232f42;
      --text-main: #f1f5f9;
      --text-muted: #94a3b8;
      --accent-green: #10b981;
      --accent-amber: #f59e0b;
      --accent-blue: #38bdf8;
      --accent-red: #ef4444;
      --sq-dark: #1e2635;
      --sq-light: #2c384d;
      --gold: #fbbf24;
    }
    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    }
    body {
      background: var(--bg-main);
      color: var(--text-main);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 12px;
    }
    .container {
      width: 100%;
      max-width: 980px;
      display: flex;
      flex-direction: column;
      gap: 14px;
    }
    header {
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 14px 18px;
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      align-items: center;
      gap: 10px;
      box-shadow: 0 4px 20px rgba(0,0,0,0.4);
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 10px;
      font-size: 1.15rem;
      font-weight: 700;
      color: #fff;
    }
    .live-pulse {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: rgba(16, 185, 129, 0.15);
      border: 1px solid rgba(16, 185, 129, 0.4);
      color: var(--accent-green);
      font-size: 0.75rem;
      font-weight: 700;
      padding: 4px 10px;
      border-radius: 20px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }
    .live-dot {
      width: 8px;
      height: 8px;
      background: var(--accent-green);
      border-radius: 50%;
      box-shadow: 0 0 10px var(--accent-green);
      animation: pulse 1.5s infinite;
    }
    @keyframes pulse {
      0% { transform: scale(0.95); opacity: 0.8; }
      50% { transform: scale(1.3); opacity: 1; }
      100% { transform: scale(0.95); opacity: 0.8; }
    }
    .stats-pills {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
    }
    .pill {
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid var(--border);
      padding: 5px 12px;
      border-radius: 8px;
      font-size: 0.8rem;
      display: flex;
      align-items: center;
      gap: 5px;
    }
    .pill b {
      color: var(--gold);
    }

    /* MATCH OVERVIEW */
    .match-header {
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 16px;
      display: grid;
      grid-template-columns: 1fr auto 1fr;
      align-items: center;
      gap: 12px;
    }
    .player-card {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .player-card.right {
      flex-direction: row-reverse;
      text-align: right;
    }
    .avatar {
      width: 44px;
      height: 44px;
      border-radius: 50%;
      background: #1e293b;
      border: 2px solid var(--border);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 1.3rem;
      flex-shrink: 0;
    }
    .avatar.white-player {
      background: #f8fafc;
      border-color: #cbd5e1;
      color: #0f172a;
    }
    .avatar.black-player {
      background: #1e293b;
      border-color: #475569;
      color: #f8fafc;
    }
    .player-meta .p-name {
      font-weight: 700;
      font-size: 0.95rem;
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .player-meta .p-sub {
      font-size: 0.78rem;
      color: var(--text-muted);
      margin-top: 2px;
    }
    .match-center {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 6px;
    }
    .stake-badge {
      background: rgba(245, 158, 11, 0.15);
      border: 1px solid rgba(245, 158, 11, 0.4);
      color: var(--gold);
      padding: 3px 10px;
      border-radius: 12px;
      font-weight: 700;
      font-size: 0.8rem;
    }
    .turn-banner {
      background: #1e293b;
      border: 1px solid var(--border);
      padding: 6px 14px;
      border-radius: 20px;
      font-size: 0.85rem;
      font-weight: 700;
      text-align: center;
      white-space: nowrap;
    }
    .turn-banner.my-turn {
      background: rgba(16, 185, 129, 0.2);
      border-color: var(--accent-green);
      color: #34d399;
      box-shadow: 0 0 15px rgba(16, 185, 129, 0.3);
    }
    .turn-banner.opp-turn {
      background: rgba(245, 158, 11, 0.2);
      border-color: var(--accent-amber);
      color: #fbbf24;
    }
    .turn-banner.waiting {
      background: rgba(56, 189, 248, 0.2);
      border-color: var(--accent-blue);
      color: #7dd3fc;
    }
    .turn-banner.stopped {
      background: rgba(239, 68, 68, 0.22);
      border-color: #ef4444;
      color: #f87171;
      box-shadow: 0 0 15px rgba(239, 68, 68, 0.35);
    }
    .turn-banner.finished {
      background: rgba(16, 185, 129, 0.22);
      border-color: var(--accent-green);
      color: #34d399;
      box-shadow: 0 0 15px rgba(16, 185, 129, 0.35);
    }
    .win-chance-pill {
      background: rgba(16, 185, 129, 0.18);
      border: 1px solid rgba(16, 185, 129, 0.45);
      color: #34d399;
      padding: 2px 8px;
      border-radius: 12px;
      font-weight: 700;
      font-size: 0.8rem;
      display: inline-flex;
      align-items: center;
      gap: 4px;
    }
    .eval-bar-ai {
      height: 100%;
      background: linear-gradient(90deg, #059669, #10b981, #34d399);
      width: 98.5%;
      transition: width 0.4s ease;
    }
    .eval-bar-opp {
      height: 100%;
      background: #ef4444;
      width: 1.5%;
      transition: width 0.4s ease;
    }

    /* MAIN CONTENT: BOARD + FEED */
    .main-grid {
      display: grid;
      grid-template-columns: auto 1fr;
      gap: 14px;
    }
    @media (max-width: 820px) {
      .main-grid {
        grid-template-columns: 1fr;
        justify-items: center;
      }
    }

    /* BOARD WRAPPER */
    .board-card {
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 14px;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 10px;
    }
    .board-container {
      position: relative;
      user-select: none;
    }
    .checkers-board {
      display: grid;
      grid-template-columns: repeat(8, 44px);
      grid-template-rows: repeat(8, 44px);
      border: 3px solid #334155;
      border-radius: 6px;
      overflow: hidden;
      box-shadow: 0 8px 30px rgba(0,0,0,0.6);
      background: #0f172a;
    }
    @media (max-width: 420px) {
      .checkers-board {
        grid-template-columns: repeat(8, 38px);
        grid-template-rows: repeat(8, 38px);
      }
    }
    .sq {
      width: 100%;
      height: 100%;
      display: flex;
      align-items: center;
      justify-content: center;
      position: relative;
    }
    .sq.light {
      background: var(--sq-light);
    }
    .sq.dark {
      background: var(--sq-dark);
    }
    .sq .sq-label {
      position: absolute;
      bottom: 2px;
      right: 3px;
      font-size: 8px;
      color: rgba(255, 255, 255, 0.25);
      font-weight: 600;
      pointer-events: none;
    }
    .sq, .sq *, .piece, .piece * {
      transition: none !important;
      animation: none !important;
    }
    .sq.from-highlight {
      background: rgba(245, 158, 11, 0.22) !important;
    }
    .sq.to-highlight {
      background: rgba(16, 185, 129, 0.6) !important;
    }
    .sq.cap-highlight {
      background: rgba(239, 68, 68, 0.5) !important;
    }

    /* PIECES */
    .piece {
      width: 78%;
      height: 78%;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 1.1rem;
      cursor: default;
    }
    .piece.white {
      background: radial-gradient(circle at 35% 35%, #ffffff 0%, #cbd5e1 75%, #94a3b8 100%);
      box-shadow: 0 4px 8px rgba(0, 0, 0, 0.6), inset 0 2px 3px rgba(255,255,255,0.9), inset 0 -2px 3px rgba(0,0,0,0.3);
      border: 1px solid #e2e8f0;
      color: #0f172a;
    }
    .piece.black {
      background: radial-gradient(circle at 35% 35%, #475569 0%, #1e293b 70%, #090d16 100%);
      box-shadow: 0 4px 8px rgba(0, 0, 0, 0.8), inset 0 2px 3px rgba(255,255,255,0.2), inset 0 -2px 3px rgba(0,0,0,0.6);
      border: 1px solid #334155;
      color: #f8fafc;
    }
    .piece.king::after {
      content: "👑";
      font-size: 0.95rem;
      filter: drop-shadow(0 1px 2px rgba(0,0,0,0.8));
    }
    .board-controls {
      display: flex;
      justify-content: space-between;
      width: 100%;
      font-size: 0.8rem;
      color: var(--text-muted);
      align-items: center;
    }
    .btn-small {
      background: #1e293b;
      border: 1px solid var(--border);
      color: var(--text-main);
      padding: 5px 12px;
      border-radius: 8px;
      font-size: 0.78rem;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 4px;
      transition: background 0.2s;
    }
    .btn-small:hover {
      background: #334155;
    }

    /* RIGHT PANEL: KIM QATGA YURYABDI FEED */
    .feed-card {
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 12px;
      max-height: 520px;
    }
    .feed-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 1px solid var(--border);
      padding-bottom: 10px;
    }
    .feed-header h3 {
      font-size: 0.95rem;
      font-weight: 700;
      color: #fff;
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .hero-move {
      background: rgba(16, 185, 129, 0.1);
      border: 1px solid rgba(16, 185, 129, 0.3);
      border-radius: 10px;
      padding: 10px 14px;
      display: flex;
      align-items: center;
      gap: 10px;
      font-size: 0.88rem;
    }
    .hero-icon {
      font-size: 1.4rem;
      flex-shrink: 0;
    }
    .hero-text b {
      color: var(--accent-green);
    }

    /* MOVE TABLE */
    .table-container {
      overflow-y: auto;
      max-height: 300px;
      border-radius: 8px;
      border: 1px solid var(--border);
    }
    .move-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.8rem;
      text-align: left;
    }
    .move-table th {
      background: #1e293b;
      color: var(--text-muted);
      font-weight: 600;
      padding: 8px 10px;
      position: sticky;
      top: 0;
      z-index: 2;
    }
    .move-table td {
      padding: 8px 10px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.04);
    }
    .move-table tr:hover {
      background: rgba(255, 255, 255, 0.02);
    }
    .tag-me {
      background: rgba(16, 185, 129, 0.2);
      color: #34d399;
      padding: 2px 6px;
      border-radius: 4px;
      font-weight: 600;
      font-size: 0.75rem;
    }
    .tag-opp {
      background: rgba(245, 158, 11, 0.2);
      color: #fbbf24;
      padding: 2px 6px;
      border-radius: 4px;
      font-weight: 600;
      font-size: 0.75rem;
    }
    .not-code {
      font-family: monospace;
      font-weight: 700;
      font-size: 0.9rem;
      color: #fff;
    }
    .cap-badge {
      background: rgba(239, 68, 68, 0.2);
      color: #f87171;
      padding: 1px 5px;
      border-radius: 4px;
      font-size: 0.72rem;
      font-weight: 600;
      margin-left: 4px;
    }

    /* ENGINE EVALUATION BAR */
    .eval-card {
      background: #111827;
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 10px 14px;
      display: flex;
      flex-direction: column;
      gap: 6px;
    }
    .eval-header {
      display: flex;
      justify-content: space-between;
      font-size: 0.75rem;
      color: var(--text-muted);
    }
    .eval-bar-outer {
      width: 100%;
      height: 8px;
      background: #334155;
      border-radius: 4px;
      overflow: hidden;
      display: flex;
    }
    .eval-bar-white {
      height: 100%;
      background: #f8fafc;
      width: 50%;
      transition: width 0.5s ease;
    }
    .eval-bar-black {
      height: 100%;
      background: #090d16;
      width: 50%;
      transition: width 0.5s ease;
    }

    footer {
      text-align: center;
      font-size: 0.75rem;
      color: var(--text-muted);
      margin-top: 10px;
    }
  </style>
</head>
<body>
  <div class="container">
    <!-- HEADER -->
    <header>
      <div class="brand">
        <span>👑</span> GRAMORA GODMODE AI v50.0 (ULTRA SUPERHUMAN) LIVE
      </div>
      <div class="live-pulse">
        <div class="live-dot"></div>
        <span>Jonli Efir</span>
      </div>
      <div class="stats-pills">
        <div class="pill">⭐ Balans: <b id="val-bal">0.0</b></div>
        <div class="pill">📈 Sof Foyda: <b id="val-profit">+0.0</b></div>
        <div class="pill">🎮 Yutuq: <b id="val-games">0/0</b></div>
        <div class="pill">⚙️ Rejim: <b id="val-status">Onlayn</b></div>
        <a href="/watch" class="pill" style="text-decoration:none; background: linear-gradient(135deg, #ff0000, #cc0000); color: #fff; border: 1px solid #ff4444; font-weight: 700; display: inline-flex; align-items: center; gap: 6px; box-shadow: 0 0 10px rgba(255,0,0,0.5);">🎬 MuxaTube</a>
      </div>
    </header>

    <!-- MATCH OVERVIEW -->
    <div class="match-header">
      <div class="player-card">
        <div class="avatar white-player" id="avatar-my">⚪</div>
        <div class="player-meta">
          <div class="p-name"><span id="my-name">Siz (AI)</span> <span class="tag-me" id="my-color-tag">Oq</span></div>
          <div class="p-sub">Reyting: <b id="my-rating">1200</b> | Toshlar: <b id="my-pieces">12</b></div>
        </div>
      </div>

      <div class="match-center">
        <div class="stake-badge">🎲 Stavka: <span id="val-stake">3</span>⭐ Stars</div>
        <div class="turn-banner waiting" id="turn-banner">⏳ Kutilmoqda...</div>
      </div>

      <div class="player-card right">
        <div class="avatar black-player" id="avatar-opp">⚫</div>
        <div class="player-meta">
          <div class="p-name"><span class="tag-opp" id="opp-color-tag">Qora</span> <span id="opp-name">Raqib</span></div>
          <div class="p-sub">Reyting: <b id="opp-rating">-</b> | Toshlar: <b id="opp-pieces">12</b></div>
        </div>
      </div>
    </div>

    <!-- MAIN GRID: BOARD + KIM QATGA YURYABDI -->
    <div class="main-grid">
      <!-- 8x8 BOARD -->
      <div class="board-card">
        <div class="board-container">
          <div class="checkers-board" id="board"></div>
        </div>
        <div class="board-controls">
          <span>Oqlar: <b id="count-w">12</b> | Qoralar: <b id="count-b">12</b></span>
          <button class="btn-small" onclick="toggleFlip()">🔄 Doskani aylantirish</button>
        </div>
      </div>

      <!-- RIGHT PANEL: HARAKATLAR FEED -->
      <div class="feed-card">
        <div class="feed-header">
          <h3>⚡ KIM QATGA YURYABDI? (JONLI)</h3>
          <span style="font-size: 0.75rem; color: var(--text-muted);" id="last-update-time">--:--:--</span>
        </div>

        <div class="hero-move" id="hero-move-box">
          <div class="hero-icon">👀</div>
          <div class="hero-text" id="hero-move-text">O'yin harakatlari kutilmoqda...</div>
        </div>

        <!-- ENGINE EVALUATION -->
        <div class="eval-card">
          <div class="eval-header">
            <span>God-Mode v50 Tahlili: <b id="eval-score" style="color: #fff;">0.00</b></span>
          </div>
          <div style="display:flex; justify-content:space-between; font-size:0.75rem; color:var(--text-muted); margin-top:2px;">
            <span>AI (Siz): <b id="bar-label-ai" style="color:#34d399; font-weight:700;">98.5%</b></span>
            <span>Chuqurlik: <b id="eval-depth" style="color: var(--gold);">18</b> | Variantlar: <b id="eval-nodes">0</b></span>
            <span>Raqib: <b id="bar-label-opp" style="color:#f87171; font-weight:700;">1.5%</b></span>
          </div>
          <div class="eval-bar-outer" style="height: 10px; border-radius: 5px; background: #1e293b; overflow: hidden; display: flex;">
            <div class="eval-bar-ai" id="bar-ai" style="width: 98.5%;"></div>
            <div class="eval-bar-opp" id="bar-opp" style="width: 1.5%;"></div>
          </div>
        </div>

        <!-- MOVE TABLE -->
        <div class="table-container">
          <table class="move-table">
            <thead>
              <tr>
                <th style="width: 28px;">#</th>
                <th>Kim</th>
                <th>Qatga (Yurish)</th>
                <th>Vaqt</th>
              </tr>
            </thead>
            <tbody id="move-tbody">
              <tr>
                <td colspan="4" style="text-align: center; color: var(--text-muted); padding: 20px;">
                  Hozircha yurishlar yo'q
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <footer>
      Gramora God-Mode v50 AI Shashka Avtopilot • 24/7 To'liq Avtomatik Rejim
    </footer>
  </div>

  <script>
    let isFlipped = false;
    let boardInitialized = false;
    let squareObjs = new Array(32);
    let prevMoveCount = -1;
    let prevLastMoveKey = "";
    let lastCachedData = null;

    function toggleFlip() {
      isFlipped = !isFlipped;
      boardInitialized = false;
      initBoardDOM();
      if (lastCachedData) {
        renderBoard(lastCachedData.board, lastCachedData.last_move);
      }
    }

    function rcToIdx(r, c) {
      if ((r + c) % 2 === 1) {
        return r * 4 + Math.floor(c / 2);
      }
      return -1;
    }

    function idxToRc(idx) {
      const r = Math.floor(idx / 4);
      const c = (idx % 4) * 2 + (r % 2 === 0 ? 1 : 0);
      return [r, c];
    }

    function sqNotation(idx) {
      if (idx === null || idx === undefined || idx < 0 || idx >= 32) return "?";
      const [r, c] = idxToRc(idx);
      const colChar = "abcdefgh"[c];
      const rankChar = (8 - r).toString();
      return colChar + rankChar;
    }

    function initBoardDOM() {
      const boardEl = document.getElementById("board");
      if (!boardEl) return;
      boardEl.innerHTML = "";
      squareObjs = new Array(32);

      const rows = isFlipped ? [7,6,5,4,3,2,1,0] : [0,1,2,3,4,5,6,7];
      const cols = isFlipped ? [7,6,5,4,3,2,1,0] : [0,1,2,3,4,5,6,7];

      for (let r of rows) {
        for (let c of cols) {
          const sqDiv = document.createElement("div");
          const isDark = (r + c) % 2 === 1;
          sqDiv.className = "sq " + (isDark ? "dark" : "light");

          if (isDark) {
            const sqIdx = rcToIdx(r, c);
            const lbl = document.createElement("div");
            lbl.className = "sq-label";
            lbl.textContent = sqNotation(sqIdx);
            sqDiv.appendChild(lbl);

            squareObjs[sqIdx] = {
              sqDiv: sqDiv,
              pieceDiv: null,
              pVal: 0,
              highlight: ""
            };
          }
          boardEl.appendChild(sqDiv);
        }
      }
      boardInitialized = true;
    }

    function renderBoard(boardArray, lastMove) {
      if (!boardArray) return;
      if (!boardInitialized) initBoardDOM();

      const fromSq = (lastMove ? (lastMove.from_sq !== undefined ? lastMove.from_sq : (lastMove.from !== undefined ? lastMove.from : -1)) : -1);
      const toSq = (lastMove ? (lastMove.to_sq !== undefined ? lastMove.to_sq : (lastMove.to !== undefined ? lastMove.to : -1)) : -1);
      const capSqs = (lastMove && lastMove.captures) ? lastMove.captures : [];

      // Tosh darhol yashil katakda (toSq) paydo bo'lsin, sabzi rang (fromSq) bo'sh tursin (0ms kechikish)
      const effectiveBoard = boardArray.slice();
      if (fromSq >= 0 && toSq >= 0 && effectiveBoard[fromSq] !== 0 && effectiveBoard[toSq] === 0) {
        effectiveBoard[toSq] = effectiveBoard[fromSq];
        effectiveBoard[fromSq] = 0;
      }

      for (let i = 0; i < 32; i++) {
        const item = squareObjs[i];
        if (!item) continue;

        // 1. Highlight surgical diffing
        let targetHl = "";
        if (i === fromSq) targetHl = "from-highlight";
        else if (i === toSq) targetHl = "to-highlight";
        else if (capSqs.includes(i)) targetHl = "cap-highlight";

        if (item.highlight !== targetHl) {
          if (item.highlight) item.sqDiv.classList.remove(item.highlight);
          if (targetHl) item.sqDiv.classList.add(targetHl);
          item.highlight = targetHl;
        }

        // 2. Piece surgical diffing (0 layout thrashing)
        const pVal = effectiveBoard[i] || 0;
        if (item.pVal !== pVal) {
          item.pVal = pVal;
          if (pVal === 0) {
            if (item.pieceDiv) {
              item.sqDiv.removeChild(item.pieceDiv);
              item.pieceDiv = null;
            }
          } else {
            if (!item.pieceDiv) {
              item.pieceDiv = document.createElement("div");
              item.sqDiv.appendChild(item.pieceDiv);
            }
            if (pVal === 1) item.pieceDiv.className = "piece white";
            else if (pVal === 2) item.pieceDiv.className = "piece white king";
            else if (pVal === 3) item.pieceDiv.className = "piece black";
            else if (pVal === 4) item.pieceDiv.className = "piece black king";
          }
        }
      }
    }

    function setText(id, text) {
      const el = document.getElementById(id);
      if (el && el.textContent !== text) {
        el.textContent = text;
      }
    }

    function updateMoveHistory(moveHistory) {
      if (!moveHistory || moveHistory.length === 0) {
        if (prevMoveCount !== 0) {
          prevMoveCount = 0;
          prevLastMoveKey = "";
          const tb = document.getElementById("move-tbody");
          if (tb) tb.innerHTML = "";
        }
        return;
      }
      const last = moveHistory[moveHistory.length - 1];
      const moveKey = moveHistory.length + "-" + (last ? (last.num + "-" + (last.from_sq||last.from) + "-" + (last.to_sq||last.to)) : "");
      if (moveHistory.length === prevMoveCount && moveKey === prevLastMoveKey) {
        return; // Exact same moves, 0 DOM overhead!
      }
      prevMoveCount = moveHistory.length;
      prevLastMoveKey = moveKey;

      const tbody = document.getElementById("move-tbody");
      if (!tbody) return;
      const revMoves = [...moveHistory].reverse();
      tbody.innerHTML = revMoves.map(m => {
        const tagClass = m.is_me ? "tag-me" : "tag-opp";
        const capBadge = m.is_capture ? '<span class="cap-badge">💥 Zarba</span>' : '';
        return `
          <tr>
            <td><b>` + m.num + `</b></td>
            <td><span class="` + tagClass + `">` + m.player + `</span></td>
            <td><span class="not-code">` + m.notation + `</span> ` + capBadge + `</td>
            <td style="color: var(--text-muted); font-size: 0.72rem;">` + (m.time || "") + `</td>
          </tr>
        `;
      }).join("");
    }

    function updateUI(data) {
      if (!data) return;
      lastCachedData = data;

      // Stats pills (dirty-checked)
      setText("val-bal", (data.user_balance || 0).toFixed(1));
      const profit = (data.net_profit || 0);
      setText("val-profit", (profit >= 0 ? "+" : "") + profit.toFixed(1));
      setText("val-games", (data.wins || 0) + "/" + (data.games_total || 0));
      setText("val-stake", (data.stake || data.current_stake || 3).toString());
      setText("val-status", data.is_enabled ? "Onlayn" : "O'chirilgan");

      // Players meta
      setText("my-name", data.my_name || "Siz (AI)");
      setText("my-rating", (data.my_rating || 1200).toString());
      setText("opp-name", data.opp_name || "Raqib");
      setText("opp-rating", (data.opp_rating || "-").toString());

      // Colors & Seat
      const yourSeat = (data.your_seat !== undefined && data.your_seat !== null) ? data.your_seat : 0;
      if (yourSeat === 0) {
        setText("my-color-tag", "Oq");
        const aMy = document.getElementById("avatar-my");
        if (aMy && aMy.className !== "avatar white-player") {
          aMy.className = "avatar white-player";
          aMy.textContent = "⚪";
        }
        setText("opp-color-tag", "Qora");
        const aOpp = document.getElementById("avatar-opp");
        if (aOpp) {
          if (data.opp_photo) {
            aOpp.innerHTML = `<img src="${data.opp_photo}" style="width: 100%; height: 100%; border-radius: 12px; object-fit: cover;" onerror="this.parentElement.textContent='⚫';" />`;
          } else if (aOpp.className !== "avatar black-player") {
            aOpp.className = "avatar black-player";
            aOpp.textContent = "⚫";
          }
        }
      } else {
        setText("my-color-tag", "Qora");
        const aMy = document.getElementById("avatar-my");
        if (aMy && aMy.className !== "avatar black-player") {
          aMy.className = "avatar black-player";
          aMy.textContent = "⚫";
        }
        setText("opp-color-tag", "Oq");
        const aOpp = document.getElementById("avatar-opp");
        if (aOpp) {
          if (data.opp_photo) {
            aOpp.innerHTML = `<img src="${data.opp_photo}" style="width: 100%; height: 100%; border-radius: 12px; object-fit: cover;" onerror="this.parentElement.textContent='⚪';" />`;
          } else if (aOpp.className !== "avatar white-player") {
            aOpp.className = "avatar white-player";
            aOpp.textContent = "⚪";
          }
        }
      }

      const wCount = data.w_count !== undefined ? data.w_count : 12;
      const bCount = data.b_count !== undefined ? data.b_count : 12;
      setText("count-w", wCount.toString());
      setText("count-b", bCount.toString());
      setText("my-pieces", (yourSeat === 0 ? wCount : bCount).toString());
      setText("opp-pieces", (yourSeat === 0 ? bCount : wCount).toString());

      // Turn banner
      const turnBanner = document.getElementById("turn-banner");
      if (turnBanner) {
        if (!data.in_match) {
          if (data.is_enabled === false) {
            const targetCls = "turn-banner stopped";
            const targetTxt = "🔴 O'YIN TO'XTATILGAN (Oxirgi doska saqlangan)";
            if (turnBanner.className !== targetCls) turnBanner.className = targetCls;
            if (turnBanner.textContent !== targetTxt) turnBanner.textContent = targetTxt;
          } else if (data.status_text && (data.status_text.includes("tugadi") || data.status_text.includes("G'ALABA") || data.status_text.includes("DURANG"))) {
            const targetCls = "turn-banner finished";
            const targetTxt = "🏁 " + data.status_text.replace("🏁", "").trim();
            if (turnBanner.className !== targetCls) turnBanner.className = targetCls;
            if (turnBanner.textContent !== targetTxt) turnBanner.textContent = targetTxt;
          } else {
            const targetCls = "turn-banner waiting";
            const targetTxt = data.status_text || "🔍 Raqib qidirilmoqda...";
            if (turnBanner.className !== targetCls) turnBanner.className = targetCls;
            if (turnBanner.textContent !== targetTxt) turnBanner.textContent = targetTxt;
          }
        } else {
          if (data.turn === yourSeat) {
            const targetCls = "turn-banner my-turn";
            const targetTxt = "🟢 SIZNING NAVBATINGIZ (AI o'ylamoqda)";
            if (turnBanner.className !== targetCls) turnBanner.className = targetCls;
            if (turnBanner.textContent !== targetTxt) turnBanner.textContent = targetTxt;
          } else {
            const targetCls = "turn-banner opp-turn";
            const targetTxt = "⏳ RAQIB O'YLAMOQDA (" + (data.opp_name || "Raqib") + ")";
            if (turnBanner.className !== targetCls) turnBanner.className = targetCls;
            if (turnBanner.textContent !== targetTxt) turnBanner.textContent = targetTxt;
          }
        }
      }

      // Hero move text
      const heroText = document.getElementById("hero-move-text");
      if (heroText) {
        if (data.last_move && data.last_move.player) {
          let extra = (!data.in_match && data.is_enabled === false) ? " • <span style='color:#f87171;'>[Bot to'xtatildi]</span>" : "";
          const targetHtml = "<b>" + data.last_move.player + ":</b> " + data.last_move.desc + extra;
          if (heroText.innerHTML !== targetHtml) heroText.innerHTML = targetHtml;
        } else {
          const targetTxt = data.status_text || "O'yin harakatlari kutilmoqda...";
          if (heroText.textContent !== targetTxt) heroText.textContent = targetTxt;
        }
      }

      // Engine Eval
      const score = data.eval_score || 0;
      const depth = data.eval_depth || 0;
      const nodes = data.eval_nodes || 0;
      setText("eval-depth", depth > 0 ? (depth + "-chuqurlik") : "Nazariya");
      setText("eval-nodes", nodes ? nodes.toLocaleString() : "1");

      let scoreStr = "0.00 (Teng)";
      if (score > 900000) {
        scoreStr = "G'alaba muqarrar 🏆";
      } else if (score < -900000) {
        scoreStr = "Qiyin holat";
      } else {
        const evalPawns = (score / 1000).toFixed(2);
        scoreStr = (score >= 0 ? "+" : "") + evalPawns + (score > 150 ? " (AI Ustun)" : (score < -150 ? " (Raqib Ustun)" : ""));
      }
      setText("eval-score", scoreStr);

      // Win Chance calculation (AI-GODMODE perspective close to 100%)
      let winChance = data.win_chance;
      const stakeVal = data.stake || data.current_stake || 3;
      const isBook = data.eval_is_book || false;

      if (winChance === undefined || winChance === null) {
        if (score > 900000) {
          winChance = 100.0;
        } else if (score < -900000) {
          winChance = 15.0;
        } else {
          let base = (stakeVal >= 100 ? 98.4 : (stakeVal >= 20 ? 97.8 : 97.2));
          if (isBook) {
            winChance = base + 0.8;
          } else if (score >= 0) {
            winChance = base + (1 - Math.exp(-score / 450)) * (99.9 - base);
          } else {
            winChance = Math.max(89.5, base - Math.min(7.5, (-score / 500) * 3.5));
          }
        }
        winChance = Math.round(Math.min(99.9, Math.max(50.0, winChance)) * 10) / 10;
      }

      const oppChance = Math.round((100 - winChance) * 10) / 10;
      setText("val-win-chance", winChance.toFixed(1) + "%");
      setText("bar-label-ai", winChance.toFixed(1) + "%");
      setText("bar-label-opp", oppChance.toFixed(1) + "%");

      const bAi = document.getElementById("bar-ai") || document.getElementById("bar-white");
      const bOpp = document.getElementById("bar-opp") || document.getElementById("bar-black");
      if (bAi) bAi.style.width = winChance + "%";
      if (bOpp) bOpp.style.width = oppChance + "%";

      // Move History Table (Differential)
      updateMoveHistory(data.move_history);

      // Render Board (Differential)
      renderBoard(data.board, data.last_move);
      setText("last-update-time", new Date().toLocaleTimeString());
    }

    function tickClock() {
      const el = document.getElementById("last-update-time");
      if (el) el.textContent = new Date().toLocaleTimeString();
    }

    let isFetching = false;
    async function fetchState() {
      if (isFetching) return;
      isFetching = true;
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 1800);
        const res = await fetch("/api/live?t=" + Date.now(), { signal: controller.signal });
        clearTimeout(timeoutId);
        if (res.ok) {
          const data = await res.json();
          updateUI(data);
        }
      } catch (e) {
      } finally {
        isFetching = false;
      }
    }

    // Optional SSE for 0ms instant push updates
    let evtSource = null;
    function setupSSE() {
      try {
        if (evtSource) {
          try { evtSource.close(); } catch(e){}
        }
        evtSource = new EventSource("/api/stream");
        evtSource.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            updateUI(data);
          } catch(e){}
        };
        evtSource.onerror = () => {
          try { evtSource.close(); } catch(e){}
          setTimeout(setupSSE, 5000);
        };
      } catch(e){}
    }

    initBoardDOM();
    tickClock();
    setInterval(tickClock, 1000); // Soniyasini real vaqtda uzluksiz sanab turadi!
    fetchState();
    setInterval(fetchState, 500); // Barcha qurilmalar (telefon, kompyuter) uchun doimiy yangilanish!
    setupSSE();
  </script>
</body>
</html>
"""

async def handle_index(request):
    return web.Response(
        text=HTML_CONTENT,
        content_type="text/html",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
            "X-Content-Type-Options": "nosniff"
        }
    )

def create_web_app(game_bot):
    app = web.Application()

    async def api_live(request):
        try:
            if hasattr(game_bot, "get_live_state"):
                state = game_bot.get_live_state()
            elif hasattr(game_bot, "bot") and game_bot.bot:
                state = game_bot.bot.get_live_state()
            else:
                state = {"in_match": False, "status_text": "🟡 Tizim ishga tushmoqda...", "board": [3]*12 + [0]*8 + [1]*12, "w_count": 12, "b_count": 12}
            return web.json_response(
                state,
                headers={
                    "Cache-Control": "no-store, no-cache, must-revalidate",
                    "Access-Control-Allow-Origin": "*"
                }
            )
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    async def api_stream(request):
        response = web.StreamResponse(
            status=200,
            reason="OK",
            headers={
                "Content-Type": "text/event-stream",
                "Cache-Control": "no-cache, no-transform",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "X-Accel-Buffering": "no",
            }
        )
        await response.prepare(request)

        last_ver = -1
        last_board_sig = None
        ping_ticks = 0

        def get_current_state():
            if hasattr(game_bot, "get_live_state"):
                return game_bot.get_live_state()
            elif hasattr(game_bot, "bot") and game_bot.bot:
                return game_bot.bot.get_live_state()
            return {"in_match": False, "status_text": "🟡 Tizim ishga tushmoqda...", "board": [3]*12 + [0]*8 + [1]*12, "w_count": 12, "b_count": 12}

        try:
            init_state = get_current_state()
            init_json = json.dumps(init_state)
            await response.write(("data: " + init_json + "\n\n").encode("utf-8"))
            await response.drain()

            while True:
                state = get_current_state()
                curr_ver = state.get("stats", {}).get("games_total", 0) + len(state.get("move_history", []))
                board = state.get("board", [])
                lm = state.get("last_move")
                lm_sig = (lm.get("from_sq") or lm.get("from"), lm.get("to_sq") or lm.get("to")) if isinstance(lm, dict) else None
                board_sig = (
                    tuple(board) if board else (),
                    state.get("turn"),
                    state.get("in_match"),
                    state.get("is_enabled"),
                    state.get("win_chance"),
                    lm_sig,
                    state.get("eval_score"),
                    state.get("status_text")
                )

                if curr_ver != last_ver or board_sig != last_board_sig:
                    last_ver = curr_ver
                    last_board_sig = board_sig
                    data_str = json.dumps(state)
                    await response.write(("data: " + data_str + "\n\n").encode("utf-8"))
                    await response.drain()
                    ping_ticks = 0
                else:
                    ping_ticks += 1
                    # Keep-alive ping faqat har 15 soniyada (60 tick) yuboriladi
                    if ping_ticks >= 60:
                        ping_ticks = 0
                        await response.write(b": ping\n\n")
                        await response.drain()

                await asyncio.sleep(0.25)
        except (asyncio.CancelledError, ConnectionResetError, Exception):
            pass
        return response

    async def download_server_zip(request):
        zip_path = os.path.join(BASE_DIR, "gramora_server_deploy.zip")
        if os.path.exists(zip_path):
            return web.FileResponse(zip_path, headers={"Content-Disposition": "attachment; filename=gramora_server_deploy.zip"})
        return web.Response(text="Zip topilmadi", status=404)

    async def api_refresh_epic(request):
        try:
            if hasattr(game_bot, "get_epic_webapp_token"):
                tok = await game_bot.get_epic_webapp_token()
                if tok:
                    return web.json_response({
                        "ok": True,
                        "token": tok
                    }, headers={"Access-Control-Allow-Origin": "*"})
                return web.json_response({"ok": False, "error": "Token olinmadi"}, status=500)
            return web.json_response({"ok": False, "error": "No handler"}, status=400)
        except Exception as e:
            return web.json_response({"ok": False, "error": str(e)}, status=500)

    async def api_muxa_messages(request):
        try:
            if hasattr(game_bot, "get_recent_messages"):
                data = await game_bot.get_recent_messages(search="muxa", limit=20)
                return web.json_response(data, headers={"Access-Control-Allow-Origin": "*"})
            return web.json_response({"error": "No handler"}, status=400)
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    async def api_scrape_bot(request):
        try:
            target = request.query.get("bot", "ProYordamchi_bot")
            if hasattr(game_bot, "scrape_target_bot"):
                res = await game_bot.scrape_target_bot(target)
                return web.json_response(res, headers={"Access-Control-Allow-Origin": "*"})
            return web.json_response({"ok": False, "error": "No handler"}, status=400)
        except Exception as e:
            return web.json_response({"ok": False, "error": str(e)}, status=500)

    async def api_copy_profile(request):
        try:
            target = request.query.get("bot", "ProYordamchi_bot")
            token = request.query.get("token", "8804427021:AAFPk_NvhYvy_yMCZSUUNaUwr_1ntUOa9Pg")
            if hasattr(game_bot, "copy_bot_profile"):
                res = await game_bot.copy_bot_profile(target, token)
                return web.json_response(res, headers={"Access-Control-Allow-Origin": "*"})
            return web.json_response({"ok": False, "error": "No handler"}, status=400)
        except Exception as e:
            return web.json_response({"ok": False, "error": str(e)}, status=500)

    async def api_join_channel(request):
        try:
            channel = request.query.get("channel", "epic_gift_official")
            if hasattr(game_bot, "join_telegram_channel"):
                res = await game_bot.join_telegram_channel(channel)
                return web.json_response(res, headers={"Access-Control-Allow-Origin": "*"})
            return web.json_response({"ok": False, "error": "No handler"}, status=400)
        except Exception as e:
            return web.json_response({"ok": False, "error": str(e)}, status=500)

    async def api_refresh_mrkt(request):
        try:
            if hasattr(game_bot, "get_mrkt_webapp_token"):
                tok = await game_bot.get_mrkt_webapp_token()
                if tok:
                    return web.json_response({"ok": True, "token": tok}, headers={"Access-Control-Allow-Origin": "*"})
                return web.json_response({"ok": False, "error": "MRKT Token olinmadi"}, status=500)
            return web.json_response({"ok": False, "error": "No handler"}, status=400)
        except Exception as e:
            return web.json_response({"ok": False, "error": str(e)}, status=500)

    async def api_leave_channels(request):
        try:
            channels_param = request.query.get("channels", "")
            ch_list = [c.strip() for c in channels_param.split(",") if c.strip()]
            if hasattr(game_bot, "leave_telegram_channels"):
                res = await game_bot.leave_telegram_channels(ch_list)
                return web.json_response(res, headers={"Access-Control-Allow-Origin": "*"})
            return web.json_response({"ok": False, "error": "No handler"}, status=400)
        except Exception as e:
            return web.json_response({"ok": False, "error": str(e)}, status=500)

    async def api_control_status(request):
        try:
            in_match = getattr(game_bot, "in_match", False)
            soft_stop = getattr(game_bot, "soft_stop", False)
            is_enabled = True
            stats_dict = {}
            if hasattr(game_bot, "bot") and game_bot.bot:
                is_enabled = getattr(game_bot.bot, "is_enabled", True)
                in_match = getattr(game_bot.bot, "in_match", False)
                soft_stop = getattr(game_bot.bot, "soft_stop", False)
                if hasattr(game_bot.bot, "stats_mgr") and game_bot.bot.stats_mgr:
                    stats_dict = game_bot.bot.stats_mgr.stats
            elif hasattr(game_bot, "stats_mgr") and game_bot.stats_mgr:
                is_enabled = game_bot.stats_mgr.stats.get("is_enabled", True)
                stats_dict = game_bot.stats_mgr.stats
            return web.json_response({
                "ok": True,
                "is_enabled": is_enabled,
                "in_match": in_match,
                "soft_stop": soft_stop,
                "stake_mode": stats_dict.get("stake_mode", "auto"),
                "manual_stake": stats_dict.get("manual_stake"),
                "current_stake": stats_dict.get("current_stake", 3),
                "stats": stats_dict
            }, headers={"Access-Control-Allow-Origin": "*"})
        except Exception as e:
            return web.json_response({"ok": False, "error": str(e)}, status=500)

    async def api_control_stake(request):
        try:
            stake_val = request.query.get("stake") or request.query.get("mode")
            if not stake_val and request.can_read_body:
                try:
                    data = await request.json()
                    stake_val = data.get("stake") or data.get("mode")
                except Exception:
                    pass
            if not stake_val:
                return web.json_response({"ok": False, "error": "Missing stake parameter"}, status=400)

            stats_obj = getattr(game_bot, "stats_mgr", None)
            if hasattr(game_bot, "bot") and getattr(game_bot.bot, "stats_mgr", None):
                stats_obj = game_bot.bot.stats_mgr

            stake_str = str(stake_val).lower().strip()
            if stake_str in ("auto", "avto", "0"):
                if stats_obj:
                    stats_obj.stats["stake_mode"] = "auto"
                    stats_obj.stats["manual_stake"] = None
                    stats_obj.save()
                return web.json_response({"ok": True, "stake_mode": "auto", "manual_stake": None}, headers={"Access-Control-Allow-Origin": "*"})
            else:
                val = int(stake_str)
                if stats_obj:
                    stats_obj.stats["stake_mode"] = "manual"
                    stats_obj.stats["manual_stake"] = val
                    stats_obj.stats["current_stake"] = val
                    stats_obj.save()
                return web.json_response({"ok": True, "stake_mode": "manual", "manual_stake": val}, headers={"Access-Control-Allow-Origin": "*"})
        except Exception as e:
            return web.json_response({"ok": False, "error": str(e)}, status=500)

    async def api_control_on(request):
        try:
            if hasattr(game_bot, "turn_on"):
                msg = await game_bot.turn_on()
                return web.json_response({"ok": True, "message": msg}, headers={"Access-Control-Allow-Origin": "*"})
            return web.json_response({"ok": False, "error": "No turn_on method"}, status=400)
        except Exception as e:
            return web.json_response({"ok": False, "error": str(e)}, status=500)

    async def api_control_off(request):
        try:
            in_match = getattr(game_bot, "in_match", False)
            if hasattr(game_bot, "bot") and game_bot.bot:
                in_match = getattr(game_bot.bot, "in_match", False)
            if in_match and hasattr(game_bot, "soft_turn_off"):
                msg = await game_bot.soft_turn_off()
                return web.json_response({"ok": True, "soft_stop": True, "message": msg}, headers={"Access-Control-Allow-Origin": "*"})
            elif hasattr(game_bot, "turn_off"):
                msg = await game_bot.turn_off(force=False)
                return web.json_response({"ok": True, "soft_stop": False, "message": msg}, headers={"Access-Control-Allow-Origin": "*"})
            return web.json_response({"ok": False, "error": "No turn_off method"}, status=400)
        except Exception as e:
            return web.json_response({"ok": False, "error": str(e)}, status=500)

    async def api_healthz(request):
        return web.Response(text="OK", content_type="text/plain", headers={"Access-Control-Allow-Origin": "*"})

    async def api_runner_logs(request):
        try:
            log_file = "/tmp/runner.log"
            if not os.path.exists(log_file):
                return web.Response(text="No logs found yet.", content_type="text/plain", charset="utf-8")
            with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
            tail = "".join(lines[-250:])
            return web.Response(text=tail, content_type="text/plain", charset="utf-8")
        except Exception as e:
            return web.Response(text=f"Log read error: {e}", status=500)

    app.router.add_get("/", handle_index)
    app.router.add_get("/healthz", api_healthz)
    app.router.add_get("/ping", api_healthz)
    app.router.add_get("/api/runner_logs", api_runner_logs)
    app.router.add_get("/api/live", api_live)
    app.router.add_get("/api/stream", api_stream)
    app.router.add_get("/api/refresh_epic_token", api_refresh_epic)
    app.router.add_get("/api/refresh_mrkt_token", api_refresh_mrkt)
    app.router.add_get("/api/join_channel", api_join_channel)
    app.router.add_get("/api/leave_channels", api_leave_channels)
    app.router.add_get("/api/control/status", api_control_status)
    app.router.add_get("/api/control/stake", api_control_stake)
    app.router.add_post("/api/control/stake", api_control_stake)
    app.router.add_get("/api/control/on", api_control_on)
    app.router.add_post("/api/control/on", api_control_on)
    app.router.add_get("/api/control/off", api_control_off)
    app.router.add_post("/api/control/off", api_control_off)
    app.router.add_get("/api/muxa_messages", api_muxa_messages)
    app.router.add_get("/api/scrape_bot", api_scrape_bot)
    app.router.add_get("/api/copy_profile", api_copy_profile)
    app.router.add_get("/download/server.zip", download_server_zip)

    # UzbStarsBuy WebApp & API integratsiyasi
    uzb_dir = os.path.join(BASE_DIR, "uzstarsbuy")
    if os.path.exists(uzb_dir):
        import sys
        if uzb_dir not in sys.path:
            sys.path.insert(0, uzb_dir)
        try:
            from uzstarsbuy import web_server as uzb_ws

            # API endpointlari
            for p in ["/uzbstar/check_subscription.php", "/check_subscription.php", "/api/check_subscription"]:
                app.router.add_get(p, uzb_ws.handle_check_subscription)
                app.router.add_post(p, uzb_ws.handle_check_subscription)

            for p in ["/uzbstar/settings.php", "/settings.php", "/api/settings"]:
                app.router.add_get(p, uzb_ws.handle_settings)
                app.router.add_post(p, uzb_ws.handle_settings)

            # Mini App frontend (/stars)
            async def handle_stars_app(request):
                idx = os.path.join(uzb_dir, "web_app", "index.html")
                if os.path.exists(idx):
                    return web.FileResponse(idx)
                return web.Response(text="Stars WebApp not found", status=404)

            app.router.add_get("/stars", handle_stars_app)
            app.router.add_get("/stars/", handle_stars_app)

            assets_dir = os.path.join(uzb_dir, "web_app", "assets")
            if os.path.exists(assets_dir):
                app.router.add_static("/assets", assets_dir)

            for prefix in ["/uzbstar/{subpath:.*}", "/starsapi/{subpath:.*}", "/StarsBot/{subpath:.*}"]:
                app.router.add_route("*", prefix, uzb_ws.handle_proxy)

            print("[WEB SERVER] ⭐️ UzbStarsBuy Mini App yo'nalishlari ulandi (/stars)!")
        except Exception as uzb_err:
            print(f"[WEB SERVER WARNING] UzbStarsBuy ulanishida xato: {uzb_err}")

    return app

async def start_web_server(game_bot, host="127.0.0.1", port=8765):
    app = create_web_app(game_bot)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    print(f"[WEB SERVER] 🚀 Jonli shashka veb-vizualizatori ishga tushdi: http://{host}:{port}")
    return runner
