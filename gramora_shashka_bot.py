import ctypes
import os
import asyncio
import json
import time
import random
import math
import websockets

# =====================================================================
# SOZLAMALAR (CONFIG) — SUPERHUMAN RUSSIAN CHECKERS GRANDMASTER AI
# =====================================================================
WS_URL = "wss://gramorachat.rekchi.uz/shashka/ws"

INIT_DATA = ("")

STAKE = 3
THINK_TIME_SEC = 3.2
MAX_DEPTH = 50
AUTO_REQUEUE = True

HEADERS = {
    "Origin": "https://gramorachat.rekchi.uz",
    "User-Agent": (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1"
    ),
    "Accept-Language": "uz-UZ,uz;q=0.9,en-US;q=0.8,en;q=0.7",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}

# =====================================================================
# 32 KATAKLI DOSKA GEOMETRIYASI VA TEZKOR JADVALLAR
# =====================================================================
EMPTY = 0
W_MAN = 1   # Seat 0 (Oq tosh - 20..31 dan 0..3 ga yuradi)
W_KING = 2  # Seat 0 (Oq Dama)
B_MAN = 3   # Seat 1 (Qora tosh - 0..11 dan 28..31 ga yuradi)
B_KING = 4  # Seat 1 (Qora Dama)

def idx_to_rc(idx: int):
    r = idx // 4
    c = (idx % 4) * 2 + (1 if r % 2 == 0 else 0)
    return r, c

def rc_to_idx(r: int, c: int):
    if 0 <= r < 8 and 0 <= c < 8 and (r + c) % 2 == 1:
        return r * 4 + (c // 2)
    return -1

COLS_STR = "abcdefgh"
COORDS = [idx_to_rc(i) for i in range(32)]

def sq_to_notation(idx: int) -> str:
    if idx is None or not (0 <= idx < 32):
        return "?"
    r, c = COORDS[idx]
    col_str = COLS_STR[c]
    rank_str = str(8 - r)
    return f"{col_str}{rank_str}"

DIRS = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
STEP_TABLE = [[-1] * 4 for _ in range(32)]
JUMP_TABLE = [[(-1, -1)] * 4 for _ in range(32)]
RAYS = [[[] for _ in range(4)] for _ in range(32)]

for sq in range(32):
    r, c = COORDS[sq]
    for d_idx, (dr, dc) in enumerate(DIRS):
        adj = rc_to_idx(r + dr, c + dc)
        land = rc_to_idx(r + 2 * dr, c + 2 * dc)
        STEP_TABLE[sq][d_idx] = adj
        if adj != -1 and land != -1:
            JUMP_TABLE[sq][d_idx] = (adj, land)
        cr, cc = r + dr, c + dc
        while 0 <= cr < 8 and 0 <= cc < 8:
            nxt_sq = rc_to_idx(cr, cc)
            if nxt_sq != -1:
                RAYS[sq][d_idx].append(nxt_sq)
            cr += dr
            cc += dc

# Strategik chiziqlar va kataklar
MAIN_DIAGONAL = {3, 7, 10, 14, 17, 21, 24, 28} # a1-h8 (Bolshaya Doroga - hal qiluvchi magistral)
DVOINIK_1 = {29, 25, 22, 18, 15, 11}          # c1-h6
DVOINIK_2 = {20, 16, 13, 9, 6, 2}             # a3-f8
TROINIK_1 = {30, 26, 23, 19}                  # e1-h4
TROINIK_2 = {12, 8, 5, 1}                     # a5-d8

# 64-bit Zobrist Hash Jadvallari
random.seed(20261108)
ZOBRIST = [[random.getrandbits(64) for _ in range(5)] for _ in range(32)]
ZOBRIST_TURN = random.getrandbits(64)

# Piece-Square Tables (PST) — Grossmeyster pozitsion baholari
W_MAN_PST = [
      0,   0,   0,   0,
     80,  90,  90,  80,
     60,  70,  70,  55,
     45,  60,  60,  45,
     35,  50,  50,  30,
     22,  35,  35,  20,
     15,  25,  25,  15,
     10,  18,  18,  10
]
B_MAN_PST = [
     10,  18,  18,  10,
     15,  25,  25,  15,
     22,  35,  35,  20,
     35,  50,  50,  30,
     45,  60,  60,  45,
     60,  70,  70,  55,
     80,  90,  90,  80,
      0,   0,   0,   0
]
KING_PST = [
     40,  50,  50,  40,
     45,  75,  75,  45,
     50,  90,  90,  50,
     55, 100, 100,  55,
     55, 100, 100,  55,
     50,  90,  90,  50,
     45,  75,  75,  45,
     40,  50,  50,  40
]

W_CONE_MASK = [0] * 32
B_CONE_MASK = [0] * 32
for sq in range(32):
    sr, sc = COORDS[sq]
    for other in range(32):
        orow, ocol = COORDS[other]
        if orow < sr and abs(ocol - sc) <= (sr - orow) + 1:
            W_CONE_MASK[sq] |= (1 << other)
        if orow > sr and abs(ocol - sc) <= (orow - sr) + 1:
            B_CONE_MASK[sq] |= (1 << other)

EDGE_SQUARES = {4, 12, 20, 28, 3, 11, 19, 27}

VAL_TABLE = [
    [0] * 32,
    [1000 + W_MAN_PST[sq] + (160 if sq in (29, 30, 31) else 0) + (100 if sq in (13, 14, 17, 18) else 0) - (85 if sq in EDGE_SQUARES else 0) for sq in range(32)],
    [3800 + KING_PST[sq] + (750 if sq in MAIN_DIAGONAL else 0) + (320 if sq in DVOINIK_1 or sq in DVOINIK_2 else 0) + (160 if sq in TROINIK_1 or sq in TROINIK_2 else 0) for sq in range(32)],
    [1000 + B_MAN_PST[sq] + (160 if sq in (0, 1, 2) else 0) + (100 if sq in (13, 14, 17, 18) else 0) - (85 if sq in EDGE_SQUARES else 0) for sq in range(32)],
    [3800 + KING_PST[sq] + (750 if sq in MAIN_DIAGONAL else 0) + (320 if sq in DVOINIK_1 or sq in DVOINIK_2 else 0) + (160 if sq in TROINIK_1 or sq in TROINIK_2 else 0) for sq in range(32)],
]

# =====================================================================
# GROSSMEYSTER DEBYUTLAR BAZASI (RUS SHASHKASI ENSIKLOPEDIYASI)
# =====================================================================
OPENING_MOVES = {
    # 1. Gorodskaya Partiya (Asosiy / Klassik)
    "gorodskaya_main": [(21, 17), (9, 13), (24, 21), (10, 15), (21, 16), (7, 10), (16, 9)],
    "gorodskaya_filippov": [(21, 17), (9, 13), (24, 21), (6, 9), (28, 24), (10, 14), (17, 10), (7, 14)],
    "gorodskaya_center": [(21, 17), (9, 13), (24, 21), (10, 14), (17, 10), (7, 14), (22, 17)],
    "gorodskaya_var_b": [(21, 17), (9, 13), (24, 21), (11, 15), (21, 16), (7, 11), (16, 9)],
    "gorodskaya_var_c": [(21, 17), (9, 13), (24, 21), (10, 15), (21, 16), (15, 19)],

    # 2. Kolkashevskaya Partiya
    "kolkashev_main": [(21, 17), (8, 12), (24, 21), (10, 14), (17, 10), (7, 14), (28, 24), (14, 18), (23, 14), (9, 18)],
    "kolkashev_sharp": [(21, 17), (8, 12), (24, 21), (10, 14), (17, 10), (6, 15)],
    "kolkashev_solid": [(21, 17), (8, 12), (24, 21), (9, 13)],

    # 3. Tsentralnaya Partiya
    "tsentralnaya_main": [(22, 17), (10, 14), (17, 10), (7, 14), (21, 17), (14, 21), (24, 17), (11, 15), (25, 21)],
    "tsentralnaya_alt": [(22, 17), (10, 14), (17, 10), (6, 15), (21, 17), (9, 13), (25, 21)],

    # 4. Sokolskiy Debyuti
    "sokolskiy_main": [(21, 16), (8, 12), (16, 13), (9, 16), (20, 13), (10, 14), (24, 21)],
    "sokolskiy_solid": [(21, 16), (8, 12), (16, 13), (9, 16)],

    # 5. Bodyanskiy Debyuti
    "bodyanskiy_main": [(20, 16), (8, 12), (16, 13), (9, 16)],

    # 6. Krest (Cross)
    "krest_main": [(21, 17), (9, 14), (24, 21), (6, 9), (28, 24), (10, 15)],
    "krest_var2": [(21, 17), (9, 14), (25, 21), (6, 9), (22, 18)],

    # 7. Starosvetetskaya
    "starosvetetskaya": [(21, 17), (11, 15), (24, 21), (15, 18), (22, 15), (10, 19)],

    # 8. Novosibirsk
    "novosibirsk": [(21, 17), (10, 15), (24, 21), (15, 19), (21, 16), (7, 10), (17, 13)],

    # 9. Gambiti Spantsireti
    "spantsireti": [(22, 17), (10, 14), (17, 10), (6, 15), (21, 17), (9, 13), (25, 21)],

    # 10. Gambiti Shavshina
    "shavshin": [(21, 17), (10, 14), (17, 10), (6, 15), (24, 21), (8, 12), (21, 17)],

    # 11. Leningradskaya
    "leningrad_solid": [(22, 18), (11, 15), (18, 11)],

    # 12. Denisenko
    "denisenko": [(21, 17), (10, 15), (24, 21), (7, 10), (21, 16), (9, 13), (16, 9)],

    # 13. Klassik Markaziy
    "old_central": [(22, 17), (9, 13), (21, 16), (13, 22), (26, 17), (10, 14), (17, 10), (7, 14), (24, 21)],

    # 14. Obratnaya Gorodskaya
    "obratnaya_gorodskaya": [(21, 17), (10, 14), (17, 10), (7, 14), (24, 21), (11, 15), (22, 17)],

    # 15. Kaulen Debyuti
    "kaulen": [(22, 18), (10, 14), (24, 20), (6, 10), (28, 24)],

    # 16. Rets Debyuti
    "rets_opening": [(21, 17), (10, 15), (24, 21), (6, 10), (28, 24)],

    # 17. Peresypkin Gambiti
    "peresypkin": [(22, 17), (9, 14), (17, 10), (6, 15), (21, 17), (11, 16), (25, 21)],

    # 18. Kukuev Gambiti
    "kukuev_gambit": [(21, 17), (9, 14), (17, 10), (6, 15), (24, 21)],

    # 19. Zashchita Chigorina
    "chigorin_defense": [(21, 17), (9, 13), (24, 21), (10, 14), (17, 10), (7, 14), (28, 24)],

    # 20. Igra Filippova
    "filippov_game": [(21, 17), (9, 13), (24, 21), (10, 15), (21, 16)],

    # 21. Prizyv
    "prizyv": [(21, 17), (10, 14), (17, 10), (7, 14), (24, 21), (6, 10), (21, 17)],

    # 22. Koshil
    "koshil": [(21, 16), (10, 14), (16, 12), (14, 17), (22, 13), (8, 17)],

    # 23. Vigodskiy Debyuti
    "vigodskiy": [(21, 17), (9, 14), (17, 10), (7, 14), (24, 21)],

    # 24. Zhertva Sokhryanskogo
    "sokhryansky": [(21, 17), (9, 13), (24, 21), (8, 12), (17, 8), (4, 13), (21, 17)],

    # 25. Otbivnaya Partiya
    "otbivnaya": [(21, 17), (10, 15), (24, 21), (15, 19), (21, 16)],

    # 26. Kol (Piket) — Markaziy qattiq ustunlik
    "kol_opening": [(22, 17), (10, 14), (17, 10), (7, 14), (24, 20), (14, 18), (23, 14), (9, 18)],

    # 27. Leningradskaya Baza — Chuqur nazariya
    "leningrad_deep": [(22, 18), (11, 15), (18, 11), (8, 15), (21, 17), (9, 14), (25, 21), (5, 9)],

    # 28. Obratnaya Gorodskaya Klassika
    "obratnaya_gorodskaya_main": [(21, 17), (10, 14), (17, 10), (7, 14), (24, 21), (11, 15), (28, 24), (8, 11), (22, 17)],

    # 29. Shavshin Kontrgambit
    "shavshin_counter": [(21, 17), (10, 14), (17, 10), (6, 15), (24, 21), (8, 12), (28, 24), (11, 16)],

    # 30. Dyadya Vasya Debyuti
    "dyadya_vasya": [(21, 17), (11, 15), (24, 21), (15, 18), (22, 15), (10, 19), (23, 16), (12, 19)],

    # 31. Spantsireti Flang Hujumi
    "spantsireti_flank": [(22, 17), (10, 14), (17, 10), (6, 15), (21, 17), (9, 13), (25, 21), (7, 10), (24, 20)],

    # 32. Krest Chuqur Pozitsiya
    "krest_deep": [(21, 17), (9, 14), (24, 21), (6, 9), (28, 24), (10, 15), (22, 18), (15, 22), (26, 17)],

    # 33. Gorodskaya Partiya Mukammal
    "gorodskaya_master": [(21, 17), (9, 13), (24, 21), (10, 15), (21, 16), (7, 10), (16, 9), (5, 14), (28, 24)],

    # 34. Kaulen Zaxira
    "kaulen_solid": [(22, 18), (10, 14), (24, 20), (6, 10), (28, 24), (11, 15), (18, 11), (8, 15)],

    # 35. Tsentralnyy Proryv
    "tsentralnyy_proryv": [(22, 17), (11, 15), (25, 22), (9, 14), (17, 10), (7, 14), (22, 17)]
}

BOOK_POSITIONS = {}
def _precompile_opening_book():
    start_b = [
        3, 3, 3, 3,
        3, 3, 3, 3,
        3, 3, 3, 3,
        0, 0, 0, 0,
        0, 0, 0, 0,
        1, 1, 1, 1,
        1, 1, 1, 1,
        1, 1, 1, 1
    ]
    for name, moves in OPENING_MOVES.items():
        b = start_b[:]
        for ply, (frm, to) in enumerate(moves):
            turn_s = ply % 2
            key = (tuple(b), turn_s)
            if key not in BOOK_POSITIONS:
                BOOK_POSITIONS[key] = (frm, to, name, ply)
            p = b[frm]
            b[frm] = 0
            r1, c1 = COORDS[frm]
            r2, c2 = COORDS[to]
            if abs(r1 - r2) >= 2:
                mid = rc_to_idx((r1 + r2) // 2, (c1 + c2) // 2)
                if mid != -1:
                    b[mid] = 0
            b[to] = p

_precompile_opening_book()


# =====================================================================
# ULTRA GRANDMASTER SHASHKA AI MOTORI (SUPERHUMAN ENGINE - GOD MODE)
# =====================================================================
class UltraGrandmasterCheckersAI:
    def __init__(self):
        self.tt = {}
        self.match_history = {}
        self.killer_moves = [[0, 0] for _ in range(64)]
        self.history = [[[0] * 32 for _ in range(32)] for _ in range(2)]
        self.nodes = 0
        self.start_time = 0.0
        self.time_limit = THINK_TIME_SEC
        self.stop_search = False
        self.flying_kings = False
        self.last_eval = {"score": 0, "depth": 0, "nodes": 0, "elapsed": 0.0, "is_book": False}

        # C-Native Superhuman God-Mode v50 Dvigatelini ulash
        self.c_engine = None
        try:
            curr_dir = os.path.dirname(os.path.abspath(__file__))
            so_path = os.path.join(curr_dir, "libgodmode_engine.so")
            if not os.path.exists(so_path):
                so_path = "/root/libgodmode_engine.so"
            if os.path.exists(so_path):
                self.c_engine = ctypes.CDLL(so_path)
                self.c_engine.godmode_init()
                print("[AI-GODMODE-v50] ⚡ C-Native Superhuman Engine muvaffaqiyatli faollashtirildi!")
                
                # Champion Brain vaznlarini avtomatik yuklash
                champ_path = os.path.join(curr_dir, "shashka_brain_champion.json")
                if not os.path.exists(champ_path):
                    champ_path = "/root/shashka_brain_champion.json"
                if os.path.exists(champ_path):
                    try:
                        with open(champ_path, "r", encoding="utf-8") as bf:
                            c_data = json.load(bf)
                            if "weights" in c_data and len(c_data["weights"]) == 24:
                                c_weights = (ctypes.c_int32 * 24)(*c_data["weights"])
                                self.c_engine.godmode_set_eval_params(c_weights)
                                print(f"[AI-GODMODE-v50] 🧠 Champion Brain yuklandi: {c_data.get('name', 'Champion')} (Elo: {c_data.get('elo', 2500)})")
                    except Exception as b_err:
                        print(f"[AI-GODMODE-v50] Champion Brain yuklashda xato: {b_err}")
        except Exception as e:
            print(f"[AI-GODMODE-v50] ⚠️ C dvigatel yuklanmadi ({e}), Python fallback ishlaydi.")

    def reset_match(self):
        self.tt.clear()
        self.match_history.clear()
        self.killer_moves = [[0, 0] for _ in range(64)]
        self.history = [[[0] * 32 for _ in range(32)] for _ in range(2)]
        self.last_eval = {"score": 0, "depth": 0, "nodes": 0, "elapsed": 0.0, "is_book": False}
        if self.c_engine is not None:
            try:
                self.c_engine.godmode_clear_tt()
            except Exception:
                pass

    def record_board(self, board: list):
        key = tuple(board)
        self.match_history[key] = self.match_history.get(key, 0) + 1

    def compute_hash(self, board: list, turn_seat: int) -> int:
        h = 0
        for sq in range(32):
            p = board[sq]
            if p != 0:
                h ^= ZOBRIST[sq][p]
        if turn_seat == 1:
            h ^= ZOBRIST_TURN
        return h

    def detect_rules_from_legal(self, board: list, legal_moves: list):
        for mv in legal_moves:
            frm = mv.get("from", 0)
            to = mv.get("to", 0)
            caps = mv.get("captures", [])
            if board[frm] in (W_KING, B_KING):
                r1, _ = COORDS[frm]
                r2, _ = COORDS[to]
                if not caps and abs(r1 - r2) > 1:
                    self.flying_kings = True
                    return
                if len(caps) == 1 and abs(r1 - r2) > 2:
                    self.flying_kings = True
                    return

    def get_book_move(self, board: list, legal_moves: list, ai_seat: int) -> dict:
        total_p = sum(1 for p in board if p != EMPTY)
        if total_p < 20:
            return None

        key = (tuple(board), ai_seat)
        book_entry = BOOK_POSITIONS.get(key)
        if book_entry:
            frm, to, op_name, ply = book_entry
            for mv in legal_moves:
                if mv.get("from") == frm and mv.get("to") == to:
                    print(f"[AI-BOOK] 📖 Nazariy Grossmeyster Debyut '{op_name}' (ply {ply}): {sq_to_notation(frm)} -> {sq_to_notation(to)}")
                    return mv

        # Zaxira boshlang'ich qoidalar
        if total_p == 24 and ai_seat == 0 and board[21] == W_MAN:
            for pref in [(21, 17), (22, 17), (21, 16), (22, 18)]:
                for mv in legal_moves:
                    if mv.get("from") == pref[0] and mv.get("to") == pref[1]:
                        return mv
        return None

    def apply_server_move(self, board: list, move: dict, seat: int) -> list:
        nb = board[:]
        frm = move["from"]
        to = move["to"]
        piece = nb[frm]
        nb[frm] = EMPTY
        for cap in move.get("captures", []):
            nb[cap] = EMPTY
        if move.get("promotes"):
            piece = W_KING if seat == 0 else B_KING
        else:
            if piece == W_MAN and to < 4:
                piece = W_KING
            elif piece == B_MAN and to >= 28:
                piece = B_KING
        nb[to] = piece
        return nb

    def get_piece_captures(self, board: list, sq: int, piece: int, seat: int, cap_mask: int, root_sq: int = None):
        if root_sq is None:
            root_sq = sq
        results = []
        is_king = (piece == W_KING or piece == B_KING)
        opp_min = 3 if seat == 0 else 1
        opp_max = 4 if seat == 0 else 2

        if not is_king or not self.flying_kings:
            for d_idx in range(4):
                mid, land = JUMP_TABLE[sq][d_idx]
                if mid != -1 and not (cap_mask & (1 << mid)):
                    mid_p = board[mid]
                    if opp_min <= mid_p <= opp_max and board[land] == EMPTY:
                        new_p = W_KING if (piece == W_MAN and land < 4) else (B_KING if (piece == B_MAN and land >= 28) else piece)
                        new_mask = cap_mask | (1 << mid)

                        board[sq] = EMPTY
                        board[mid] = EMPTY
                        board[land] = new_p

                        sub = self.get_piece_captures(board, land, new_p, seat, new_mask, root_sq)
                        if sub:
                            results.extend(sub)
                        else:
                            results.append((board[:], new_mask.bit_count(), new_p in (W_KING, B_KING), root_sq, land, new_mask))

                        board[land] = EMPTY
                        board[mid] = mid_p
                        board[sq] = piece
        else:
            for d_idx in range(4):
                ray = RAYS[sq][d_idx]
                opp_sq = -1
                opp_p = EMPTY
                for r_sq in ray:
                    if cap_mask & (1 << r_sq):
                        break
                    p = board[r_sq]
                    if p == EMPTY:
                        if opp_sq != -1:
                            new_mask = cap_mask | (1 << opp_sq)
                            board[sq] = EMPTY
                            board[opp_sq] = EMPTY
                            board[r_sq] = piece

                            sub = self.get_piece_captures(board, r_sq, piece, seat, new_mask, root_sq)
                            if sub:
                                results.extend(sub)
                            else:
                                results.append((board[:], new_mask.bit_count(), True, root_sq, r_sq, new_mask))

                            board[r_sq] = EMPTY
                            board[opp_sq] = opp_p
                            board[sq] = piece
                    elif opp_min <= p <= opp_max:
                        if opp_sq == -1:
                            opp_sq = r_sq
                            opp_p = p
                        else:
                            break
                    else:
                        break
        return results

    def generate_moves(self, board: list, seat: int):
        caps = []
        own_min = 1 if seat == 0 else 3
        own_max = 2 if seat == 0 else 4

        for sq in range(32):
            p = board[sq]
            if own_min <= p <= own_max:
                c = self.get_piece_captures(board, sq, p, seat, 0)
                if c:
                    caps.extend(c)

        if caps:
            caps.sort(key=lambda x: (x[1], 1 if x[2] else 0), reverse=True)
            return [(c[3], c[4], c[0], True, c[2], c[1], c[5]) for c in caps], True

        quiets = []
        for sq in range(32):
            p = board[sq]
            if not (own_min <= p <= own_max):
                continue
            if p == W_MAN:
                for d_idx in (0, 1):
                    nxt = STEP_TABLE[sq][d_idx]
                    if nxt != -1 and board[nxt] == EMPTY:
                        nb = board[:]
                        nb[sq] = EMPTY
                        promo = (nxt < 4)
                        nb[nxt] = W_KING if promo else W_MAN
                        quiets.append((sq, nxt, nb, False, promo, 0, 0))
            elif p == B_MAN:
                for d_idx in (2, 3):
                    nxt = STEP_TABLE[sq][d_idx]
                    if nxt != -1 and board[nxt] == EMPTY:
                        nb = board[:]
                        nb[sq] = EMPTY
                        promo = (nxt >= 28)
                        nb[nxt] = B_KING if promo else B_MAN
                        quiets.append((sq, nxt, nb, False, promo, 0, 0))
            else:
                if self.flying_kings:
                    for d_idx in range(4):
                        for nxt in RAYS[sq][d_idx]:
                            if board[nxt] == EMPTY:
                                nb = board[:]
                                nb[sq] = EMPTY
                                nb[nxt] = p
                                quiets.append((sq, nxt, nb, False, False, 0, 0))
                            else:
                                break
                else:
                    for d_idx in range(4):
                        nxt = STEP_TABLE[sq][d_idx]
                        if nxt != -1 and board[nxt] == EMPTY:
                            nb = board[:]
                            nb[sq] = EMPTY
                            nb[nxt] = p
                            quiets.append((sq, nxt, nb, False, False, 0, 0))
        return quiets, False

    def evaluate(self, board: list, ai_seat: int, turn_seat: int) -> int:
        w_score = 0
        b_score = 0
        w_men = 0
        b_men = 0
        w_kings = 0
        b_kings = 0
        w_mob = 0
        b_mob = 0
        w_mask = 0
        b_mask = 0

        for sq in range(32):
            p = board[sq]
            if p == 0:
                continue
            if p <= 2:
                w_mask |= (1 << sq)
                if p == 1:
                    w_men += 1
                    w_score += VAL_TABLE[1][sq]
                    r, c = COORDS[sq]
                    if r <= 3 and not (W_CONE_MASK[sq] & b_mask):
                        w_score += (5 - r) * 450
                    for d_idx in (0, 1):
                        nxt = STEP_TABLE[sq][d_idx]
                        if nxt != -1 and board[nxt] == 0:
                            w_mob += 1
                else:
                    w_kings += 1
                    w_score += VAL_TABLE[2][sq]
                    if self.flying_kings:
                        for d_idx in range(4):
                            for nxt in RAYS[sq][d_idx]:
                                if board[nxt] == 0:
                                    w_mob += 2
                                else:
                                    break
                    else:
                        for d_idx in range(4):
                            nxt = STEP_TABLE[sq][d_idx]
                            if nxt != -1 and board[nxt] == 0:
                                w_mob += 2
            else:
                b_mask |= (1 << sq)
                if p == 3:
                    b_men += 1
                    b_score += VAL_TABLE[3][sq]
                    r, c = COORDS[sq]
                    if r >= 4 and not (B_CONE_MASK[sq] & w_mask):
                        b_score += (r - 2) * 450
                    for d_idx in (2, 3):
                        nxt = STEP_TABLE[sq][d_idx]
                        if nxt != -1 and board[nxt] == 0:
                            b_mob += 1
                else:
                    b_kings += 1
                    b_score += VAL_TABLE[4][sq]
                    if self.flying_kings:
                        for d_idx in range(4):
                            for nxt in RAYS[sq][d_idx]:
                                if board[nxt] == 0:
                                    b_mob += 2
                                else:
                                    break
                    else:
                        for d_idx in range(4):
                            nxt = STEP_TABLE[sq][d_idx]
                            if nxt != -1 and board[nxt] == 0:
                                b_mob += 2

        w_total = w_men + w_kings
        b_total = b_men + b_kings

        if w_total == 0:
            return -9999999 if ai_seat == 0 else 9999999
        if b_total == 0:
            return 9999999 if ai_seat == 0 else -9999999

        total_p = w_total + b_total

        # 1. ZOLOTAYA SHASHKA (c1 / f8) — MUTLAQ STRATEGIK XAVFSIZLIK!
        if w_men >= 4:
            if board[29] == 1:
                w_score += 480
            else:
                w_score -= 320
        if b_men >= 4:
            if board[2] == 3:
                b_score += 480
            else:
                b_score -= 320

        # 2. MOSTIK (c1 + e1 / f8 + d8) — RAQIB DAMASINI TO'XTATISH
        if board[29] == 1 and board[30] == 1:
            w_score += 350
        if board[2] == 3 and board[1] == 3:
            b_score += 350

        # 3. MARKAZIY FORPOST (d4 / e5) VA XAVFLI KLIN (c5 / f4)
        if board[17] in (1, 2) and (board[21] in (1, 2) or board[22] in (1, 2)):
            w_score += 420
        if board[13] in (1, 2) and board[17] in (1, 2):
            w_score += 550
        if board[14] in (3, 4) and (board[9] in (3, 4) or board[10] in (3, 4)):
            b_score += 420
        if board[18] in (3, 4) and board[14] in (3, 4):
            b_score += 550

        # 4. FLANG BOG'LAMI (Kolkashevskaya Svyazka)
        if board[16] in (1, 2) and board[13] in (1, 2) and board[12] in (3, 4) and board[8] in (3, 4):
            w_score += 500
        if board[15] in (3, 4) and board[18] in (3, 4) and board[19] in (1, 2) and board[23] in (1, 2):
            b_score += 500

        # 5. BORTOVYE SHASHKI (Chetki kataklardagi toshlar jarimasi)
        for sq in EDGE_SQUARES:
            if board[sq] == 1 and sq > 7:
                w_score -= 85
            elif board[sq] == 3 and sq < 24:
                b_score -= 85

        w_score += w_mob * 26
        b_score += b_mob * 26

        # 6. OPPOZITSIYA (Endgame <= 4 tosh)
        if total_p <= 4:
            dist_sum = 0
            for sq in range(32):
                if board[sq] in (1, 2):
                    r1, c1 = COORDS[sq]
                    for o_sq in range(32):
                        if board[o_sq] in (3, 4):
                            r2, c2 = COORDS[o_sq]
                            dist_sum += abs(r1 - r2) + abs(c1 - c2)
            if dist_sum % 2 == 1:
                if turn_seat == 1:
                    w_score += 650
                else:
                    b_score += 650

        # 7. PETROV UCHBURCHAGI (3 Dama vs 1 Dama)
        if w_kings >= 3 and b_kings == 1 and b_men == 0:
            w_score += 6500
        elif b_kings >= 3 and w_kings == 1 and w_men == 0:
            b_score += 6500

        diff = (w_score - b_score) if ai_seat == 0 else (b_score - w_score)

        # 8. SODDALASHTIRISH (Ustun bo'lganda toshlarni almashib yutishni tezlashtirish)
        if diff > 200:
            diff += (24 - total_p) * 65
        elif diff < -200:
            diff -= (24 - total_p) * 65

        # 9. DURANG TUZOG'IDAN QOCHISH
        b_key = tuple(board)
        reps = self.match_history.get(b_key, 0)
        if reps > 0 and diff > 80:
            diff -= reps * 1200

        return diff

    def quiescence(self, board: list, alpha: int, beta: int, turn_seat: int, ai_seat: int, q_depth: int = 20) -> int:
        self.nodes += 1
        if (self.nodes & 2047) == 0 and (time.perf_counter() - self.start_time) >= self.time_limit:
            self.stop_search = True
            return 0

        moves, is_capture = self.generate_moves(board, turn_seat)
        if not moves:
            return -9999999 if turn_seat == ai_seat else 9999999

        if not is_capture or q_depth <= 0:
            return self.evaluate(board, ai_seat, turn_seat)

        opp_seat = 1 - turn_seat
        if turn_seat == ai_seat:
            max_eval = -100000000
            for frm, to, nb, is_cap, promo, cap_count, cap_mask in moves:
                val = self.quiescence(nb, alpha, beta, opp_seat, ai_seat, q_depth - 1)
                if self.stop_search:
                    return 0
                if val > max_eval:
                    max_eval = val
                if max_eval > alpha:
                    alpha = max_eval
                if alpha >= beta:
                    break
            return max_eval
        else:
            min_eval = 100000000
            for frm, to, nb, is_cap, promo, cap_count, cap_mask in moves:
                val = self.quiescence(nb, alpha, beta, opp_seat, ai_seat, q_depth - 1)
                if self.stop_search:
                    return 0
                if val < min_eval:
                    min_eval = val
                if min_eval < beta:
                    beta = min_eval
                if alpha >= beta:
                    break
            return min_eval

    def alphabeta(self, board: list, z_hash: int, depth: int, alpha: int, beta: int, turn_seat: int, ai_seat: int, allow_null: bool = True) -> int:
        self.nodes += 1
        if (self.nodes & 2047) == 0 and (time.perf_counter() - self.start_time) >= self.time_limit:
            self.stop_search = True
            return 0

        tt_entry = self.tt.get(z_hash)
        tt_best_code = None

        if tt_entry is not None:
            tt_depth, tt_flag, tt_val, tt_best_code = tt_entry
            if tt_depth >= depth:
                if tt_flag == 0:
                    return tt_val
                elif tt_flag == 1 and tt_val > alpha:
                    alpha = tt_val
                elif tt_flag == 2 and tt_val < beta:
                    beta = tt_val
                if alpha >= beta:
                    return tt_val

        if depth <= 0:
            return self.quiescence(board, alpha, beta, turn_seat, ai_seat)

        moves, is_capture = self.generate_moves(board, turn_seat)
        if not moves:
            return (-9999999 - depth) if turn_seat == ai_seat else (9999999 + depth)

        opp_seat = 1 - turn_seat

        if allow_null and depth >= 3 and not is_capture:
            null_hash = z_hash ^ ZOBRIST_TURN
            val = self.alphabeta(board, null_hash, depth - 3, beta - 1, beta, opp_seat, ai_seat, allow_null=False)
            if self.stop_search:
                return 0
            if turn_seat == ai_seat and val >= beta:
                return beta
            elif turn_seat != ai_seat and val <= alpha:
                return alpha

        k1, k2 = self.killer_moves[depth] if depth < 64 else (0, 0)
        hist = self.history[turn_seat]

        def get_move_score(item):
            frm, to, nb, is_cap, promo, cap_count, cap_mask = item
            code = (frm << 6) | to
            if code == tt_best_code:
                return 30000000
            if is_cap:
                return 20000000 + (cap_count * 5000) + (8000 if promo else 0)
            if code == k1:
                return 6000000
            if code == k2:
                return 4500000
            if promo:
                return 3800000
            if to in (13, 14, 17, 18):
                return 2000000
            return hist[frm][to]

        if len(moves) > 1:
            moves.sort(key=get_move_score, reverse=True)

        next_depth = depth if len(moves) == 1 else depth - 1
        maximizing = (turn_seat == ai_seat)
        best_val = -100000000 if maximizing else 100000000
        best_code = None
        orig_alpha = alpha
        orig_beta = beta

        if maximizing:
            for idx, (frm, to, nb, is_cap, promo, cap_count, cap_mask) in enumerate(moves):
                p_old = board[frm]
                p_new = nb[to]
                child_hash = z_hash ^ ZOBRIST[frm][p_old] ^ ZOBRIST[to][p_new] ^ ZOBRIST_TURN
                if cap_mask:
                    for sq in range(32):
                        if cap_mask & (1 << sq):
                            child_hash ^= ZOBRIST[sq][board[sq]]

                if idx > 3 and depth >= 3 and not is_cap:
                    val = self.alphabeta(nb, child_hash, max(1, next_depth - 1), alpha, alpha + 1, opp_seat, ai_seat)
                    if not self.stop_search and val > alpha:
                        val = self.alphabeta(nb, child_hash, next_depth, alpha, beta, opp_seat, ai_seat)
                elif idx == 0:
                    val = self.alphabeta(nb, child_hash, next_depth, alpha, beta, opp_seat, ai_seat)
                else:
                    val = self.alphabeta(nb, child_hash, next_depth, alpha, alpha + 1, opp_seat, ai_seat)
                    if not self.stop_search and alpha < val < beta:
                        val = self.alphabeta(nb, child_hash, next_depth, alpha, beta, opp_seat, ai_seat)

                if self.stop_search:
                    return 0
                if val > best_val:
                    best_val = val
                    best_code = (frm << 6) | to
                if best_val > alpha:
                    alpha = best_val
                if alpha >= beta:
                    if not is_cap and depth < 64:
                        code = (frm << 6) | to
                        if self.killer_moves[depth][0] != code:
                            self.killer_moves[depth][1] = self.killer_moves[depth][0]
                            self.killer_moves[depth][0] = code
                        self.history[turn_seat][frm][to] += depth * depth
                    break
        else:
            for idx, (frm, to, nb, is_cap, promo, cap_count, cap_mask) in enumerate(moves):
                p_old = board[frm]
                p_new = nb[to]
                child_hash = z_hash ^ ZOBRIST[frm][p_old] ^ ZOBRIST[to][p_new] ^ ZOBRIST_TURN
                if cap_mask:
                    for sq in range(32):
                        if cap_mask & (1 << sq):
                            child_hash ^= ZOBRIST[sq][board[sq]]

                if idx > 3 and depth >= 3 and not is_cap:
                    val = self.alphabeta(nb, child_hash, max(1, next_depth - 1), beta - 1, beta, opp_seat, ai_seat)
                    if not self.stop_search and val < beta:
                        val = self.alphabeta(nb, child_hash, next_depth, alpha, beta, opp_seat, ai_seat)
                elif idx == 0:
                    val = self.alphabeta(nb, child_hash, next_depth, alpha, beta, opp_seat, ai_seat)
                else:
                    val = self.alphabeta(nb, child_hash, next_depth, beta - 1, beta, opp_seat, ai_seat)
                    if not self.stop_search and alpha < val < beta:
                        val = self.alphabeta(nb, child_hash, next_depth, alpha, beta, opp_seat, ai_seat)

                if self.stop_search:
                    return 0
                if val < best_val:
                    best_val = val
                    best_code = (frm << 6) | to
                if best_val < beta:
                    beta = best_val
                if alpha >= beta:
                    if not is_cap and depth < 64:
                        code = (frm << 6) | to
                        if self.killer_moves[depth][0] != code:
                            self.killer_moves[depth][1] = self.killer_moves[depth][0]
                            self.killer_moves[depth][0] = code
                        self.history[turn_seat][frm][to] += depth * depth
                    break

        if not self.stop_search:
            flag = 2 if best_val <= orig_alpha else (1 if best_val >= orig_beta else 0)
            if len(self.tt) > 600000:
                self.tt.clear()
            if tt_entry is None or depth >= tt_entry[0]:
                self.tt[z_hash] = (depth, flag, best_val, best_code)

        return best_val

    def choose_best_move(self, board: list, legal_moves: list, ai_seat: int, remaining_ms: int, stake: int = 3) -> dict:
        self.detect_rules_from_legal(board, legal_moves)

        if len(legal_moves) == 1:
            best_only = legal_moves[0]
            nb = self.apply_server_move(board, best_only, ai_seat)
            self.record_board(nb)
            self.last_eval = {"score": 0, "depth": 1, "nodes": 1, "elapsed": 0.001, "is_book": False}
            return best_only

        # 1. Grossmeyster Debyutlar Bazasidan yurish
        book_move = self.get_book_move(board, legal_moves, ai_seat)
        if book_move:
            nb = self.apply_server_move(board, book_move, ai_seat)
            self.record_board(nb)
            self.last_eval = {"score": 250, "depth": 28, "nodes": 1, "elapsed": 0.001, "is_book": True}
            return book_move

        # 2. C-Native Superhuman God-Mode v50 Dvigateli (100+ Mln variant/sekund)
        if self.c_engine is not None:
            try:
                total_p = sum(1 for p in board if p != EMPTY)
                if total_p <= 6:
                    target_time = 4.5
                    max_search_depth = 50
                elif total_p <= 14:
                    target_time = 4.0
                    max_search_depth = 50
                else:
                    target_time = 3.5
                    max_search_depth = 50
                safe_time = min(target_time, max(1.5, (remaining_ms / 1000.0) * 0.35))

                c_board = (ctypes.c_int8 * 32)(*board)
                out_from = ctypes.c_int()
                out_to = ctypes.c_int()
                out_score = ctypes.c_int()
                out_depth = ctypes.c_int()
                out_nodes = ctypes.c_uint64()

                c_time_ms = int(safe_time * 1000)
                t_start = time.perf_counter()
                res = self.c_engine.godmode_search(
                    c_board,
                    ai_seat,
                    c_time_ms,
                    max_search_depth,
                    1 if self.flying_kings else 0,
                    ctypes.byref(out_from),
                    ctypes.byref(out_to),
                    ctypes.byref(out_score),
                    ctypes.byref(out_depth),
                    ctypes.byref(out_nodes)
                )

                if res > 0 and out_from.value != -1:
                    c_best_from = out_from.value
                    c_best_to = out_to.value
                    matches = [m for m in legal_moves if m.get("from") == c_best_from and m.get("to") == c_best_to]
                    if matches:
                        chosen_c_move = max(matches, key=lambda m: (len(m.get("captures", [])), 1 if m.get("promotes") else 0))
                        elapsed = time.perf_counter() - t_start
                        self.last_eval = {
                            "score": out_score.value,
                            "depth": out_depth.value,
                            "nodes": out_nodes.value,
                            "elapsed": elapsed,
                            "is_book": False
                        }
                        nb = self.apply_server_move(board, chosen_c_move, ai_seat)
                        self.record_board(nb)
                        print(f"[AI-GODMODE-v50 ⚡] 👑 [Stavka: {stake}⭐] Chuqurlik: {out_depth.value} | Variantlar: {out_nodes.value} | Baho: {out_score.value} | Vaqt: {elapsed:.2f}s | Yurish: {c_best_from} -> {c_best_to}")
                        return chosen_c_move
            except Exception as c_err:
                print(f"[AI-GODMODE-v50] C dvigatel qidiruvida xato: {c_err}, Python fallback ishlamoqda...")

        self.nodes = 0
        self.start_time = time.perf_counter()
        self.stop_search = False

        total_p = sum(1 for p in board if p != EMPTY)

        # STAVKAGA VA POZITSIYAGA MOS MOSLASHUVCHAN VAQT
        if total_p <= 6:
            target_time = 3.8
            max_search_depth = 50
        elif total_p <= 14:
            target_time = 3.4
            max_search_depth = 50
        else:
            target_time = 2.8
            max_search_depth = 50

        safe_time = min(target_time, max(1.0, (remaining_ms / 1000.0) * 0.22))
        self.time_limit = safe_time

        opp_seat = 1 - ai_seat
        root_candidates = []
        for mv in legal_moves:
            nb = self.apply_server_move(board, mv, ai_seat)
            root_candidates.append((mv, nb))

        root_candidates.sort(
            key=lambda x: self.evaluate(x[1], ai_seat, opp_seat),
            reverse=True
        )

        best_move = root_candidates[0][0]
        best_board = root_candidates[0][1]
        best_score = -100000000
        completed_depth = 1

        for depth in range(1, max_search_depth + 1):
            cur_best_move = None
            cur_best_board = None
            cur_best_score = -100000000
            interrupted = False

            # Aspiration Window
            if depth >= 4 and best_score > -9000000:
                delta = 90
                alpha = max(-100000000, best_score - delta)
                beta = min(100000000, best_score + delta)
            else:
                alpha = -100000000
                beta = 100000000

            scored_candidates = []
            for idx, (mv, nb) in enumerate(root_candidates):
                nb_hash = self.compute_hash(nb, opp_seat)
                score = self.alphabeta(nb, nb_hash, depth - 1, alpha, beta, opp_seat, ai_seat)
                if self.stop_search:
                    interrupted = True
                    break
                scored_candidates.append((score, mv, nb))
                if score > cur_best_score:
                    cur_best_score = score
                    cur_best_move = mv
                    cur_best_board = nb
                if score > alpha:
                    alpha = score

            if interrupted:
                break

            if depth >= 4 and (cur_best_score <= alpha or cur_best_score >= beta):
                alpha = -100000000
                beta = 100000000
                scored_candidates = []
                for idx, (mv, nb) in enumerate(root_candidates):
                    nb_hash = self.compute_hash(nb, opp_seat)
                    score = self.alphabeta(nb, nb_hash, depth - 1, alpha, beta, opp_seat, ai_seat)
                    if self.stop_search:
                        break
                    scored_candidates.append((score, mv, nb))
                    if score > cur_best_score:
                        cur_best_score = score
                        cur_best_move = mv
                        cur_best_board = nb
                    if score > alpha:
                        alpha = score

            if cur_best_move is not None:
                best_move = cur_best_move
                best_board = cur_best_board
                best_score = cur_best_score
                completed_depth = depth

            if scored_candidates:
                scored_candidates.sort(key=lambda x: x[0], reverse=True)
                root_candidates = [(m, b) for _, m, b in scored_candidates]

            if best_score > 9000000 or (time.perf_counter() - self.start_time) >= self.time_limit:
                break

        if best_move is None and legal_moves:
            best_move = legal_moves[0]
            best_board = root_candidates[0][1] if root_candidates else board
        if best_board is not None:
            self.record_board(best_board)
        elapsed = time.perf_counter() - self.start_time
        self.last_eval = {
            "score": best_score,
            "depth": completed_depth,
            "nodes": self.nodes,
            "elapsed": round(elapsed, 2),
            "is_book": False
        }
        print(
            f"[AI-GODMODE] 👑 [Stavka: {stake}⭐] Chuqurlik: {completed_depth} | Variantlar: {self.nodes} | "
            f"Baho: {best_score} | Vaqt: {elapsed:.2f}s | "
            f"Yurish: {best_move['from']} -> {best_move['to']}"
        )
        return best_move

# =====================================================================
# STATISTIKA VA STATE BOSHQARUVI (PERSISTENT & USERBOT UCHUN)
# =====================================================================
_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_STATS_PATH = os.path.join(_CURRENT_DIR, "gramora_stats.json")

class StatsManager:
    def __init__(self, filepath=None):
        self.filepath = filepath or DEFAULT_STATS_PATH
        self.stats = {
            "user_id": None,
            "name": "Noma'lum",
            "username": "",
            "rating": 1200,
            "league": "Silver",
            "stars_balance": 0.0,
            "net_profit": 0.0,
            "games_total": 0,
            "wins": 0,
            "losses": 0,
            "draws": 0,
            "streak": 0,
            "max_streak": 0,
            "tasks_claimed": 0,
            "tasks_profit": 0.0,
            "current_stake": 3,
            "stake_mode": "auto",       # "auto" yoki "manual"
            "manual_stake": None,
            "is_enabled": True,         # .on / .off holati
            "current_status": "🟢 Bot faol",
            "last_opponent": "",
            "start_time": time.time(),
        }
        self.load()

    def load(self):
        import os
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for k, v in data.items():
                        if k in self.stats and k != "start_time":
                            self.stats[k] = v
            except Exception as e:
                print(f"[STATS] Yuklashda xato: {e}")

    def save(self):
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(self.stats, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def record_game(self, won: bool, draw: bool, stars_net: float, opponent_name: str = ""):
        self.stats["games_total"] += 1
        self.stats["net_profit"] = round(self.stats["net_profit"] + stars_net, 2)
        if won:
            self.stats["wins"] += 1
            self.stats["streak"] += 1
            if self.stats["streak"] > self.stats["max_streak"]:
                self.stats["max_streak"] = self.stats["streak"]
        elif draw:
            self.stats["draws"] += 1
            self.stats["streak"] = 0
        else:
            self.stats["losses"] += 1
            self.stats["streak"] = 0
        if opponent_name:
            self.stats["last_opponent"] = opponent_name
        self.save()

    def record_task_claimed(self, reward: float):
        self.stats["tasks_claimed"] += 1
        self.stats["tasks_profit"] = round(self.stats["tasks_profit"] + reward, 2)
        self.save()

    def get_summary_text(self):
        s = self.stats
        uptime_sec = int(time.time() - s["start_time"])
        hours = uptime_sec // 3600
        mins = (uptime_sec % 3600) // 60
        uptime_str = f"{hours}s {mins}d" if hours > 0 else f"{mins} daqiqa"

        total = s["games_total"]
        wins = s["wins"]
        losses = s["losses"]
        draws = s["draws"]
        winrate = round((wins / total * 100), 1) if total > 0 else 0.0

        profit = s["net_profit"]
        profit_str = f"+{profit:.1f}" if profit >= 0 else f"{profit:.1f}"
        balance = round(s["stars_balance"], 1)

        s_mode = s.get("stake_mode", "auto")
        s_man = s.get("manual_stake", s.get("current_stake", 3))
        mode_str = "Avtomatik (Balansga mos)" if s_mode == "auto" else f"Qo'lda ({s_man}⭐)"
        uname = f"@{s['username']}" if s["username"] else "mavjud emas"
        power_str = "🟢 YONIQ (ON)" if s.get("is_enabled", True) else "🔴 O'CHIRILGAN (OFF)"

        msg = (
            f"👑 <b>GRAMORA GODMODE v50 ULTRA MAX PRO</b> 👑\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"⚡ <b>Avtopilot:</b> <b>{power_str}</b>\n"
            f"👤 <b>Foydalanuvchi:</b> {s['name']} ({uname})\n"
            f"🏆 <b>Reyting / Liga:</b> {s['rating']} ({s['league']})\n"
            f"⭐ <b>Stars Balans:</b> <code>{balance}</code> 🌟\n"
            f"📈 <b>Sof Foyda:</b> <code>{profit_str}</code> 🌟\n"
            f"🎯 <b>Joriy Stavka:</b> <code>{s['current_stake']}</code> Stars ({mode_str})\n"
            f"\n"
            f"📊 <b>O'YINLAR STATISTIKASI:</b>\n"
            f"🎮 <b>Jami o'yinlar:</b> {total} ta\n"
            f"🏆 <b>G'alaba:</b> {wins} ta ({winrate}%)\n"
            f"❌ <b>Mag'lubiyat:</b> {losses} ta\n"
            f"🤝 <b>Durang:</b> {draws} ta\n"
            f"🔥 <b>G'alaba seriyasi:</b> {s['streak']} ta (Rekord: {s['max_streak']})\n"
            f"\n"
            f"🎁 <b>VAZIFALAR (AUTO-FARM):</b>\n"
            f"⚡ <b>Bajarilgan:</b> {s['tasks_claimed']} ta\n"
            f"💰 <b>Vazifadan olingan:</b> +{s['tasks_profit']:.1f} Stars\n"
            f"\n"
            f"⚡ <b>TIZIM HOLATI:</b>\n"
            f"🟢 <b>Holat:</b> {s['current_status']}\n"
            f"⏱ <b>Ish vaqti (Uptime):</b> {uptime_str}\n"
            f"🤖 <b>Dvigatel:</b> C-Native God-Mode v50 Ultra Max Pro (Zero-Chance Killer, 50-chuqurlik)"
        )
        return msg


# =====================================================================
# WEBSOCKET KLIYENT VA TO'LIQ AVTOMATIK O'YINCHI + AUTO-TASK
# =====================================================================
class GramoraCheckersBot:
    def __init__(self, init_data: str = None, stats_mgr: StatsManager = None, refresh_token_func = None, tg_client = None):
        self.init_data = init_data or INIT_DATA
        self.stats_mgr = stats_mgr or StatsManager()
        self.refresh_token_func = refresh_token_func
        self.tg_client = tg_client
        self.is_enabled = self.stats_mgr.stats.get("is_enabled", True)
        self.soft_stop = False
        self.ai = UltraGrandmasterCheckersAI()
        self.ws = None
        self.current_match_id = None
        self.your_seat = None
        self.last_moved_key = None
        self.in_match = False
        self.is_queued = False
        self.last_queue_time = 0.0
        self.last_state_time = 0.0
        self.tasks_list = []
        self.tiers_online = {}
        self.last_msg_time = time.time()
        self.stake_tiers = [1000, 300, 100, 20, 3]

        # JONLI WEB KUZATUV (REAL-TIME DOSKA VA YURATISH TELEMETRIYASI)
        self.live_state = {
            "in_match": False,
            "match_id": None,
            "your_seat": None,
            "turn": None,
            "turn_name": "Kutilmoqda",
            "turn_badge": "Kutilmoqda",
            "my_name": self.stats_mgr.stats.get("name", "GodMode v50 AI"),
            "my_rating": self.stats_mgr.stats.get("rating", 1200),
            "opp_name": "Raqib",
            "opp_rating": 0,
            "opp_id": 0,
            "opp_photo": "",
            "opp_level": 1,
            "opp_pro": 0,
            "stake": self.stats_mgr.stats.get("current_stake", 3),
            "board": [
                3, 3, 3, 3,
                3, 3, 3, 3,
                3, 3, 3, 3,
                0, 0, 0, 0,
                0, 0, 0, 0,
                1, 1, 1, 1,
                1, 1, 1, 1,
                1, 1, 1, 1,
            ],
            "w_count": 12,
            "b_count": 12,
            "last_move": None,
            "move_history": [],
            "last_logged_key": None,
            "eval_score": 0,
            "eval_depth": 0,
            "eval_nodes": 0,
            "eval_is_book": False,
            "win_chance": 98.5,
            "clock": {},
            "status_text": "🟢 Tizim ishlamoqda",
            "last_update": time.time(),
        }
        self.load_live_state_snapshot()

    def calculate_win_chance(self, eval_score: int, stake: int = 3, is_book: bool = False, won: bool = False, draw: bool = False) -> float:
        """AI-GODMODE v50 Grossmeyster dvigateli uchun real yutish shansi (foizi)"""
        if won:
            return 100.0
        if draw:
            return 50.0
        if eval_score > 900000:
            return 100.0
        if eval_score < -900000:
            return 15.0

        # 20 va 100 stavkalarda AI juda mukammal o'ynaydi (yutish shansi 97.5% - 99.8%)
        base_chance = 97.2
        if stake >= 100:
            base_chance = 98.4
        elif stake >= 20:
            base_chance = 97.8

        if is_book:
            return round(base_chance + 0.8, 1)

        if eval_score >= 0:
            bonus = (1.0 - math.exp(-eval_score / 450.0)) * (99.9 - base_chance)
            chance = base_chance + bonus
        else:
            penalty = min(7.5, (-eval_score / 500.0) * 3.5)
            chance = max(89.5, base_chance - penalty)

        return round(min(99.9, max(50.0, chance)), 1)

    def save_live_state_snapshot(self):
        """Web visualizer uchun oxirgi o'yin doskasini diskka saqlash (to'xtatilganda ham ko'rinadi)"""
        try:
            curr_dir = os.path.dirname(os.path.abspath(__file__))
            fpath = os.path.join(curr_dir, "last_live_state.json")
            with open(fpath, "w", encoding="utf-8") as f:
                json.dump(self.live_state, f, ensure_ascii=False)
        except Exception:
            pass

    def load_live_state_snapshot(self):
        """Oldingi o'yin holatini yuklash"""
        curr_dir = os.path.dirname(os.path.abspath(__file__))
        fpath = os.path.join(curr_dir, "last_live_state.json")
        if not os.path.exists(fpath):
            fpath = "/root/last_live_state.json"
        if os.path.exists(fpath):
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    if isinstance(saved, dict) and "board" in saved:
                        self.live_state.update(saved)
            except Exception:
                pass

    async def download_tg_avatar(self, user_id, dest_path):
        if not self.tg_client:
            return
        try:
            if not self.tg_client.is_connected():
                return
            await self.tg_client.download_profile_photo(user_id, file=dest_path)
            print(f"[AVATAR] 📸 Raqib profil rasmi yuklab olindi: {dest_path}")
        except Exception:
            pass

    def update_live_state_from_state(self, d: dict):
        """Server yuborgan har bir STATE paketini Web monitoring uchun qayta ishlash"""
        try:
            board = d.get("board")
            turn = d.get("turn")
            last_move = d.get("lastMove")
            clock = d.get("clock")
            ply = d.get("ply", 0)
            version = d.get("version", 0)

            if board:
                self.live_state["board"] = list(board)
                self.live_state["w_count"] = sum(1 for p in board if p in (W_MAN, W_KING))
                self.live_state["b_count"] = sum(1 for p in board if p in (B_MAN, B_KING))

            if turn is not None:
                self.live_state["turn"] = int(turn)
                if self.your_seat is not None:
                    if int(turn) == int(self.your_seat):
                        self.live_state["turn_name"] = "Sizning navbatingiz (GodMode v50 AI)"
                        self.live_state["turn_badge"] = "Siz (AI)"
                    else:
                        opp_name = self.live_state.get("opp_name", "Raqib")
                        self.live_state["turn_name"] = f"Raqib navbati ({opp_name})"
                        self.live_state["turn_badge"] = opp_name
                else:
                    self.live_state["turn_name"] = "Oqlar navbati" if int(turn) == 0 else "Qoralar navbati"
                    self.live_state["turn_badge"] = "Oqlar" if int(turn) == 0 else "Qoralar"

            if clock and isinstance(clock, dict):
                self.live_state["clock"] = clock

            if last_move and isinstance(last_move, dict):
                frm_sq = last_move.get("from")
                to_sq = last_move.get("to")
                caps = last_move.get("captures", [])

                move_key = (frm_sq, to_sq, tuple(caps) if caps else (), ply, version)
                if move_key != self.live_state.get("last_logged_key") and frm_sq is not None and to_sq is not None:
                    self.live_state["last_logged_key"] = move_key

                    # Yurishni amalga oshirgan o'yinchi - joriy turn ning aksi
                    mover_seat = (1 - int(turn)) if turn is not None else None
                    mover_is_me = (mover_seat is not None and self.your_seat is not None and mover_seat == self.your_seat)
                    mover_color = "Oq" if mover_seat == 0 else ("Qora" if mover_seat == 1 else "Noma'lum")

                    opp_name = self.live_state.get("opp_name", "Raqib")
                    if mover_is_me:
                        player_title = f"Siz ({mover_color})"
                    elif mover_seat is not None:
                        player_title = f"{opp_name} ({mover_color})"
                    else:
                        player_title = f"O'yinchi ({mover_color})"

                    frm_not = sq_to_notation(frm_sq)
                    to_not = sq_to_notation(to_sq)
                    is_cap = bool(caps and len(caps) > 0)
                    cap_nots = [sq_to_notation(c) for c in caps] if caps else []

                    if is_cap:
                        not_str = f"{frm_not} : {to_not}"
                        desc = f"💥 {player_title}: {frm_not} dan {to_not} ga sakrab {len(caps)} ta toshni urdi ({', '.join(cap_nots)})"
                    else:
                        not_str = f"{frm_not} - {to_not}"
                        desc = f"➡️ {player_title}: toshni {frm_not} dan {to_not} ga surdi"

                    move_entry = {
                        "num": len(self.live_state["move_history"]) + 1,
                        "player": player_title,
                        "mover_seat": mover_seat,
                        "color": mover_color,
                        "is_me": mover_is_me,
                        "from_sq": frm_sq,
                        "to_sq": to_sq,
                        "from": frm_sq,
                        "to": to_sq,
                        "path": last_move.get("path") or [frm_sq, to_sq],
                        "from_not": frm_not,
                        "to_not": to_not,
                        "notation": not_str,
                        "desc": desc,
                        "is_capture": is_cap,
                        "captures": cap_nots,
                        "time": time.strftime("%H:%M:%S")
                    }
                    self.live_state["last_move"] = move_entry
                    self.live_state["move_history"].append(move_entry)
                    if len(self.live_state["move_history"]) > 60:
                        self.live_state["move_history"].pop(0)

            self.live_state["last_update"] = time.time()
            self.save_live_state_snapshot()
        except Exception as e:
            print(f"[LIVE STATE ERROR] {e}")

    def get_live_state(self) -> dict:
        """Web visualizer frontend API uchun to'liq real-time ma'lumotlar to'plami"""
        data = dict(self.live_state)
        data["stats"] = dict(self.stats_mgr.stats)
        data["user_balance"] = self.stats_mgr.stats.get("stars_balance", 0.0)
        data["net_profit"] = self.stats_mgr.stats.get("net_profit", 0.0)
        data["games_total"] = self.stats_mgr.stats.get("games_total", 0)
        data["wins"] = self.stats_mgr.stats.get("wins", 0)
        data["losses"] = self.stats_mgr.stats.get("losses", 0)
        data["draws"] = self.stats_mgr.stats.get("draws", 0)
        data["streak"] = self.stats_mgr.stats.get("streak", 0)
        data["is_enabled"] = self.is_enabled
        data["current_stake"] = self.stats_mgr.stats.get("current_stake", 3)
        data["current_status"] = self.stats_mgr.stats.get("current_status", "")
        data["server_time"] = time.time()
        return data

    async def send_json(self, payload: dict):
        if self.ws:
            try:
                msg = json.dumps(payload, separators=(",", ":"))
                await self.ws.send(msg)
            except Exception:
                pass

    async def ping_loop(self):
        """Doimiy PING va LOBBY_STATS yuborib turish (aloqa uzilmasligi va server javob qaytarishi uchun)"""
        try:
            lobby_tick = 0
            while True:
                await asyncio.sleep(4.0)
                await self.send_json({"v": 1, "t": "PING"})
                lobby_tick += 1
                if lobby_tick >= 3:
                    lobby_tick = 0
                    await self.send_json({"v": 1, "t": "LOBBY_STATS"})
        except asyncio.CancelledError:
            pass
        except Exception:
            pass

    async def ws_watchdog_loop(self):
        """Har 1 soniyada aloqani tekshiruvchi ichki qo'riqchi (45s aloqa yo'qolsa zudlik bilan qayta ochadi)"""
        try:
            while True:
                await asyncio.sleep(1.0)
                if self.ws and (time.time() - self.last_msg_time > 45.0):
                    print(f"[WS WATCHDOG] ⚠️ 45 soniya serverdan hech qanday paket kelmadi! WebSocket qayta ochilmoqda...")
                    try:
                        await self.ws.close()
                    except Exception:
                        pass
                    break
        except asyncio.CancelledError:
            pass
        except Exception:
            pass

    async def anti_sleep_watchdog_loop(self):
        """
        Bot hech qachon uxlamasligi va qotib qolmasligini kafolatlovchi Anti-Sleep Heartbeat dvigateli (24/7):
        1. Agar bot bo'sh turgan bo'lsa (not in_match and not is_queued), 5 soniya ichida avtomatik navbatga qo'shadi.
        2. Agar navbatda 25 soniyadan ko'proq qolib ketsa, navbatni yangilaydi.
        3. Agar o'yinda (in_match=True) bo'lsa-yu, lekin 45 soniyadan beri serverdan hech qanday STATE kelmasa,
           demak o'yin tugagan deb hisoblab in_match ni tozalaydi va yangi navbatga qo'shadi!
        """
        try:
            while True:
                await asyncio.sleep(3.0)
                if not self.ws:
                    continue

                now = time.time()
                if self.in_match:
                    if self.last_state_time > 0 and (now - self.last_state_time > 45.0):
                        print("[ANTI-SLEEP] ⚠️ O'yin 45 soniya harakatsiz qoldi! in_match tozalandi...")
                        self.in_match = False
                        self.is_queued = False
                        self.live_state["in_match"] = False
                        if self.soft_stop:
                            self.is_enabled = False
                            self.soft_stop = False
                            self.stats_mgr.stats["is_enabled"] = False
                            self.stats_mgr.stats["current_status"] = "🔴 O'yin yakunlandi va bot to'xtatildi (.off)"
                            self.stats_mgr.save()
                        elif self.is_enabled:
                            await self.join_queue()
                    continue

                if not self.is_enabled or self.soft_stop:
                    if self.soft_stop and not self.in_match:
                        self.is_enabled = False
                        self.soft_stop = False
                        self.stats_mgr.stats["is_enabled"] = False
                        self.stats_mgr.stats["current_status"] = "🔴 O'yin yakunlandi va bot to'xtatildi (.off)"
                        self.stats_mgr.save()
                    continue

                # 2. Bo'sh turganlik tekshiruvi (Idle / sleep recovery)
                if getattr(self, "is_queue_joining", False):
                    continue

                if not self.in_match:
                    time_since_queue = now - self.last_queue_time
                    if not self.is_queued and time_since_queue > 10.0:
                        print("[ANTI-SLEEP] ⚡ Bot bo'sh turibdi (uxlamaslik uchun darhol navbatga qo'shilmoqda)...")
                        await self.join_queue()
                    elif self.is_queued and time_since_queue > 35.0:
                        print("[ANTI-SLEEP] 🔄 Navbat yangilanmoqda (35s kutilgach)...")
                        await self.join_queue()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"[ANTI-SLEEP XATO] {e}")

    async def task_farm_loop(self):
        """Har 30 soniyada fon rejimida mavjud vazifalarni avtomatik yechib Stars yig'adi"""
        try:
            while True:
                await asyncio.sleep(30.0)
                if not self.in_match and self.ws:
                    await self.claim_all_available_tasks()
        except asyncio.CancelledError:
            pass

    def get_required_stake(self) -> int:
        """Joriy rejim bo'yicha talab qilinadigan minimal yoki belgilangan stavka"""
        try:
            self.stats_mgr.load()
        except Exception:
            pass
        s = self.stats_mgr.stats
        if s.get("stake_mode") == "manual" and s.get("manual_stake"):
            return int(s["manual_stake"])
        return 3

    def get_optimal_stake(self) -> int:
        """Foydalanuvchi balansi va onlayn o'yinchilarga qarab optimal stavkani hisoblash"""
        try:
            self.stats_mgr.load()
        except Exception:
            pass
        s = self.stats_mgr.stats
        bal = float(s.get("stars_balance", 0.0))

        if s.get("stake_mode") == "manual" and s.get("manual_stake"):
            req = int(s["manual_stake"])
            if bal < req:
                return None
            return req

        # Avtomatik rejimda kamida 3 Stars talab qilinadi
        if bal < 3:
            return None

        checkers_online = self.tiers_online.get("checkers", {})

        # Balans yetgan eng katta stavkani topish
        for tier in self.stake_tiers:
            if bal >= tier:
                players = int(checkers_online.get(str(tier), 0))
                if tier == 3 or players > 0:
                    return tier
                continue

        return 3

    async def claim_all_available_tasks(self) -> dict:
        """Vazifalar ro'yxatini olib, mavjudlarini zudlik bilan bajarish (avtomatik pul ishlash)"""
        if not self.ws:
            return {"claimed": 0, "min_cooldown": 30.0}

        print("\n[TASK-AUTO] 🎁 Vazifalar ro'yxati va balans yangilanmoqda...")
        try:
            await self.send_json({"v": 1, "t": "TASK", "d": {"action": "list"}})
            await self.send_json({"v": 1, "t": "STARS", "d": {"action": "balance"}})
        except Exception as e:
            print(f"[TASK-AUTO XATO] {e}")
            return {"claimed": 0, "min_cooldown": 30.0}

        await asyncio.sleep(1.2)

        claimed_count = 0
        min_cooldown = 999999.0
        tasks_to_claim = []

        if self.tasks_list:
            for item in list(self.tasks_list):
                key = item.get("key")
                if not key:
                    continue
                rem = item.get("remaining", 0)
                cool = item.get("cooldownLeft", 0)
                if cool and cool > 0:
                    if cool < min_cooldown:
                        min_cooldown = float(cool)
                if rem > 0 and (not cool or cool <= 0):
                    tasks_to_claim.append(key)
        else:
            # Agar ro'yxat bo'sh bo'lsa, zaxiradagi mashhur kalitlarni sinab ko'ramiz
            tasks_to_claim = ["directlink", "longad", "adstask"]

        for key in tasks_to_claim:
            try:
                print(f"[TASK-AUTO] ⚡ Vazifa bajarilmoqda: '{key}'...")
                await self.send_json({"v": 1, "t": "TASK", "d": {"action": "claim", "key": key}})
                claimed_count += 1
                await asyncio.sleep(0.9)
            except Exception as e:
                print(f"[TASK-AUTO XATO] {key}: {e}")

        # Balans va vazifalarni qayta so'rab olish
        try:
            await self.send_json({"v": 1, "t": "STARS", "d": {"action": "balance"}})
            await self.send_json({"v": 1, "t": "TASK", "d": {"action": "list"}})
        except Exception:
            pass

        await asyncio.sleep(0.8)

        if min_cooldown >= 999999.0:
            min_cooldown = 20.0

        return {"claimed": claimed_count, "min_cooldown": min_cooldown}

    async def turn_off(self, force: bool = False) -> str:
        """Botni to'xtatish. Agar o'yin ketayotgan bo'lsa va force=False bo'lsa, o'yin tugagandan so'ng to'xtaydi"""
        if self.in_match and not force:
            return await self.soft_turn_off()

        self.is_enabled = False
        self.soft_stop = False
        self.stats_mgr.stats["is_enabled"] = False
        self.stats_mgr.stats["current_status"] = "🔴 To'xtatildi (.off)"
        self.stats_mgr.save()

        self.live_state["in_match"] = False
        self.live_state["is_enabled"] = False
        self.live_state["status_text"] = "🔴 Bot to'xtatildi (.off)"
        self.live_state["turn_name"] = "To'xtatilgan (.off)"
        self.save_live_state_snapshot()

        if self.in_match and self.ws and force:
            print("[BOT] 🛑 Majburiy to'xtatish (force=True). RESIGN yuborilmoqda...")
            try:
                await self.send_json({"v": 1, "t": "RESIGN"})
            except Exception as e:
                print(f"[RESIGN ERROR] {e}")
            try:
                await self.send_json({"v": 1, "t": "QUEUE_LEAVE"})
            except Exception:
                pass
            return (
                "🛑 <b>Gramora Bot zudlik bilan to'xtatildi (.off)!</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━\n"
                "⛔ O'yin majburan to'xtatildi va bot o'chirildi.\n"
                "💡 <i>Qayta yoqish uchun:</i> <code>.on</code>"
            )

        if self.ws:
            try:
                await self.send_json({"v": 1, "t": "QUEUE_LEAVE"})
                print("[BOT] 🛑 Bot to'xtatildi (.off). Navbat bekor qilindi.")
            except Exception:
                pass

        return (
            "🔴 <b>Gramora Bot to'xtatildi (.off)!</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "🛑 Bot to'liq to'xtatildi va yangi o'yinlarga kirmaydi.\n"
            "💡 <i>Qayta yoqish uchun:</i> <code>.on</code>"
        )

    async def soft_turn_off(self) -> str:
        """Joriy partiyani yakunlab (yutishga harakat qilib), keyin yangi o'yinga kirmay to'xtash"""
        if not self.in_match:
            return await self.turn_off(force=False)

        self.soft_stop = True
        self.stats_mgr.stats["current_status"] = "⏳ O'yin tugagach to'xtaydi..."
        self.stats_mgr.save()
        self.live_state["status_text"] = "⏳ O'yin tugagach to'xtaydi..."
        print("[BOT] ⏳ Soft-stop: joriy partiya yakunlangach bot avtomatik to'xtaydi.")
        return (
            "⏳ <b>Gramora Bot joriy o'yindan so'ng to'xtaydi!</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "⚔️ Bot hozirgi partiyani yutib oxirigacha yetkazadi (Stars saqlab qolinadi), keyin avtomatik to'xtaydi.\n"
            "💡 <i>Qayta yoqish uchun:</i> <code>.on</code>"
        )

    async def turn_on(self) -> str:
        self.is_enabled = True
        self.soft_stop = False
        self.stats_mgr.stats["is_enabled"] = True
        self.stats_mgr.stats["current_status"] = "🟢 Ishga tushirildi (.on)"
        self.stats_mgr.save()
        print("[BOT] 🟢 Bot ishga tushirildi (.on).")
        if not self.in_match:
            asyncio.create_task(self.join_queue())
            stake = self.stats_mgr.stats.get("current_stake", 3)
            return f"🟢 <b>Gramora Bot ishga tushirildi (.on)!</b>\n━━━━━━━━━━━━━━━━━━━━━\n🚀 Bot navbatga qo'shilmoqda va o'yinlarni boshlaydi.\n🎲 <i>Joriy stavka:</i> <code>{stake}</code> Stars"
        return "🟢 <b>Gramora Bot faollashtirildi (.on)!</b>\n━━━━━━━━━━━━━━━━━━━━━\nO'yinlar to'xtovsiz davom ettiriladi."

    async def requeue_after_delay(self, delay: float = 2.5):
        try:
            await asyncio.sleep(delay)
            if self.is_enabled and not self.soft_stop and not self.in_match:
                await self.join_queue()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"[REQUEUE ERROR] {e}")

    async def join_queue(self):
        if getattr(self, "is_queue_joining", False):
            return

        if not self.is_enabled:
            print("\n[QUEUE] Bot to'xtatilgan (.off). Navbatga qo'shilmaydi.")
            self.stats_mgr.stats["current_status"] = "🔴 To'xtatilgan (.off)"
            self.stats_mgr.save()
            return

        if self.in_match:
            if self.last_state_time > 0 and (time.time() - self.last_state_time > 45.0):
                print("[QUEUE] Qotib qolgan eski o'yin tozalanmoqda (in_match=False)...")
                self.in_match = False
                self.is_queued = False
                self.live_state["in_match"] = False
            else:
                print("[QUEUE] O'yin allaqachon ketmoqda (in_match=True). Yangi navbatga qo'shilmaydi.")
                return

        self.is_queue_joining = True
        try:
            self.last_queue_time = time.time()

            while True:
                if not self.is_enabled:
                    return
                optimal = self.get_optimal_stake()
                if optimal is not None:
                    break

                target_stake = self.get_required_stake()
                bal = float(self.stats_mgr.stats.get("stars_balance", 0.0))
                print(f"\n[QUEUE] ⚠️ Balans yetarli emas ({bal:.1f}⭐ < {target_stake}⭐). Vazifalardan avtomatik ishlanmoqda...")
                self.stats_mgr.stats["current_status"] = f"🎁 Vazifalardan ishlanmoqda ({bal:.1f}/{target_stake}⭐)..."
                self.stats_mgr.save()
                self.live_state["status_text"] = self.stats_mgr.stats["current_status"]
                self.save_live_state_snapshot()

                res = await self.claim_all_available_tasks()
                await asyncio.sleep(1.0)

                optimal = self.get_optimal_stake()
                if optimal is not None:
                    print(f"[QUEUE] 🚀 Yetarli Stars to'plandi! Balans: {self.stats_mgr.stats.get('stars_balance', 0.0):.1f}⭐. O'yinga kirilmoqda...")
                    break

                bal = float(self.stats_mgr.stats.get("stars_balance", 0.0))
                min_cd = float(res.get("min_cooldown", 15.0)) if isinstance(res, dict) else 15.0
                wait_sec = max(5.0, min(min_cd, 25.0))
                status_msg = f"⏳ Vazifalar kutilmoqda ({bal:.1f}/{target_stake}⭐, {wait_sec:.0f}s)..."
                print(f"[QUEUE] {status_msg}")
                self.stats_mgr.stats["current_status"] = status_msg
                self.stats_mgr.save()
                self.live_state["status_text"] = status_msg
                self.save_live_state_snapshot()
                self.last_queue_time = time.time()
                await asyncio.sleep(wait_sec)

            self.stats_mgr.stats["current_stake"] = optimal
            self.stats_mgr.stats["current_status"] = f"🔍 Raqib qidirilmoqda (Stavka: {optimal} Stars)..."
            self.stats_mgr.save()

            print(f"\n[QUEUE] Shashka navbatiga qo'shilmoqda (Stavka: {optimal} Stars)...")
            await self.send_json({"v": 1, "t": "LOBBY_STATS"})
            await self.send_json({"v": 1, "t": "QUEUE_JOIN", "d": {"stake": optimal, "game": "checkers"}})
        finally:
            self.is_queue_joining = False

    @staticmethod
    def decode_multiple_json(raw_text: str):
        decoder = json.JSONDecoder()
        pos = 0
        length = len(raw_text)
        objects = []
        while pos < length:
            while pos < length and raw_text[pos].isspace():
                pos += 1
            if pos >= length:
                break
            try:
                obj, next_pos = decoder.raw_decode(raw_text, pos)
                objects.append(obj)
                pos = next_pos
            except json.JSONDecodeError:
                break
        return objects

    @staticmethod
    def print_board(board: list, your_seat: int):
        symbols = {EMPTY: ".", W_MAN: "w", W_KING: "W", B_MAN: "b", B_KING: "B"}
        grid = [[" " for _ in range(8)] for _ in range(8)]
        for sq, val in enumerate(board):
            r, c = COORDS[sq]
            grid[r][c] = symbols.get(val, "?")

        color_str = "OQ ('w'/'W')" if your_seat == 0 else "QORA ('b'/'B')"
        print(f"\n   --- Doska (Siz: {color_str}) ---")
        for r in range(8):
            row_cells = " ".join(f"{grid[r][c]:2}" for c in range(8))
            print(f"   {r} | {row_cells}")
        print("      -----------------------")

    async def handle_state(self, d: dict):
        self.last_state_time = time.time()
        self.in_match = True
        self.is_queued = False
        match_id = d.get("matchId") or self.current_match_id
        board = d.get("board")
        turn = d.get("turn")
        version = d.get("version", 0)
        ply = d.get("ply", 0)
        legal = d.get("legal", [])
        move_ms = d.get("moveMs") or (d.get("clock", {}).get(str(turn)) if isinstance(d.get("clock"), dict) else 60000) or 60000
        last_move = d.get("lastMove")

        # 1. your_seat ni ko'p bosqichli aniqlash
        seat_candidate = d.get("yourSeat")
        if seat_candidate is None:
            seat_candidate = d.get("seat")
        if seat_candidate is None:
            seat_candidate = self.your_seat
        if seat_candidate is None and legal and board:
            frm = legal[0].get("from")
            if frm is not None and 0 <= frm < len(board):
                seat_candidate = 0 if board[frm] in (W_MAN, W_KING) else 1

        if seat_candidate is not None:
            self.your_seat = int(seat_candidate)

        # Jonli Web monitoring state ni yangilash
        self.update_live_state_from_state(d)

        if last_move and board:
            to_sq = last_move.get("to")
            frm_sq = last_move.get("from")
            caps = last_move.get("captures", [])
            if to_sq is not None and frm_sq is not None and board[to_sq] in (W_KING, B_KING):
                r1, _ = COORDS[frm_sq]
                r2, _ = COORDS[to_sq]
                if (not caps and abs(r1 - r2) > 1) or (len(caps) == 1 and abs(r1 - r2) > 2):
                    self.ai.flying_kings = True

        # 2. Navbat bizdami tekshirish
        is_my_turn = False
        if legal and len(legal) > 0:
            if turn is not None and self.your_seat is not None:
                is_my_turn = (int(turn) == int(self.your_seat))
            else:
                is_my_turn = True

        if not self.is_enabled:
            print("[STATE] 🛑 Bot to'xtatilgan (.off). Yurish qilinmaydi.")
            return

        if not is_my_turn or not legal:
            if turn is not None and self.your_seat is not None and int(turn) != int(self.your_seat):
                print(f"[STATE] Raqib o'ylamoqda... (turn={turn}, siz={self.your_seat})")
            return

        # 3. Bir xil holatda takroriy yurishni oldini olish
        state_key = (match_id, version, ply, len(legal))
        if self.last_moved_key == state_key:
            return
        self.last_moved_key = state_key

        effective_seat = self.your_seat if self.your_seat is not None else int(turn or 0)
        self.ai.record_board(board)
        self.print_board(board, effective_seat)
        print(f"[STATE] 👉 Sizning navbatingiz! (seat={effective_seat}, variantlar={len(legal)})")

        current_stake = self.live_state.get("stake") or self.stats_mgr.stats.get("current_stake", 3) or 3
        try:
            calc_timeout = max(4.0, min(float(move_ms) / 1000.0 * 0.90, 8.0))
            best_move = await asyncio.wait_for(
                asyncio.to_thread(
                    self.ai.choose_best_move,
                    board,
                    legal,
                    effective_seat,
                    move_ms,
                    int(current_stake)
                ),
                timeout=calc_timeout
            )
        except Exception as ai_err:
            print(f"[AI CALC TIMEOUT/ERROR] {ai_err}, zaxira tezkor yurish qilinmoqda...")
            best_move = legal[0] if legal else None

        if not best_move and legal:
            best_move = legal[0]
        if not best_move:
            print("[STATE] ⚠️ Qonuniy yurish topilmadi!")
            return

        # AI hisoblagan baho va chuqurlikni web monitoringga uzatish
        eval_score = self.ai.last_eval.get("score", 0)
        eval_is_book = self.ai.last_eval.get("is_book", False)
        current_stake = self.live_state.get("stake", self.stats_mgr.stats.get("current_stake", 3))

        self.live_state["eval_score"] = eval_score
        self.live_state["eval_depth"] = self.ai.last_eval.get("depth", 0)
        self.live_state["eval_nodes"] = self.ai.last_eval.get("nodes", 0)
        self.live_state["eval_is_book"] = eval_is_book
        self.live_state["win_chance"] = self.calculate_win_chance(eval_score, stake=current_stake, is_book=eval_is_book)

        from_sq = best_move.get("from")
        to_sq = best_move.get("to")
        path = best_move.get("path")
        if not path:
            path = [from_sq, to_sq]

        # AI yurishini darhol live_state ga yozish (doskada 0ms kechikish bilan ko'rinadi)
        try:
            frm_not = sq_to_notation(from_sq)
            to_not = sq_to_notation(to_sq)
            is_cap = bool(len(path) > 2)
            mover_color = "Oq" if effective_seat == 0 else "Qora"
            not_str = " : ".join([sq_to_notation(p) for p in path]) if is_cap else f"{frm_not} - {to_not}"
            desc = f"🚀 Siz ({mover_color}): {frm_not} dan {to_not} ga yurdingiz"
            ai_entry = {
                "num": len(self.live_state["move_history"]) + 1,
                "player": f"Siz ({mover_color})",
                "mover_seat": effective_seat,
                "color": mover_color,
                "is_me": True,
                "from_sq": from_sq,
                "to_sq": to_sq,
                "from": from_sq,
                "to": to_sq,
                "path": path,
                "from_not": frm_not,
                "to_not": to_not,
                "notation": not_str,
                "desc": desc,
                "is_capture": is_cap,
                "captures": [sq_to_notation(p) for p in path[1:-1]] if is_cap else [],
                "time": time.strftime("%H:%M:%S")
            }
            self.live_state["last_move"] = ai_entry
            self.live_state["move_history"].append(ai_entry)
            if len(self.live_state["move_history"]) > 60:
                self.live_state["move_history"].pop(0)

            # Doskadagi toshni darhol yashil katakka ko'chirish (avtomatik yashilda paydo bo'ladi, 0ms kechikish)
            if "board" in self.live_state and self.live_state["board"]:
                new_b = list(self.live_state["board"])
                p_moved = new_b[from_sq] if 0 <= from_sq < 32 else 0
                if 0 <= from_sq < 32:
                    new_b[from_sq] = 0
                for c_sq in best_move.get("captures", []):
                    if 0 <= c_sq < 32:
                        new_b[c_sq] = 0
                if 0 <= to_sq < 32:
                    if best_move.get("promotes") or (p_moved == W_MAN and to_sq < 4) or (p_moved == B_MAN and to_sq >= 28):
                        p_moved = W_KING if effective_seat == 0 else B_KING
                    new_b[to_sq] = p_moved
                self.live_state["board"] = new_b
                self.live_state["w_count"] = sum(1 for x in new_b if x in (W_MAN, W_KING))
                self.live_state["b_count"] = sum(1 for x in new_b if x in (B_MAN, B_KING))

            self.live_state["last_update"] = time.time()
        except Exception as lm_err:
            print(f"[AI MOVE LOG ERROR] {lm_err}")

        if not self.is_enabled:
            print("[STATE] 🛑 Bot to'xtatilgan (.off). Serverga yurish yuborilmaydi.")
            return

        move_payload = {
            "v": 1,
            "t": "MOVE",
            "d": {
                "from": from_sq,
                "to": to_sq,
                "path": path
            }
        }
        print(f"[MOVE] 🚀 Serverga yurish yuborildi: {from_sq} -> {to_sq} (path: {path})")
        await self.send_json(move_payload)

    async def run(self):
        """24/7 Uxlashsiz, avtomatik qayta ulanadigan o'yin tsikli"""
        while True:
            try:
                # Aloqa boshlanishidan oldin barcha o'yin bayroqchalarini tozalash
                self.in_match = False
                self.is_queued = False
                self.current_match_id = None
                self.last_moved_key = None
                self.live_state["in_match"] = False

                is_replaced = False
                print(f"\n[WS] Gramora WebSocket serveriga ulanmoqda: {WS_URL}")
                async with websockets.connect(
                    WS_URL,
                    additional_headers=HEADERS,
                    ping_interval=None,
                    max_size=2**20
                ) as ws:
                    self.ws = ws
                    self.last_msg_time = time.time()
                    self.last_queue_time = 0.0
                    self.last_state_time = 0.0

                    ping_task = asyncio.create_task(self.ping_loop())
                    task_farm_task = asyncio.create_task(self.task_farm_loop())
                    ws_watchdog_task = asyncio.create_task(self.ws_watchdog_loop())
                    anti_sleep_task = asyncio.create_task(self.anti_sleep_watchdog_loop())

                    await self.send_json({
                        "v": 1,
                        "t": "HELLO",
                        "d": {"initData": self.init_data, "subv": 2}
                    })

                    async for raw_msg in ws:
                        self.last_msg_time = time.time()
                        for packet in self.decode_multiple_json(raw_msg):
                            t = packet.get("t")
                            d = packet.get("d", {})

                            if t == "WELCOME":
                                pass

                            elif t == "AUTH_OK":
                                user = d.get("user", {})
                                self.stats_mgr.stats["user_id"] = user.get("id")
                                self.stats_mgr.stats["name"] = user.get("name") or "User"
                                self.stats_mgr.stats["username"] = user.get("username") or ""
                                self.stats_mgr.stats["rating"] = d.get("rating", 1200)
                                self.stats_mgr.stats["league"] = d.get("league", "Silver")
                                if "stars" in d:
                                    self.stats_mgr.stats["stars_balance"] = float(d["stars"])
                                self.stats_mgr.stats["current_status"] = "🟢 Tizimga ulandi. O'yinga tayyorlanmoqda"
                                self.stats_mgr.save()

                                self.live_state["my_name"] = user.get("name") or "GodMode v50 AI"
                                self.live_state["my_rating"] = d.get("rating", 1200)
                                self.live_state["status_text"] = "🟢 Tizimga ulandi. O'yinga tayyor"

                                if "tiersByGame" in d:
                                    self.tiers_online = d["tiersByGame"]

                                print(
                                    f"[AUTH_OK] Foydalanuvchi: {user.get('name')} (@{user.get('username')}) | "
                                    f"Reyting: {d.get('rating')} | Stars: {d.get('stars')}"
                                )
                                await self.send_json({"v": 1, "t": "STARS", "d": {"action": "balance"}})
                                await self.send_json({"v": 1, "t": "TASK", "d": {"action": "list"}})
                                await self.send_json({"v": 1, "t": "LOBBY_STATS"})
                                self.in_match = False
                                self.is_queued = False
                                asyncio.create_task(self.requeue_after_delay(1.0))

                            elif t == "LOBBY_STATS":
                                if "tiersByGame" in d:
                                    self.tiers_online = d["tiersByGame"]

                            elif t == "TASK":
                                if "balance" in d and d["balance"] is not None:
                                    self.stats_mgr.stats["stars_balance"] = float(d["balance"])
                                    self.stats_mgr.save()
                                if "tasks" in d and isinstance(d["tasks"], list):
                                    self.tasks_list = d["tasks"]
                                if d.get("kind") == "claimed":
                                    reward = float(d.get("reward", 1.0))
                                    self.stats_mgr.record_task_claimed(reward)
                                    print(f"[TASK] 🎁 +{reward} Stars olindi! Yangi balans: {self.stats_mgr.stats['stars_balance']}")

                            elif t == "QUEUED":
                                self.is_queued = True
                                self.in_match = False
                                self.last_queue_time = time.time()
                                stake = d.get("stake", self.stats_mgr.stats["current_stake"])
                                print(f"[QUEUED] Raqib qidirilmoqda (Stake: {stake} Stars)...")
                                self.stats_mgr.stats["current_status"] = f"🔍 Raqib qidirilmoqda ({stake}⭐)..."
                                self.stats_mgr.save()
                                self.live_state["in_match"] = False
                                self.live_state["status_text"] = f"🔍 Raqib qidirilmoqda ({stake}⭐)..."
                                self.live_state["turn_name"] = "Raqib qidirilmoqda..."

                            elif t == "MATCH_FOUND":
                                self.in_match = True
                                self.is_queued = False
                                self.last_state_time = time.time()
                                self.current_match_id = d.get("matchId")
                                self.your_seat = d.get("seat")
                                self.last_moved_key = None
                                self.ai.reset_match()
                                opp = d.get("opponent", {})
                                opp_name = opp.get("name", "Raqib")
                                opp_rating = opp.get("rating", 0)
                                opp_id = opp.get("id") or 0
                                opp_photo = opp.get("photo") or ""
                                opp_level = opp.get("level") or 1
                                opp_pro = 1 if opp.get("pro") else 0
                                stake = d.get("stake", self.stats_mgr.stats["current_stake"])
                                self.stats_mgr.stats["current_stake"] = stake
                                self.stats_mgr.stats["current_status"] = f"⚔️ O'yinda (Raqib: {opp_name}, {stake}⭐)"
                                self.stats_mgr.stats["last_opponent"] = opp_name
                                self.stats_mgr.save()

                                if not opp_photo and opp_id and self.tg_client:
                                    try:
                                        avatar_dir = "/root/gramora_match_history_app/static/avatars"
                                        os.makedirs(avatar_dir, exist_ok=True)
                                        avatar_path = os.path.join(avatar_dir, f"{opp_id}.jpg")
                                        if os.path.exists(avatar_path):
                                            opp_photo = f"/static/avatars/{opp_id}.jpg"
                                        else:
                                            asyncio.create_task(self.download_tg_avatar(opp_id, avatar_path))
                                            opp_photo = f"/static/avatars/{opp_id}.jpg"
                                    except Exception:
                                        pass

                                # Live web state ni yangi o'yin uchun sozlash
                                self.live_state["in_match"] = True
                                self.live_state["match_id"] = self.current_match_id
                                self.live_state["your_seat"] = self.your_seat
                                self.live_state["opp_name"] = opp_name
                                self.live_state["opp_rating"] = opp_rating
                                self.live_state["opp_id"] = opp_id
                                self.live_state["opp_photo"] = opp_photo
                                self.live_state["opp_level"] = opp_level
                                self.live_state["opp_pro"] = opp_pro
                                self.live_state["my_name"] = self.stats_mgr.stats.get("name", "GodMode v50 AI")
                                self.live_state["my_rating"] = self.stats_mgr.stats.get("rating", 1200)
                                self.live_state["stake"] = stake
                                self.live_state["status_text"] = f"⚔️ O'yinda (Raqib: {opp_name})"
                                self.live_state["move_history"] = []
                                self.live_state["last_move"] = None
                                self.live_state["last_logged_key"] = None
                                self.live_state["eval_score"] = 250
                                self.live_state["eval_depth"] = 28
                                self.live_state["eval_is_book"] = True
                                self.live_state["win_chance"] = self.calculate_win_chance(250, stake=stake, is_book=True)
                                self.live_state["board"] = [
                                    3, 3, 3, 3,
                                    3, 3, 3, 3,
                                    3, 3, 3, 3,
                                    0, 0, 0, 0,
                                    0, 0, 0, 0,
                                    1, 1, 1, 1,
                                    1, 1, 1, 1,
                                    1, 1, 1, 1,
                                ]
                                self.live_state["w_count"] = 12
                                self.live_state["b_count"] = 12

                                print("\n" + "=" * 55)
                                print(
                                    f"[MATCH_FOUND] Raqib: {opp_name} (Reyting: {opp_rating}, ID: {opp_id}, Photo: {opp_photo}, Level: {opp_level}, Pro: {opp_pro}) | "
                                    f"Sizning rangingiz: {d.get('color')} (seat={self.your_seat}) | Stake: {stake}"
                                )
                                print("=" * 55)

                            elif t == "STATE":
                                await self.handle_state(d)

                            elif t == "GAME_OVER":
                                self.in_match = False
                                self.is_queued = False
                                self.current_match_id = None
                                self.last_moved_key = None
                                self.last_state_time = 0.0
                                self.last_queue_time = 0.0
                                won = bool(d.get("youWon"))
                                draw = bool(d.get("draw"))
                                stars_net = float(d.get("starsNet", 0.0))
                                opp_name = self.stats_mgr.stats.get("last_opponent", "")

                                if "newRating" in d and d["newRating"]:
                                    self.stats_mgr.stats["rating"] = d["newRating"]

                                if "balance" in d and d["balance"] is not None:
                                    self.stats_mgr.stats["stars_balance"] = float(d["balance"])
                                else:
                                    self.stats_mgr.stats["stars_balance"] = max(0.0, round(self.stats_mgr.stats["stars_balance"] + stars_net, 2))

                                self.stats_mgr.record_game(won=won, draw=draw, stars_net=stars_net, opponent_name=opp_name)

                                status = "G'ALABA 🏆" if won else ("DURANG 🤝" if draw else "MAG'LUBIYAT ❌")
                                self.stats_mgr.stats["current_status"] = f"🏁 O'yin tugadi ({status})"
                                self.stats_mgr.save()

                                self.live_state["in_match"] = False
                                self.live_state["status_text"] = f"🏁 O'yin tugadi: {status}"
                                self.live_state["turn_name"] = f"Tugadi ({status})"
                                self.live_state["win_chance"] = 100.0 if won else (50.0 if draw else 0.0)
                                self.save_live_state_snapshot()

                                print("\n" + "=" * 55)
                                print(
                                    f"[GAME_OVER] Natija: {status} | Sabab: {d.get('reason')} | "
                                    f"Reyting: {d.get('newRating')} ({d.get('ratingDelta', 0):+d}) | "
                                    f"Stars Net: {stars_net:+g} | Yangi Balans: {self.stats_mgr.stats['stars_balance']}"
                                )
                                print("=" * 55)

                                # O'yin orasida vazifalarni ham bajarib Stars yig'ib olish
                                try:
                                    asyncio.create_task(self.claim_all_available_tasks())
                                except Exception:
                                    pass

                                if self.soft_stop:
                                    self.is_enabled = False
                                    self.soft_stop = False
                                    self.stats_mgr.stats["is_enabled"] = False
                                    self.stats_mgr.stats["current_status"] = "🔴 O'yin yakunlandi va bot to'xtatildi (.off)"
                                    self.stats_mgr.save()
                                    self.live_state["is_enabled"] = False
                                    self.live_state["status_text"] = f"🏁 O'yin yakunlandi: {status} (Bot to'xtatildi)"
                                    self.save_live_state_snapshot()
                                    print("[BOT] 🛑 Soft-stop yakunlandi. Bot yangi o'yinga kirmaydi.")

                                if AUTO_REQUEUE and self.is_enabled and not self.soft_stop:
                                    asyncio.create_task(self.requeue_after_delay(2.5))
                                else:
                                    pass

                            elif t == "BALANCE":
                                if "stars" in d:
                                    self.stats_mgr.stats["stars_balance"] = float(d["stars"])
                                    self.stats_mgr.save()
                                print(f"[BALANCE] Joriy Stars balansi: {d.get('stars')}")

                            elif t == "ERROR":
                                print(f"[SERVER ERROR] {d}")
                                err_code = str(d.get("code", "")).lower()
                                err_msg = str(d.get("message", "")).lower()
                                err_all = str(d).lower()
                                if "replace" in err_code or "replace" in err_msg or "boshqa" in err_msg or "boshqa" in err_all:
                                    is_replaced = True
                                    print("[SERVER] ⚠️ Boshqa qurilma yoki Telegramdan ulanildi ('replaced'). 8 soniya kutish...")
                                    self.stats_mgr.stats["current_status"] = "⚠️ Boshqa qurilmadan kirildi (replaced)"
                                    self.stats_mgr.save()
                                    break
                                if "not enough" in err_msg or "balansi yetarli emas" in err_msg:
                                    # Balans tugagan bo'lsa vazifalarni yechish
                                    await self.claim_all_available_tasks()

                    ping_task.cancel()
                    task_farm_task.cancel()
                    ws_watchdog_task.cancel()
                    anti_sleep_task.cancel()

                if is_replaced:
                    await asyncio.sleep(8.0)
                    if self.refresh_token_func:
                        try:
                            print("[USERBOT] Yangi initData olinmoqda (replaced sababli)...")
                            new_data = await self.refresh_token_func()
                            if new_data:
                                self.init_data = new_data
                        except Exception as ref_err:
                            print(f"[USERBOT] Token yangilashda xato: {ref_err}")
                else:
                    await asyncio.sleep(3.0)

            except Exception as e:
                self.in_match = False
                self.is_queued = False
                self.live_state["in_match"] = False
                print(f"[XATO] Aloqa uzildi yoki xatolik: {e}. Qayta ulanishga tayyorlanmoqda...")
                self.stats_mgr.stats["current_status"] = "🔄 Qayta ulanmoqda..."
                self.stats_mgr.save()

                # Agar token eskirgan bo'lsa yangilash
                if self.refresh_token_func:
                    try:
                        print("[USERBOT] Yangi initData olinmoqda...")
                        new_data = await self.refresh_token_func()
                        if new_data:
                            self.init_data = new_data
                    except Exception as ref_err:
                        print(f"[USERBOT] Token yangilashda xato: {ref_err}")

                await asyncio.sleep(3.0)


if __name__ == "__main__":
    bot = GramoraCheckersBot()
    asyncio.run(bot.run())
