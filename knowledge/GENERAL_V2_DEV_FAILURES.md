# 开发诊断中的失败现象：不要用增强观感代替证据

类型：项目开发集实测。适用版本：0.6.0 / general_rgb_v1固定阈值0.35的开发诊断；不使用保留测试案例。核实日期：2026-10-23。

案例一：固定30张开发基图、313个非crowd目标，原图TP/FP/FN为98/61/215；Gamma后为98/62/215。召回未增加，误报多1个；这说明变亮或新增框不能自动证明改善。它是同一30张基图的配对结果，不是60张独立图。

案例二：同样30张开发图先乘亮度0.6，再做局部校正；未校正的TP/FP/FN为97/67/216，局部校正为96/58/217。误报减少同时漏报增加1个，展示召回与误报之间的取舍；数字变暗明确为模拟扰动。

案例三：开发图乘亮度1.4后，未校正TP/FP/FN为98/63/215，Gamma后为96/58/217；误报下降同时真阳性下降2个。不能只凭误报变少或图像观感改善宣称整体识别更好。

适用条件与限制：以上是冻结开发子集聚合案例，不是当前上传图片的定位结果；本卡不提供旧目标框或可代替新推理的图片编号。开发子集按固定哈希选30张，不能外推为任意普通照片的校正效果或真实曝光恢复。

来源与原文位置：D盘general_v060/development_summary.json的diagnostics中original:original、original:gamma_only、dark_06:original、dark_06:local_bounded、bright_14:original、bright_14:gamma_only；同文件diagnostic_images_per_split=30。摘要规则与来源说明：https://github.com/sadbrand11-blip/underwater-vision-agent/blob/main/docs/GENERAL_DATA.md 。原始摘要SHA和来源位置见D盘RAG authoring_manifest.json，不把个人路径或原始目标框写入公开卡。
