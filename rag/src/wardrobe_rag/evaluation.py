"""Reproducible retrieval evaluation, independent of LLM and embedding libraries.

The supplied callable accepts a RetrievalRequest-shaped dictionary and returns
a RetrievalResult or an equivalent dict. No backend or paid API is required.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import platform
import statistics
import time
from collections import defaultdict
from collections.abc import Callable, Iterable, Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SLOTS = frozenset(('tops', 'bottoms', 'shoes', 'outerwear', 'accessories'))
REQUEST_FIELDS = frozenset(('query', 'query_image', 'context', 'anchor_item_id',
                            'exclude_item_ids', 'exclude_colors', 'require_outerwear'))


def _jsonable(value: Any) -> Any:
    if hasattr(value, 'model_dump'):
        return value.model_dump(mode='json')
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    return value


def validate_dataset(dataset: Mapping[str, Any], corpus_items: Sequence[Mapping[str, Any]] | None = None) -> None:
    """Fail early for ambiguous labels, duplicate IDs and incorrect categories."""
    if dataset.get('schema_version') != 1:
        raise ValueError('Unsupported evaluation dataset schema_version; expected 1.')
    queries = dataset.get('queries')
    if not isinstance(queries, list) or not queries:
        raise ValueError('Dataset must contain a nonempty queries list.')
    if not isinstance(dataset.get('user_id'), str) or not dataset['user_id'].strip():
        raise ValueError('Dataset user_id is required for isolated retrieval.')
    required_slots = dataset.get('required_slots', ['tops', 'bottoms', 'shoes'])
    if not isinstance(required_slots, list) or not set(required_slots) <= SLOTS:
        raise ValueError('required_slots contains an unknown category.')
    if len(required_slots) != len(set(required_slots)):
        raise ValueError('required_slots must be unique.')
    if not isinstance(dataset.get('mrr_k', 3), int) or isinstance(dataset.get('mrr_k', 3), bool) or dataset.get('mrr_k', 3) < 1:
        raise ValueError('mrr_k must be a positive integer.')
    alpha = dataset.get('alpha', 0.65)
    if not isinstance(alpha, (float, int)) or isinstance(alpha, bool) or not 0 <= alpha <= 1:
        raise ValueError('alpha must be a finite number from 0 to 1.')
    catalog = None
    if corpus_items is not None:
        catalog = {}
        for item in corpus_items:
            identifier, category = item.get('id'), item.get('category')
            if not isinstance(identifier, str) or not identifier or identifier in catalog:
                raise ValueError(f'Invalid or duplicate corpus ID: {identifier!r}')
            if category not in SLOTS:
                raise ValueError(f'Unknown corpus category: {category!r}')
            catalog[identifier] = category
    ids = set()
    for entry in queries:
        identifier = entry.get('id')
        if not isinstance(identifier, str) or not identifier or identifier in ids:
            raise ValueError(f'Invalid or duplicate query ID: {identifier!r}')
        ids.add(identifier)
        if not isinstance(entry.get('query', ''), str):
            raise ValueError(f'{identifier}: query must be a string.')
        if not entry.get('query', '').strip() and not entry.get('query_image'):
            raise ValueError(f'{identifier}: provide query text or query_image.')
        labels = entry.get('relevant_by_slot')
        if not isinstance(labels, dict) or not labels or not set(labels) <= SLOTS:
            raise ValueError(f'{identifier}: relevant_by_slot must contain valid categories.')
        if not set(required_slots) <= set(labels):
            raise ValueError(f'{identifier}: each required slot needs ground truth.')
        for slot, relevant in labels.items():
            if not isinstance(relevant, list) or not relevant or any(not isinstance(value, str) or not value for value in relevant):
                raise ValueError(f'{identifier}/{slot}: labels must be nonempty ID lists. Put no-answer cases in engineering tests.')
            if len(relevant) != len(set(relevant)):
                raise ValueError(f'{identifier}/{slot}: duplicate relevance IDs.')
            if catalog is not None:
                for item_id in relevant:
                    if catalog.get(item_id) != slot:
                        raise ValueError(f'{identifier}/{slot}: label {item_id!r} is missing or belongs to another category.')
            excluded = set(entry.get('exclude_item_ids', []))
            if excluded.intersection(relevant):
                raise ValueError(f'{identifier}/{slot}: relevant IDs contradict exclude_item_ids.')


def load_dataset(path: str | Path) -> dict[str, Any]:
    dataset_path = Path(path).resolve()
    dataset = json.loads(dataset_path.read_text(encoding='utf-8'))
    if not isinstance(dataset, dict):
        raise ValueError('Evaluation dataset must be a JSON object.')
    corpus_path = dataset_path.parent / dataset['corpus'] if dataset.get('corpus') else None
    corpus = load_corpus(corpus_path) if corpus_path and corpus_path.is_file() else None
    validate_dataset(dataset, corpus)
    dataset['_dataset_path'] = str(dataset_path)
    if corpus_path is not None:
        dataset['_corpus_path'] = str(corpus_path.resolve())
    return dataset


def load_corpus(path: str | Path) -> list[dict[str, Any]]:
    raw = json.loads(Path(path).read_text(encoding='utf-8'))
    items = raw.get('items') if isinstance(raw, dict) else raw
    if not isinstance(items, list) or any(not isinstance(item, dict) for item in items):
        raise ValueError('Evaluation corpus must contain a wardrobe item array.')
    return items


def retrieval_metrics(ranked_ids: Sequence[str], relevant_ids: Iterable[str],
                      ks: Sequence[int] = (1, 3), mrr_k: int = 3) -> dict[str, float]:
    """Binary hit rate and truncated reciprocal rank for one query-slot pair.

    There may be several relevant items. Empty ground truth is undefined, not a
    zero: no-answer behavior belongs in a separate engineering test suite.
    """
    relevant = set(relevant_ids)
    if not relevant:
        raise ValueError('Metrics require nonempty relevance labels.')
    if any(not isinstance(k, int) or isinstance(k, bool) or k < 1 for k in (*ks, mrr_k)):
        raise ValueError('Metric cutoffs must be positive integers.')
    if len(ranked_ids) != len(set(ranked_ids)):
        raise ValueError('Ranking contains duplicate item IDs.')
    metrics = {f'hit_rate@{k}': float(bool(set(ranked_ids[:k]).intersection(relevant))) for k in ks}
    first = next((rank for rank, identifier in enumerate(ranked_ids[:mrr_k], 1) if identifier in relevant), None)
    metrics[f'mrr@{mrr_k}'] = 1.0 / first if first is not None else 0.0
    return metrics


def _ranking(result: Mapping[str, Any], slot: str, *, include_fallback: bool = False) -> list[str]:
    by_slot = result.get('candidates_by_slot')
    if not isinstance(by_slot, Mapping):
        raise ValueError('Retriever result must contain candidates_by_slot.')
    candidates = by_slot.get(slot, [])
    if not isinstance(candidates, list):
        raise ValueError(f'candidates_by_slot[{slot!r}] must be a list.')
    identifiers = []
    for candidate in candidates:
        if isinstance(candidate, str):
            identifier = candidate
        elif isinstance(candidate, Mapping):
            if candidate.get('fallback') and not include_fallback:
                continue
            item = candidate.get('item', {})
            identifier = item.get('id') if isinstance(item, Mapping) else None
            identifier = identifier or candidate.get('item_id') or candidate.get('id')
        else:
            identifier = None
        if not isinstance(identifier, str) or not identifier:
            raise ValueError(f'Candidate in slot {slot!r} has no canonical ID.')
        identifiers.append(identifier)
    if len(identifiers) != len(set(identifiers)):
        raise ValueError(f'Retriever returned duplicate IDs in slot {slot!r}.')
    return identifiers


def _percentile(values: Sequence[float], quantile: float) -> float:
    """Linear interpolation; avoid changing percentile definitions per platform."""
    if not values:
        return 0.0
    ordered = sorted(values)
    index = (len(ordered) - 1) * quantile
    low, high = math.floor(index), math.ceil(index)
    return ordered[low] + (ordered[high] - ordered[low]) * (index - low)


def _timing_summary(values: Sequence[float]) -> dict[str, float | int]:
    return dict(samples=len(values), median=statistics.median(values) if values else 0.0,
                p95=_percentile(values, .95), mean=statistics.fmean(values) if values else 0.0,
                minimum=min(values, default=0.0), maximum=max(values, default=0.0))


def _mean_metrics(rows: Sequence[Mapping[str, Any]], keys: Sequence[str]) -> dict[str, float]:
    return {key: statistics.fmean(row[key] for row in rows) if rows else 0.0 for key in keys}


def evaluate(retrieve: Callable[[dict[str, Any]], Any], dataset: dict[str, Any],
             output_dir: str | Path, *, modes: Sequence[str] = ('bm25', 'dense', 'hybrid'),
             repeats: int = 3, metadata: Mapping[str, Any] | None = None,
             warmup: int = 1) -> dict[str, Any]:
    """Run equal-condition retrieval modes and write auditable measurements.

    All calls are serial on purpose; latency is not a concurrency benchmark.
    Each query/mode receives `warmup` untimed calls before `repeats` measured
    calls. First observed warmup latency is stored separately, never described
    as a fresh-process cold start. Initialize/sync the engine before calling.
    """
    validate_dataset(dataset)
    if not modes or len(modes) != len(set(modes)):
        raise ValueError('Provide distinct evaluation modes.')
    if not isinstance(repeats, int) or isinstance(repeats, bool) or repeats < 1:
        raise ValueError('repeats must be a positive integer.')
    if not isinstance(warmup, int) or isinstance(warmup, bool) or warmup < 0:
        raise ValueError('warmup must be a nonnegative integer.')
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    mrr_k = dataset.get('mrr_k', 3)
    metric_keys = ['hit_rate@1', 'hit_rate@3', f'mrr@{mrr_k}']
    rows: list[dict[str, Any]] = []
    raw_rows: list[dict[str, Any]] = []
    latencies: dict[str, list[float]] = defaultdict(list)
    components: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    first_observed: dict[str, float] = {}
    coverage: dict[str, dict[int, list[float]]] = defaultdict(lambda: defaultdict(list))
    candidate_coverage: dict[str, list[float]] = defaultdict(list)
    mode_warnings: dict[str, set[str]] = defaultdict(set)
    corpus_lookup = None
    corpus_path = Path(dataset['_corpus_path']) if dataset.get('_corpus_path') else None
    if corpus_path and corpus_path.is_file():
        corpus = load_corpus(corpus_path)
        validate_dataset(dataset, corpus)
        corpus_lookup = {item['id']: item['category'] for item in corpus}
    dataset_dir = Path(dataset.get('_dataset_path', '.')).parent

    for mode in modes:
        for entry in dataset['queries']:
            request = {field: entry[field] for field in REQUEST_FIELDS if field in entry}
            if request.get('query_image') and not Path(request['query_image']).is_absolute():
                # Manifests use paths relative to the Python project, not cwd.
                # A manifest in rag/data may name data/visual_queries/... .
                value = Path(request['query_image'])
                base = dataset_dir.parent if value.parts and value.parts[0] == 'data' else dataset_dir
                request['query_image'] = str((base / value).resolve())
            request.update(user_id=dataset['user_id'], mode=mode, alpha=dataset.get('alpha', .65))
            if 'visual_weight' in dataset:
                request['visual_weight'] = dataset['visual_weight']
            for _ in range(warmup):
                start = time.perf_counter()
                retrieve(dict(request))
                first_observed.setdefault(mode, (time.perf_counter() - start) * 1000)
            baseline_ranking = None
            for repeat in range(repeats):
                start = time.perf_counter()
                try:
                    result = _jsonable(retrieve(dict(request)))
                except Exception as exc:
                    raise RuntimeError(f'Evaluation failed for {mode}/{entry["id"]}, repeat {repeat + 1}.') from exc
                elapsed = (time.perf_counter() - start) * 1000
                if not isinstance(result, Mapping):
                    raise ValueError('Retriever must return a mapping or Pydantic model.')
                first_observed.setdefault(mode, elapsed)
                latencies[mode].append(elapsed)
                for component, value in result.get('timings_ms', {}).items():
                    if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value):
                        components[mode][component].append(float(value))
                rankings = {slot: _ranking(result, slot) for slot in entry['relevant_by_slot']}
                if corpus_lookup is not None:
                    for slot, ranking in rankings.items():
                        if any(corpus_lookup.get(identifier) != slot for identifier in ranking):
                            raise ValueError(f'{mode}/{entry["id"]}: returned IDs outside the corpus or category {slot}.')
                if baseline_ranking is None:
                    baseline_ranking = rankings
                elif baseline_ranking != rankings:
                    mode_warnings[mode].add('Rankings changed across repeats; metrics average every measured repeat.')
                for slot, relevant in entry['relevant_by_slot'].items():
                    ranked = rankings[slot]
                    metrics = retrieval_metrics(ranked, relevant, mrr_k=mrr_k)
                    first_rank = next((rank for rank, identifier in enumerate(ranked, 1) if identifier in relevant), None)
                    rows.append(dict(mode=mode, query_id=entry['id'], slot=slot, repeat=repeat + 1,
                                     latency_ms=elapsed, first_relevant_rank=first_rank,
                                     relevant_ids=json.dumps(relevant, ensure_ascii=False),
                                     ranked_ids=json.dumps(ranked, ensure_ascii=False), **metrics))
                coverage_slots = dataset.get('required_slots') or list(entry['relevant_by_slot'])
                candidate_coverage[mode].append(float(all(_ranking(result, slot, include_fallback=True) for slot in coverage_slots)))
                for cutoff in (1, 3):
                    complete = all(set(rankings.get(slot, [])[:cutoff]).intersection(entry['relevant_by_slot'][slot]) for slot in coverage_slots)
                    coverage[mode][cutoff].append(float(complete))
                recorded_request = dict(request)
                if 'query_image' in entry:
                    recorded_request['query_image'] = entry['query_image']
                raw_rows.append(dict(mode=mode, query_id=entry['id'], repeat=repeat + 1,
                                     latency_ms=elapsed, request=recorded_request, result=result))

    summary: dict[str, Any] = dict(
        schema_version=1, created_at=datetime.now(timezone.utc).isoformat(),
        dataset={key: value for key, value in dataset.items() if key not in ('queries',) and not key.startswith('_')},
        query_count=len(dataset['queries']), repeats=repeats, warmup_per_query_mode=warmup,
        mrr_k=mrr_k,
        latency_protocol='Serial in-process wall-clock retrieval only, after declared warmups. No LLM, UI, indexing or model initialization included.',
        statistical_unit='Query-slot pairs; repeated calls are repeated measurements, not independent new queries.',
        runtime=dict(python=platform.python_version(), system=platform.platform()),
        metadata=_jsonable(dict(metadata or {})), modes={})
    for key, internal in (('dataset_sha256', '_dataset_path'), ('corpus_sha256', '_corpus_path')):
        if dataset.get(internal) and Path(dataset[internal]).is_file():
            summary[key] = hashlib.sha256(Path(dataset[internal]).read_bytes()).hexdigest()
    for mode in modes:
        selected = [row for row in rows if row['mode'] == mode]
        by_slot = {slot: _mean_metrics([row for row in selected if row['slot'] == slot], metric_keys)
                   for slot in sorted({row['slot'] for row in selected})}
        # Macro across categories; pooled query-slot mean is reported separately.
        macro = {key: statistics.fmean(value[key] for value in by_slot.values()) for key in metric_keys}
        summary['modes'][mode] = dict(metrics=macro, pooled_metrics=_mean_metrics(selected, metric_keys),
            by_slot=by_slot, full_slot_coverage={f'@{cutoff}': statistics.fmean(values) for cutoff, values in coverage[mode].items()},
            candidate_slot_coverage_with_fallback=statistics.fmean(candidate_coverage[mode]),
            query_slot_pairs=len(selected) // repeats, retrieval_calls=len(latencies[mode]),
            latency_ms=_timing_summary(latencies[mode]),
            component_timings_ms={key: _timing_summary(values) for key, values in components[mode].items()},
            first_observed_call_ms=first_observed[mode],
            warnings=sorted(mode_warnings[mode]))

    measurement_fields = ['mode', 'query_id', 'slot', 'repeat', 'latency_ms', 'first_relevant_rank', *metric_keys, 'relevant_ids', 'ranked_ids']
    with (output / 'measurements.csv').open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=measurement_fields)
        writer.writeheader()
        writer.writerows(rows)
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(row['mode'], row['query_id'], row['slot'])].append(row)
    aggregate_rows = []
    for (mode, query_id, slot), group in grouped.items():
        aggregate_rows.append(dict(mode=mode, query_id=query_id, slot=slot,
            latency_median_ms=statistics.median(row['latency_ms'] for row in group),
            repeats=repeats, relevant_ids=group[0]['relevant_ids'], ranked_ids_first_repeat=group[0]['ranked_ids'],
            **_mean_metrics(group, metric_keys)))
    with (output / 'per_query.csv').open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=['mode', 'query_id', 'slot', 'repeats', 'latency_median_ms', *metric_keys, 'relevant_ids', 'ranked_ids_first_repeat'])
        writer.writeheader()
        writer.writerows(aggregate_rows)
    (output / 'raw_rankings.jsonl').write_text(''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in raw_rows), encoding='utf-8')
    (output / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    _write_report(summary, output / 'research_report.md')
    return summary


def _write_report(summary: Mapping[str, Any], path: Path) -> None:
    mrr_k = summary['mrr_k']
    lines = ['# Измерения retrieval', '',
        f'Запросов: {summary["query_count"]}; повторов: {summary["repeats"]}; прогревов на запрос/режим: {summary["warmup_per_query_mode"]}.', '',
        '| Режим | HitRate@1 | HitRate@3 | MRR@' + str(mrr_k) + ' | Все слоты @3 | Median, ms | p95, ms |',
        '|---|---:|---:|---:|---:|---:|---:|']
    for mode, values in summary['modes'].items():
        metrics = values['metrics']
        lines.append(f'| {mode} | {metrics["hit_rate@1"]:.4f} | {metrics["hit_rate@3"]:.4f} | {metrics[f"mrr@{mrr_k}"]:.4f} | {values["full_slot_coverage"]["@3"]:.4f} | {values["latency_ms"]["median"]:.2f} | {values["latency_ms"]["p95"]:.2f} |')
    lines.extend(['', 'HitRate и MRR показаны как macro-average по категориям. Покомпонентные результаты находятся в summary.json и per_query.csv.', '',
        'Latency — последовательные вызовы retrieval внутри процесса после прогрева. Индексация, скачивание/загрузка модели, LLM и браузер сюда не входят. first_observed_call_ms в JSON — первый наблюдавшийся вызов, а не гарантированный холодный запуск нового процесса.', '',
        'Кандидаты fallback=true исключены из рангов HitRate/MRR и релевантного покрытия слотов. Они учитываются отдельно в candidate_slot_coverage_with_fallback: это возможность собрать категории, а не качество поиска.', '',
        'Повторные измерения не увеличивают число независимых тестовых запросов. На небольшой выборке p95 следует интерпретировать осторожно.', '',
        'Происхождение корпуса и разметки:', '', '```json',
        json.dumps(summary['dataset'].get('provenance', {}), ensure_ascii=False, indent=2), '```', '',
        'Если annotation_status указывает draft/requires_review, метрики предварительные до независимой проверки ground truth командой. SVG и их преобразования не подтверждают качество поиска по новым фотографиям одежды.', '',
        'Конфигурация и оборудование:', '', '```json', json.dumps(dict(runtime=summary['runtime'], metadata=summary['metadata'],
            dataset_sha256=summary.get('dataset_sha256'), corpus_sha256=summary.get('corpus_sha256')), ensure_ascii=False, indent=2), '```', ''])
    path.write_text('\n'.join(lines), encoding='utf-8')
