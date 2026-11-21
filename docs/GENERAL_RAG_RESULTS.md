# 通用图像 RAG 独立对照报告

80 条问题：开发集与保留集各 40 条；同事实按组隔离。标签经同模型家族独立代理暂定审核，未经外部人工验收。

G0/G1 主分母统一为 30 条可回答问题，另有 10 条无答案问题。另报旧知识 20 题和新知识 10 题；G0 的新题仍计入覆盖分母，失败原因标为知识缺失。

下表均为保留集。固定阈值对照隔离知识补充，调优阈值仅由开发集选择。排名分数不是正确概率。

CPU列两表共用各方法开发集调优后配置的计时；固定阈值未另行计时，不表示两种阈值耗时相同。

## 固定阈值（TF-IDF 0.10，Embedding 0.75）

|语料 / 方法|交付 R@1 / 3 / 5 / 10|原始 R@3|交付 MRR@10|多证据完整命中@3|无答案误返回|调优配置CPU P95 ms|
|---|---|---:|---:|---:|---:|---:|
|G0/tfidf|60.0% / 60.0% / 60.0% / 60.0%|63.3%|0.600|20.0%|0.0%|0.8|
|G0/embedding|3.3% / 3.3% / 3.3% / 3.3%|56.7%|0.033|10.0%|0.0%|31.4|
|G0/hybrid|53.3% / 60.0% / 60.0% / 60.0%|60.0%|0.567|20.0%|0.0%|34.3|
|G1/tfidf|71.7% / 80.0% / 80.0% / 80.0%|88.3%|0.850|60.0%|10.0%|0.9|
|G1/embedding|6.7% / 6.7% / 6.7% / 6.7%|70.0%|0.067|20.0%|0.0%|34.1|
|G1/hybrid|65.0% / 80.0% / 80.0% / 80.0%|88.3%|0.800|60.0%|10.0%|35.3|

## 开发集选定阈值

|语料 / 方法|交付 R@1 / 3 / 5 / 10|原始 R@3|交付 MRR@10|多证据完整命中@3|无答案误返回|调优配置CPU P95 ms|
|---|---|---:|---:|---:|---:|---:|
|G0/tfidf|60.0% / 60.0% / 60.0% / 60.0%|63.3%|0.600|20.0%|0.0%|0.8|
|G0/embedding|26.7% / 26.7% / 26.7% / 26.7%|56.7%|0.267|20.0%|0.0%|31.4|
|G0/hybrid|53.3% / 60.0% / 60.0% / 60.0%|60.0%|0.567|20.0%|0.0%|34.3|
|G1/tfidf|71.7% / 80.0% / 80.0% / 80.0%|88.3%|0.850|60.0%|10.0%|0.9|
|G1/embedding|23.3% / 25.0% / 26.7% / 26.7%|70.0%|0.300|50.0%|0.0%|34.1|
|G1/hybrid|53.3% / 60.0% / 60.0% / 60.0%|88.3%|0.617|60.0%|0.0%|35.3|

## 发布决定

开发集预先选择：G1/hybrid。保留集门槛：未通过，保留当前默认值。

```json
{
  "protocol_version": "general-rag-v1",
  "selected_using": "dev_only",
  "candidate": {
    "corpus": "G1",
    "mode": "hybrid"
  },
  "promotion_passed": false,
  "method_checks": {
    "recall3_gain_at_least_5pp": false,
    "mrr_not_lower": false,
    "no_answer_false_return_at_most_10pct": true,
    "cpu_hot_p95_at_most_500ms": true
  },
  "method_gate_passed": false,
  "method_replacement_required": true,
  "corpus_checks": {
    "old_fixed_recall3_not_lower": false,
    "old_fixed_mrr_not_lower": false,
    "new_fixed_recall3_at_least_80pct": true
  },
  "release_guard_checks": {
    "release_old_recall3_not_lower_than_current": false,
    "release_old_mrr_not_lower_than_current": false,
    "release_new_recall3_at_least_80pct": false
  },
  "release_recommendation": {
    "corpus": "general-natural-v1",
    "snapshot": "G0",
    "mode": "tfidf",
    "thresholds": {
      "tfidf": 0.1,
      "dense": 0.75
    }
  },
  "acceptance_status": "not_promoted_current_default_retained",
  "external_human_label_review": false,
  "label_review_status": "same_model_family_provisional",
  "limits": "Retrieval only; not real LLM answer quality, visual accuracy, or multi-agent performance."
}
```

## 解释与复现

- 同一事实在重叠片段中只记一次；多证据问题按证据组计算 Recall，MRR 取首条相关证据的倒数排名。
- 原始排名不设拒绝阈值；交付排名使用对应固定或开发集阈值。无答案问题不进入 Recall/MRR 分母。
- 热查询计时包含 CPU 查询编码，排除模型加载，每题重复五次；重复不增加独立样本数。缓存命中耗时另存 JSON。
- 原始逐题排名在 dev.json / test.json，错误表在 failures.csv；summary.json 包含按事实组配对置信区间、资源占用、索引时间与来源哈希。
- retrieval_off_target_ids 仅表示没有覆盖该题必要证据组的检索结果；本轮不生成答案，不评测生成式引用正确率。版本隔离由语料校验与回归测试保障，不以此宣称已测量语义版本错误率。
- TF-IDF、Embedding 与 Hybrid 的算法差异、G0/G1 的知识差异及阈值变化分别列示，不把旧水下 C0/C1 成绩用于通用语料。
- 评测全程本地，无付费 API；结果只说明小规模项目检索效果，不代表真实 LLM 回答质量、视觉精度或多 Agent 协作收益。

## 日常使用与审计轨迹

- [中文操作与实现](GENERAL_RAG.md) · [机器可读结果](GENERAL_RAG_RESULTS.json) · [逐题失败表](GENERAL_RAG_FAILURES.csv)
- 首次审题发现多余证据、漏标等价来源、重复算术计分及MPD表述问题；全部在首次检索前修复并独立复审。初始失败记录保留在D盘。
- 旧水下C0/C1和0.6.0视觉成绩未改写。本轮只比较检索，不调用付费API。

### 固定阈值下的知识收益（同20道旧题，另列10道新题）

|方法|G0旧题R@3 / MRR|G1旧题R@3 / MRR|G1新题R@3|
|---|---:|---:|---:|
|tfidf|90.0% / 0.900|80.0% / 0.775|80.0%|
|embedding|5.0% / 0.050|5.0% / 0.050|10.0%|
|hybrid|90.0% / 0.850|80.0% / 0.750|80.0%|

实际发布还要求调优配置的旧题不低于当前基线、新题R@3≥80%；固定阈值收益不能代替此检查。

### 本轮分析

新增知识扩展了新问题的覆盖，但没有同时保持旧问题表现。固定TF-IDF下，旧题R@3从90%降到80%；新增10题R@3为80%。因此，不能把总体覆盖提高直接当成无回归的默认升级。

|G1方法|未过滤R@3 / MRR@10|固定阈值R@3|开发阈值R@3|调优后的排序失败 / 阈值拒绝 / 无答案误返回题数|
|---|---:|---:|---:|---:|
|tfidf|88.3% / 0.900|80.0%|80.0%|5 / 3 / 1|
|embedding|70.0% / 0.758|6.7%|25.0%|11 / 13 / 0|
|hybrid|88.3% / 0.831|80.0%|60.0%|4 / 9 / 0|

开发阈值下Hybrid相对同G1的TF-IDF，R@3差值为-20.0个百分点，事实组配对95%区间为[-35.0, -5.0]个百分点。只对应本题集，不推断所有语料上的优劣。

Hybrid未过滤R@3仍为88.3%，但开发阈值后交付降为60%；保留集10道未知问题没有误返回。这个取舍提示后续需在开发数据上分开改进排序和拒绝机制；本轮保持冻结，不放宽阈值追测试成绩。

### 冻结身份

- 运行：`run_20261023`；题集SHA256：`e67a9107fcee405233f3fb53256436f56c66b913836e17c336c27f3edbe89f97`。
- BGE revision：`7999e1d3359715c523056ef9478215996d62a620`；CPU线程：2。
- 语料片段数：G0=14、G1=65；80道题来自40个事实组，保留集40道题来自20组，其中可回答15组。改写不是独立事实样本。
- 计时JSON的`independent_questions`仅计不同问题文本，以区别五次重复；统计独立单元按`fact_group`处理，不能据该字段把改写视为独立事实。
- [实验审计](GENERAL_RAG_AUDIT.md)为另一位同模型家族代理的暂定意见；不替代外部人工验收。
- 原始冻结哈希对应本地评测实现。公开版额外包装可选依赖缺失错误，因此不能声称两个仓库所有文件字节完全相同；检索语料与评测标签保持相同身份。
- 配对置信区间按事实组bootstrap，2000次，种子20261023；完整数值见机器可读结果，不能将点估计当成稳定泛化保证。
