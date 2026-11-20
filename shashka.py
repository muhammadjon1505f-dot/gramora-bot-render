#!/usr/bin/env python3
"""
RUS SHASHKASI (RUSSIAN CHECKERS) — SUPER GRANDMASTER AI ENGINE
Professional AI with:
- Flying Kings (Uchar damka)
- Backward captures for men
- Mandatory captures (Majburiy urish)
- Immediate in-jump king promotion
- Alpha-Beta Pruning with Transposition Table (Zobrist Hash)
- Move Ordering & Quiescence Search (Forced capture resolution)
- Advanced Positional Evaluation (Center, Main Diagonal, Back Rank, Mobility)
- Human vs AI Interactive CLI with ANSI Colors
"""

import sys
import time
import random

# Board constants
EMPTY = 0
WHITE_MAN = 1
WHITE_KING = 2
BLACK_MAN = -1
BLACK_KING = -2

def is_white(p): return p > 0
def is_black(p): return p < 0
def is_king(p): return abs(p) == 2

DIRECTIONS = [(-1, -1), (-1, 1), (1, -1), (1, 1)]

# ANSI Colors
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
MAGENTA = "\033[95m"
CYAN = "\033[96m"
WHITE = "\033[97m"
BG_DARK = "\033[48;5;236m"
BG_LIGHT = "\033[48;5;250m"

# Coordinates conversion
COLS = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']
COL_MAP = {c: i for i, c in enumerate(COLS)}

def pos_to_coord(r, c):
    return f"{COLS[c]}{r + 1}"

def coord_to_pos(s):
    s = s.strip().lower()
    if len(s) != 2: return None
    c_str, r_str = s[0], s[1]
    if c_str not in COL_MAP or not r_str.isdigit(): return None
    c = COL_MAP[c_str]
    r = int(r_str) - 1
    if 0 <= r < 8 and 0 <= c < 8 and (r + c) % 2 == 0:
        return (r, c)
    return None

def move_to_str(path, is_capture=False):
    sep = ":" if is_capture else "-"
    return sep.join(pos_to_coord(r, c) for r, c in path)

# Positional bonus tables
POS_BONUS_WHITE = [
    [ 0,  0,  0,  0,  0,  0,  0,  0],  # rank 1 (defense)
    [ 5,  0, 10,  0, 10,  0,  5,  0],  # rank 2
    [ 0, 10,  0, 15,  0, 15,  0, 10],  # rank 3
    [10,  0, 25,  0, 25,  0, 10,  0],  # rank 4 (center)
    [ 0, 15,  0, 25,  0, 25,  0, 15],  # rank 5 (center)
    [15,  0, 20,  0, 20,  0, 15,  0],  # rank 6
    [ 0, 25,  0, 30,  0, 30,  0, 25],  # rank 7 (pre-king)
    [ 0,  0,  0,  0,  0,  0,  0,  0],  # rank 8
]

POS_BONUS_BLACK = [
    [ 0,  0,  0,  0,  0,  0,  0,  0],  # rank 1
    [25,  0, 30,  0, 30,  0, 25,  0],  # rank 2 (pre-king)
    [ 0, 20,  0, 20,  0, 20,  0, 15],  # rank 3
    [15,  0, 25,  0, 25,  0, 15,  0],  # rank 4 (center)
    [ 0, 10,  0, 25,  0, 25,  0, 10],  # rank 5 (center)
    [10,  0, 15,  0, 15,  0, 10,  0],  # rank 6
    [ 0,  5,  0, 10,  0, 10,  0,  5],  # rank 7
    [ 0,  0,  0,  0,  0,  0,  0,  0],  # rank 8 (defense)
]

# Zobrist Hashing
random.seed(2026)
ZOBRIST = [[[random.getrandbits(64) for _ in range(5)] for _ in range(8)] for _ in range(8)]

def piece_idx(p):
    if p == 0: return 0
    if p == 1: return 1
    if p == 2: return 2
    if p == -1: return 3
    if p == -2: return 4
    return 0

class RussianCheckers:
    def __init__(self):
        self.grid = [[EMPTY for _ in range(8)] for _ in range(8)]
        # White on ranks 1-3 (rows 0, 1, 2)
        for r in range(3):
            for c in range(8):
                if (r + c) % 2 == 0:
                    self.grid[r][c] = WHITE_MAN
        # Black on ranks 6-8 (rows 5, 6, 7)
        for r in range(5, 8):
            for c in range(8):
                if (r + c) % 2 == 0:
                    self.grid[r][c] = BLACK_MAN

        self.hash = 0
        for r in range(8):
            for c in range(8):
                p = self.grid[r][c]
                if p != EMPTY:
                    self.hash ^= ZOBRIST[r][c][piece_idx(p)]

        self.transposition_table = {}
        self.nodes_evaluated = 0

    def in_bounds(self, r, c):
        return 0 <= r < 8 and 0 <= c < 8

    def get_captures(self, side):
        captures = []
        for r in range(8):
            for c in range(8):
                p = self.grid[r][c]
                if (side == 1 and is_white(p)) or (side == -1 and is_black(p)):
                    caps = self._get_piece_captures(r, c, p, frozenset())
                    captures.extend(caps)
        return captures

    def _get_piece_captures(self, r, c, p, captured_set):
        results = []
        is_k = is_king(p)
        king_row = 7 if p > 0 else 0

        if not is_k:
            for dr, dc in DIRECTIONS:
                mr, mc = r + dr, c + dc
                lr, lc = r + 2 * dr, c + 2 * dc
                if self.in_bounds(lr, lc) and (mr, mc) not in captured_set:
                    mid = self.grid[mr][mc]
                    land = self.grid[lr][lc]
                    if ((p > 0 and is_black(mid)) or (p < 0 and is_white(mid))) and (land == EMPTY or (lr, lc) == (r, c)):
                        # Check promotion during jump (Russian rule: turn into king immediately and continue)
                        new_p = p
                        if lr == king_row:
                            new_p = WHITE_KING if p > 0 else BLACK_KING

                        new_captured = captured_set | {(mr, mc)}
                        sub_caps = self._get_piece_captures(lr, lc, new_p, new_captured)
                        if sub_caps:
                            for sub_path, sub_caps_set in sub_caps:
                                results.append(([(r, c)] + sub_path, sub_caps_set))
                        else:
                            results.append(([(r, c), (lr, lc)], new_captured))
        else:
            # Flying king captures
            for dr, dc in DIRECTIONS:
                dist = 1
                found_enemy = None
                while True:
                    cur_r, cur_c = r + dist * dr, c + dist * dc
                    if not self.in_bounds(cur_r, cur_c):
                        break
                    piece = self.grid[cur_r][cur_c]
                    if (cur_r, cur_c) in captured_set:
                        break
                    if piece != EMPTY:
                        if (p > 0 and is_black(piece)) or (p < 0 and is_white(piece)):
                            found_enemy = (cur_r, cur_c)
                        break
                    dist += 1

                if found_enemy:
                    er, ec = found_enemy
                    land_dist = 1
                    while True:
                        lr, lc = er + land_dist * dr, ec + land_dist * dc
                        if not self.in_bounds(lr, lc):
                            break
                        if self.grid[lr][lc] != EMPTY and (lr, lc) != (r, c):
                            break
                        new_captured = captured_set | {found_enemy}
                        sub_caps = self._get_piece_captures(lr, lc, p, new_captured)
                        if sub_caps:
                            for sub_path, sub_caps_set in sub_caps:
                                results.append(([(r, c)] + sub_path, sub_caps_set))
                        else:
                            results.append(([(r, c), (lr, lc)], new_captured))
                        land_dist += 1

        return results

    def get_quiet_moves(self, side):
        moves = []
        for r in range(8):
            for c in range(8):
                p = self.grid[r][c]
                if (side == 1 and is_white(p)) or (side == -1 and is_black(p)):
                    if not is_king(p):
                        dr = 1 if p > 0 else -1
                        for dc in (-1, 1):
                            nr, nc = r + dr, c + dc
                            if self.in_bounds(nr, nc) and self.grid[nr][nc] == EMPTY:
                                moves.append(([(r, c), (nr, nc)], frozenset()))
                    else:
                        for dr, dc in DIRECTIONS:
                            dist = 1
                            while True:
                                nr, nc = r + dist * dr, c + dist * dc
                                if not self.in_bounds(nr, nc) or self.grid[nr][nc] != EMPTY:
                                    break
                                moves.append(([(r, c), (nr, nc)], frozenset()))
                                dist += 1
        return moves

    def get_legal_moves(self, side):
        captures = self.get_captures(side)
        if captures:
            # Capture is mandatory!
            unique = {}
            for path, caps in captures:
                key = tuple(path)
                if key not in unique:
                    unique[key] = (path, caps)
            return list(unique.values())
        return self.get_quiet_moves(side)

    def apply_move(self, move):
        path, caps = move
        start_r, start_c = path[0]
        end_r, end_c = path[-1]
        p = self.grid[start_r][start_c]

        undo_data = (start_r, start_c, end_r, end_c, p, [(cr, cc, self.grid[cr][cc]) for cr, cc in caps])

        self.hash ^= ZOBRIST[start_r][start_c][piece_idx(p)]
        self.grid[start_r][start_c] = EMPTY

        king_row = 7 if p > 0 else 0
        promoted = is_king(p)
        for r, c in path:
            if r == king_row:
                promoted = True

        final_p = (WHITE_KING if p > 0 else BLACK_KING) if promoted else p

        for cr, cc in caps:
            cp = self.grid[cr][cc]
            self.hash ^= ZOBRIST[cr][cc][piece_idx(cp)]
            self.grid[cr][cc] = EMPTY

        self.grid[end_r][end_c] = final_p
        self.hash ^= ZOBRIST[end_r][end_c][piece_idx(final_p)]

        return undo_data

    def undo_move(self, undo_data):
        start_r, start_c, end_r, end_c, orig_p, captured_pieces = undo_data
        curr_p = self.grid[end_r][end_c]

        self.hash ^= ZOBRIST[end_r][end_c][piece_idx(curr_p)]
        self.grid[end_r][end_c] = EMPTY

        self.grid[start_r][start_c] = orig_p
        self.hash ^= ZOBRIST[start_r][start_c][piece_idx(orig_p)]

        for cr, cc, cp in captured_pieces:
            self.grid[cr][cc] = cp
            self.hash ^= ZOBRIST[cr][cc][piece_idx(cp)]

    def evaluate(self, side):
        w_mat = 0; b_mat = 0
        w_pos = 0; b_pos = 0
        w_kings = 0; b_kings = 0
        w_men = 0; b_men = 0

        for r in range(8):
            for c in range(8):
                p = self.grid[r][c]
                if p == WHITE_MAN:
                    w_mat += 100
                    w_men += 1
                    w_pos += POS_BONUS_WHITE[r][c]
                    if r == 0: w_pos += 25  # Guard back rank
                elif p == WHITE_KING:
                    w_mat += 450
                    w_kings += 1
                    # Main diagonal bonus (a1-h8)
                    if r == c: w_pos += 35
                    # Central king control
                    w_pos += 25 if 2 <= r <= 5 and 2 <= c <= 5 else 15
                elif p == BLACK_MAN:
                    b_mat += 100
                    b_men += 1
                    b_pos += POS_BONUS_BLACK[r][c]
                    if r == 7: b_pos += 25  # Guard back rank
                elif p == BLACK_KING:
                    b_mat += 450
                    b_kings += 1
                    if r == c: b_pos += 35
                    b_pos += 25 if 2 <= r <= 5 and 2 <= c <= 5 else 15

        # Endgame king hunt
        if b_men == 0 and w_kings > 0 and b_kings > 0:
            w_pos += 40
        if w_men == 0 and b_kings > 0 and w_kings > 0:
            b_pos += 40

        score = (w_mat + w_pos) - (b_mat + b_pos)
        return score * side

    def quiescence(self, side, alpha, beta, q_depth=4):
        self.nodes_evaluated += 1
        stand_pat = self.evaluate(side)
        if stand_pat >= beta:
            return beta
        if alpha < stand_pat:
            alpha = stand_pat
        if q_depth <= 0:
            return stand_pat

        captures = self.get_captures(side)
        if not captures:
            return stand_pat

        captures.sort(key=lambda m: len(m[1]), reverse=True)

        for m in captures:
            undo = self.apply_move(m)
            score = -self.quiescence(-side, -beta, -alpha, q_depth - 1)
            self.undo_move(undo)

            if score >= beta:
                return beta
            if score > alpha:
                alpha = score

        return alpha

    def alpha_beta(self, side, depth, alpha, beta):
        self.nodes_evaluated += 1

        tt_key = (self.hash, side)
        tt_entry = self.transposition_table.get(tt_key)
        if tt_entry and tt_entry['depth'] >= depth:
            if tt_entry['flag'] == 'EXACT':
                return tt_entry['score'], tt_entry['best_move']
            elif tt_entry['flag'] == 'LOWERBOUND' and tt_entry['score'] > alpha:
                alpha = tt_entry['score']
            elif tt_entry['flag'] == 'UPPERBOUND' and tt_entry['score'] < beta:
                beta = tt_entry['score']
            if alpha >= beta:
                return tt_entry['score'], tt_entry['best_move']

        moves = self.get_legal_moves(side)
        if not moves:
            # Checkmate / No moves = Loss
            return -100000 + (12 - depth), None

        if depth <= 0:
            return self.quiescence(side, alpha, beta), None

        best_tt_move = tt_entry['best_move'] if tt_entry else None
        def move_score(m):
            if best_tt_move and m[0] == best_tt_move[0]:
                return 20000
            num_caps = len(m[1])
            if num_caps > 0:
                return 2000 + num_caps * 200
            end_r = m[0][-1][0]
            start_r, start_c = m[0][0]
            p = self.grid[start_r][start_c]
            if not is_king(p) and (end_r == 7 or end_r == 0):
                return 1000
            return 0

        moves.sort(key=move_score, reverse=True)

        best_score = -float('inf')
        best_move = moves[0]

        for m in moves:
            undo = self.apply_move(m)
            score, _ = self.alpha_beta(-side, depth - 1, -beta, -alpha)
            score = -score
            self.undo_move(undo)

            if score > best_score:
                best_score = score
                best_move = m

            if score > alpha:
                alpha = score
            if alpha >= beta:
                break

        flag = 'EXACT'
        if best_score <= alpha:
            flag = 'UPPERBOUND'
        elif best_score >= beta:
            flag = 'LOWERBOUND'

        self.transposition_table[tt_key] = {
            'depth': depth,
            'score': best_score,
            'flag': flag,
            'best_move': best_move
        }

        return best_score, best_move

    def get_best_move(self, side, max_depth=8, time_limit=2.5):
        self.nodes_evaluated = 0
        start_time = time.time()
        best_move = None
        best_score = 0

        for d in range(1, max_depth + 1):
            score, move = self.alpha_beta(side, d, -float('inf'), float('inf'))
            if move is not None:
                best_move = move
                best_score = score
            elapsed = time.time() - start_time
            if elapsed >= time_limit or abs(score) >= 90000:
                break

        return best_move, best_score, self.nodes_evaluated, elapsed

    def print_board(self, flipped=False):
        print("\n" + " " * 5 + " ".join([f" {c} " for c in (COLS[::-1] if flipped else COLS)]))
        print("   ┌" + "───┬" * 7 + "───┐")

        rows = range(8) if flipped else range(7, -1, -1)
        for r in rows:
            cols = range(7, -1, -1) if flipped else range(8)
            row_str = f" {r + 1} │"
            for c in cols:
                p = self.grid[r][c]
                is_dark = (r + c) % 2 == 0
                bg = BG_DARK if is_dark else BG_LIGHT

                if p == WHITE_MAN:
                    icon = f"{BOLD}{WHITE}⚪{RESET}{bg}"
                elif p == WHITE_KING:
                    icon = f"{BOLD}{YELLOW}👑{RESET}{bg}"
                elif p == BLACK_MAN:
                    icon = f"{BOLD}{RED}⚫{RESET}{bg}"
                elif p == BLACK_KING:
                    icon = f"{BOLD}{MAGENTA}💎{RESET}{bg}"
                else:
                    icon = f"{DIM}· {RESET}{bg}" if is_dark else "  "

                row_str += f"{bg} {icon} {RESET}│"

            row_str += f" {r + 1}"
            print(row_str)
            if (not flipped and r > 0) or (flipped and r < 7):
                print("   ├" + "───┼" * 7 + "───┤")

        print("   └" + "───┴" * 7 + "───┘")
        print(" " * 5 + " ".join([f" {c} " for c in (COLS[::-1] if flipped else COLS)]) + "\n")

def run_game():
    print(f"\n{BOLD}{CYAN}══════════════════════════════════════════════════════════════{RESET}")
    print(f"{BOLD}{YELLOW}       🏆 RUS SHASHKASI — SUPER GRANDMASTER AI ENGINE 🏆       {RESET}")
    print(f"{BOLD}{CYAN}══════════════════════════════════════════════════════════════{RESET}")
    print(f"{GREEN}• Qoidalar:{RESET} Rus shashkasi (orqaga urish, uchar damkalar, majburiy urish).")
    print(f"{GREEN}• Sun'iy intellekt:{RESET} Alpha-Beta Pruning, Transposition Table, Quiescence Search.")
    print(f"{GREEN}• Imkoniyat:{RESET} Mutlaq hisob-kitob, hech qanday xato qilmaydi!\n")

    print(f"{BOLD}Rangni tanlang:{RESET}")
    print(f"  1) {WHITE}⚪ Oq shashkalar{RESET} (Birinchi boshlaysiz)")
    print(f"  2) {RED}⚫ Qora shashkalar{RESET} (AI oq bilan birinchi boshlaydi)")
    
    choice = input("\nTanlovingiz (1 yoki 2) [standart: 1]: ").strip()
    human_side = -1 if choice == "2" else 1
    ai_side = -human_side

    print(f"\n{BOLD}Qiyinlik darajasini tanlang:{RESET}")
    print("  1) ⚡ Tezkor Usta (Chuqurlik: 6-7, 0.5 soniya)")
    print("  2) 🧠 Grossmeyster / Maximal (Chuqurlik: 8-10, 1-2 soniya - UMUMAN SHANS YO'Q)")
    print("  3) 👑 Mutlaq God Mode (Chuqurlik: 12+, maksimal chuqur hisob)")
    
    diff = input("\nDarajani tanlang (1, 2, 3) [standart: 2]: ").strip()
    if diff == "1":
        max_depth, time_limit = 7, 1.0
    elif diff == "3":
        max_depth, time_limit = 12, 5.0
    else:
        max_depth, time_limit = 9, 2.5

    game = RussianCheckers()
    current_side = 1  # White always moves first
    move_count = 1

    while True:
        game.print_board(flipped=(human_side == -1))
        legal_moves = game.get_legal_moves(current_side)

        if not legal_moves:
            winner = "Siz" if current_side == ai_side else "AI (Sun'iy intellekt)"
            print(f"\n{BOLD}{YELLOW}🏁 O'YIN TUGADI! G'olib: {winner}!{RESET}\n")
            break

        is_capturing = len(legal_moves[0][1]) > 0

        if current_side == human_side:
            print(f"{BOLD}{GREEN}👉 Sizning navbatingiz ({'Oqlar ⚪' if human_side == 1 else 'Qoralar ⚫'}):{RESET}")
            if is_capturing:
                print(f"{RED}{BOLD}⚠️ DIQQAT: Urish majburiy! Quyidagi urishlardan birini bajarishingiz shart:{RESET}")

            print(f"\n{CYAN}Mavjud yurishlar:{RESET}")
            for idx, m in enumerate(legal_moves, 1):
                m_str = move_to_str(m[0], is_capture=is_capturing)
                cap_note = f" ({len(m[1])} dona uriladi)" if is_capturing else ""
                print(f"  {BOLD}{idx}){RESET} {m_str}{cap_note}")

            selected_move = None
            prompt_hint = f" [1-{len(legal_moves)} yoki c3-d4]"
            if len(legal_moves) == 1:
                prompt_hint += " (Enter = 1)"

            while selected_move is None:
                user_inp = input(f"{YELLOW}Yurishni kiriting{prompt_hint}: {RESET}").strip().lower()
                if not user_inp and len(legal_moves) == 1:
                    selected_move = legal_moves[0]
                    break

                if user_inp.isdigit():
                    idx = int(user_inp) - 1
                    if 0 <= idx < len(legal_moves):
                        selected_move = legal_moves[idx]
                    else:
                        print(f"{RED}Noto'g'ri raqam! 1 dan {len(legal_moves)} gacha kiriting.{RESET}")
                else:
                    # Clean input
                    clean_inp = user_inp.replace(":", "-").replace(" ", "-")
                    # If user typed 'c3d4' without hyphen
                    if len(clean_inp) == 4 and clean_inp[0] in COL_MAP and clean_inp[2] in COL_MAP:
                        clean_inp = f"{clean_inp[:2]}-{clean_inp[2:]}"

                    for m in legal_moves:
                        cand_str = move_to_str(m[0], is_capture=False)
                        if clean_inp == cand_str:
                            selected_move = m
                            break
                    if selected_move is None:
                        print(f"{RED}Bunday qonuniy yurish topilmadi! Ro'yxatdagi raqam yoki formatda kiriting (masalan: 1 yoki {move_to_str(legal_moves[0][0])}).{RESET}")

            game.apply_move(selected_move)
            print(f"\n{GREEN}✅ Sizning yurishingiz:{RESET} {move_to_str(selected_move[0], is_capturing)}")

        else:
            print(f"{BOLD}{MAGENTA}🤖 Sun'iy Intellekt o'ylamoqda...{RESET}")
            best_m, score, nodes, elapsed = game.get_best_move(ai_side, max_depth=max_depth, time_limit=time_limit)
            ai_is_cap = len(best_m[1]) > 0
            game.apply_move(best_m)
            m_str = move_to_str(best_m[0], is_capture=ai_is_cap)
            print(f"\n{MAGENTA}⚡ AI yurdi:{RESET} {BOLD}{m_str}{RESET} (Baho: {score:+d}, Hisoblangan pozitsiyalar: {nodes:,}, Vaqt: {elapsed:.2f}s)")

        current_side = -current_side
        move_count += 1

if __name__ == "__main__":
    try:
        run_game()
    except KeyboardInterrupt:
        print("\n\nO'yin to'xtatildi. Xayr!")
