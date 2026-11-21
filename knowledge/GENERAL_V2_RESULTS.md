# 0.6.0 冻结视觉基准：实测结果与分母

类型：项目实测。适用版本：0.6.0 / general_rgb_v1 官方 COCO 检测分支；本卡只复述冻结实验，不测量当前图片。核实日期：2026-10-23。

结论：COCO val2017 共5,000张，按固定种子20261023分成3,000张开发、1,000张校准和1,000张保留测试；测试有7,448个非crowd实例。该公开验证集的项目重新分组，不证明模型从未见过数据，也不能保证拍摄场景独立。

结论：冻结测试 COCO AP@[.50:.95] 为24.12%，AP50为39.46%。AP使用官方COCOeval、原始预测分数下限0.05；它与固定工作阈值的召回、精度含义不同，不能当作当前每个目标框的正确概率。

结论：固定0.35阈值时测试微召回36.36%、误报1.525个/图；冻结逐类工作点为33.55%、1.086个/图。阈值取舍减少误报同时降低召回，不是所有指标同时提升。

适用条件与限制：RTX3060 Laptop本地实验单图平均110.29ms、P95为132.98ms，包含读图、质量测量和推理，到缓存写入前停止计时；不是云端LLM端到端延迟或实时保证。测试冻结后没有根据这些成绩重新调整阈值。

结论：SICE作者Drive入口返回配额超限页面，百度入口需要浏览器或账号；真实多曝光及参考PSNR/SSIM状态为not_run，未运行。不能用COCO数字亮度扰动替代真实多曝光实验。

来源与原文位置：docs/GENERAL_EVALUATION.md 的“数据与测试范围”“保留测试结果”“SICE 未运行”；docs/results/general_v060_summary.json；D盘冻结原件 public_summary.json、test_summary.json、freeze.json。公开报告：https://github.com/sadbrand11-blip/underwater-vision-agent/blob/main/docs/GENERAL_EVALUATION.md
