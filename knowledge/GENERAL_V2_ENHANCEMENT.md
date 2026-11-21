# 观感、检测偏好与校正收益

类型：论文研究与项目工程规则，分别注明。适用版本：0.6.0 / general_rgb_v1；论文年份2025。核实日期：2026-10-23。

研究结论：Li等CVPR2025《Image Quality Assessment: From Human to Machine Preference》以机器视觉下游任务刻画偏好，指出面向人类观感的IQA与机器任务偏好可能不一致。该结论支持单独检查检测收益，不意味着某个增强算法在本项目必然有效。

研究范围：论文建立MPD（Machine Preference Database），包含30k参考/失真图像对与2.25M细粒度标注。论文图1展示人类主观质量和机器任务结果不一致的例子；MPD是数据库与评测基准，不是某个未指明的质量模型；本项目已报告的是COCO视觉基准，不是MPD基准复现，论文数值不作为本项目检测成绩。

项目规则：校正方案必须用带标注开发数据比较召回和误报，不能只看图更亮、框更多或模型分数更高。开发门槛是平均宏召回增加大于0.005，且每种输入误报增量不超过0.05个/图；本轮两种校正都未过门槛，默认保留原图。

适用条件与限制：相同图的数字亮度乘法只模拟部分成像退化，没有模拟真实传感器曝光、运动、散粒噪声或镜头眩光。模拟结果应单列，不能解释为真实相机重拍效果，也不能从单帧增强观感推断不可见物体真实存在。

来源与原文位置：论文官方摘要及Figure 1，CVPR2025 pp.7570—7581：https://openaccess.thecvf.com/content/CVPR2025/html/Li_Image_Quality_Assessment_From_Human_to_Machine_Preference_CVPR_2025_paper.html ；本项目docs/GENERAL_DATA.md“评测顺序”、冻结exposure_policy.json。已核实官方摘要和既有官方PDF，未收录论文全文到公开知识卡。
