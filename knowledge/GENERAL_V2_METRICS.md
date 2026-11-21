# 图像质量与检测指标：何时可以计算

类型：官方指标文档与工程评测规则。适用版本：0.6.0 / general_rgb_v1；scikit-image文档0.20。核实日期：2026-10-23。

结论：PSNR与SSIM是全参考比较，需要空间对齐、形状对应的参考图。参考增强结果只是一种选定处理，不是唯一正确曝光；没有合格参考时应记not_run，不把原图自身或另一失真图冒充真值。

官方参数：对浮点图计算SSIM时应显式设置data_range；常用0到1浮点图的data_range为1，8位完整量程为255。彩色输入需声明channel_axis；形状、通道和数值范围不一致会使比较失去可比性。

结论：项目sharpness是归一化灰度的Laplacian方差；noise_estimate是局部平坦区高频残差的MAD估计。数值不是物理传感器噪声或SNR，边缘变强也可能来自噪声放大，不能据此单独宣布图像更准确。

工程评测：COCO AP对多个IoU阈值的排序结果汇总；固定阈值召回与误报/图是工作点指标。框匹配使用同类别、IoU0.5、分数降序的一对一匹配，重复框计误报，crowd按覆盖关系忽略；这些指标的分母不能互换。

适用条件与限制：比较校正前后检测需要同图、同标签、相同匹配与工作点；所有模拟副本与原图保持同组，参数只用开发或校准数据确定。PSNR/SSIM和启发式曝光指标均不能替代带标注检测对照。

来源与原文位置：scikit-image 0.20 metrics.peak_signal_noise_ratio与structural_similarity的Parameters、Notes：https://scikit-image.org/docs/0.20.x/api/skimage.metrics.html ；项目quality.py::_tile_metrics、optical_agent/general_eval.py、docs/GENERAL_EVALUATION.md“曝光与局部可辨性描述统计”。
