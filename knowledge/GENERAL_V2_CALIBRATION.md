# 校准、候选分数与可靠性限制

类型：项目实测与工程规则，分别以“实测”和“规则”标记。适用版本：0.6.0 / general_rgb_v1；只适用于绑定版本的COCO原图校准。核实日期：2026-10-23。

规则：校准只使用1,000张校准原图；每类至少30个GT、10张正样本图、30个预测，且至少两个有效分数桶。在经验精度不低于80%的约束下选最大召回的阈值；条件不足时标为insufficient并回退0.35。

实测：80类中22类满足校准集工程条件，58类不足。这不是22类通过保留测试精度验收；测试中这22类合计精度81.05%，仍有10/22类单类精度低于80%。不能宣称每个类别都达到80%精度。

规则：经验分数桶记录的是该样本的TP比例，不是逐框正确概率；校准文件绑定模型SHA、预处理版本、类别版本和数据清单SHA。原图校准范围为coco_originals，不自动适用于校正图、换模型或新拍摄分布。

适用条件与限制：图像质量检查、同图处理后的检测稳定性、校准适用范围必须分别检查；没有适用校准依据的框保持候选状态。历史成绩只能帮助理解限制，不能提高当前框的置信度或代替当前工具证据。

来源与原文位置：docs/GENERAL_EVALUATION.md“校准与校正限制”；docs/GENERAL_DATA.md“评测顺序”；optical_agent/general_eval.py 的 calibrate_class_thresholds；optical_agent/general_vision.py 的校准身份检查。公开报告：https://github.com/sadbrand11-blip/underwater-vision-agent/blob/main/docs/GENERAL_EVALUATION.md
