# Gamma 与 CLAHE：公式、实现与使用边界

类型：官方算法文档与项目工程实现，分别注明；不是学习型纹理恢复模型。适用版本：0.6.0 / general_rgb_v1，scikit-image文档0.20与OpenCV文档3.4.14。核实日期：2026-10-23。

官方算法：Gamma对归一化像素执行 O=I**gamma；gamma小于1使中间亮度变亮，大于1使其变暗。相同符号在其他库中可能采用倒数定义，因此以具体实现公式为准。0和1端点仍在原端点，不能据此恢复被截断的真实细节。

项目实现：从原图中位灰度估计Gamma，目标中位数0.45，Gamma限制在0.65—1.45；gamma_only只使用查找表亮度映射。不是把相机曝光时间变为某个值，也不保证所有局部区域同时改善。

官方算法：CLAHE分小块做局部直方图均衡，用直方图裁剪限制对比度放大，并对块边界做插值；它可能放大噪声。CLAHE名称中的Contrast Limited不等于绝不引入伪影，均衡后的观感也不是检测正确率。

项目实现：local_bounded先Gamma，再对Lab的L通道执行clipLimit=1.6、tileGridSize=(8,8)的CLAHE，最多混合25%；欠曝或混合光照且噪声估计至少0.01时才触发条件降噪。不能把本项目Lab实现与scikit-image默认HSV流程混为同一处理。

适用条件与限制：原图质量失败时不恢复，曝光正常或二值图时如实返回未调整；每种候选直接从原图生成一次。原图始终保留，是否采用候选需实际比较，不以框数增加作决定。

来源与原文位置：quality.py::correct_exposure；scikit-image 0.20 exposure.adjust_gamma的公式和Notes：https://scikit-image.org/docs/0.20.x/api/skimage.exposure.html#skimage.exposure.adjust_gamma ；OpenCV 3.4.14“CLAHE”段：https://docs.opencv.org/3.4.14/d2/d74/tutorial_js_histogram_equalization.html 。OpenCV文档站本次403，已核对同版本官方GitHub源文件，原始响应与替代源均留存D盘。
