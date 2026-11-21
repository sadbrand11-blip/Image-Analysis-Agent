"""Versioned natural-image knowledge and an auditable local release profile.

The old constructor deliberately keeps its v1 defaults. Application factories
read the release file, so an experiment cannot silently replace a live corpus.
"""
import json
import math
from pathlib import Path

from optical_agent.rag_engine import RagRetriever, RagUnavailable, build_chunks, fingerprint

CORPUS_VERSION = 'general-natural-v1'
GENERAL_RAG_ROOT = Path(r'D:\CodexData\optical_agent\rag\general_rgb_v1')
CORPUS_MANIFESTS = {
    'general-natural-v1': 'knowledge/GENERAL_SOURCES.json',
    'general-natural-v2': 'knowledge/GENERAL_V2_SOURCES.json',
}
RELEASE_PATH = 'knowledge/general_rag_release.json'


def _legacy_config(root):
    return {'profile_id': 'general_rgb_v1', 'corpus': CORPUS_VERSION,
            'mode': 'tfidf', 'thresholds': {'tfidf': .10, 'dense': .75},
            'acceptance_status': 'not_formally_evaluated',
            'evaluation_status': 'not_run',
            'corpus_hash': fingerprint(build_chunks(root, CORPUS_MANIFESTS[CORPUS_VERSION]))}


def _checked_thresholds(value):
    if not isinstance(value, dict) or set(value) != {'tfidf', 'dense'}:
        raise RagUnavailable('检索阈值必须明确包含tfidf和dense')
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or
           not math.isfinite(v) or not 0 <= v <= 1.1 for v in value.values()):
        raise RagUnavailable('检索阈值无效，拒绝使用损坏的发布配置')
    return dict(value)


def general_release_config(root=None):
    root = Path(root or Path(__file__).resolve().parents[1])
    path = root / RELEASE_PATH
    if not path.exists():
        config = _legacy_config(root)
    else:
        try:
            config = json.loads(path.read_text(encoding='utf8'))
            if (config['profile_id'] != 'general_rgb_v1' or
                    config['corpus'] not in CORPUS_MANIFESTS or
                    config['mode'] not in {'tfidf', 'embedding', 'hybrid'}):
                raise ValueError('Unsupported profile/corpus/mode')
            _checked_thresholds(config['thresholds'])
            if any(not isinstance(config.get(key), str) or not config[key].strip()
                   for key in ('acceptance_status', 'evaluation_status')):
                raise ValueError('Missing evaluation or acceptance status')
            if not isinstance(config.get('mode_thresholds', {}), dict):
                raise ValueError('mode_thresholds must be an object')
            if not isinstance(config.get('evaluated_corpora', {}), dict):
                raise ValueError('evaluated_corpora must be an object')
            if any(key not in CORPUS_MANIFESTS or not isinstance(value, dict)
                   for key, value in config.get('evaluated_corpora', {}).items()):
                raise ValueError('Invalid evaluated corpus profile')
            for mode, thresholds in config.get('mode_thresholds', {}).items():
                if mode not in {'tfidf', 'embedding', 'hybrid'}:
                    raise ValueError('Unsupported mode thresholds')
                _checked_thresholds(thresholds)
            chunks = build_chunks(root, CORPUS_MANIFESTS[config['corpus']])
            if fingerprint(chunks) != config['corpus_hash']:
                raise ValueError('Published corpus fingerprint changed')
        except (KeyError, ValueError, OSError, TypeError) as exc:
            raise RagUnavailable('通用RAG发布配置或知识版本损坏，需重新发布：' + str(exc)) from exc
    return dict(config, release_config_hash=fingerprint(config))


class GeneralKnowledgeRetriever(RagRetriever):
    """KnowledgeRetriever.search-compatible local retrieval with explicit versions."""
    def __init__(self, root=None, chunk_size=400, overlap=80, min_score=.10, *,
                 mode='tfidf', encoder=None, build=False, cache_root=None,
                 corpus_version=CORPUS_VERSION, thresholds=None, release_profile=None):
        if chunk_size != 400 or overlap != 80:
            raise ValueError('通用语料使用固定400字符、最多80重叠分段；修改须建立新版本')
        root = Path(root or Path(__file__).resolve().parents[1])
        if corpus_version not in CORPUS_MANIFESTS:
            raise ValueError('未知通用知识版本')
        chunks = build_chunks(root, CORPUS_MANIFESTS[corpus_version])
        if any(c.get('vision_modes') != ['general_rgb_v1'] for c in chunks):
            raise ValueError('通用知识清单含非通用资料，拒绝混用历史水下证据')
        super().__init__(chunks, mode, encoder=encoder, build=build,
                         cache_root=cache_root or GENERAL_RAG_ROOT / 'indexes',
                         thresholds=_checked_thresholds(thresholds or {'tfidf': min_score, 'dense': .75}),
                         vision_mode=None, corpus_name=corpus_version)
        self.root, self.vision_mode = root, 'general_rgb_v1'
        self.corpus_version = corpus_version
        # Snapshot rather than reread a mutable file while a session is running.
        config = release_profile or dict(_legacy_config(root), corpus=corpus_version,
                                        corpus_hash=self.corpus_hash)
        self.release_config = json.loads(json.dumps(config))
        self.release_config.setdefault('release_config_hash', fingerprint(config))
        if self.release_config['corpus_hash'] != self.corpus_hash:
            raise RagUnavailable('通用知识在创建过程中发生变化，请重新创建会话')
        expected_assets = self.release_config.get('model_asset_hash')
        if self.encoder is not None and expected_assets and self.encoder.asset_hash != expected_assets:
            raise RagUnavailable('本地Embedding模型与已评测版本不一致，请恢复冻结模型或重新评测')

    def metadata(self):
        return dict(super().metadata(), profile_id='general_rgb_v1',
                    corpus_version=self.corpus_version, frozen_historical_scores_applicable=False,
                    acceptance_status=self.release_config['acceptance_status'],
                    evaluation_status=self.release_config.get('evaluation_status', 'not_run'),
                    evaluation=self.release_config.get('evaluation'),
                    release_notice=self.release_config.get('release_notice'), fallback_reason=None,
                    release_config_hash=self.release_config['release_config_hash'])


def create_general_retriever(root=None, mode=None, vision_mode='general_rgb_v1', *,
                             encoder=None, allow_fallback=False, build=False, cache_root=None,
                             corpus_version=None):
    if vision_mode != 'general_rgb_v1':
        raise ValueError('通用知识只适用于general_rgb_v1，旧水下资料请使用归档检索器')
    # An explicit legacy selection retains sparse behavior but does not import C0.
    config = general_release_config(root)
    if corpus_version is not None:
        if corpus_version not in CORPUS_MANIFESTS:
            raise ValueError('未知通用知识版本')
        experimental = config.get('evaluated_corpora', {}).get(corpus_version, {})
        config = dict(config)
        config.update(experimental)
        config.update(corpus=corpus_version, mode='tfidf',
            acceptance_status='experimental_explicit_selection',
            corpus_hash=fingerprint(build_chunks(Path(root or Path(__file__).resolve().parents[1]),
                                                CORPUS_MANIFESTS[corpus_version])),
            release_notice='手动语料对照；不表示该配置已经通过发布门槛')
        config.pop('release_config_hash', None)
        config['release_config_hash'] = fingerprint(config)
    selected = config['mode'] if mode is None else 'tfidf' if mode == 'legacy' else mode
    if selected not in {'tfidf', 'embedding', 'hybrid'}:
        raise ValueError('rag_mode须为legacy、tfidf、embedding或hybrid')
    try:
        retriever = GeneralKnowledgeRetriever(root, mode=selected, encoder=encoder,
            build=build, cache_root=cache_root, corpus_version=config['corpus'],
            thresholds=config.get('mode_thresholds', {}).get(selected, config['thresholds']),
            release_profile=config)
    except (RagUnavailable, ImportError) as exc:
        if not allow_fallback or mode is not None:
            raise RagUnavailable('通用Embedding/Hybrid不可用；需为当前独立语料准备本地模型和索引：' + str(exc)) from exc
        retriever = GeneralKnowledgeRetriever(root, corpus_version=config['corpus'],
            thresholds=config.get('mode_thresholds', {}).get('tfidf', {'tfidf': .1, 'dense': .75}),
            release_profile=config)
        original, reason = retriever.metadata, str(exc)
        retriever.metadata = lambda original=original, reason=reason: dict(original(), requested_mode=selected, fallback_reason=reason,
            release_acceptance_status=config['acceptance_status'],
            acceptance_status='degraded_not_equivalent_to_release')
    if mode is not None and selected != config['mode'] and corpus_version is None:
        original = retriever.metadata
        retriever.metadata = lambda original=original: dict(original(), requested_mode=mode,
            release_acceptance_status=config['acceptance_status'],
            acceptance_status='experimental_explicit_mode')
    if mode == 'legacy':
        original = retriever.metadata
        retriever.metadata = lambda original=original: dict(original(), requested_mode='legacy',
            mode_alias_notice='通用配置的legacy选项使用独立TF-IDF资料；未加载旧C0语料')
    return retriever
