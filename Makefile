PY ?= .venv/bin/python
LYRICS ?= $(HOME)/Documents/Gemini Spark/Lyrics

.PHONY: all setup ingest analyze export build db graph cand audit

all: analyze export build          ## 分词 → 导出 → 生成网页

setup:                             ## 创建虚拟环境并安装依赖
	python3 -m venv .venv && $(PY) -m pip install -r requirements.txt

ingest:                            ## 从本地歌词库导入新歌；FORCE=1 时覆盖仓库里改过的歌词
	$(PY) scripts/ingest.py "$(LYRICS)" $(if $(FORCE),--force)

analyze:
	$(PY) scripts/analyze.py

export:
	$(PY) scripts/export.py

build:
	$(PY) scripts/build.py

db:                                ## 生成 local/kotoba.sqlite
	$(PY) scripts/make_db.py

graph:                             ## 关系图演示的数据 web/demos/graph.json（需要 pip install networkx）
	$(PY) scripts/graph.py

cand:                              ## 某张专辑的候选词（附原句）：make cand ALBUM=tousaku
	$(PY) scripts/candidates.py $(ALBUM)

audit:                             ## 核对词条在某张专辑里命中的读音：make audit ALBUM=tousaku
	$(PY) scripts/candidates.py $(ALBUM) --audit
