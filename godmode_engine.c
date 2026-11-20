#define _GNU_SOURCE
#include <stdint.h>
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <time.h>
#include <omp.h>

#define EMPTY 0
#define W_MAN 1
#define W_KING 2
#define B_MAN 3
#define B_KING 4

#define INF_SCORE 100000000
#define WIN_SCORE  9999999
#define MAX_MOVES 256
#define MAX_PLY 64
#define TT_SIZE (1 << 22) // 4,194,304 entries (~64 MB, 16-byte aligned)
#define MAX_THREADS 4
#define NUM_EVAL_PARAMS 24

typedef struct {
    int32_t man_base;           // 0: default 1000
    int32_t king_base;          // 1: default 4100
    int32_t center_weight;      // 2: default 140
    int32_t edge_penalty;       // 3: default 115
    int32_t passed_rank_7;      // 4: default 1800
    int32_t passed_rank_6;      // 5: default 880
    int32_t protection_bonus;   // 6: default 48
    int32_t back_rank_4;        // 7: default 320
    int32_t back_rank_3;        // 8: default 190
    int32_t back_rank_2;        // 9: default 85
    int32_t kolonka_1;          // 10: default 270
    int32_t kolonka_2;          // 11: default 240
    int32_t center_hole;        // 12: default 150
    int32_t golden_pawn_bonus;  // 13: default 600
    int32_t golden_pawn_penalty;// 14: default 400
    int32_t mostik_bridge;      // 15: default 460
    int32_t outpost_d4_e5;      // 16: default 500
    int32_t wedge_c5_f4;        // 17: default 600
    int32_t kolkashev_pin;      // 18: default 600
    int32_t mobility_weight;    // 19: default 34
    int32_t king_main_diag;     // 20: default 980
    int32_t king_dvoinik;       // 21: default 450
    int32_t king_troinik;       // 22: default 220
    int32_t liquidation_bonus;  // 23: default 105
} EvalParams;

static EvalParams g_eval_params = {
    1000, 4100, 140, 115, 1800, 880, 48,
    320, 190, 85, 270, 240, 150,
    600, 400, 460, 500, 600, 600,
    34, 980, 450, 220, 105
};

void godmode_get_eval_params(int32_t *out_params) {
    if (!out_params) return;
    memcpy(out_params, &g_eval_params, sizeof(EvalParams));
}

void godmode_set_eval_params(const int32_t *in_params) {
    if (!in_params) return;
    memcpy(&g_eval_params, in_params, sizeof(EvalParams));
}

static const int8_t COORDS_R[32] = {
    0, 0, 0, 0,
    1, 1, 1, 1,
    2, 2, 2, 2,
    3, 3, 3, 3,
    4, 4, 4, 4,
    5, 5, 5, 5,
    6, 6, 6, 6,
    7, 7, 7, 7
};

static const int8_t COORDS_C[32] = {
    1, 3, 5, 7,
    0, 2, 4, 6,
    1, 3, 5, 7,
    0, 2, 4, 6,
    1, 3, 5, 7,
    0, 2, 4, 6,
    1, 3, 5, 7,
    0, 2, 4, 6
};

// DIRS: (-1, -1), (-1, 1), (1, -1), (1, 1)
static const int8_t STEP_TABLE[32][4] = {
    {-1, -1, 4, 5},
    {-1, -1, 5, 6},
    {-1, -1, 6, 7},
    {-1, -1, 7, -1},
    {-1, 0, -1, 8},
    {0, 1, 8, 9},
    {1, 2, 9, 10},
    {2, 3, 10, 11},
    {4, 5, 12, 13},
    {5, 6, 13, 14},
    {6, 7, 14, 15},
    {7, -1, 15, -1},
    {-1, 8, -1, 16},
    {8, 9, 16, 17},
    {9, 10, 17, 18},
    {10, 11, 18, 19},
    {12, 13, 20, 21},
    {13, 14, 21, 22},
    {14, 15, 22, 23},
    {15, -1, 23, -1},
    {-1, 16, -1, 24},
    {16, 17, 24, 25},
    {17, 18, 25, 26},
    {18, 19, 26, 27},
    {20, 21, 28, 29},
    {21, 22, 29, 30},
    {22, 23, 30, 31},
    {23, -1, 31, -1},
    {-1, 24, -1, -1},
    {24, 25, -1, -1},
    {25, 26, -1, -1},
    {26, 27, -1, -1}
};

static const int8_t JUMP_MID[32][4] = {
    {-1, -1, -1, 5},
    {-1, -1, 5, 6},
    {-1, -1, 6, 7},
    {-1, -1, 7, -1},
    {-1, -1, -1, 8},
    {-1, -1, 8, 9},
    {-1, -1, 9, 10},
    {-1, -1, 10, -1},
    {-1, 5, -1, 13},
    {5, 6, 13, 14},
    {6, 7, 14, 15},
    {7, -1, 15, -1},
    {-1, 8, -1, 16},
    {8, 9, 16, 17},
    {9, 10, 17, 18},
    {10, -1, 18, -1},
    {-1, 13, -1, 21},
    {13, 14, 21, 22},
    {14, 15, 22, 23},
    {15, -1, 23, -1},
    {-1, 16, -1, 24},
    {16, 17, 24, 25},
    {17, 18, 25, 26},
    {18, -1, 26, -1},
    {-1, 21, -1, -1},
    {21, 22, -1, -1},
    {22, 23, -1, -1},
    {23, -1, -1, -1},
    {-1, 24, -1, -1},
    {24, 25, -1, -1},
    {25, 26, -1, -1},
    {26, -1, -1, -1}
};

static const int8_t JUMP_LAND[32][4] = {
    {-1, -1, -1, 9},
    {-1, -1, 8, 10},
    {-1, -1, 9, 11},
    {-1, -1, 10, -1},
    {-1, -1, -1, 13},
    {-1, -1, 12, 14},
    {-1, -1, 13, 15},
    {-1, -1, 14, -1},
    {-1, 1, -1, 17},
    {0, 2, 16, 18},
    {1, 3, 17, 19},
    {2, -1, 18, -1},
    {-1, 5, -1, 21},
    {4, 6, 20, 22},
    {5, 7, 21, 23},
    {6, -1, 22, -1},
    {-1, 9, -1, 25},
    {8, 10, 24, 26},
    {9, 11, 25, 27},
    {10, -1, 26, -1},
    {-1, 13, -1, 29},
    {12, 14, 28, 30},
    {13, 15, 29, 31},
    {14, -1, 30, -1},
    {-1, 17, -1, -1},
    {16, 18, -1, -1},
    {17, 19, -1, -1},
    {18, -1, -1, -1},
    {-1, 21, -1, -1},
    {20, 22, -1, -1},
    {21, 23, -1, -1},
    {22, -1, -1, -1}
};

static const int8_t RAYS[32][4][8] = {
    {{-1, -1, -1, -1, -1, -1, -1, -1}, {-1, -1, -1, -1, -1, -1, -1, -1}, {4, -1, -1, -1, -1, -1, -1, -1}, {5, 9, 14, 18, 23, 27, -1, -1}},
    {{-1, -1, -1, -1, -1, -1, -1, -1}, {-1, -1, -1, -1, -1, -1, -1, -1}, {5, 8, 12, -1, -1, -1, -1, -1}, {6, 10, 15, 19, -1, -1, -1, -1}},
    {{-1, -1, -1, -1, -1, -1, -1, -1}, {-1, -1, -1, -1, -1, -1, -1, -1}, {6, 9, 13, 16, 20, -1, -1, -1}, {7, 11, -1, -1, -1, -1, -1, -1}},
    {{-1, -1, -1, -1, -1, -1, -1, -1}, {-1, -1, -1, -1, -1, -1, -1, -1}, {7, 10, 14, 17, 21, 24, 28, -1}, {-1, -1, -1, -1, -1, -1, -1, -1}},
    {{-1, -1, -1, -1, -1, -1, -1, -1}, {0, -1, -1, -1, -1, -1, -1, -1}, {-1, -1, -1, -1, -1, -1, -1, -1}, {8, 13, 17, 22, 26, 31, -1, -1}},
    {{0, -1, -1, -1, -1, -1, -1, -1}, {1, -1, -1, -1, -1, -1, -1, -1}, {8, 12, -1, -1, -1, -1, -1, -1}, {9, 14, 18, 23, 27, -1, -1, -1}},
    {{1, -1, -1, -1, -1, -1, -1, -1}, {2, -1, -1, -1, -1, -1, -1, -1}, {9, 13, 16, 20, -1, -1, -1, -1}, {10, 15, 19, -1, -1, -1, -1, -1}},
    {{2, -1, -1, -1, -1, -1, -1, -1}, {3, -1, -1, -1, -1, -1, -1, -1}, {10, 14, 17, 21, 24, 28, -1, -1}, {11, -1, -1, -1, -1, -1, -1, -1}},
    {{4, -1, -1, -1, -1, -1, -1, -1}, {5, 1, -1, -1, -1, -1, -1, -1}, {12, -1, -1, -1, -1, -1, -1, -1}, {13, 17, 22, 26, 31, -1, -1, -1}},
    {{5, 0, -1, -1, -1, -1, -1, -1}, {6, 2, -1, -1, -1, -1, -1, -1}, {13, 16, 20, -1, -1, -1, -1, -1}, {14, 18, 23, 27, -1, -1, -1, -1}},
    {{6, 1, -1, -1, -1, -1, -1, -1}, {7, 3, -1, -1, -1, -1, -1, -1}, {14, 17, 21, 24, 28, -1, -1, -1}, {15, 19, -1, -1, -1, -1, -1, -1}},
    {{7, 2, -1, -1, -1, -1, -1, -1}, {-1, -1, -1, -1, -1, -1, -1, -1}, {15, 18, 22, 25, 29, -1, -1, -1}, {-1, -1, -1, -1, -1, -1, -1, -1}},
    {{-1, -1, -1, -1, -1, -1, -1, -1}, {8, 5, 1, -1, -1, -1, -1, -1}, {-1, -1, -1, -1, -1, -1, -1, -1}, {16, 21, 25, 30, -1, -1, -1, -1}},
    {{8, 4, -1, -1, -1, -1, -1, -1}, {9, 6, 2, -1, -1, -1, -1, -1}, {16, 20, -1, -1, -1, -1, -1, -1}, {17, 22, 26, 31, -1, -1, -1, -1}},
    {{9, 5, 0, -1, -1, -1, -1, -1}, {10, 7, 3, -1, -1, -1, -1, -1}, {17, 21, 24, 28, -1, -1, -1, -1}, {18, 23, 27, -1, -1, -1, -1, -1}},
    {{10, 6, 1, -1, -1, -1, -1, -1}, {11, -1, -1, -1, -1, -1, -1, -1}, {18, 22, 25, 29, -1, -1, -1, -1}, {19, -1, -1, -1, -1, -1, -1, -1}},
    {{12, -1, -1, -1, -1, -1, -1, -1}, {13, 9, 6, 2, -1, -1, -1, -1}, {20, -1, -1, -1, -1, -1, -1, -1}, {21, 25, 30, -1, -1, -1, -1, -1}},
    {{13, 8, 4, -1, -1, -1, -1, -1}, {14, 10, 7, 3, -1, -1, -1, -1}, {21, 24, 28, -1, -1, -1, -1, -1}, {22, 26, 31, -1, -1, -1, -1, -1}},
    {{14, 9, 5, 0, -1, -1, -1, -1}, {15, 11, -1, -1, -1, -1, -1, -1}, {22, 25, 29, -1, -1, -1, -1, -1}, {23, 27, -1, -1, -1, -1, -1, -1}},
    {{15, 10, 6, 1, -1, -1, -1, -1}, {-1, -1, -1, -1, -1, -1, -1, -1}, {23, 26, 30, -1, -1, -1, -1, -1}, {-1, -1, -1, -1, -1, -1, -1, -1}},
    {{-1, -1, -1, -1, -1, -1, -1, -1}, {16, 13, 9, 6, 2, -1, -1, -1}, {-1, -1, -1, -1, -1, -1, -1, -1}, {24, 29, -1, -1, -1, -1, -1, -1}},
    {{16, 12, -1, -1, -1, -1, -1, -1}, {17, 14, 10, 7, 3, -1, -1, -1}, {24, 28, -1, -1, -1, -1, -1, -1}, {25, 30, -1, -1, -1, -1, -1, -1}},
    {{17, 13, 8, 4, -1, -1, -1, -1}, {18, 15, 11, -1, -1, -1, -1, -1}, {25, 29, -1, -1, -1, -1, -1, -1}, {26, 31, -1, -1, -1, -1, -1, -1}},
    {{18, 14, 9, 5, 0, -1, -1, -1}, {19, -1, -1, -1, -1, -1, -1, -1}, {26, 30, -1, -1, -1, -1, -1, -1}, {27, -1, -1, -1, -1, -1, -1, -1}},
    {{20, -1, -1, -1, -1, -1, -1, -1}, {21, 17, 14, 10, 7, 3, -1, -1}, {28, -1, -1, -1, -1, -1, -1, -1}, {29, -1, -1, -1, -1, -1, -1, -1}},
    {{21, 16, 12, -1, -1, -1, -1, -1}, {22, 18, 15, 11, -1, -1, -1, -1}, {29, -1, -1, -1, -1, -1, -1, -1}, {30, -1, -1, -1, -1, -1, -1, -1}},
    {{22, 17, 13, 8, 4, -1, -1, -1}, {23, 19, -1, -1, -1, -1, -1, -1}, {30, -1, -1, -1, -1, -1, -1, -1}, {31, -1, -1, -1, -1, -1, -1, -1}},
    {{23, 18, 14, 9, 5, 0, -1, -1}, {-1, -1, -1, -1, -1, -1, -1, -1}, {31, -1, -1, -1, -1, -1, -1, -1}, {-1, -1, -1, -1, -1, -1, -1, -1}},
    {{-1, -1, -1, -1, -1, -1, -1, -1}, {24, 21, 17, 14, 10, 7, 3, -1}, {-1, -1, -1, -1, -1, -1, -1, -1}, {-1, -1, -1, -1, -1, -1, -1, -1}},
    {{24, 20, -1, -1, -1, -1, -1, -1}, {25, 22, 18, 15, 11, -1, -1, -1}, {-1, -1, -1, -1, -1, -1, -1, -1}, {-1, -1, -1, -1, -1, -1, -1, -1}},
    {{25, 21, 16, 12, -1, -1, -1, -1}, {26, 23, 19, -1, -1, -1, -1, -1}, {-1, -1, -1, -1, -1, -1, -1, -1}, {-1, -1, -1, -1, -1, -1, -1, -1}},
    {{26, 22, 17, 13, 8, 4, -1, -1}, {27, -1, -1, -1, -1, -1, -1, -1}, {-1, -1, -1, -1, -1, -1, -1, -1}, {-1, -1, -1, -1, -1, -1, -1, -1}}
};

static const uint32_t MAIN_DIAG_MASK = (1U<<3)|(1U<<7)|(1U<<10)|(1U<<14)|(1U<<17)|(1U<<21)|(1U<<24)|(1U<<28);
static const uint32_t DVOINIK_MASK   = (1U<<29)|(1U<<25)|(1U<<22)|(1U<<18)|(1U<<15)|(1U<<11)|(1U<<20)|(1U<<16)|(1U<<13)|(1U<<9)|(1U<<6)|(1U<<2);
static const uint32_t TROINIK_MASK   = (1U<<30)|(1U<<26)|(1U<<23)|(1U<<19)|(1U<<12)|(1U<<8)|(1U<<5)|(1U<<1);
static const uint32_t EDGE_MASK      = (1U<<4)|(1U<<12)|(1U<<20)|(1U<<28)|(1U<<3)|(1U<<11)|(1U<<19)|(1U<<27);
static const uint32_t CENTER_MASK    = (1U<<13)|(1U<<14)|(1U<<17)|(1U<<18);
static const uint32_t WHITE_BACK_MASK= (1U<<28)|(1U<<29)|(1U<<30)|(1U<<31);
static const uint32_t BLACK_BACK_MASK= (1U<<0)|(1U<<1)|(1U<<2)|(1U<<3);

// Piece-Square Tables (PST) - Positional Values
static const int32_t W_MAN_PST[32] = {
      0,   0,   0,   0,
     85,  98,  98,  85,
     65,  80,  80,  60,
     50,  70,  70,  50,
     40,  60,  60,  35,
     25,  40,  40,  25,
     18,  30,  30,  18,
     12,  22,  22,  12
};

static const int32_t B_MAN_PST[32] = {
     12,  22,  22,  12,
     18,  30,  30,  18,
     25,  40,  40,  25,
     40,  60,  60,  35,
     50,  70,  70,  50,
     65,  80,  80,  60,
     85,  98,  98,  85,
      0,   0,   0,   0
};

static const int32_t KING_PST[32] = {
     45,  60,  60,  45,
     50,  90,  90,  50,
     55, 105, 105,  55,
     60, 120, 120,  60,
     60, 120, 120,  60,
     55, 105, 105,  55,
     50,  90,  90,  50,
     45,  60,  60,  45
};

// Zobrist keys
static uint64_t ZOBRIST[32][5];
static uint64_t ZOBRIST_TURN;

typedef struct {
    int8_t from;
    int8_t to;
    int8_t is_capture;
    int8_t promotes;
    int8_t cap_count;
    uint32_t cap_mask;
    int8_t new_board[32];
} CMove;

typedef struct __attribute__((aligned(16))) {
    uint64_t key;
    int16_t depth;
    int8_t flag; // 0 = EXACT, 1 = LOWER (beta cutoff), 2 = UPPER (alpha fail-low)
    int8_t age;
    int32_t score;
    uint16_t best_move;
    int16_t reserved;
} TTEntry;

static TTEntry TT[TT_SIZE];
static uint8_t tt_current_age = 0;

static uint16_t killer_moves[MAX_THREADS][MAX_PLY][2];
static uint16_t counter_moves[MAX_THREADS][32][32];
static int32_t history[MAX_THREADS][2][32][32];

static uint64_t search_nodes = 0;
static struct timespec search_start;
static double search_time_limit = 2.5;
static volatile bool search_stopped = false;
static bool g_flying_kings = true;

static uint64_t rng64(void) {
    static uint64_t s = 0x853c49e6748fea9bULL;
    s ^= s << 13;
    s ^= s >> 7;
    s ^= s << 17;
    return s;
}

static inline int score_to_tt(int score, int ply) {
    if (score >= WIN_SCORE - MAX_PLY) return score + ply;
    if (score <= -WIN_SCORE + MAX_PLY) return score - ply;
    return score;
}

static inline int score_from_tt(int score, int ply) {
    if (score >= WIN_SCORE - MAX_PLY) return score - ply;
    if (score <= -WIN_SCORE + MAX_PLY) return score + ply;
    return score;
}

void godmode_init(void) {
    for (int sq = 0; sq < 32; sq++) {
        for (int p = 0; p < 5; p++) {
            ZOBRIST[sq][p] = rng64();
        }
    }
    ZOBRIST_TURN = rng64();
    memset(TT, 0, sizeof(TT));
    memset(killer_moves, 0, sizeof(killer_moves));
    memset(counter_moves, 0, sizeof(counter_moves));
    memset(history, 0, sizeof(history));
    tt_current_age = 0;
}

void godmode_clear_tt(void) {
    memset(TT, 0, sizeof(TT));
    memset(killer_moves, 0, sizeof(killer_moves));
    memset(counter_moves, 0, sizeof(counter_moves));
    memset(history, 0, sizeof(history));
    tt_current_age++;
}

static inline double get_elapsed_sec(void) {
    struct timespec now;
    clock_gettime(CLOCK_MONOTONIC, &now);
    return (now.tv_sec - search_start.tv_sec) + (now.tv_nsec - search_start.tv_nsec) * 1e-9;
}

static inline uint64_t compute_hash(const int8_t *b, int turn) {
    uint64_t h = 0;
    for (int sq = 0; sq < 32; sq++) {
        int8_t p = b[sq];
        if (p != EMPTY) h ^= ZOBRIST[sq][p];
    }
    if (turn == 1) h ^= ZOBRIST_TURN;
    return h;
}

// Full Russian Checkers Recursive Capture Generator with Turkish Strike & Immediate Promotion
static void get_piece_caps(int8_t *b, int sq, int piece, int seat, uint32_t cap_mask, int root_sq, CMove *out_moves, int *out_count) {
    bool is_king = (piece == W_KING || piece == B_KING);
    int opp_min = (seat == 0) ? 3 : 1;
    int opp_max = (seat == 0) ? 4 : 2;

    if (!is_king || !g_flying_kings) {
        for (int d = 0; d < 4; d++) {
            int mid = JUMP_MID[sq][d];
            int land = JUMP_LAND[sq][d];
            if (mid != -1 && !(cap_mask & (1U << mid))) {
                int8_t mid_p = b[mid];
                // Opponent piece on mid, and land is empty and was not previously jumped
                if (mid_p >= opp_min && mid_p <= opp_max && b[land] == EMPTY && !(cap_mask & (1U << land))) {
                    int new_p = piece;
                    bool promo = false;
                    // Russian Checkers promotion during multi-jump
                    if (piece == W_MAN && land < 4) { new_p = W_KING; promo = true; }
                    else if (piece == B_MAN && land >= 28) { new_p = B_KING; promo = true; }

                    uint32_t new_mask = cap_mask | (1U << mid);
                    b[sq] = EMPTY;
                    b[land] = new_p;

                    int prev_cnt = *out_count;
                    get_piece_caps(b, land, new_p, seat, new_mask, root_sq, out_moves, out_count);
                    if (*out_count == prev_cnt && *out_count < MAX_MOVES) {
                        CMove *m = &out_moves[(*out_count)++];
                        m->from = root_sq;
                        m->to = land;
                        m->is_capture = 1;
                        m->promotes = promo ? 1 : 0;
                        m->cap_count = __builtin_popcount(new_mask);
                        m->cap_mask = new_mask;
                        memcpy(m->new_board, b, 32);
                        // Turkish strike: captured pieces removed only after jump finishes
                        for (int k = 0; k < 32; k++) {
                            if (new_mask & (1U << k)) m->new_board[k] = EMPTY;
                        }
                    }

                    b[land] = EMPTY;
                    b[sq] = piece;
                }
            }
        }
    } else {
        // Flying King Multi-Captures
        for (int d = 0; d < 4; d++) {
            int opp_sq = -1;
            for (int r = 0; r < 8; r++) {
                int r_sq = RAYS[sq][d][r];
                if (r_sq == -1) break;
                if (cap_mask & (1U << r_sq)) break;
                int8_t p = b[r_sq];
                if (p == EMPTY) {
                    if (opp_sq != -1) {
                        uint32_t new_mask = cap_mask | (1U << opp_sq);
                        b[sq] = EMPTY;
                        b[r_sq] = piece;

                        int prev_cnt = *out_count;
                        get_piece_caps(b, r_sq, piece, seat, new_mask, root_sq, out_moves, out_count);
                        if (*out_count == prev_cnt && *out_count < MAX_MOVES) {
                            CMove *m = &out_moves[(*out_count)++];
                            m->from = root_sq;
                            m->to = r_sq;
                            m->is_capture = 1;
                            m->promotes = 0;
                            m->cap_count = __builtin_popcount(new_mask);
                            m->cap_mask = new_mask;
                            memcpy(m->new_board, b, 32);
                            for (int k = 0; k < 32; k++) {
                                if (new_mask & (1U << k)) m->new_board[k] = EMPTY;
                            }
                        }

                        b[r_sq] = EMPTY;
                        b[sq] = piece;
                    }
                } else if (p >= opp_min && p <= opp_max) {
                    if (opp_sq == -1) {
                        opp_sq = r_sq;
                    } else {
                        // Two enemy pieces in a row along ray cannot be jumped
                        break;
                    }
                } else {
                    // Friendly piece blocks ray
                    break;
                }
            }
        }
    }
}

static int generate_moves(int8_t *b, int seat, CMove *out_moves, bool *out_is_cap) {
    int count = 0;
    int own_min = (seat == 0) ? 1 : 3;
    int own_max = (seat == 0) ? 2 : 4;

    // 1. Mandatory Captures
    for (int sq = 0; sq < 32; sq++) {
        int8_t p = b[sq];
        if (p >= own_min && p <= own_max) {
            get_piece_caps(b, sq, p, seat, 0, sq, out_moves, &count);
        }
    }

    if (count > 0) {
        *out_is_cap = true;
        return count;
    }

    *out_is_cap = false;
    // 2. Quiet Moves
    for (int sq = 0; sq < 32; sq++) {
        int8_t p = b[sq];
        if (p < own_min || p > own_max) continue;

        if (p == W_MAN) {
            for (int d = 0; d < 2; d++) {
                int nxt = STEP_TABLE[sq][d];
                if (nxt != -1 && b[nxt] == EMPTY && count < MAX_MOVES) {
                    CMove *m = &out_moves[count++];
                    m->from = sq;
                    m->to = nxt;
                    m->is_capture = 0;
                    m->promotes = (nxt < 4);
                    m->cap_count = 0;
                    m->cap_mask = 0;
                    memcpy(m->new_board, b, 32);
                    m->new_board[sq] = EMPTY;
                    m->new_board[nxt] = m->promotes ? W_KING : W_MAN;
                }
            }
        } else if (p == B_MAN) {
            for (int d = 2; d < 4; d++) {
                int nxt = STEP_TABLE[sq][d];
                if (nxt != -1 && b[nxt] == EMPTY && count < MAX_MOVES) {
                    CMove *m = &out_moves[count++];
                    m->from = sq;
                    m->to = nxt;
                    m->is_capture = 0;
                    m->promotes = (nxt >= 28);
                    m->cap_count = 0;
                    m->cap_mask = 0;
                    memcpy(m->new_board, b, 32);
                    m->new_board[sq] = EMPTY;
                    m->new_board[nxt] = m->promotes ? B_KING : B_MAN;
                }
            }
        } else {
            // King quiet moves
            if (g_flying_kings) {
                for (int d = 0; d < 4; d++) {
                    for (int r = 0; r < 8; r++) {
                        int nxt = RAYS[sq][d][r];
                        if (nxt == -1) break;
                        if (b[nxt] == EMPTY && count < MAX_MOVES) {
                            CMove *m = &out_moves[count++];
                            m->from = sq;
                            m->to = nxt;
                            m->is_capture = 0;
                            m->promotes = 0;
                            m->cap_count = 0;
                            m->cap_mask = 0;
                            memcpy(m->new_board, b, 32);
                            m->new_board[sq] = EMPTY;
                            m->new_board[nxt] = p;
                        } else {
                            break;
                        }
                    }
                }
            } else {
                for (int d = 0; d < 4; d++) {
                    int nxt = STEP_TABLE[sq][d];
                    if (nxt != -1 && b[nxt] == EMPTY && count < MAX_MOVES) {
                        CMove *m = &out_moves[count++];
                        m->from = sq;
                        m->to = nxt;
                        m->is_capture = 0;
                        m->promotes = 0;
                        m->cap_count = 0;
                        m->cap_mask = 0;
                        memcpy(m->new_board, b, 32);
                        m->new_board[sq] = EMPTY;
                        m->new_board[nxt] = p;
                    }
                }
            }
        }
    }
    return count;
}

// Exact Russian Checkers Endgame Solver & Tablebase Logic
static inline bool solve_exact_endgame(const int8_t *b, int ai_seat, int turn_seat, int *exact_score) {
    int w_men = 0, b_men = 0, w_kings = 0, b_kings = 0;
    int w_k_sq[4], b_k_sq[4];

    for (int sq = 0; sq < 32; sq++) {
        int8_t p = b[sq];
        if (p == W_MAN) w_men++;
        else if (p == B_MAN) b_men++;
        else if (p == W_KING) { if (w_kings < 4) w_k_sq[w_kings] = sq; w_kings++; }
        else if (p == B_KING) { if (b_kings < 4) b_k_sq[b_kings] = sq; b_kings++; }
    }

    int total_pieces = w_men + b_men + w_kings + b_kings;

    // 1. 1 King vs 1 King: If either king holds Main Diagonal, it's a proven mathematical DRAW
    if (w_men == 0 && b_men == 0 && w_kings == 1 && b_kings == 1) {
        int wk = w_k_sq[0];
        int bk = b_k_sq[0];
        if ((MAIN_DIAG_MASK & (1U << wk)) || (MAIN_DIAG_MASK & (1U << bk))) {
            *exact_score = 0;
            return true;
        }
    }

    // 2. Petrov's Triangle: 3 Kings vs 1 King (Classic Endgame Theorem)
    if (w_men == 0 && b_men == 0 && w_kings >= 3 && b_kings == 1) {
        int bk = b_k_sq[0];
        if (!(MAIN_DIAG_MASK & (1U << bk))) {
            // Lone king is off the Main Diagonal: 100% Guaranteed Forced Win in <= 15 moves
            *exact_score = (ai_seat == 0) ? (WIN_SCORE - 30) : (-WIN_SCORE + 30);
            return true;
        }
    } else if (w_men == 0 && b_men == 0 && b_kings >= 3 && w_kings == 1) {
        int wk = w_k_sq[0];
        if (!(MAIN_DIAG_MASK & (1U << wk))) {
            *exact_score = (ai_seat == 1) ? (WIN_SCORE - 30) : (-WIN_SCORE + 30);
            return true;
        }
    }

    // 3. 2 Kings vs 1 King in Corner / Double Corner
    if (w_men == 0 && b_men == 0 && w_kings >= 2 && b_kings == 1) {
        int bk = b_k_sq[0];
        // If lone king is trapped on corners (0, 7, 24, 31)
        if (bk == 0 || bk == 7 || bk == 24 || bk == 31) {
            *exact_score = (ai_seat == 0) ? (WIN_SCORE - 50) : (-WIN_SCORE + 50);
            return true;
        }
    } else if (w_men == 0 && b_men == 0 && b_kings >= 2 && w_kings == 1) {
        int wk = w_k_sq[0];
        if (wk == 0 || wk == 7 || wk == 24 || wk == 31) {
            *exact_score = (ai_seat == 1) ? (WIN_SCORE - 50) : (-WIN_SCORE + 50);
            return true;
        }
    }

    // 4. Opposition Parity in 1 vs 1 Men Ending (Without Kings)
    if (total_pieces == 2 && w_men == 1 && b_men == 1 && w_kings == 0 && b_kings == 0) {
        int w_sq = -1, b_sq = -1;
        for (int i = 0; i < 32; i++) {
            if (b[i] == W_MAN) w_sq = i;
            if (b[i] == B_MAN) b_sq = i;
        }
        if (w_sq != -1 && b_sq != -1) {
            int dist = abs(COORDS_R[w_sq] - COORDS_R[b_sq]) + abs(COORDS_C[w_sq] - COORDS_C[b_sq]);
            if (dist % 2 == 1) {
                // Favorable opposition for the side to move
                int favored = (turn_seat == 0) ? 0 : 1;
                *exact_score = (ai_seat == favored) ? 8000 : -8000;
                return true;
            }
        }
    }

    return false;
}

// Ultra Master Positional & Tactical Evaluation with Dynamically Tunable Weights
static int evaluate(const int8_t *b, int ai_seat, int turn_seat) {
    int exact_val = 0;
    if (solve_exact_endgame(b, ai_seat, turn_seat, &exact_val)) {
        return exact_val;
    }

    int32_t w_score = 0, b_score = 0;
    int w_men = 0, b_men = 0, w_kings = 0, b_kings = 0;
    int w_mob = 0, b_mob = 0;
    uint32_t w_mask = 0, b_mask = 0;

    for (int sq = 0; sq < 32; sq++) {
        int8_t p = b[sq];
        if (p == EMPTY) continue;
        if (p <= 2) {
            w_mask |= (1U << sq);
            if (p == W_MAN) {
                w_men++;
                w_score += g_eval_params.man_base + W_MAN_PST[sq];
                if (CENTER_MASK & (1U << sq)) w_score += g_eval_params.center_weight;
                if (EDGE_MASK & (1U << sq)) w_score -= g_eval_params.edge_penalty;

                // Passed pawn / Candidate King
                int8_t r = COORDS_R[sq];
                if (r == 1) w_score += g_eval_params.passed_rank_7;
                else if (r == 2) w_score += g_eval_params.passed_rank_6;

                // Protection check
                for (int d = 2; d < 4; d++) {
                    int behind = STEP_TABLE[sq][d];
                    if (behind != -1 && b[behind] == W_MAN) {
                        w_score += g_eval_params.protection_bonus;
                        break;
                    }
                }

                for (int d = 0; d < 2; d++) {
                    int nxt = STEP_TABLE[sq][d];
                    if (nxt != -1 && b[nxt] == EMPTY) w_mob++;
                }
            } else {
                w_kings++;
                w_score += g_eval_params.king_base + KING_PST[sq];
                if (MAIN_DIAG_MASK & (1U << sq)) w_score += g_eval_params.king_main_diag;
                if (DVOINIK_MASK & (1U << sq)) w_score += g_eval_params.king_dvoinik;
                if (TROINIK_MASK & (1U << sq)) w_score += g_eval_params.king_troinik;
                if (g_flying_kings) {
                    for (int d = 0; d < 4; d++) {
                        for (int r = 0; r < 8; r++) {
                            int nxt = RAYS[sq][d][r];
                            if (nxt == -1) break;
                            if (b[nxt] == EMPTY) w_mob += 2;
                            else break;
                        }
                    }
                } else {
                    for (int d = 0; d < 4; d++) {
                        int nxt = STEP_TABLE[sq][d];
                        if (nxt != -1 && b[nxt] == EMPTY) w_mob += 2;
                    }
                }
            }
        } else {
            b_mask |= (1U << sq);
            if (p == B_MAN) {
                b_men++;
                b_score += g_eval_params.man_base + B_MAN_PST[sq];
                if (CENTER_MASK & (1U << sq)) b_score += g_eval_params.center_weight;
                if (EDGE_MASK & (1U << sq)) b_score -= g_eval_params.edge_penalty;

                int8_t r = COORDS_R[sq];
                if (r == 6) b_score += g_eval_params.passed_rank_7;
                else if (r == 5) b_score += g_eval_params.passed_rank_6;

                for (int d = 0; d < 2; d++) {
                    int behind = STEP_TABLE[sq][d];
                    if (behind != -1 && b[behind] == B_MAN) {
                        b_score += g_eval_params.protection_bonus;
                        break;
                    }
                }

                for (int d = 2; d < 4; d++) {
                    int nxt = STEP_TABLE[sq][d];
                    if (nxt != -1 && b[nxt] == EMPTY) b_mob++;
                }
            } else {
                b_kings++;
                b_score += g_eval_params.king_base + KING_PST[sq];
                if (MAIN_DIAG_MASK & (1U << sq)) b_score += g_eval_params.king_main_diag;
                if (DVOINIK_MASK & (1U << sq)) b_score += g_eval_params.king_dvoinik;
                if (TROINIK_MASK & (1U << sq)) b_score += g_eval_params.king_troinik;
                if (g_flying_kings) {
                    for (int d = 0; d < 4; d++) {
                        for (int r = 0; r < 8; r++) {
                            int nxt = RAYS[sq][d][r];
                            if (nxt == -1) break;
                            if (b[nxt] == EMPTY) b_mob += 2;
                            else break;
                        }
                    }
                } else {
                    for (int d = 0; d < 4; d++) {
                        int nxt = STEP_TABLE[sq][d];
                        if (nxt != -1 && b[nxt] == EMPTY) b_mob += 2;
                    }
                }
            }
        }
    }

    int w_total = w_men + w_kings;
    int b_total = b_men + b_kings;
    if (w_total == 0) return (ai_seat == 0) ? -WIN_SCORE : WIN_SCORE;
    if (b_total == 0) return (ai_seat == 0) ? WIN_SCORE : -WIN_SCORE;

    int total_p = w_total + b_total;

    // 0a. Back-rank integrity (Zatylok)
    int w_back = __builtin_popcount(w_mask & WHITE_BACK_MASK);
    int b_back = __builtin_popcount(b_mask & BLACK_BACK_MASK);
    if (w_back == 4) w_score += g_eval_params.back_rank_4;
    else if (w_back == 3) w_score += g_eval_params.back_rank_3;
    else if (w_back == 2) w_score += g_eval_params.back_rank_2;

    if (b_back == 4) b_score += g_eval_params.back_rank_4;
    else if (b_back == 3) b_score += g_eval_params.back_rank_3;
    else if (b_back == 2) b_score += g_eval_params.back_rank_2;

    // 0b. Core Triangles / Columns (Kolonka)
    if (b[29] == W_MAN && b[25] == W_MAN && b[22] == W_MAN) w_score += g_eval_params.kolonka_1;
    if (b[24] == W_MAN && b[21] == W_MAN && b[17] == W_MAN) w_score += g_eval_params.kolonka_2;
    if (b[2] == B_MAN && b[6] == B_MAN && b[9] == B_MAN) b_score += g_eval_params.kolonka_1;
    if (b[7] == B_MAN && b[10] == B_MAN && b[14] == B_MAN) b_score += g_eval_params.kolonka_2;

    // 0c. Center Hole / Swiss Cheese Penalty (Dyrchataja pozitsiya)
    if (b[25] == W_MAN && b[26] == W_MAN && b[22] == EMPTY && b_men >= 2) w_score -= g_eval_params.center_hole;
    if (b[21] == W_MAN && b[22] == W_MAN && b[17] == EMPTY && b_men >= 2) w_score -= g_eval_params.center_hole;
    if (b[5] == B_MAN && b[6] == B_MAN && b[9] == EMPTY && w_men >= 2) b_score -= g_eval_params.center_hole;
    if (b[9] == B_MAN && b[10] == B_MAN && b[14] == EMPTY && w_men >= 2) b_score -= g_eval_params.center_hole;

    // 1. Zolotaya Shashka (c1 = 29 / f8 = 2)
    if (w_men >= 4) {
        if (b[29] == W_MAN) w_score += g_eval_params.golden_pawn_bonus;
        else w_score -= g_eval_params.golden_pawn_penalty;
    }
    if (b_men >= 4) {
        if (b[2] == B_MAN) b_score += g_eval_params.golden_pawn_bonus;
        else b_score -= g_eval_params.golden_pawn_penalty;
    }

    // 2. Mostik (c1+e1 = 29+30 / f8+d8 = 2+1)
    if (b[29] == W_MAN && b[30] == W_MAN) w_score += g_eval_params.mostik_bridge;
    if (b[2] == B_MAN && b[1] == B_MAN) b_score += g_eval_params.mostik_bridge;

    // 3. Central Outpost (d4 / e5) & Wedge (c5 / f4)
    if ((b[17] == 1 || b[17] == 2) && (b[21] || b[22])) w_score += g_eval_params.outpost_d4_e5;
    if ((b[13] == 1 || b[13] == 2) && (b[17] == 1 || b[17] == 2)) w_score += g_eval_params.wedge_c5_f4;
    if ((b[14] == 3 || b[14] == 4) && (b[9] || b[10])) b_score += g_eval_params.outpost_d4_e5;
    if ((b[18] == 3 || b[18] == 4) && (b[14] == 3 || b[14] == 4)) b_score += g_eval_params.wedge_c5_f4;

    // 4. Kolkashev Svyazka (wing pin)
    if (b[16] && b[13] && b[12] && b[8]) w_score += g_eval_params.kolkashev_pin;
    if (b[15] && b[18] && b[19] && b[23]) b_score += g_eval_params.kolkashev_pin;

    w_score += w_mob * g_eval_params.mobility_weight;
    b_score += b_mob * g_eval_params.mobility_weight;

    // 5. Lone Piece Corner Suffocation
    if (total_p <= 6) {
        if (w_kings >= 2 && b_total == 1) {
            for (int wq = 0; wq < 32; wq++) {
                if (b[wq] == W_KING) {
                    for (int bq = 0; bq < 32; bq++) {
                        if (b[bq] == 3 || b[bq] == 4) {
                            int dist = abs(COORDS_R[wq] - COORDS_R[bq]) + abs(COORDS_C[wq] - COORDS_C[bq]);
                            w_score += (14 - dist) * 75;
                        }
                    }
                }
            }
        } else if (b_kings >= 2 && w_total == 1) {
            for (int bq = 0; bq < 32; bq++) {
                if (b[bq] == B_KING) {
                    for (int wq = 0; wq < 32; wq++) {
                        if (b[wq] == 1 || b[wq] == 2) {
                            int dist = abs(COORDS_R[bq] - COORDS_R[wq]) + abs(COORDS_C[bq] - COORDS_C[wq]);
                            b_score += (14 - dist) * 75;
                        }
                    }
                }
            }
        }
    }

    int32_t diff = (ai_seat == 0) ? (w_score - b_score) : (b_score - w_score);

    // Simplification / Liquidation bonus: trade down pieces when winning to seal victory
    if (diff > 250) {
        diff += (24 - total_p) * g_eval_params.liquidation_bonus;
    } else if (diff < -250) {
        diff -= (24 - total_p) * g_eval_params.liquidation_bonus;
    }

    return diff;
}

// Quiescence Search with Extended Capture Cascade
static int quiescence(int8_t *b, int alpha, int beta, int turn, int ai_seat, int qdepth, int tid) {
    #pragma omp atomic
    search_nodes++;

    if ((search_nodes & 8191) == 0) {
        if (get_elapsed_sec() >= search_time_limit) {
            search_stopped = true;
            return 0;
        }
    }

    CMove moves[MAX_MOVES];
    bool is_cap = false;
    int count = generate_moves(b, turn, moves, &is_cap);

    if (count == 0) {
        return (turn == ai_seat) ? (-WIN_SCORE) : WIN_SCORE;
    }

    if (!is_cap || qdepth <= 0) {
        return evaluate(b, ai_seat, turn);
    }

    int opp = 1 - turn;
    if (turn == ai_seat) {
        int max_val = -INF_SCORE;
        for (int i = 0; i < count; i++) {
            int val = quiescence(moves[i].new_board, alpha, beta, opp, ai_seat, qdepth - 1, tid);
            if (search_stopped) return 0;
            if (val > max_val) max_val = val;
            if (max_val > alpha) alpha = max_val;
            if (alpha >= beta) break;
        }
        return max_val;
    } else {
        int min_val = INF_SCORE;
        for (int i = 0; i < count; i++) {
            int val = quiescence(moves[i].new_board, alpha, beta, opp, ai_seat, qdepth - 1, tid);
            if (search_stopped) return 0;
            if (val < min_val) min_val = val;
            if (min_val < beta) beta = min_val;
            if (alpha >= beta) break;
        }
        return min_val;
    }
}

// Inlined fast move score sorting
typedef struct {
    int score;
    int idx;
} MoveScore;

static inline void sort_moves(MoveScore *mscores, int count) {
    for (int i = 1; i < count; i++) {
        MoveScore key = mscores[i];
        int j = i - 1;
        while (j >= 0 && mscores[j].score < key.score) {
            mscores[j + 1] = mscores[j];
            j--;
        }
        mscores[j + 1] = key;
    }
}

// Full Negamax Alpha-Beta Search with PVS, IID, LMR, NMP, RFP, TT, Killers & Countermoves
static int alphabeta(int8_t *b, uint64_t z_hash, int depth, int alpha, int beta, int turn, int ai_seat, int ply, bool allow_null, int prev_from, int prev_to, int tid) {
    #pragma omp atomic
    search_nodes++;

    if ((search_nodes & 8191) == 0) {
        if (get_elapsed_sec() >= search_time_limit) {
            search_stopped = true;
            return 0;
        }
    }

    // Transposition Table lookup (lockless 16-byte atomic read)
    uint32_t tt_idx = (uint32_t)(z_hash & (TT_SIZE - 1));
    TTEntry *tte = &TT[tt_idx];
    uint16_t tt_move = 0;

    if (tte->key == z_hash) {
        tt_move = tte->best_move;
        if (tte->depth >= depth) {
            int tt_score = score_from_tt(tte->score, ply);
            if (tte->flag == 0) return tt_score;
            if (tte->flag == 1 && tt_score > alpha) alpha = tt_score;
            if (tte->flag == 2 && tt_score < beta) beta = tt_score;
            if (alpha >= beta) return tt_score;
        }
    }

    if (depth <= 0) {
        return quiescence(b, alpha, beta, turn, ai_seat, 24, tid);
    }

    // Internal Iterative Deepening (IID)
    if (depth >= 5 && tt_move == 0 && ply < MAX_PLY) {
        alphabeta(b, z_hash, depth - 2, alpha, beta, turn, ai_seat, ply, false, prev_from, prev_to, tid);
        if (tte->key == z_hash) {
            tt_move = tte->best_move;
        }
    }

    CMove moves[MAX_MOVES];
    bool is_cap = false;
    int count = generate_moves(b, turn, moves, &is_cap);

    if (count == 0) {
        return (turn == ai_seat) ? (-WIN_SCORE + ply) : (WIN_SCORE - ply);
    }

    int opp = 1 - turn;

    // 1. Reverse Futility Pruning (Static Null Move Pruning)
    if (allow_null && depth <= 4 && !is_cap && ply > 0 && abs(beta) < WIN_SCORE / 2) {
        int static_eval = evaluate(b, ai_seat, turn);
        int margin = 145 * depth;
        if (turn == ai_seat) {
            if (static_eval - margin >= beta) return beta;
        } else {
            if (static_eval + margin <= alpha) return alpha;
        }
    }

    // 2. Null Move Pruning
    if (allow_null && depth >= 3 && !is_cap && ply > 0 && abs(beta) < WIN_SCORE / 2) {
        uint64_t null_hash = z_hash ^ ZOBRIST_TURN;
        int val = alphabeta(b, null_hash, depth - 1 - 2, beta - 1, beta, opp, ai_seat, ply + 1, false, -1, -1, tid);
        if (search_stopped) return 0;
        if (turn == ai_seat && val >= beta) return beta;
        if (turn != ai_seat && val <= alpha) return alpha;
    }

    // Move Ordering
    MoveScore mscores[MAX_MOVES];
    uint16_t k1 = (ply < MAX_PLY) ? killer_moves[tid][ply][0] : 0;
    uint16_t k2 = (ply < MAX_PLY) ? killer_moves[tid][ply][1] : 0;
    uint16_t cmove = (prev_from >= 0 && prev_to >= 0) ? counter_moves[tid][prev_from][prev_to] : 0;

    for (int i = 0; i < count; i++) {
        uint16_t code = ((uint16_t)moves[i].from << 6) | (uint16_t)moves[i].to;
        int s = 0;
        if (code == tt_move) {
            s = 35000000;
        } else if (moves[i].is_capture) {
            s = 18000000 + moves[i].cap_count * 150000 + (moves[i].promotes ? 300000 : 0);
        } else if (code == k1) {
            s = 2500000;
        } else if (code == cmove) {
            s = 1800000;
        } else if (code == k2) {
            s = 1200000;
        } else if (moves[i].promotes) {
            s = 950000;
        } else {
            s = history[tid][turn][moves[i].from][moves[i].to];
        }
        mscores[i].score = s;
        mscores[i].idx = i;
    }
    sort_moves(mscores, count);

    bool maximizing = (turn == ai_seat);
    int best_val = maximizing ? -INF_SCORE : INF_SCORE;
    uint16_t best_code = 0;
    int orig_alpha = alpha;
    int orig_beta = beta;
    int next_depth = (count == 1) ? depth : (depth - 1);

    for (int i = 0; i < count; i++) {
        int idx = mscores[i].idx;
        CMove *m = &moves[idx];
        uint16_t code = ((uint16_t)m->from << 6) | (uint16_t)m->to;

        uint64_t child_hash = compute_hash(m->new_board, opp);
        int val = 0;

        // PVS (Principal Variation Search) + LMR (Late Move Reductions)
        if (maximizing) {
            if (i == 0) {
                val = alphabeta(m->new_board, child_hash, next_depth, alpha, beta, opp, ai_seat, ply + 1, true, m->from, m->to, tid);
            } else {
                int reduce = 0;
                if (i >= 3 && depth >= 3 && !m->is_capture && !m->promotes && code != k1 && code != k2 && code != cmove) {
                    reduce = 1;
                    if (i >= 7 && depth >= 5) reduce = 2;
                    if (i >= 14 && depth >= 7) reduce = 3;
                }
                val = alphabeta(m->new_board, child_hash, next_depth - reduce, alpha, alpha + 1, opp, ai_seat, ply + 1, true, m->from, m->to, tid);
                if (!search_stopped && val > alpha && (reduce > 0 || val < beta)) {
                    val = alphabeta(m->new_board, child_hash, next_depth, alpha, beta, opp, ai_seat, ply + 1, true, m->from, m->to, tid);
                }
            }
            if (search_stopped) return 0;

            if (val > best_val) {
                best_val = val;
                best_code = code;
            }
            if (best_val > alpha) alpha = best_val;
            if (alpha >= beta) {
                if (!m->is_capture && ply < MAX_PLY) {
                    if (killer_moves[tid][ply][0] != code) {
                        killer_moves[tid][ply][1] = killer_moves[tid][ply][0];
                        killer_moves[tid][ply][0] = code;
                    }
                    if (prev_from >= 0 && prev_to >= 0) {
                        counter_moves[tid][prev_from][prev_to] = code;
                    }
                    history[tid][turn][m->from][m->to] += depth * depth;
                    for (int j = 0; j < i; j++) {
                        int prev_idx = mscores[j].idx;
                        if (!moves[prev_idx].is_capture) {
                            history[tid][turn][moves[prev_idx].from][moves[prev_idx].to] -= (depth * depth) / 2;
                        }
                    }
                }
                break;
            }
        } else {
            if (i == 0) {
                val = alphabeta(m->new_board, child_hash, next_depth, alpha, beta, opp, ai_seat, ply + 1, true, m->from, m->to, tid);
            } else {
                int reduce = 0;
                if (i >= 3 && depth >= 3 && !m->is_capture && !m->promotes && code != k1 && code != k2 && code != cmove) {
                    reduce = 1;
                    if (i >= 7 && depth >= 5) reduce = 2;
                    if (i >= 14 && depth >= 7) reduce = 3;
                }
                val = alphabeta(m->new_board, child_hash, next_depth - reduce, beta - 1, beta, opp, ai_seat, ply + 1, true, m->from, m->to, tid);
                if (!search_stopped && val < beta && (reduce > 0 || val > alpha)) {
                    val = alphabeta(m->new_board, child_hash, next_depth, alpha, beta, opp, ai_seat, ply + 1, true, m->from, m->to, tid);
                }
            }
            if (search_stopped) return 0;

            if (val < best_val) {
                best_val = val;
                best_code = code;
            }
            if (best_val < beta) beta = best_val;
            if (alpha >= beta) {
                if (!m->is_capture && ply < MAX_PLY) {
                    if (killer_moves[tid][ply][0] != code) {
                        killer_moves[tid][ply][1] = killer_moves[tid][ply][0];
                        killer_moves[tid][ply][0] = code;
                    }
                    if (prev_from >= 0 && prev_to >= 0) {
                        counter_moves[tid][prev_from][prev_to] = code;
                    }
                    history[tid][turn][m->from][m->to] += depth * depth;
                    for (int j = 0; j < i; j++) {
                        int prev_idx = mscores[j].idx;
                        if (!moves[prev_idx].is_capture) {
                            history[tid][turn][moves[prev_idx].from][moves[prev_idx].to] -= (depth * depth) / 2;
                        }
                    }
                }
                break;
            }
        }
    }

    if (!search_stopped) {
        int8_t flag = 0;
        if (best_val <= orig_alpha) flag = 2; // UPPER
        else if (best_val >= orig_beta) flag = 1; // LOWER

        if (tte->key == 0 || tte->key == z_hash || depth >= tte->depth - 1 || tte->age != tt_current_age) {
            tte->key = z_hash;
            tte->depth = (int16_t)depth;
            tte->flag = flag;
            tte->age = tt_current_age;
            tte->score = score_to_tt(best_val, ply);
            tte->best_move = best_code;
        }
    }

    return best_val;
}

// Zero-Blunder Verification Filter
// Ensures candidate move does not allow an immediate opponent tactical trap
static bool verify_move_safety(const int8_t *board, int seat, int from, int to) {
    CMove moves[MAX_MOVES];
    bool is_cap = false;
    int count = generate_moves((int8_t *)board, seat, moves, &is_cap);

    const CMove *chosen = NULL;
    for (int i = 0; i < count; i++) {
        if (moves[i].from == from && moves[i].to == to) {
            chosen = &moves[i];
            break;
        }
    }
    if (!chosen) return false;

    int opp = 1 - seat;
    CMove opp_moves[MAX_MOVES];
    bool opp_is_cap = false;
    int opp_count = generate_moves((int8_t *)chosen->new_board, opp, opp_moves, &opp_is_cap);

    if (opp_count == 0) return true; // Opponent has no moves = opponent loses!

    // If opponent has a multi-capture that annihilates 2+ pieces and AI didn't capture equally
    if (opp_is_cap) {
        for (int i = 0; i < opp_count; i++) {
            if (opp_moves[i].cap_count >= 2 && chosen->cap_count < opp_moves[i].cap_count) {
                int ev = evaluate(opp_moves[i].new_board, seat, seat);
                if (ev < -1400) return false; // Blunder detected!
            }
        }
    }
    return true;
}

// Multi-Threaded Lazy SMP Search Function
int godmode_search(
    const int8_t *board,
    int seat,
    int time_limit_ms,
    int max_depth,
    int flying_kings,
    int *out_from,
    int *out_to,
    int *out_score,
    int *out_depth,
    uint64_t *out_nodes
) {
    g_flying_kings = (flying_kings != 0);
    search_nodes = 0;
    search_stopped = false;
    clock_gettime(CLOCK_MONOTONIC, &search_start);
    search_time_limit = (double)time_limit_ms / 1000.0;

    int8_t b[32];
    memcpy(b, board, 32);

    CMove moves[MAX_MOVES];
    bool is_cap = false;
    int count = generate_moves(b, seat, moves, &is_cap);

    if (count == 0) {
        *out_from = -1;
        *out_to = -1;
        *out_score = -WIN_SCORE;
        *out_depth = 0;
        *out_nodes = 0;
        return 0;
    }

    if (count == 1) {
        *out_from = moves[0].from;
        *out_to = moves[0].to;
        *out_score = 0;
        *out_depth = 1;
        *out_nodes = 1;
        return 1;
    }


    int best_from = moves[0].from;
    int best_to = moves[0].to;
    int best_score = -INF_SCORE;
    int completed_depth = 1;
    int opp = 1 - seat;

    // Use OpenMP Lazy SMP with 4 threads
    omp_set_num_threads(MAX_THREADS);

    #pragma omp parallel
    {
        int tid = omp_get_thread_num();

        if (tid == 0) {
            // Master Thread (Thread 0) - Drives Iterative Deepening
            for (int d = 1; d <= max_depth; d++) {
                if (d > 1) {
                    for (int i = 0; i < count; i++) {
                        if (moves[i].from == best_from && moves[i].to == best_to) {
                            if (i != 0) {
                                CMove tmp = moves[0];
                                moves[0] = moves[i];
                                moves[i] = tmp;
                            }
                            break;
                        }
                    }
                }

                int alpha = -INF_SCORE;
                int beta = INF_SCORE;

                // Aspiration Window
                if (d >= 4 && best_score > -WIN_SCORE / 2) {
                    int delta = 55;
                    alpha = best_score - delta;
                    beta = best_score + delta;
                }

                int iter_best_from = best_from;
                int iter_best_to = best_to;
                int iter_best_score = -INF_SCORE;
                bool iter_interrupted = false;

                for (int i = 0; i < count; i++) {
                    uint64_t child_hash = compute_hash(moves[i].new_board, opp);
                    int score;

                    if (i == 0) {
                        score = alphabeta(moves[i].new_board, child_hash, d - 1, alpha, beta, opp, seat, 1, true, moves[i].from, moves[i].to, tid);
                    } else {
                        score = alphabeta(moves[i].new_board, child_hash, d - 1, alpha, alpha + 1, opp, seat, 1, true, moves[i].from, moves[i].to, tid);
                        if (!search_stopped && score > alpha && score < beta) {
                            score = alphabeta(moves[i].new_board, child_hash, d - 1, score, beta, opp, seat, 1, true, moves[i].from, moves[i].to, tid);
                        }
                    }

                    if (search_stopped) {
                        iter_interrupted = true;
                        break;
                    }

                    if (score > iter_best_score) {
                        iter_best_score = score;
                        iter_best_from = moves[i].from;
                        iter_best_to = moves[i].to;
                    }
                    if (score > alpha) alpha = score;
                }

                if (iter_interrupted) break;

                // Aspiration Window Fail Recovery
                if (d >= 4 && (iter_best_score <= alpha || iter_best_score >= beta)) {
                    alpha = -INF_SCORE;
                    beta = INF_SCORE;
                    iter_best_score = -INF_SCORE;

                    for (int i = 0; i < count; i++) {
                        uint64_t child_hash = compute_hash(moves[i].new_board, opp);
                        int score;
                        if (i == 0) {
                            score = alphabeta(moves[i].new_board, child_hash, d - 1, alpha, beta, opp, seat, 1, true, moves[i].from, moves[i].to, tid);
                        } else {
                            score = alphabeta(moves[i].new_board, child_hash, d - 1, alpha, alpha + 1, opp, seat, 1, true, moves[i].from, moves[i].to, tid);
                            if (!search_stopped && score > alpha && score < beta) {
                                score = alphabeta(moves[i].new_board, child_hash, d - 1, score, beta, opp, seat, 1, true, moves[i].from, moves[i].to, tid);
                            }
                        }
                        if (search_stopped) break;
                        if (score > iter_best_score) {
                            iter_best_score = score;
                            iter_best_from = moves[i].from;
                            iter_best_to = moves[i].to;
                        }
                        if (score > alpha) alpha = score;
                    }
                }

                if (!search_stopped) {
                    best_from = iter_best_from;
                    best_to = iter_best_to;
                    best_score = iter_best_score;
                    completed_depth = d;
                }

                if (best_score >= WIN_SCORE - 100 || get_elapsed_sec() >= search_time_limit) {
                    search_stopped = true;
                    break;
                }
            }
        } else {
            // Helper Threads (Lazy SMP): populate shared Transposition Table with depth offsets
            int helper_start_depth = 1 + (tid % 2);
            for (int d = helper_start_depth; d <= max_depth && !search_stopped; d += 2) {
                for (int i = 0; i < count && !search_stopped; i++) {
                    int idx = (i + tid) % count;
                    uint64_t child_hash = compute_hash(moves[idx].new_board, opp);
                    alphabeta(moves[idx].new_board, child_hash, d - 1, -INF_SCORE, INF_SCORE, opp, seat, 1, true, moves[idx].from, moves[idx].to, tid);
                }
            }
        }
    }

    // Zero-Blunder Verification Filter
    if (!verify_move_safety(b, seat, best_from, best_to)) {
        for (int i = 0; i < count; i++) {
            if (verify_move_safety(b, seat, moves[i].from, moves[i].to)) {
                best_from = moves[i].from;
                best_to = moves[i].to;
                break;
            }
        }
    }

    *out_from = best_from;
    *out_to = best_to;
    *out_score = best_score;
    *out_depth = completed_depth;
    *out_nodes = search_nodes;
    return count;
}

// Search with specific custom parameter set (used by Self-Play evolution & testing)
int godmode_search_custom(
    const int8_t *board,
    int seat,
    int time_limit_ms,
    int max_depth,
    int flying_kings,
    const int32_t *custom_params,
    int *out_from,
    int *out_to,
    int *out_score,
    int *out_depth,
    uint64_t *out_nodes
) {
    EvalParams saved = g_eval_params;
    if (custom_params) {
        memcpy(&g_eval_params, custom_params, sizeof(EvalParams));
    }
    int res = godmode_search(
        board, seat, time_limit_ms, max_depth, flying_kings,
        out_from, out_to, out_score, out_depth, out_nodes
    );
    if (custom_params) {
        g_eval_params = saved;
    }
    return res;
}
