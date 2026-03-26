.PHONY: skill deploy sync-skill

# 同步 core/ → skill/references/ + skill/assets/
sync-skill:
	cp core/SOUL.md skill/references/SOUL.md
	cp core/EXPLORER.md skill/references/EXPLORER.md
	cp core/sources.yaml skill/references/sources.yaml
	cp core/postcard-format.md skill/references/postcard-format.md
	cp core/templates/state.json skill/assets/state.json
	cp core/templates/interest-graph.json skill/assets/interest-graph.json
	@echo "✅ core/ → skill/ 同步完成"

# 打包 Skill 版
skill: sync-skill
	@echo "打包 wanderclaw skill..."
	@if command -v clawhub >/dev/null 2>&1; then \
		clawhub package skill/; \
	else \
		echo "⚠ clawhub CLI 未安装，请手动打包"; \
	fi

# 部署服务器版到远端
deploy:
	scp -r core/ server/ root@47.236.224.62:/root/wanderClaw/
	ssh root@47.236.224.62 "systemctl restart wanderclaw"
	@echo "✅ 服务器版部署完成"
