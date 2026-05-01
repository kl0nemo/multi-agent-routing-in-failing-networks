import random
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import networkx as nx
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from collections import deque


N = 30
MAX_TICKS = 100
ROUNDS = 20

EDGE_DEATH_PROB = 0.3
EDGE_RECOVERY_PROB = 0.1

fig, ax = plt.subplots(figsize=(7, 7))

round_id = 0
tick = 0
running = True

G = None
active_edges = set()
dead_edges = set()
pos = None
A = None
B = None

agents = []
edge_risk = {}

stats = {
    "planner": [],
    "greedy": [],
    "risky": [],
    "cautious": [],
    "fallback": []
}


def bfs(adj, start):
    dist = {i: -1 for i in range(N)}
    dist[start] = 0
    q = deque([start])

    while q:
        u = q.popleft()
        for v in adj[u]:
            if dist[v] == -1:
                dist[v] = dist[u] + 1
                q.append(v)
    return dist


def shortest_next(adj, start, goal):
    parent = {i: -1 for i in range(N)}
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


def generate_graph():
    global G, active_edges, dead_edges, pos, A, B, edge_risk

    while True:
        G = nx.Graph()
        G.add_nodes_from(range(N))

        nodes = list(range(N))
        random.shuffle(nodes)

        for i in range(1, N):
            u = nodes[i]
            v = random.choice(nodes[:i])
            G.add_edge(u, v)

        for _ in range(N):
            u, v = random.sample(range(N), 2)
            if u != v and G.degree[u] < 6 and G.degree[v] < 6:
                G.add_edge(u, v)

        if all(2 <= G.degree[n] <= 6 for n in G.nodes()):
            break

    lengths = dict(nx.all_pairs_shortest_path_length(G))

    A, B = 0, 1
    max_dist = -1

    for u in range(N):
        for v in range(N):
            if u != v and v in lengths[u] and lengths[u][v] > max_dist:
                max_dist = lengths[u][v]
                A, B = u, v

    if G.has_edge(A, B):
        G.remove_edge(A, B)

    active_edges = set(G.edges())
    dead_edges = set()

    edge_risk = {tuple(sorted(e)): EDGE_DEATH_PROB for e in active_edges}

    pos = nx.spring_layout(G, seed=random.randint(1, 999), k=0.25)


def new_agent(color, strategy):
    return {
        "pos": A,
        "goal": B,
        "steps": 0,
        "alive": True,
        "color": color,
        "strategy": strategy,
        "history": deque(maxlen=5),
    }


def reset_agents():
    global agents
    agents = [
        new_agent("blue", "planner"),
        new_agent("green", "greedy"),
        new_agent("purple", "risky"),
        new_agent("cyan", "cautious"),
        new_agent("orange", "fallback")
    ]


def move(a, adj, dist):
    if not a["alive"]:
        return

    if a["steps"] >= MAX_TICKS or a["pos"] == a["goal"]:
        a["alive"] = False
        return

    pos_a = a["pos"]
    neigh = adj[pos_a]

    if not neigh:
        a["steps"] += 1
        return

    hist = a["history"]
    strat = a["strategy"]

    if strat == "planner":
        nxt = shortest_next(adj, pos_a, B)

        if nxt is None:
            new_pos = random.choice(neigh)

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
            new_pos = best if best is not None else random.choice(neigh)

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
        new_pos = best if best is not None else random.choice(neigh)

    elif strat == "risky":
        if random.random() < 0.2:
            new_pos = random.choice(neigh)
        else:
            best = neigh[0]
            best_d = dist[best] if dist[best] != -1 else 10**9
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
            e = tuple(sorted((pos_a, v)))
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
            new_pos = random.choice(neigh) if random.random() < 0.3 else pos_a

    else:  
        best = neigh[0]
        best_d = dist[best] if dist[best] != -1 else 10**9

        for v in neigh[1:]:
            d = dist[v]
            if d == -1:
                d = 10**9
            if d < best_d:
                best_d = d
                best = v

        new_pos = best if dist[best] != -1 else random.choice(neigh)

    hist.append(pos_a)
    a["pos"] = new_pos
    a["steps"] += 1


def update(frame):
    global tick, round_id, running, active_edges, dead_edges, edge_risk

    if not running:
        return

    tick += 1
    new_active = set()

    for e in active_edges:
        if random.random() >= EDGE_DEATH_PROB:
            new_active.add(e)
        else:
            dead_edges.add(e)

    for e in list(dead_edges):
        if random.random() < EDGE_RECOVERY_PROB:
            new_active.add(e)
            dead_edges.discard(e)

    # обновление риска (как во втором коде)
    for e in active_edges:
        edge_risk[e] = edge_risk.get(e, EDGE_DEATH_PROB) * 0.9
    for e in dead_edges:
        edge_risk[e] = edge_risk.get(e, EDGE_DEATH_PROB) * 0.9 + 0.1

    active_edges = new_active

    adj = {i: [] for i in range(N)}
    for u, v in active_edges:
        adj[u].append(v)
        adj[v].append(u)

    dist = bfs(adj, B)

    for a in agents:
        move(a, adj, dist)

    ax.clear()

    G_plot = nx.Graph()
    G_plot.add_nodes_from(range(N))
    G_plot.add_edges_from(active_edges)

    nx.draw_networkx_nodes(G_plot, pos, node_color="skyblue", node_size=180, ax=ax)
    nx.draw_networkx_edges(G_plot, pos, edgelist=list(active_edges),
                           edge_color="green", width=2, ax=ax)
    nx.draw_networkx_edges(G_plot, pos, edgelist=list(dead_edges),
                           edge_color="red", style="dashed", alpha=0.5, ax=ax)

    ax.scatter(*pos[A], color="red", s=250, zorder=20)
    ax.scatter(*pos[B], color="orange", s=250, zorder=20)

    ax.text(pos[A][0], pos[A][1], "START")
    ax.text(pos[B][0], pos[B][1], "FINISH")

    for a in agents:
        color = a["color"] if a["alive"] else "black"
        size = 130 if a["alive"] else 80
        marker = "o" if a["alive"] else "x"
        ax.scatter(*pos[a["pos"]], color=color, s=size, marker=marker, zorder=30)

    ax.set_title(f"Round {round_id+1} | Tick {tick}/{MAX_TICKS}")
    ax.set_axis_off()

    if tick >= MAX_TICKS:
        round_id += 1
        if round_id >= ROUNDS:
            plt.close()
            running = False
        else:
            generate_graph()
            reset_agents()
            tick = 0


generate_graph()
reset_agents()

ani = FuncAnimation(fig, update, interval=1, blit=False, cache_frame_data=False)
plt.show()