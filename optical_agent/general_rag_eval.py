"""Independent, frozen evaluation for general-natural knowledge retrieval.

This protocol is deliberately separate from the historical C0/C1 benchmark.
Gold labels are consumed by scoring only; retrieval receives query text only.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import csv
from datetime import datetime, timezone
from importlib.metadata import version, PackageNotFoundError
import json
import os
from pathlib import Path
import platform
import shutil
import sys
from time import perf_counter

import numpy as np

from .rag_engine import (MODEL_REVISION, QUERY_INSTRUCTION, LocalEncoder,
                         RagRetriever, build_chunks, file_hash, fingerprint)
from .rag_eval import KS, chunk_groups, paired_interval, score_question, summarize

PROTOCOL = 'general-rag-v1'
SEED = 20261023
MODES = ('tfidf', 'embedding', 'hybrid')
CORPORA = ('G0', 'G1')
FIXED_THRESHOLDS = {'tfidf': .1, 'dense': .75}
DEFAULT_ROOT = Path(r'D:\CodexData\optical_agent\rag\general_v061\run_20261023')
MANIFESTS = {'G0': 'knowledge/GENERAL_SOURCES.json',
             'G1': 'knowledge/GENERAL_V2_SOURCES.json'}
LABEL_PATH = 'eval/general_rag_questions.json'
MODEL_PATH = Path(r'D:\CodexData\optical_agent\rag\models\bge-small-zh-v1.5')
POLICY = {
    'selection': 'dev_only; feasible negative<=0.10, then Recall@3, MRR@10, lower CPU P95; ties tfidf/embedding/hybrid',
    'threshold_selection': 'dev_only; Recall@3, MRR@10, lower negative error, higher thresholds',
    'method_gate': 'tuned G1 selected candidate vs tuned G1 TF-IDF: R3 gain>=.05, MRR nondecrease, negative<=.10, CPU P95<=500ms',
    'corpus_gate': 'selected method SAME FIXED thresholds G1 vs G0: old R3/MRR nondecrease and G1 new R3>=.80',
    'release_guard': 'selected tuned G1 old R3/MRR nondecrease vs current fixed G0 TF-IDF AND tuned new R3>=.80',
    'failed_gate': 'retain G0 TF-IDF at .10/.75; never choose another method using heldout results',
    'G0_primary': '30 answerable + 10 negative per split; new-only questions remain in denominator and are marked missing knowledge',
    'G1_primary': '30 answerable + 10 negative per split',
    'negative': 'any delivered result on an unanswerable question is a false return',
    'confidence_interval': 'paired fact-group bootstrap; seed 20261023; 2000 resamples; 80 questions are small scale',
}


def _read(path):
    return json.loads(Path(path).read_text(encoding='utf8'))


def _write(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    temporary.replace(path)


def evidence_map(dataset):
    """Flatten per-question gold without putting it into the retrieval corpus."""
    result = {}
    for question in dataset['questions']:
        for group in question.get('evidence', []):
            key = group['group_id']
            spec = {'alternatives': group['alternatives']}
            if key in result and result[key] != spec:
                raise ValueError('Conflicting evidence group: ' + key)
            result[key] = spec
    return result


def validate_general_labels(dataset, source_root, corpora=None):
    """Validate denominators, split isolation and exact Unicode source offsets."""
    questions = dataset.get('questions', [])
    if dataset.get('protocol_version') != PROTOCOL:
        raise ValueError('Unexpected general RAG protocol version')
    if dataset.get('seed') != SEED:
        raise ValueError('Unexpected general RAG seed')
    if len(questions) != 80 or len({q['id'] for q in questions}) != 80:
        raise ValueError('General RAG requires exactly 80 unique questions')
    expected = {(split, scope): count for split in ('dev', 'test')
                for scope, count in (('existing', 20), ('new', 10), ('unanswerable', 10))}
    if dict(Counter((q['split'], q['scope']) for q in questions)) != expected:
        raise ValueError('General RAG split denominators differ from 20/10/10')
    groups, required_splits = defaultdict(set), defaultdict(set)
    evidence = evidence_map(dataset)
    root = Path(source_root).resolve()
    for q in questions:
        if not isinstance(q['query'], str) or not q['query'].strip() or len(q['query']) > 2000:
            raise ValueError('Invalid evaluation query')
        groups[q['fact_group']].add(q['split'])
        required = q['required_groups']
        if len(set(required)) != len(required):
            raise ValueError('Repeated required evidence group')
        if (q['scope'] == 'unanswerable') != (not required):
            raise ValueError('Unanswerable question must have no required evidence')
        if q['scope'] == 'unanswerable' and q.get('evidence'):
            raise ValueError('Unanswerable question has gold evidence')
        if {g['group_id'] for g in q.get('evidence', [])} != set(required):
            raise ValueError('Per-question gold must exactly cover required groups')
        for group in required:
            required_splits[group].add(q['split'])
            if not evidence[group]['alternatives']:
                raise ValueError('Empty evidence alternatives')
    if any(len(splits) > 1 for splits in list(groups.values()) + list(required_splits.values())):
        raise ValueError('Fact or evidence group leaked across dev/test')
    for spec in evidence.values():
        for alternative in spec['alternatives']:
            path = (root / alternative['path']).resolve()
            if not path.is_relative_to(root) or 'knowledge' not in path.relative_to(root).parts:
                raise ValueError('Gold source must be a knowledge file inside the repository')
            source = path.read_text(encoding='utf8')
            start, end = alternative['start'], alternative['end']
            if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(source):
                raise ValueError('Invalid gold source offsets')
            if source[start:end] != alternative['quote']:
                raise ValueError('Gold quote offset invalid')
    if corpora is not None:
        g0, g1 = corpora['G0'], corpora['G1']
        if len(g0) != 14 or g1[:len(g0)] != g0:
            raise ValueError('G1 must retain all 14 original G0 chunks unchanged and in order')
        if any(c.get('vision_modes') != ['general_rgb_v1'] for c in g1):
            raise ValueError('Non-general knowledge entered the general corpus')
        if any(not str(c['path']).replace('\\', '/').startswith('knowledge/') for c in g1):
            raise ValueError('Evaluation labels must never enter the index')
        source_pairs = {(c['source_id'], c['path']) for c in g1}
        for spec in evidence.values():
            if any((a['source_id'], a['path']) not in source_pairs for a in spec['alternatives']):
                raise ValueError('Gold source identity/path is not in the general corpus')
        represented = {name: set(g for c in chunks for g in chunk_groups(c, evidence))
                       for name, chunks in corpora.items()}
        for q in questions:
            required = set(q['required_groups'])
            if q['scope'] != 'unanswerable' and not required <= represented['G1']:
                raise ValueError('Gold evidence is not representable in G1 chunks: ' + q['id'])
            if q['scope'] == 'existing' and not required <= represented['G0']:
                raise ValueError('Existing question cannot be answered by G0: ' + q['id'])
            if q['scope'] == 'new' and required <= represented['G0']:
                raise ValueError('New-only question already fully answered by G0: ' + q['id'])
    return True


def load_inputs(repo):
    repo = Path(repo).resolve()
    dataset = _read(repo / LABEL_PATH)
    corpora = {name: build_chunks(repo, manifest) for name, manifest in MANIFESTS.items()}
    validate_general_labels(dataset, repo, corpora)
    return dataset, corpora


def validate_review(review_file, labels_path):
    review = _read(review_file)
    if review.get('accepted') is not True or review.get('provisional') is not True:
        raise ValueError('Independent provisional label review must explicitly accept the dataset')
    if review.get('dataset_sha256') != file_hash(labels_path):
        raise ValueError('Label review does not match the current dataset hash')
    return review


def _input_files(repo, model_path):
    repo = Path(repo).resolve()
    paths = [repo / LABEL_PATH]
    for manifest in MANIFESTS.values():
        paths.append(repo / manifest)
        paths.extend(repo / source['path'] for source in _read(repo / manifest))
    paths.extend(repo / name for name in ('optical_agent/rag_engine.py', 'optical_agent/rag_eval.py',
        'optical_agent/general_rag_eval.py', 'optical_agent/experiments/evaluate_general_rag.py'))
    paths.extend(p for p in Path(model_path).iterdir()
                 if p.is_file() and p.suffix in {'.json', '.txt', '.safetensors'})
    return {str(path.resolve()): file_hash(path) for path in sorted(set(paths))}


def prepare_run(repo, run_root=DEFAULT_ROOT, *, review_file, model_path=MODEL_PATH):
    repo, run = Path(repo).resolve(), Path(run_root).resolve()
    if (run / 'freeze.json').exists():
        raise ValueError('A frozen run cannot be prepared or reset again')
    dataset, corpora = load_inputs(repo)
    review = validate_review(review_file, repo / LABEL_PATH)
    run.mkdir(parents=True, exist_ok=True)
    _write(run / 'review.json', review)
    _write(run / 'questions.json', dataset)
    encoder_started = perf_counter()
    encoder = LocalEncoder(model_path=model_path, device='cpu')
    model_load_ms = (perf_counter() - encoder_started) * 1000
    index_metadata = {}
    for name, chunks in corpora.items():
        _write(run / (name + '_chunks.json'), chunks)
        retriever = RagRetriever(chunks, 'embedding', encoder=encoder,
            cache_root=run / 'indexes', build=True, corpus_name=name)
        index_metadata[name] = dict(retriever.metadata(), count=len(chunks),
                                   index_build_ms=retriever.index_build_ms)
    paths = _input_files(repo, model_path)
    for name, digest in paths.items():
        path = Path(name)
        if path.is_relative_to(repo):
            archived = run / 'frozen_source' / path.relative_to(repo)
            archived.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, archived)
    frozen_artifacts = [run / 'review.json', run / 'questions.json']
    frozen_artifacts.extend(run / (name + '_chunks.json') for name in CORPORA)
    frozen_artifacts.extend(p for p in (run / 'indexes').rglob('*') if p.is_file())
    freeze = {'protocol_version': PROTOCOL, 'seed': SEED,
        'created_at_utc': datetime.now(timezone.utc).isoformat(),
        'repository': str(repo), 'model_path': str(Path(model_path).resolve()),
        'model_revision': MODEL_REVISION, 'query_instruction': QUERY_INSTRUCTION,
        'chunking': {'maximum_characters': 400, 'overlap_characters': 80},
        'rrf': {'channel_top_k': 20, 'constant': 60, 'equal_weights': True},
        'policy': POLICY, 'files': paths,
        'artifacts': {str(p.relative_to(run)): file_hash(p) for p in sorted(frozen_artifacts)},
        'corpora': index_metadata, 'model_load_ms': model_load_ms,
        'environment': environment_snapshot(),
        'paid_api_requests': 0, 'external_human_label_review': False,
        'review_status': 'same_model_family_provisional'}
    _write(run / 'freeze.json', freeze)
    return freeze


def environment_snapshot():
    packages = {}
    for name in ('numpy', 'scikit-learn', 'torch', 'transformers', 'tokenizers', 'safetensors'):
        try:
            packages[name] = version(name)
        except PackageNotFoundError:
            packages[name] = None
    torch = sys.modules.get('torch')
    return {'python': platform.python_version(), 'platform': platform.platform(),
            'cpu': platform.processor(), 'logical_cpu_count': os.cpu_count(),
            'torch_cpu_threads': torch.get_num_threads() if torch is not None else None,
            'packages': packages, 'query_device': 'cpu'}


def verify_freeze(repo, run_root, *, require_selection=False):
    run = Path(run_root)
    frozen = _read(run / 'freeze.json')
    if frozen.get('protocol_version') != PROTOCOL or frozen.get('policy') != POLICY:
        raise ValueError('Evaluation protocol or predeclared policy changed')
    if frozen['files'] != _input_files(repo, frozen['model_path']):
        raise ValueError('Frozen source, labels, knowledge or model changed; use a new run')
    for relative, digest in frozen['artifacts'].items():
        if file_hash(run / relative) != digest:
            raise ValueError('Frozen run artifact changed: ' + relative)
    if require_selection:
        lock = _read(run / 'selection.lock.json')
        if lock['freeze_sha256'] != file_hash(run / 'freeze.json') or lock['selection_sha256'] != file_hash(run / 'selection.json'):
            raise ValueError('Frozen development selection changed')
    return frozen


def _primary(records, corpus):
    # The 2x3 comparison always has identical denominators. Existing/new scopes
    # are also reported separately for questions that G0 could actually answer.
    return list(records)


def metrics_for(records, corpus):
    primary = _primary(records, corpus)
    old = [r for r in records if r['scope'] in {'existing', 'unanswerable'}]
    new = [r for r in records if r['scope'] == 'new']
    multi = [r for r in primary if len(r['required_groups']) > 1]
    return {'delivered': summarize(primary), 'raw': summarize(primary, 'raw'),
        'multi_evidence': {'questions': len(multi),
            'delivered_full_hit': {str(k): float(np.mean([r['delivered']['full'][str(k)] for r in multi])) if multi else None for k in KS},
            'raw_full_hit': {str(k): float(np.mean([r['raw']['full'][str(k)] for r in multi])) if multi else None for k in KS}},
        'old_questions': {'delivered': summarize(old), 'raw': summarize(old, 'raw')},
        'new_questions': {'delivered': summarize(new), 'raw': summarize(new, 'raw')},
        'denominators': {'all_queries': len(records), 'primary_answerable': sum(r['kind'] != 'unanswerable' for r in primary),
                         'primary_negative': sum(r['kind'] == 'unanswerable' for r in primary),
                         'new_excluded_from_G0_primary': False}}


def _failure(q, raw_score, delivered_score, corpus):
    if q['scope'] == 'new' and corpus == 'G0':
        return 'knowledge_missing'
    if q['scope'] == 'unanswerable':
        return 'unsupported_return' if delivered_score['false_return'] else None
    if delivered_score['full']['3']:
        return None
    return 'threshold_rejection' if raw_score['full']['3'] else 'ranking_error'


def evaluate_questions(retriever, questions, evidence):
    records = []
    for question in questions:
        raw = retriever.rank(question['query'], 20, filtered=False)
        delivered = retriever.rank(question['query'], 20, filtered=True)
        raw_score = score_question(question, raw, evidence)
        delivered_score = score_question(question, delivered, evidence)
        required = set(question['required_groups'])
        off_target = [chunk['citation_id'] for chunk in delivered
                      if not required.intersection(chunk_groups(chunk, evidence))]
        records.append(dict(question, kind=question['scope'], raw=raw_score, delivered=delivered_score,
            raw_ranking=raw, delivered_ranking=delivered, retrieval_off_target_ids=off_target,
            citation_validation_status='not_applicable_no_generated_answers',
            failure_class=_failure(question, raw_score, delivered_score, retriever.corpus_name)))
    return records


def select_thresholds(retriever, questions, evidence):
    if any(q['split'] != 'dev' for q in questions):
        raise ValueError('Threshold selection may only consume development labels')
    lexical = (.05, .1, .15, .2, .25, .3, .4, .5, 1.1)
    semantic = (.5, .55, .6, .65, .7, .75, .8, .85, .9, .95, 1.1)
    grid = [(a, b) for a in lexical for b in semantic]
    if retriever.mode == 'tfidf':
        grid = [(a, .75) for a in lexical]
    if retriever.mode == 'embedding':
        grid = [(.1, b) for b in semantic]
    tried, best = [], None
    for lexical_threshold, dense_threshold in grid:
        retriever.thresholds = {'tfidf': lexical_threshold, 'dense': dense_threshold}
        records = evaluate_questions(retriever, questions, evidence)
        metrics = metrics_for(records, retriever.corpus_name)['delivered']
        feasible = metrics['no_answer_false_return'] <= .1
        tried.append({'thresholds': dict(retriever.thresholds), 'metrics': metrics, 'feasible': feasible})
        objective = (metrics['recall']['3'], metrics['mrr10'], -metrics['no_answer_false_return'], lexical_threshold, dense_threshold)
        if feasible and (best is None or objective > best[0]):
            best = objective, dict(retriever.thresholds)
    if best is None:
        raise ValueError('No feasible development rejection threshold; do not use heldout labels')
    retriever.thresholds = best[1]
    return best[1], tried


def latency(retriever, questions, repeats=5):
    if not questions:
        raise ValueError('Latency requires questions')
    retriever.rank(questions[0]['query'])
    uncached, cached = [], []
    for _ in range(repeats):
        for question in questions:
            retriever.query_cache.clear()
            started = perf_counter()
            retriever.rank(question['query'])
            uncached.append((perf_counter() - started) * 1000)
            started = perf_counter()
            retriever.rank(question['query'])
            cached.append((perf_counter() - started) * 1000)
    return {'cpu_warm_mean_ms': float(np.mean(uncached)), 'cpu_warm_p95_ms': float(np.percentile(uncached, 95)),
        'cached_mean_ms': float(np.mean(cached)), 'cached_p95_ms': float(np.percentile(cached, 95)),
        'timed_queries': len(uncached), 'repetitions': repeats, 'independent_questions': len(questions),
        'includes_query_encoding': True, 'excludes_model_load': True, 'device': 'cpu'}


def _rss_mb():
    try:
        import psutil
        return psutil.Process().memory_info().rss / 1024 ** 2
    except ImportError:
        return None


def run_split(repo, run_root, split):
    if split not in {'dev', 'test'}:
        raise ValueError('Unknown split')
    run = Path(run_root)
    frozen = verify_freeze(repo, run, require_selection=split == 'test')
    output = run / (split + '.json')
    if output.exists():
        raise ValueError('Existing split results cannot be overwritten')
    if split == 'dev' and (run / 'selection.json').exists():
        raise ValueError('Development selection already exists')
    dataset = _read(run / 'questions.json')
    evidence = evidence_map(dataset)
    questions = [q for q in dataset['questions'] if q['split'] == split]
    selected = _read(run / 'selection.json') if split == 'test' else None
    encoder_started = perf_counter()
    encoder = LocalEncoder(model_path=frozen['model_path'], device='cpu')
    model_load_ms = (perf_counter() - encoder_started) * 1000
    progress_path = run / (split + '_progress.json')
    if progress_path.exists():
        progress = _read(progress_path)
        if progress.get('freeze_sha256') != file_hash(run / 'freeze.json'):
            raise ValueError('Partial results belong to a different frozen run')
        results, selections = progress['results'], progress['selections']
    else:
        results, selections = {}, {}
    for corpus in CORPORA:
        chunks = _read(run / (corpus + '_chunks.json'))
        for mode in MODES:
            key = corpus + '/' + mode
            if key in results:
                continue
            started, rss_before = perf_counter(), _rss_mb()
            retriever = RagRetriever(chunks, mode, encoder=encoder if mode != 'tfidf' else None,
                cache_root=run / 'indexes', corpus_name=corpus, thresholds=FIXED_THRESHOLDS)
            load_ms = (perf_counter() - started) * 1000
            fixed_records = evaluate_questions(retriever, questions, evidence)
            if split == 'dev':
                thresholds, grid = select_thresholds(retriever, questions, evidence)
                selections[key] = {'thresholds': thresholds, 'grid': grid}
            else:
                retriever.thresholds = selected['profiles'][key]['thresholds']
            tuned_records = evaluate_questions(retriever, questions, evidence)
            speed = latency(retriever, questions)
            rss_after = _rss_mb()
            results[key] = {
                'fixed': dict(metrics_for(fixed_records, corpus), records=fixed_records,
                              thresholds=dict(FIXED_THRESHOLDS)),
                'tuned': dict(metrics_for(tuned_records, corpus), records=tuned_records,
                              thresholds=dict(retriever.thresholds)),
                'latency': speed, 'metadata': retriever.metadata(), 'load_ms': load_ms,
                'index_build_ms': retriever.index_build_ms, 'process_rss_mb': rss_after,
                'rss_delta_mb': rss_after - rss_before if rss_after is not None and rss_before is not None else None,
                'sparse_matrix_bytes': int(retriever.matrix.data.nbytes + retriever.matrix.indices.nbytes + retriever.matrix.indptr.nbytes),
                'dense_vector_bytes': int(retriever.vectors.nbytes) if retriever.vectors is not None else 0}
            _write(progress_path, {'freeze_sha256': file_hash(run / 'freeze.json'),
                                  'results': results, 'selections': selections})
            metrics = results[key]['tuned']['delivered']
            print(key, 'Recall@3', round(metrics['recall']['3'], 4), 'MRR@10', round(metrics['mrr10'], 4),
                  'negative', metrics['no_answer_false_return'], flush=True)
    payload = {'protocol_version': PROTOCOL, 'split': split, 'results': results,
        'freeze_sha256': file_hash(run / 'freeze.json'), 'http_requests': 0, 'paid_api_requests': 0,
        'model_load_ms': model_load_ms, 'label_review': 'same_model_family_provisional',
        'external_human_label_review': False}
    _write(output, payload)
    if split == 'dev':
        eligible = [mode for mode in MODES
                    if results['G1/' + mode]['tuned']['delivered']['no_answer_false_return'] <= .1]
        candidate = max(eligible, key=lambda mode: (
            results['G1/' + mode]['tuned']['delivered']['recall']['3'],
            results['G1/' + mode]['tuned']['delivered']['mrr10'],
            -results['G1/' + mode]['latency']['cpu_warm_p95_ms'], -MODES.index(mode)))
        selection = {'profiles': selections, 'candidate': {'corpus': 'G1', 'mode': candidate},
                     'selected_using': 'dev_only', 'policy': POLICY}
        _write(run / 'selection.json', selection)
        _write(run / 'selection.lock.json', {'freeze_sha256': file_hash(run / 'freeze.json'),
            'selection_sha256': file_hash(run / 'selection.json')})
    return payload


def release_decision(test_payload, selection):
    """Check the one preselected candidate; never select a heldout runner-up."""
    results = test_payload['results']
    mode = selection['candidate']['mode']
    selected = results['G1/' + mode]
    candidate = selected['tuned']['delivered']
    reference = results['G1/tfidf']['tuned']['delivered']
    method_checks = {
        'recall3_gain_at_least_5pp': candidate['recall']['3'] - reference['recall']['3'] >= .05 - 1e-12,
        'mrr_not_lower': candidate['mrr10'] >= reference['mrr10'] - 1e-12,
        'no_answer_false_return_at_most_10pct': candidate['no_answer_false_return'] <= .1 + 1e-12,
        'cpu_hot_p95_at_most_500ms': selected['latency']['cpu_warm_p95_ms'] <= 500}
    # Retaining the TF-IDF algorithm is not an algorithm promotion, but the new
    # corpus and its tuned rejection threshold still need their own guards.
    method_passed = all(method_checks.values()) if mode != 'tfidf' else (
        method_checks['no_answer_false_return_at_most_10pct'] and method_checks['cpu_hot_p95_at_most_500ms'])
    old_g0 = results['G0/' + mode]['fixed']['old_questions']['delivered']
    old_g1 = selected['fixed']['old_questions']['delivered']
    new_g1 = selected['fixed']['new_questions']['delivered']
    corpus_checks = {
        'old_fixed_recall3_not_lower': old_g1['recall']['3'] >= old_g0['recall']['3'] - 1e-12,
        'old_fixed_mrr_not_lower': old_g1['mrr10'] >= old_g0['mrr10'] - 1e-12,
        'new_fixed_recall3_at_least_80pct': new_g1['recall']['3'] >= .8 - 1e-12}
    release_old = selected['tuned']['old_questions']['delivered']
    current_old = results['G0/tfidf']['fixed']['old_questions']['delivered']
    guard_checks = {
        'release_old_recall3_not_lower_than_current': release_old['recall']['3'] >= current_old['recall']['3'] - 1e-12,
        'release_old_mrr_not_lower_than_current': release_old['mrr10'] >= current_old['mrr10'] - 1e-12,
        'release_new_recall3_at_least_80pct': selected['tuned']['new_questions']['delivered']['recall']['3'] >= .8 - 1e-12}
    passed = method_passed and all(corpus_checks.values()) and all(guard_checks.values())
    release = {'corpus': 'general-natural-v2', 'snapshot': 'G1', 'mode': mode,
               'thresholds': selected['tuned']['thresholds']} if passed else {
                   'corpus': 'general-natural-v1', 'snapshot': 'G0', 'mode': 'tfidf',
                   'thresholds': dict(FIXED_THRESHOLDS)}
    return {'protocol_version': PROTOCOL, 'selected_using': 'dev_only',
        'candidate': selection['candidate'], 'promotion_passed': passed,
        'method_checks': method_checks, 'method_gate_passed': method_passed,
        'method_replacement_required': mode != 'tfidf', 'corpus_checks': corpus_checks,
        'release_guard_checks': guard_checks, 'release_recommendation': release,
        'acceptance_status': 'passed_small_scale_project_eval' if passed else 'not_promoted_current_default_retained',
        'external_human_label_review': False, 'label_review_status': 'same_model_family_provisional',
        'limits': 'Retrieval only; not real LLM answer quality, visual accuracy, or multi-agent performance.'}


def _paired(left, right):
    left = [r for r in left if r['scope'] != 'unanswerable']
    right = [r for r in right if r['scope'] != 'unanswerable']
    return {metric: paired_interval(left, right, metric=metric, seed=SEED)
            for metric in ('recall3', 'mrr10')}


def write_report(repo, run_root):
    run = Path(run_root)
    frozen = verify_freeze(repo, run, require_selection=True)
    dev, test, selection = _read(run / 'dev.json'), _read(run / 'test.json'), _read(run / 'selection.json')
    decision = release_decision(test, selection)
    intervals = {'fixed_corpus_old': {}, 'tuned_algorithm': {}, 'threshold_changes': {}}
    for mode in MODES:
        left = [r for r in test['results']['G0/' + mode]['fixed']['records'] if r['scope'] != 'new']
        right = [r for r in test['results']['G1/' + mode]['fixed']['records'] if r['scope'] != 'new']
        intervals['fixed_corpus_old'][mode] = _paired(left, right)
        intervals['tuned_algorithm'][mode] = _paired(test['results']['G1/tfidf']['tuned']['records'],
                                                    test['results']['G1/' + mode]['tuned']['records'])
    for key, result in test['results'].items():
        intervals['threshold_changes'][key] = _paired(_primary(result['fixed']['records'], key.split('/')[0]),
                                                       _primary(result['tuned']['records'], key.split('/')[0]))
    summary = {'protocol_version': PROTOCOL, 'run_id': run.name,
        'environment': frozen.get('environment'), 'corpus_identities': frozen['corpora'],
        'labels_sha256': file_hash(run / 'frozen_source' / LABEL_PATH),
        'freeze_sha256': file_hash(run / 'freeze.json'),
        'selection_sha256': file_hash(run / 'selection.json'), 'dev_sha256': file_hash(run / 'dev.json'),
        'test_sha256': file_hash(run / 'test.json'), 'decision': decision, 'paired_intervals': intervals,
        'question_counts': {'dev': 40, 'test': 40, 'total': 80},
        'metrics': {split: {key: {stage: {field: result[stage][field] for field in
            ('delivered', 'raw', 'old_questions', 'new_questions', 'multi_evidence', 'denominators', 'thresholds')}
            for stage in ('fixed', 'tuned')} | {'latency': result['latency'],
                'index_build_ms': result['index_build_ms'], 'process_rss_mb': result['process_rss_mb'],
                'sparse_matrix_bytes': result['sparse_matrix_bytes'], 'dense_vector_bytes': result['dense_vector_bytes']}
            for key, result in payload['results'].items()} for split, payload in (('dev', dev), ('test', test))},
        'paid_api_requests': 0, 'http_requests': 0,
        'external_human_label_review': False, 'label_review_status': 'same_model_family_provisional'}
    _write(run / 'decision.json', decision)
    _write(run / 'summary.json', summary)
    rows = []
    for split, payload in (('dev', dev), ('test', test)):
        for key, result in payload['results'].items():
            for stage in ('fixed', 'tuned'):
                for record in result[stage]['records']:
                    if record['failure_class']:
                        rows.append({'split': split, 'profile': key, 'stage': stage, 'id': record['id'],
                            'scope': record['scope'], 'fact_group': record['fact_group'], 'query': record['query'],
                            'failure_class': record['failure_class'],
                            'missing_at10': '|'.join(record['delivered']['missing_at10']),
                            'delivered_citations': '|'.join(c['citation_id'] for c in record['delivered_ranking']),
                            'retrieval_off_target_ids': '|'.join(record['retrieval_off_target_ids'])})
    with (run / 'failures.csv').open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=['split', 'profile', 'stage', 'id', 'scope', 'fact_group',
            'query', 'failure_class', 'missing_at10', 'delivered_citations', 'retrieval_off_target_ids'])
        writer.writeheader()
        writer.writerows(rows)
    lines = ['# 通用图像 RAG 独立对照报告', '',
        '80 条问题：开发集与保留集各 40 条；同事实按组隔离。标签经同模型家族独立代理暂定审核，未经外部人工验收。', '',
        'G0/G1 主分母统一为 30 条可回答问题，另有 10 条无答案问题。另报旧知识 20 题和新知识 10 题；G0 的新题仍计入覆盖分母，失败原因标为知识缺失。', '',
        '下表均为保留集。固定阈值对照隔离知识补充，调优阈值仅由开发集选择。排名分数不是正确概率。', '']
    for stage, title in (('fixed', '固定阈值（TF-IDF 0.10，Embedding 0.75）'), ('tuned', '开发集选定阈值')):
        lines.extend(['## ' + title, '', '|语料 / 方法|交付 R@1 / 3 / 5 / 10|原始 R@3|交付 MRR@10|多证据完整命中@3|无答案误返回|CPU P95 ms|',
                      '|---|---|---:|---:|---:|---:|---:|'])
        for key, result in test['results'].items():
            metric = result[stage]['delivered']
            raw = result[stage]['raw']
            recalls = ' / '.join(f"{100 * metric['recall'][str(k)]:.1f}%" for k in KS)
            multi = result[stage]['multi_evidence']['delivered_full_hit']['3']
            multi_text = f'{100 * multi:.1f}%' if multi is not None else '无多证据题'
            lines.append(f"|{key}|{recalls}|{100 * raw['recall']['3']:.1f}%|{metric['mrr10']:.3f}|{multi_text}|{100 * metric['no_answer_false_return']:.1f}%|{result['latency']['cpu_warm_p95_ms']:.1f}|")
        lines.append('')
    lines.extend(['## 发布决定', '', f"开发集预先选择：G1/{selection['candidate']['mode']}。保留集门槛：{'通过' if decision['promotion_passed'] else '未通过，保留当前默认值'}。", '',
        '```json', json.dumps(decision, ensure_ascii=False, indent=2), '```', '',
        '## 解释与复现', '',
        '- 同一事实在重叠片段中只记一次；多证据问题按证据组计算 Recall，MRR 取首条相关证据的倒数排名。',
        '- 原始排名不设拒绝阈值；交付排名使用对应固定或开发集阈值。无答案问题不进入 Recall/MRR 分母。',
        '- 热查询计时包含 CPU 查询编码，排除模型加载，每题重复五次；重复不增加独立样本数。缓存命中耗时另存 JSON。',
        '- 原始逐题排名在 dev.json / test.json，错误表在 failures.csv；summary.json 包含按事实组配对置信区间、资源占用、索引时间与来源哈希。',
        '- retrieval_off_target_ids 仅表示没有覆盖该题必要证据组的检索结果；本轮不生成答案，不评测生成式引用正确率。版本隔离由语料校验与回归测试保障，不以此宣称已测量语义版本错误率。',
        '- TF-IDF、Embedding 与 Hybrid 的算法差异、G0/G1 的知识差异及阈值变化分别列示，不把旧水下 C0/C1 成绩用于通用语料。',
        '- 评测全程本地，无付费 API；结果只说明小规模项目检索效果，不代表真实 LLM 回答质量、视觉精度或多 Agent 协作收益。', ''])
    (run / 'REPORT.md').write_text('\n'.join(lines), encoding='utf8')
    return summary
