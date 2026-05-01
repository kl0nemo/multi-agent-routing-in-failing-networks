import random
import numpy as np
import matplotlib.pyplot as plt
from collections import deque
import time
import math

BASE_N = 10
BASE_TICKS = 10
STEP_N = 5
STEP_T = 5
INCREMENTS = 10
ROUNDS = 100

EDGE_DEATH_PROB = 0.3
EDGE_RECOVERY_PROB = 0.1

STRATEGIES = ("planner", "greedy", "risky", "cautious", "fallback")


def bfs(adj, start, N):
    dist = [-1] * N
    dist[start] = 0
    q = deque([start])

    while q:
        u = q.popleft()
        du = dist[u] + 1
        for v in adj[u]:
            if dist[v] == -1:
                dist[v] = du
                q.append(v)
    return dist


def shortest_next(adj, start, goal, N):
    parent = [-1] * N
    q = deque([start])
    parent[start] = start

    while q:
        u = q.popleft()
        if u == goal:
            break
        for v in adj[u]:
            if parent[v] == -1:
                parent[v] = u
                q.append(v)

    if parent[goal] == -1:
        return None

    cur = goal
    while parent[cur] != start:
        cur = parent[cur]
    return cur


def generate_graph(N):
    while True:
        adj = [[] for _ in range(N)]
        edges = set()

        nodes = list(range(N))
        random.shuffle(nodes)

        for i in range(1, N):
            u = nodes[i]
            v = nodes[random.randrange(i)]
            adj[u].append(v)
            adj[v].append(u)
            edges.add((u, v) if u < v else (v, u))

        for _ in range(N):
            u = random.randrange(N)
            v = random.randrange(N)
            if u != v and len(adj[u]) < 6 and len(adj[v]) < 6:
                if v not in adj[u]:
                    adj[u].append(v)
                    adj[v].append(u)
                    edges.add((u, v) if u < v else (v, u))

        if all(2 <= len(adj[i]) <= 6 for i in range(N)):
            break

    A, B = 0, 1
    max_dist = -1

    for i in range(N):
        d = bfs(adj, i, N)
        for j in range(N):
            if d[j] > max_dist:
                max_dist = d[j]
                A, B = i, j

    if B in adj[A]:
        adj[A].remove(B)
        adj[B].remove(A)

    return adj, edges, A, B


def new_agent(strategy, A, B):
    return {
        "pos": A,
        "goal": B,
        "steps": 0,
        "alive": True,
        "strategy": strategy,
        "history": deque(maxlen=5)
    }


def run_sim(N, T):
    adj, active_edges, A, B = generate_graph(N)
    dead_edges = set()

    edge_risk = {e: EDGE_DEATH_PROB for e in active_edges}
    agents = [new_agent(s, A, B) for s in STRATEGIES]

    rand = random.random
    choice = random.choice

    for _ in range(T):

        new_active = set()

        for e in active_edges:
            if rand() >= EDGE_DEATH_PROB:
                new_active.add(e)
            else:
                dead_edges.add(e)

        for e in list(dead_edges):
            if rand() < EDGE_RECOVERY_PROB:
                new_active.add(e)
                dead_edges.remove(e)

        for e in active_edges:
            edge_risk[e] = edge_risk.get(e, EDGE_DEATH_PROB) * 0.9
        for e in dead_edges:
            edge_risk[e] = edge_risk.get(e, EDGE_DEATH_PROB) * 0.9 + 0.1

        active_edges = new_active

        adj = [[] for _ in range(N)]
        for u, v in active_edges:
            adj[u].append(v)
            adj[v].append(u)

        dist = bfs(adj, B, N)

        for a in agents:
            if not a["alive"]:
                continue

            pos = a["pos"]

            if pos == B or a["steps"] >= T:
                a["alive"] = False
                continue

            neigh = adj[pos]
            if not neigh:
                a["steps"] += 1
                continue

            hist = a["history"]
            strat = a["strategy"]

            if strat == "planner":
                nxt = shortest_next(adj, pos, B, N)

                if nxt is None:
                    new_pos = choice(neigh)

                elif nxt in hist:
                    best = None
                    best_d = 10**18
                    for v in neigh:
                        if v in hist:
                            continue
                        d = dist[v]
                        if d == -1:
                            d = 10**9
                        if d < best_d:
                            best_d = d
                            best = v
                    new_pos = best if best is not None else choice(neigh)

                else:
                    new_pos = nxt

            elif strat == "greedy":
                best = None
                best_d = 10**18
                for v in neigh:
                    if v in hist:
                        continue
                    d = dist[v]
                    if d == -1:
                        d = 10**9
                    if d < best_d:
                        best_d = d
                        best = v
                new_pos = best if best is not None else choice(neigh)

            elif strat == "risky":
                if rand() < 0.2:
                    new_pos = choice(neigh)
                else:
                    best = neigh[0]
                    best_d = dist[best]
                    if best_d == -1:
                        best_d = 10**9
                    for v in neigh[1:]:
                        d = dist[v]
                        if d == -1:
                            d = 10**9
                        if d < best_d:
                            best_d = d
                            best = v
                    new_pos = best

            elif strat == "cautious":
                safe = []
                for v in neigh:
                    e = (pos, v) if pos < v else (v, pos)
                    if edge_risk.get(e, EDGE_DEATH_PROB) < 0.35:
                        safe.append(v)

                if safe:
                    best = None
                    best_d = 10**18
                    for v in safe:
                        d = dist[v]
                        if d == -1:
                            d = 10**9
                        if d < best_d:
                            best_d = d
                            best = v
                    new_pos = best
                else:
                    new_pos = choice(neigh) if rand() < 0.3 else pos

            else:
                best = neigh[0]
                best_d = dist[best]
                if best_d == -1:
                    best_d = 10**9

                for v in neigh[1:]:
                    d = dist[v]
                    if d == -1:
                        d = 10**9
                    if d < best_d:
                        best_d = d
                        best = v

                new_pos = best if dist[best] != -1 else choice(neigh)

            hist.append(pos)
            a["pos"] = new_pos
            a["steps"] += 1

    return {a["strategy"]: (a["pos"] == B) for a in agents}


results = {s: np.zeros((INCREMENTS, INCREMENTS)) for s in STRATEGIES}

total_runs = INCREMENTS * INCREMENTS
done = 0
start = time.time()

for i in range(INCREMENTS):
    for j in range(INCREMENTS):
        N = BASE_N + i * STEP_N
        T = BASE_TICKS + j * STEP_T

        score = {s: 0 for s in STRATEGIES}

        for _ in range(ROUNDS):
            out = run_sim(N, T)
            for s in STRATEGIES:
                score[s] += out[s]

        done += 1

        elapsed = time.time() - start
        percent = done / total_runs * 100
        eta = elapsed / done * (total_runs - done)

        print(f"{percent:.2f}% | elapsed: {elapsed:.1f}s | eta: {eta:.1f}s | N={N}, T={T}")

        for s in STRATEGIES:
            results[s][i][j] = score[s] / ROUNDS


n = len(STRATEGIES)
cols = 3
rows = math.ceil(n / cols)

fig, axes = plt.subplots(rows, cols, figsize=(12, 7), constrained_layout=True)
axes = np.array(axes).flatten()

x_vals = [BASE_TICKS + j * STEP_T for j in range(INCREMENTS)]
y_vals = [BASE_N + i * STEP_N for i in range(INCREMENTS)]

for idx, s in enumerate(STRATEGIES):
    ax = axes[idx]
    data = results[s]

    im = ax.imshow(
        data,
        cmap="viridis",
        origin="lower",
        extent=[x_vals[0], x_vals[-1], y_vals[0], y_vals[-1]],
        aspect="auto"
    )

    ax.set_title(s)
    ax.set_xlabel("T")
    ax.set_ylabel("N")

    ax.set_xticks(x_vals)
    ax.set_yticks(y_vals)

for k in range(len(STRATEGIES), len(axes)):
    axes[k].axis("off")

fig.colorbar(im, ax=axes.tolist(), shrink=0.7, label="Success rate")
plt.show()