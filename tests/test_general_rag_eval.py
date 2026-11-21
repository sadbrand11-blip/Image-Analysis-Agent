"""Protocol tests use invented facts and deterministic vectors, never cloud calls."""
import copy
import json
from pathlib import Path

import numpy as np
import pytest

from optical_agent import general_rag_eval as evaluation
from optical_agent.rag_engine import RagRetriever, RagUnavailable, build_chunks, file_hash
from optical_agent.rag_eval import score_question


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding='utf8')


@pytest.fixture
def protocol_fixture(tmp_path):
    repo = tmp_path / 'repo'
    old = repo / 'knowledge/old.md'
    new = repo / 'knowledge/new.md'
    old.parent.mkdir(parents=True)
    old.write_text('\n\n'.join('已有事实。第%d项说明。' % n for n in range(14)), encoding='utf8')
    new.write_text('新增事实。只供新知识题使用。', encoding='utf8')
    def source(identity, path):
        return {'id': identity, 'path': path, 'title': identity, 'url': 'https://example.invalid/source',
                'verified_at': '2026-10-23', 'source_type': 'test_fixture', 'vision_modes': ['general_rgb_v1']}
    manifest = [source('old', 'knowledge/old.md')]
    write_json(repo / evaluation.MANIFESTS['G0'], manifest)
    write_json(repo / evaluation.MANIFESTS['G1'], manifest + [source('new', 'knowledge/new.md')])
    questions = []
    for split in ('dev', 'test'):
        for scope, count in (('existing', 20), ('new', 10), ('unanswerable', 10)):
            for index in range(count):
                qid = '%s-%s-%s' % (split, scope, index)
                question = {'id': qid, 'split': split, 'scope': scope, 'fact_group': qid,
                    'query': {'existing': '已有事实', 'new': '新增事实', 'unanswerable': '无法得知的精确位置'}[scope],
                    'required_groups': [], 'evidence': []}
                if scope != 'unanswerable':
                    path = old if scope == 'existing' else new
                    quote = '已有事实。' if scope == 'existing' else '新增事实。'
                    group = 'evidence-' + qid
                    start = path.read_text(encoding='utf8').index(quote)
                    question['required_groups'] = [group]
                    question['evidence'] = [{'group_id': group, 'alternatives': [{
                        'source_id': 'old' if scope == 'existing' else 'new',
                        'path': path.relative_to(repo).as_posix(), 'quote': quote,
                        'start': start, 'end': start + len(quote)}]}]
                questions.append(question)
    dataset = {'protocol_version': evaluation.PROTOCOL, 'seed': evaluation.SEED, 'questions': questions}
    write_json(repo / evaluation.LABEL_PATH, dataset)
    for name in ('optical_agent/rag_engine.py', 'optical_agent/rag_eval.py',
                 'optical_agent/general_rag_eval.py', 'optical_agent/experiments/evaluate_general_rag.py'):
        path = repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('# synthetic frozen code', encoding='utf8')
    model = tmp_path / 'model'
    model.mkdir()
    (model / 'model.safetensors').write_bytes(b'fixture model, not real weights')
    (model / 'config.json').write_text('{}', encoding='utf8')
    review = tmp_path / 'review.json'
    write_json(review, {'accepted': True, 'provisional': True,
                        'dataset_sha256': file_hash(repo / evaluation.LABEL_PATH)})
    return repo, dataset, model, review


class FixtureEncoder:
    def __init__(self, model_path=None, device='cpu'):
        self.path, self.device = Path(model_path), device
        self.model_hash = file_hash(self.path / 'model.safetensors')
        self.asset_hash = 'fixture-assets'

    def encode(self, texts, query=False):
        vectors = np.zeros((len(texts), 512), dtype=np.float32)
        vectors[:, 0] = 1
        return vectors


def test_exact_offsets_and_fact_group_split_isolation(protocol_fixture):
    repo, dataset, _, _ = protocol_fixture
    _, corpora = evaluation.load_inputs(repo)
    assert evaluation.validate_general_labels(dataset, repo, corpora)
    bad = copy.deepcopy(dataset)
    bad['questions'][0]['evidence'][0]['alternatives'][0]['start'] += 1
    with pytest.raises(ValueError, match='offset'):
        evaluation.validate_general_labels(bad, repo)
    bad = copy.deepcopy(dataset)
    bad['questions'][40]['fact_group'] = bad['questions'][0]['fact_group']
    with pytest.raises(ValueError, match='leaked'):
        evaluation.validate_general_labels(bad, repo)
    bad = copy.deepcopy(dataset)
    bad['protocol_version'] = 'historical-c1'
    with pytest.raises(ValueError, match='protocol'):
        evaluation.validate_general_labels(bad, repo)
    bad = copy.deepcopy(dataset)
    alternative = copy.deepcopy(bad['questions'][0]['evidence'][0]['alternatives'][0])
    alternative['source_id'] = 'invented-source'
    bad['questions'][0]['evidence'][0]['alternatives'].append(alternative)
    with pytest.raises(ValueError, match='identity/path'):
        evaluation.validate_general_labels(bad, repo, corpora)


def test_review_is_bound_to_exact_label_file(protocol_fixture):
    repo, _, _, review = protocol_fixture
    assert evaluation.validate_review(review, repo / evaluation.LABEL_PATH)['accepted']
    payload = json.loads(review.read_text(encoding='utf8'))
    payload['dataset_sha256'] = '0' * 64
    write_json(review, payload)
    with pytest.raises(ValueError, match='hash'):
        evaluation.validate_review(review, repo / evaluation.LABEL_PATH)


def test_original_chunks_preserved_and_labels_cannot_enter_index(protocol_fixture):
    repo, dataset, _, _ = protocol_fixture
    _, corpora = evaluation.load_inputs(repo)
    corrupted = copy.deepcopy(corpora)
    corrupted['G1'][0]['text'] += ' changed'
    with pytest.raises(ValueError, match='14 original'):
        evaluation.validate_general_labels(dataset, repo, corrupted)
    leaked = copy.deepcopy(corpora)
    leaked['G1'][-1]['path'] = evaluation.LABEL_PATH
    with pytest.raises(ValueError, match='labels'):
        evaluation.validate_general_labels(dataset, repo, leaked)


def test_hand_computed_recall_deduplicates_overlapping_chunks():
    evidence = {'a': {'alternatives': [{'source_id': 's', 'quote': '证据甲'}]},
                'b': {'alternatives': [{'source_id': 's', 'quote': '证据乙'}]}}
    question = {'required_groups': ['a', 'b']}
    ranked = [{'citation_id': 's:1', 'source_id': 's', 'text': '证据甲'},
              {'citation_id': 's:2', 'source_id': 's', 'text': '重复的证据甲'},
              {'citation_id': 's:3', 'source_id': 's', 'text': '无关'},
              {'citation_id': 's:4', 'source_id': 's', 'text': '证据乙'}]
    score = score_question(question, ranked, evidence)
    assert score['recall']['1'] == .5
    assert score['recall']['3'] == .5
    assert score['recall']['5'] == 1
    assert score['mrr10'] == 1
    assert not score['full']['3'] and score['full']['5']


def test_g0_new_queries_stay_in_identical_coverage_denominator(protocol_fixture):
    repo, dataset, _, _ = protocol_fixture
    chunks = build_chunks(repo, evaluation.MANIFESTS['G0'])
    retriever = RagRetriever(chunks, corpus_name='G0')
    cases = [q for q in dataset['questions'] if q['split'] == 'test']
    records = evaluation.evaluate_questions(retriever, cases, evaluation.evidence_map(dataset))
    summary = evaluation.metrics_for(records, 'G0')
    assert summary['delivered']['answerable_n'] == 30
    assert summary['delivered']['negative_n'] == 10
    assert summary['old_questions']['delivered']['answerable_n'] == 20
    assert summary['new_questions']['delivered']['answerable_n'] == 10
    assert {r['failure_class'] for r in records if r['scope'] == 'new'} == {'knowledge_missing'}


def test_threshold_search_rejects_heldout_labels(protocol_fixture):
    repo, dataset, _, _ = protocol_fixture
    retriever = RagRetriever(build_chunks(repo, evaluation.MANIFESTS['G0']), corpus_name='G0')
    with pytest.raises(ValueError, match='development'):
        evaluation.select_thresholds(retriever, dataset['questions'][40:], evaluation.evidence_map(dataset))


def test_freeze_rejects_source_and_index_corruption(protocol_fixture, monkeypatch, tmp_path):
    repo, _, model, review = protocol_fixture
    monkeypatch.setattr(evaluation, 'LocalEncoder', FixtureEncoder)
    run = tmp_path / 'run'
    evaluation.prepare_run(repo, run, review_file=review, model_path=model)
    assert evaluation.verify_freeze(repo, run)['model_revision']
    with pytest.raises(ValueError, match='cannot be prepared'):
        evaluation.prepare_run(repo, run, review_file=review, model_path=model)
    vectors = next((run / 'indexes').rglob('vectors.npy'))
    original = vectors.read_bytes()
    vectors.write_bytes(b'corrupt')
    with pytest.raises(ValueError, match='artifact'):
        evaluation.verify_freeze(repo, run)
    vectors.write_bytes(original)
    (repo / 'knowledge/new.md').write_text('modified', encoding='utf8')
    with pytest.raises(ValueError, match='Frozen source'):
        evaluation.verify_freeze(repo, run)


def test_missing_model_and_corrupt_index_are_unavailable(protocol_fixture, tmp_path):
    repo, _, model, _ = protocol_fixture
    chunks = build_chunks(repo, evaluation.MANIFESTS['G0'])
    encoder = FixtureEncoder(model)
    with pytest.raises(RagUnavailable, match='尚未准备'):
        RagRetriever(chunks, 'embedding', encoder=encoder, cache_root=tmp_path / 'index')
    built = RagRetriever(chunks, 'embedding', encoder=encoder, cache_root=tmp_path / 'index', build=True)
    index = next((tmp_path / 'index').rglob('index.json'))
    index.write_text('{}', encoding='utf8')
    with pytest.raises(RagUnavailable, match='损坏'):
        RagRetriever(chunks, 'embedding', encoder=encoder, cache_root=tmp_path / 'index')
    assert built.vectors.shape[0] == 14


def profile(r3=.8, mrr=.9, negative=.1, old_r3=.8, old_mrr=.9, new_r3=.8):
    def metric(recall, reciprocal):
        return {'recall': {'3': recall}, 'mrr10': reciprocal, 'no_answer_false_return': negative}
    return {'fixed': {'delivered': metric(r3, mrr),
                     'old_questions': {'delivered': metric(old_r3, old_mrr)},
                     'new_questions': {'delivered': metric(new_r3, mrr)},
                     'thresholds': evaluation.FIXED_THRESHOLDS},
            'tuned': {'delivered': metric(r3, mrr),
                     'old_questions': {'delivered': metric(old_r3, old_mrr)},
                     'new_questions': {'delivered': metric(new_r3, mrr)},
                     'thresholds': {'tfidf': .4, 'dense': .8}},
            'latency': {'cpu_warm_p95_ms': 100}}


def test_release_cannot_choose_heldout_runner_up_or_regress_old_questions():
    results = {corpus + '/' + mode: profile(r3=.7) for corpus in evaluation.CORPORA for mode in evaluation.MODES}
    results['G1/embedding'] = profile(r3=.74)  # Preselected candidate misses +5 pp.
    results['G1/hybrid'] = profile(r3=.95)  # Heldout winner must not be selected.
    selection = {'candidate': {'corpus': 'G1', 'mode': 'embedding'}}
    decision = evaluation.release_decision({'results': results}, selection)
    assert not decision['promotion_passed']
    assert decision['release_recommendation']['snapshot'] == 'G0'
    results['G1/embedding'] = profile(r3=.8, old_r3=.7)
    decision = evaluation.release_decision({'results': results}, selection)
    assert not decision['promotion_passed']
    assert not decision['release_guard_checks']['release_old_recall3_not_lower_than_current']
    results['G1/embedding'] = profile(r3=.8)
    assert evaluation.release_decision({'results': results}, selection)['promotion_passed']
    results['G1/embedding']['tuned']['new_questions']['delivered']['recall']['3'] = .7
    decision = evaluation.release_decision({'results': results}, selection)
    assert not decision['promotion_passed']
    assert not decision['release_guard_checks']['release_new_recall3_at_least_80pct']


def test_tfidf_corpus_promotion_still_requires_negative_and_latency_gates():
    results = {corpus + '/' + mode: profile() for corpus in evaluation.CORPORA for mode in evaluation.MODES}
    results['G1/tfidf'] = profile(negative=.2)
    decision = evaluation.release_decision({'results': results}, {'candidate': {'mode': 'tfidf'}})
    assert not decision['method_gate_passed']
    assert not decision['promotion_passed']


def test_multi_evidence_summary_excludes_single_evidence_questions():
    base = {'scope': 'existing', 'kind': 'existing', 'required_groups': ['a'],
        'raw': {'recall': {str(k): 1. for k in evaluation.KS}, 'mrr10': 1.,
                'full': {str(k): True for k in evaluation.KS}, 'false_return': None}}
    base['delivered'] = copy.deepcopy(base['raw'])
    multi = copy.deepcopy(base)
    multi['required_groups'] = ['a', 'b']
    multi['delivered']['full']['3'] = False
    summary = evaluation.metrics_for([base, multi], 'G1')
    assert summary['multi_evidence']['questions'] == 1
    assert summary['multi_evidence']['delivered_full_hit']['3'] == 0
    assert summary['delivered']['full_hit']['3'] == .5


def test_staged_run_locks_selection_and_never_overwrites_heldout(protocol_fixture, monkeypatch, tmp_path):
    repo, _, model, review = protocol_fixture
    monkeypatch.setattr(evaluation, 'LocalEncoder', FixtureEncoder)
    # Timing is independently tested with the real encoder by the experiment;
    # deterministic unit tests should not select a method using CPU scheduling.
    monkeypatch.setattr(evaluation, 'latency', lambda *a, **kw: {
        'cpu_warm_mean_ms': 1., 'cpu_warm_p95_ms': 2., 'cached_mean_ms': .1,
        'cached_p95_ms': .2, 'repetitions': 5, 'timed_queries': 200,
        'independent_questions': 40, 'includes_query_encoding': True,
        'excludes_model_load': True, 'device': 'cpu'})
    run = tmp_path / 'run'
    evaluation.prepare_run(repo, run, review_file=review, model_path=model)
    with pytest.raises(FileNotFoundError):
        evaluation.run_split(repo, run, 'test')
    dev = evaluation.run_split(repo, run, 'dev')
    assert len(dev['results']) == 6
    selection = json.loads((run / 'selection.json').read_text(encoding='utf8'))
    assert selection['selected_using'] == 'dev_only'
    heldout = evaluation.run_split(repo, run, 'test')
    assert len(heldout['results']) == 6
    before = file_hash(run / 'test.json')
    with pytest.raises(ValueError, match='overwritten'):
        evaluation.run_split(repo, run, 'test')
    assert file_hash(run / 'test.json') == before
    summary = evaluation.write_report(repo, run)
    assert summary['question_counts'] == {'dev': 40, 'test': 40, 'total': 80}
    assert summary['paid_api_requests'] == 0
    assert (run / 'failures.csv').exists() and (run / 'REPORT.md').exists()
    selection['candidate']['mode'] = 'hybrid'
    write_json(run / 'selection.json', selection)
    with pytest.raises(ValueError, match='selection changed'):
        evaluation.verify_freeze(repo, run, require_selection=True)
