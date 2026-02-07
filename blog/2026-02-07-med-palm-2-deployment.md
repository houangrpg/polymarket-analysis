---
title: "🏥 智慧醫療：Med-PaLM 2 與開源模型部署建議"
date: 2026-02-07
category: 智慧醫療
---
#### Med-PaLM 2：醫療 AI 的專家級標竿
Med-PaLM 2 是第一個在 USMLE 考試達到 86.5% 專家級水平的模型，具備強大的影像分析與臨床推理能力。但因隱私考量，目前僅透過 Google Cloud Vertex AI 有條件開放。

#### Mac mini M4 (24G) 部署建議
您的主機非常適合跑 **OpenBioLLM-Llama3-8B**。24GB 記憶體可提供 16GB+ 分配給 GPU，實現極速推論。建議使用 Ollama 執行，並以此建立「本地端 100% 隱私」的醫療 AI 伺服器。

#### HIS 整合思路
重點在於「非侵入式整合」，利用 FHIR 標準化 API，讓 AI 作為外掛輔助醫護產出摘要與預警。
