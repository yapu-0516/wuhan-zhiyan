# 本地卫星底图

前端默认先加载 Esri 在线卫星瓦片。在线服务失败或超时后，先使用
`wuhan-city-z13.jpg` 显示武汉中心城区概览，再叠加 `wuhan-satellite-z17.jpg`
显示汉口重点区高清影像。

城市 z17 全量缓存按当前范围估算超过 500 MB，因此不预置；离线只保留约 1.5 MB
的 z13 全城概览和约 5 MB 的汉口 z17 重点区精图。

重新生成：

```bash
python scripts/download_satellite_basemap.py --bbox 114.15,30.45,114.55,30.72 --zoom 13 \
  --out frontend/public/basemap/wuhan-city-z13.jpg
```

默认来源为 Esri World Imagery，署名见同目录对应的 `.json` 清单。
该缓存仅用于当前项目演示；公开部署或再分发前，请核对影像提供方的服务条款。
