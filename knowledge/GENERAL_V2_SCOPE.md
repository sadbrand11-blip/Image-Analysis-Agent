# 通用版本、类别与输入的适用范围

类型：官方类别资料与项目工程规则。适用版本：0.6.0 / general_rgb_v1，类别版本coco2017_80_official_ids_zh_v1。核实日期：2026-10-23。

结论：通用检测配置标识general_rgb_v1，官方模型为Faster R-CNN MobileNetV3-Large 320 FPN、COCO_V1完整预训练头；类别表版本coco2017_80_official_ids_zh_v1。模型、预处理或类别身份改变时，旧缓存与校准不能直接复用。

结论：80个有效目标类采用官方COCO原始ID；背景与N/A占位被排除，所以80类不意味着编号必须连续1到80。中文显示名和别名用于用户选择，同一过滤结果必须同时用于框图、数量与文字报告。

结论：日常通用输入仅验收8位JPEG、PNG；输入先处理EXIF方向、转换RGB并使用官方预处理。RAW、多光谱、医学影像以及专业水下模型不是该配置已验收的通用输入或能力，不能仅凭文件扩展名或相近类别替代其语义。

适用条件与限制：本项目MIT许可仅覆盖相应代码；COCO图像仍受各自原始许可和COCO使用条款约束，不能把数据当作MIT重新许可。历史水下模型与报告继续可追溯，但不作为当前通用性能证明。

来源与原文位置：optical_agent/general_vision.py、optical_agent/general_catalog.py、docs/GENERAL_DATA.md“下载与冻结”；Torchvision 0.17模型页的COCO_V1与categories：https://docs.pytorch.org/vision/0.17/models/generated/torchvision.models.detection.fasterrcnn_mobilenet_v3_large_320_fpn.html ；COCO官方使用条款：https://cocodataset.org/#termsofuse 。
