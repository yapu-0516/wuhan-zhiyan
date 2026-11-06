# 本地卫星底图

`wuhan-satellite-z17.jpg` 是汉口沿江示范区的卫星影像拼接缓存，用于演示现场断网加载。

重新生成：

```bash
python scripts/download_satellite_basemap.py
```

默认来源为 Esri World Imagery，署名见同目录的 `wuhan-satellite-z17.json`。
该缓存仅用于当前项目演示；公开部署或再分发前，请核对影像提供方的服务条款。
