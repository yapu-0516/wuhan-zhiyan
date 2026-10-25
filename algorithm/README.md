# cityeye_algo —— 城市智眼算法包

火灾 / 交通 / 建筑 / 内涝四类城市事件的**经典**图像与时序分析算法，仅依赖 `numpy` + `Pillow`
（连通域、形态学、Otsu 等算子均为纯 numpy 实现，无 OpenCV / scipy / 深度学习依赖）。
所有检测结论都由算法在输入数据上实际计算得出，并输出标注图或时序图作为证据。

| 类型 | 输入 | 算法 | 方法 |
| --- | --- | --- | --- |
| fire | 图片 | FlameNet-Lite | YCbCr（Celik 2009）+ RGB/HSV（Chen 2004）火焰色彩规则 → 形态学 → 连通域 → 焰心 / 纹理 / 形状校验；烟羽邻域分析 |
| traffic | CSV `time,speed[,flow]` | TrafficPulse | 相对速度 → TPI（0-10 五级）→ 持续拥堵时段 / 峰值 → 阻尼 Holt 短临预测 |
| traffic | 图片 | RoadOcc | 沥青路面掩膜 − 外部区域 → 局部背景差分 → 车辆连通域 → 占有率 → 等效 TPI |
| building | CSV `date,displacement_mm` | SettleWatch | Theil–Sen 稳健速率 + 二次拟合加速度 + 滚动 MAD 异常 → normal / watch / warning |
| building | 前后 2 张图片 | ChangeScope | 辐射归一化 → 灰度 + 梯度差分 → Otsu（噪声自适应下限）→ 变化区域 |
| flood | CSV `time,water_level_cm[,rainfall_mm]` | AquaLevel | 15 / 27 / 40 cm 分级 + 涨水速率 + 雨洪滞后互相关 + ARX 降雨-径流预测 |
| flood | 图片 | AquaSeg | 低纹理 × 水体色彩似然 → Otsu → 形态学 → 积水范围占比 |

## 使用

```python
import sys; sys.path.insert(0, "algorithm")
import cityeye_algo as ca

analyzer, result = ca.run("fire", ["data/samples/fire/drone_fire_01.jpg"], out_dir=Path("out"), prefix="T0001")
print(analyzer.meta.public(), result.detected, result.summary)
result.to_dict(url_for=lambda p: f"/files/results/{p.name}")   # → AnalysisTask.result 结构
```

`ca.validate(type, files)` 做输入校验（文件类型、数量、CSV 表头），不合法时抛出带中文说明的 `InputError`。

## 测试

```bash
python -m pytest algorithm/tests -q
```

测试同时覆盖程序化生成的输入（如：程序化火焰必须检出、亮橙色屋面 + 橙色车辆不得误报、
平稳沉降为 normal、加速沉降为 warning）与 `data/samples/` 中的合成示例数据。

算法原理、阈值依据与局限性详见 [`docs/algorithms.md`](../docs/algorithms.md)。
