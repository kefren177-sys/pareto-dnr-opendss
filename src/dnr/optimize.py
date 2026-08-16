from __future__ import annotations

import itertools
import math
import random
import time
from pathlib import Path

import networkx as nx
from rich.progress import track

from .evaluate import evaluate
from .models import Evaluation, NetworkCase
from .topology import topology_status


def exhaustive(
    case: NetworkCase,
    generated_dir: Path,
    reliability_objective: str = "saidi",
) -> list[Evaluation]:
    combos = itertools.combinations(case.candidate_switches, case.open_count)
    evaluations: list[Evaluation] = []
    for open_switches in track(list(combos), description=f"Exhaustivo {case.name}"):
        evaluations.append(evaluate(case, open_switches, generated_dir, reliability_objective))
    return evaluations


def seeded_configurations(case: NetworkCase) -> list[tuple[int, ...]]:
    configs = [tuple(sorted(case.normally_open))]
    for key in ("thesis_config_1", "thesis_config_2"):
        value = case.metadata.get(key)
        if value:
            configs.append(tuple(sorted(int(x) for x in value)))
    return list(dict.fromkeys(configs))


def small_radial_configurations(case: NetworkCase, max_combinations: int = 50000) -> list[tuple[int, ...]] | None:
    total = math.comb(len(case.candidate_switches), case.open_count)
    if total > max_combinations:
        return None

    configs: list[tuple[int, ...]] = []
    for combo in itertools.combinations(case.candidate_switches, case.open_count):
        config = tuple(sorted(int(x) for x in combo))
        radial, connected = topology_status(case, config)
        if radial and connected:
            configs.append(config)
    return configs


def random_search(
    case: NetworkCase,
    generated_dir: Path,
    samples: int,
    seed: int,
    reliability_objective: str = "saidi",
) -> list[Evaluation]:
    rng = random.Random(seed)
    evaluations: list[Evaluation] = []
    seen: set[tuple[int, ...]] = set()

    for config in seeded_configurations(case):
        if len(config) == case.open_count:
            seen.add(config)
            evaluations.append(evaluate(case, config, generated_dir, reliability_objective))

    attempts = 0
    max_attempts = max(samples * 200, 1000)
    while len(seen) < samples and attempts < max_attempts:
        attempts += 1
        open_switches = feasible_random_open_set(case, rng)
        if open_switches in seen:
            continue
        seen.add(open_switches)
        evaluations.append(evaluate(case, open_switches, generated_dir, reliability_objective))
    return evaluations


def feasible_random_open_set(case: NetworkCase, rng: random.Random) -> tuple[int, ...]:
    """Generate a connected radial configuration by pruning a meshed graph."""
    g = nx.Graph()
    for bus in case.buses:
        g.add_node(bus.idx)
    edge_by_idx = {}
    for branch in case.branches:
        g.add_edge(branch.from_bus, branch.to_bus, idx=branch.idx)
        edge_by_idx[branch.idx] = (branch.from_bus, branch.to_bus)

    opened: set[int] = set()
    candidates = set(case.candidate_switches)
    target_edges = len(case.buses) - 1

    while g.number_of_edges() > target_edges:
        removable = []
        for idx in candidates - opened:
            if idx not in edge_by_idx:
                continue
            u, v = edge_by_idx[idx]
            if not g.has_edge(u, v):
                continue
            g.remove_edge(u, v)
            connected = nx.is_connected(g)
            g.add_edge(u, v, idx=idx)
            if connected:
                removable.append(idx)
        if not removable:
            break
        idx = rng.choice(removable)
        u, v = edge_by_idx[idx]
        g.remove_edge(u, v)
        opened.add(idx)

    if len(opened) != case.open_count:
        return tuple(sorted(rng.sample(case.candidate_switches, case.open_count)))
    return tuple(sorted(opened))


def evolutionary_search(
    case: NetworkCase,
    generated_dir: Path,
    population_size: int,
    generations: int,
    seed: int,
    reliability_objective: str = "saidi",
    stats: dict[str, int] | None = None,
    generation_history: list[dict[str, object]] | None = None,
    pareto_history: list[dict[str, object]] | None = None,
    run_id: str | None = None,
) -> list[Evaluation]:
    rng = random.Random(seed)
    cache: dict[tuple[int, ...], Evaluation] = {}
    population: list[tuple[int, ...]] = []
    all_small_radial = small_radial_configurations(case)
    started = time.perf_counter()
    history_run_id = run_id or f"{case.name}_seed_{seed}"
    if stats is not None:
        stats.update({"evaluation_requests": 0, "real_evaluations": 0, "cache_hits": 0})

    if all_small_radial and len(all_small_radial) <= population_size:
        for config in all_small_radial:
            if stats is not None:
                stats["evaluation_requests"] += 1
                stats["real_evaluations"] += 1
            cache[config] = evaluate(case, config, generated_dir, reliability_objective)
        return list(cache.values())

    for config in seeded_configurations(case):
        if len(config) == case.open_count and config not in population:
            population.append(config)

    while len(population) < population_size:
        config = (
            rng.choice(all_small_radial)
            if all_small_radial
            else feasible_random_open_set(case, rng)
        )
        if config not in population:
            population.append(config)

    def get_eval(config: tuple[int, ...]) -> Evaluation:
        if stats is not None:
            stats["evaluation_requests"] += 1
        if config not in cache:
            if stats is not None:
                stats["real_evaluations"] += 1
            cache[config] = evaluate(case, config, generated_dir, reliability_objective)
        elif stats is not None:
            stats["cache_hits"] += 1
        return cache[config]

    for generation in track(range(1, generations + 1), description=f"Evolutivo {case.name}"):
        real_evaluations_before = stats.get("real_evaluations", 0) if stats is not None else len(cache)
        cache_hits_before = stats.get("cache_hits", 0) if stats is not None else 0
        children: list[tuple[int, ...]] = []
        for parent in population:
            child = mutate_radial_tree(case, parent, rng)
            if child not in cache:
                children.append(child)
        candidates = list(dict.fromkeys(population + children))
        for config in candidates:
            get_eval(config)
        population = select_population(candidates, cache, population_size)
        if generation_history is not None or pareto_history is not None:
            real_evaluations_after = stats.get("real_evaluations", len(cache)) if stats is not None else len(cache)
            cache_hits_after = stats.get("cache_hits", 0) if stats is not None else 0
            feasible_population = [cfg for cfg in population if cache[cfg].feasible]
            population_front = nondominated_configs(feasible_population, cache)
            archive_feasible = [cfg for cfg, ev in cache.items() if ev.feasible]
            archive_front = nondominated_configs(archive_feasible, cache)
            feasible_evaluations = [cache[cfg] for cfg in feasible_population]
            best_loss = min(
                feasible_evaluations,
                key=lambda ev: ev.losses_kw if ev.losses_kw is not None else float("inf"),
                default=None,
            )
            best_saidi = min(
                feasible_evaluations,
                key=lambda ev: ev.saidi if ev.saidi is not None else float("inf"),
                default=None,
            )
            if generation_history is not None:
                generation_history.append(
                    {
                        "case": case.name,
                        "run_id": history_run_id,
                        "seed": seed,
                        "generation": generation,
                        "elapsed_time_s": time.perf_counter() - started,
                        "unique_evaluations_generation": real_evaluations_after - real_evaluations_before,
                        "unique_evaluations_cumulative": real_evaluations_after,
                        "cache_hits_generation": cache_hits_after - cache_hits_before,
                        "cache_hits_cumulative": cache_hits_after,
                        "population_size": len(population),
                        "feasible_population_size": len(feasible_population),
                        "nondominated_size": len(population_front),
                        "archive_nondominated_size": len(archive_front),
                        "best_loss": None if best_loss is None else best_loss.losses_kw,
                        "best_saidi": None if best_saidi is None else best_saidi.saidi,
                    }
                )
            if pareto_history is not None:
                for cfg in archive_front:
                    ev = cache[cfg]
                    pareto_history.append(
                        {
                            "case": case.name,
                            "run_id": history_run_id,
                            "seed": seed,
                            "generation": generation,
                            "unique_evaluations_cumulative": real_evaluations_after,
                            "open_switches": ",".join(str(x) for x in ev.open_switches),
                            "losses_kw": ev.losses_kw,
                            "saidi": ev.saidi,
                        }
                    )

    return list(cache.values())


def mutate_radial_tree(case: NetworkCase, open_switches: tuple[int, ...], rng: random.Random) -> tuple[int, ...]:
    open_set = set(open_switches)
    edge_by_idx = {branch.idx: (branch.from_bus, branch.to_bus) for branch in case.branches}
    g = nx.Graph()
    for bus in case.buses:
        g.add_node(bus.idx)
    for branch in case.branches:
        if branch.idx not in open_set:
            g.add_edge(branch.from_bus, branch.to_bus, idx=branch.idx)

    closable = [idx for idx in open_set if idx in case.candidate_switches and idx in edge_by_idx]
    rng.shuffle(closable)
    for close_idx in closable:
        u, v = edge_by_idx[close_idx]
        if not nx.has_path(g, u, v):
            continue
        path = nx.shortest_path(g, u, v)
        cycle_edges = [close_idx]
        for a, b in zip(path, path[1:]):
            cycle_edges.append(g.edges[a, b]["idx"])
        removable = [idx for idx in cycle_edges if idx in case.candidate_switches and idx != close_idx]
        if not removable:
            continue
        open_set.remove(close_idx)
        open_set.add(rng.choice(removable))
        return tuple(sorted(open_set))
    return feasible_random_open_set(case, rng)


def select_population(
    configs: list[tuple[int, ...]],
    cache: dict[tuple[int, ...], Evaluation],
    population_size: int,
) -> list[tuple[int, ...]]:
    feasible = [cfg for cfg in configs if cache[cfg].feasible]
    infeasible = [cfg for cfg in configs if not cache[cfg].feasible]
    selected: list[tuple[int, ...]] = []
    remaining = feasible[:]

    while remaining and len(selected) < population_size:
        front = nondominated_configs(remaining, cache)
        if len(selected) + len(front) <= population_size:
            selected.extend(front)
        else:
            selected.extend(crowding_sort(front, cache)[: population_size - len(selected)])
        remaining = [cfg for cfg in remaining if cfg not in front]

    if len(selected) < population_size:
        selected.extend(infeasible[: population_size - len(selected)])
    return selected


def nondominated_configs(
    configs: list[tuple[int, ...]],
    cache: dict[tuple[int, ...], Evaluation],
) -> list[tuple[int, ...]]:
    front: list[tuple[int, ...]] = []
    for cfg in configs:
        ev = cache[cfg]
        dominated = False
        for other_cfg in configs:
            if other_cfg == cfg:
                continue
            other = cache[other_cfg]
            if not other.feasible:
                continue
            better_or_equal = (
                (other.losses_kw or float("inf")) <= (ev.losses_kw or float("inf"))
                and (other.objective_reliability or float("inf"))
                <= (ev.objective_reliability or float("inf"))
            )
            strictly_better = (
                (other.losses_kw or float("inf")) < (ev.losses_kw or float("inf"))
                or (other.objective_reliability or float("inf"))
                < (ev.objective_reliability or float("inf"))
            )
            if better_or_equal and strictly_better:
                dominated = True
                break
        if not dominated:
            front.append(cfg)
    return front


def crowding_sort(
    configs: list[tuple[int, ...]],
    cache: dict[tuple[int, ...], Evaluation],
) -> list[tuple[int, ...]]:
    if len(configs) <= 2:
        return configs
    distance = {cfg: 0.0 for cfg in configs}
    objectives = [
        lambda ev: ev.losses_kw or float("inf"),
        lambda ev: ev.objective_reliability or float("inf"),
    ]
    for objective in objectives:
        ordered = sorted(configs, key=lambda cfg: objective(cache[cfg]))
        distance[ordered[0]] = distance[ordered[-1]] = float("inf")
        low = objective(cache[ordered[0]])
        high = objective(cache[ordered[-1]])
        span = high - low or 1.0
        for i in range(1, len(ordered) - 1):
            distance[ordered[i]] += (
                objective(cache[ordered[i + 1]]) - objective(cache[ordered[i - 1]])
            ) / span
    return sorted(configs, key=lambda cfg: distance[cfg], reverse=True)
