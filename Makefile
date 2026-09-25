PY ?= .venv/bin/python
LYRICS ?= $(HOME)/Documents/Gemini Spark/Lyrics

.PHONY: all setup ingest analyze export build db

all: analyze export build          ## 分词 → 导出 → 生成网页

setup:                             ## 创建虚拟环境并安装依赖
	python3 -m venv .venv && $(PY) -m pip install -r requirements.txt

ingest:                            ## 从本地歌词库导入新歌
	$(PY) scripts/ingest.py "$(LYRICS)"

analyze:
	$(PY) scripts/analyze.py

export:
	$(PY) scripts/export.py

build:
	$(PY) scripts/build.py

db:                                ## 生成 local/kotoba.sqlite
	$(PY) scripts/make_db.py
