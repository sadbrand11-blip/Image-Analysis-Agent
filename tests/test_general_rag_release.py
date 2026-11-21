"""Release decisions are explicit, version pinned, and usable without Torch."""
import json
from pathlib import Path
import shutil
from unittest.mock import patch

import pytest

from optical_agent.general_knowledge import (
    GeneralKnowledgeRetriever, create_general_retriever, general_release_config,
)
from optical_agent.rag_engine import RagUnavailable, build_chunks, fingerprint


def corpus(tmp_path):
    source = Path(__file__).resolve().parents[1] / 'knowledge'
    target = tmp_path / 'knowledge'
    target.mkdir()
    for path in source.glob('GENERAL_*'):
        # Windows glob is case insensitive: do not copy the live release file.
        if path.name.startswith('GENERAL_'):
            shutil.copyfile(path, target / path.name)
    return tmp_path


def publish(root, **updates):
    config = general_release_config(root)
    config.pop('release_config_hash', None)
    config.update(evaluation_status='complete', acceptance_status='retained_baseline', **updates)
    (root / 'knowledge/general_rag_release.json').write_text(
        json.dumps(config, ensure_ascii=False), encoding='utf8')
    return config


def test_release_controls_factory_but_old_constructor_keeps_compatibility(tmp_path):
    root = corpus(tmp_path)
    publish(root, thresholds={'tfidf': 1.1, 'dense': .75})
    released = create_general_retriever(root)
    assert released.search('COCO') == []
    assert released.metadata()['evaluation_status'] == 'complete'
    assert released.metadata()['acceptance_status'] == 'retained_baseline'
    assert GeneralKnowledgeRetriever(root).search('COCO')


def test_release_snapshot_cannot_change_a_live_session(tmp_path):
    root = corpus(tmp_path)
    publish(root, thresholds={'tfidf': .01, 'dense': .75})
    old = create_general_retriever(root)
    before = old.metadata()
    publish(root, thresholds={'tfidf': 1.1, 'dense': .75})
    new = create_general_retriever(root)
    assert new.metadata()['release_config_hash'] != before['release_config_hash']
    assert old.metadata() == before
    assert old.search('COCO') and not new.search('COCO')


@pytest.mark.parametrize('changes', [
    {'corpus': '../archive'}, {'mode': 'cloud'}, {'profile_id': 'sodd'},
    {'corpus_hash': 'old-hash'}, {'thresholds': {'tfidf': float('nan'), 'dense': .75}},
    {'thresholds': {'tfidf': True, 'dense': .75}},
    {'mode_thresholds': None}, {'mode_thresholds': []}, {'evaluated_corpora': None},
])
def test_corrupt_or_cross_version_release_is_not_silent_empty_knowledge(tmp_path, changes):
    root = corpus(tmp_path)
    publish(root, **changes)
    with pytest.raises(RagUnavailable):
        create_general_retriever(root)


def test_default_dense_can_fallback_but_explicit_comparison_cannot(tmp_path):
    root = corpus(tmp_path)
    publish(root, mode='hybrid')
    with patch('optical_agent.rag_engine.LocalEncoder', side_effect=ImportError('fixture no torch')):
        result = create_general_retriever(root, allow_fallback=True)
        assert result.mode == 'tfidf'
        assert result.metadata()['fallback_reason'] == 'fixture no torch'
        assert result.metadata()['requested_mode'] == 'hybrid'
        assert result.metadata()['acceptance_status'] == 'degraded_not_equivalent_to_release'
        assert create_general_retriever(root, mode='legacy').metadata()['mode'] == 'tfidf'
        with pytest.raises(RagUnavailable):
            create_general_retriever(root, mode='hybrid', allow_fallback=True)


def test_v2_selection_keeps_old_chunks_and_marks_manual_experiment(tmp_path):
    root = corpus(tmp_path)
    manifest = root / 'knowledge/GENERAL_V2_SOURCES.json'
    if not manifest.exists():
        pytest.skip('V2 authoring not yet present')
    baseline = build_chunks(root, 'knowledge/GENERAL_SOURCES.json')
    full = build_chunks(root, 'knowledge/GENERAL_V2_SOURCES.json')
    assert full[:len(baseline)] == baseline
    publish(root)
    result = create_general_retriever(root, corpus_version='general-natural-v2')
    assert result.metadata()['corpus_hash'] == fingerprint(full)
    assert result.metadata()['acceptance_status'] == 'experimental_explicit_selection'
    assert result.metadata()['corpus_hash'] != create_general_retriever(root).corpus_hash


def test_knowledge_api_validates_explicit_corpus_without_upload_or_cloud():
    import app as web
    client = web.app.test_client()
    with patch('requests.sessions.Session.request', side_effect=AssertionError('No network')):
        response = client.post('/api/knowledge/search', json={
            'query': '为什么检测分数不是正确概率？', 'modes': ['tfidf'],
            'corpus_version': 'general-natural-v1'})
        assert response.status_code == 200
        meta = response.json['comparisons']['tfidf']['metadata']
        assert meta['corpus'] == 'general-natural-v1'
        assert meta['evaluation_status']
        assert response.json['paid_api_requests'] == 0
        assert client.post('/api/knowledge/search', json={
            'query': 'COCO', 'corpus_version': 'C1'}).status_code == 400


def test_knowledge_api_partial_results_when_optional_dependencies_are_missing():
    import app as web
    with patch.object(web, '_retriever', None), patch.object(web, '_rag_retrievers', {}), \
         patch.object(web, '_rag_encoder', None), \
         patch.object(web, 'LocalEncoder', side_effect=ImportError('fixture no torch')):
        response = web.app.test_client().post('/api/knowledge/search', json={'query': 'COCO模型'})
    assert response.status_code == 200
    results = response.json['comparisons']
    assert results['tfidf']['available']
    assert not results['embedding']['available'] and results['embedding']['results'] is None
    assert not results['hybrid']['available']


def test_manual_experiment_cache_changes_when_its_corpus_changes():
    import app as web
    from types import SimpleNamespace
    config = {'corpus_hash': 'released-g0', 'release_config_hash': 'fixed-release'}
    chunks = [{'citation_id': 'manual-v1', 'text': 'first'}]
    with patch.object(web, '_retriever', None), patch.object(web, '_rag_retrievers', {}), \
         patch.object(web, 'general_release_config', return_value=config), \
         patch.object(web, 'build_chunks', side_effect=lambda *args: list(chunks)), \
         patch.object(web, 'create_general_retriever', side_effect=lambda *args, **kw: SimpleNamespace(chunks=list(chunks))):
        old = web.get_retriever('tfidf', corpus_version='general-natural-v2')
        assert old is web.get_retriever('tfidf', corpus_version='general-natural-v2')
        chunks[:] = [{'citation_id': 'manual-v2', 'text': 'changed'}]
        updated = web.get_retriever('tfidf', corpus_version='general-natural-v2')
    assert updated is not old
    assert old.chunks[0]['text'] == 'first'


def test_release_change_during_construction_never_enters_old_cache_key():
    import app as web
    config = {'corpus_hash': 'fixed-corpus', 'release_config_hash': 'A'}
    def changed_factory(*args, **kwargs):
        config['release_config_hash'] = 'B'
        return object()
    cache = {}
    with patch.object(web, '_retriever', None), patch.object(web, '_rag_retrievers', cache), \
         patch.object(web, 'general_release_config', side_effect=lambda *args: dict(config)), \
         patch.object(web, 'create_general_retriever', side_effect=changed_factory):
        with pytest.raises(RagUnavailable, match='发生变化'):
            web.get_retriever('tfidf')
    assert cache == {}
