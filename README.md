# ProjectQue - Python CLI 肇庆麻将 (LLM 对手实验版)

一个实验性质的命令行麻将小游戏：
- 1 名玩家 + 3 名 LLM 对手
- 规则覆盖：全自摸、碰杠不吃、白板鬼、无鬼加倍、买马、大胡、包赔
- 纯文本 CLI 显示，弃牌区采用“每家最近2张 + 历史合并行”

## 1. 环境要求

- Python 3.10+
- Windows PowerShell / CMD（当前仓库提供 `.bat` 启动脚本）
- OpenAI API Key（没有也能跑，AI 会自动 fallback 到规则引擎）

## 2. 初始化（一次）

推荐直接运行：

```bat
init_maque.bat
```

它会自动创建 `.venv` 并安装依赖。

手动方式：

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 3. 配置环境变量

复制 `.env.example` 并设置：

- `OPENAI_API_KEY`: 你的 OpenAI key
- `MAQUE_OPENAI_BASE_URL`: 可选，自定义 OpenAI 兼容接口地址（代理/网关）
- `MAQUE_MODEL`: 可选，默认 `gpt-4.1-mini`

PowerShell 示例：

```powershell
$env:OPENAI_API_KEY="sk-..."
$env:MAQUE_OPENAI_BASE_URL="https://your-proxy.example.com/v1"
$env:MAQUE_MODEL="gpt-4.1-mini"
```

## 4. 运行方式

### 4.1 一键启动（推荐）

```bat
start_maque.bat
```

或指定模型：

```bat
start_maque.bat gpt-4.1-mini
```

AI 自打模式（无人工输入，适合快速验证）：

```bat
start_maque.bat gpt-4.1-mini --ai-only
```

说明：`start_maque.bat` 只负责启动，不会重复安装依赖。若提示缺少环境，请先运行 `init_maque.bat`。

### 4.2 直接命令启动

```bash
python -m maque play --model gpt-4.1-mini --seed 42 --log-dir ./logs --interactive
```

如需临时指定自定义接口地址：

```bash
python -m maque play --model gpt-4.1-mini --base-url https://your-proxy.example.com/v1 --log-dir ./logs --interactive
```

不加 `--interactive` 时四家都由 AI 控制：

```bash
python -m maque play --model gpt-4.1-mini --seed 42 --log-dir ./logs
```

### 4.3 启动手机网页端

```bash
python -m maque web --host 0.0.0.0 --port 8000
```

浏览器打开：

```text
http://127.0.0.1:8000/
```

牌图目录规范（PNG）：

```text
assets/tiles/
  1T.png ... 9T.png
  1B.png ... 9B.png
  EW.png SW.png WW.png NW.png
  RD.png GD.png WB.png
  back.png
```

若素材缺失，网页会自动回退为中文牌名显示并在状态栏提示缺图数量。

## 5. 回放日志

```bash
python -m maque replay --log ./logs/game_YYYYMMDD_HHMMSS.jsonl
```

## 6. CLI 显示说明

主视图只显示：
- 你的手牌（上方中文牌名）
- 最近动作
- 弃牌区
  - `E/S/W/N` 每行仅显示最近 2 张
  - 更早弃牌进入 `History` 一行（不区分玩家）

## 7. 玩家操作

- 不再手打命令，改为方向键 + Enter 选择动作与出牌
- 牌型只使用索/筒/字牌（不含万）

## 8. 运行测试

```bash
python -m pytest -q
```

## 9. 目录结构

```text
maque/
  cli.py
  engine.py
  rules.py
  scoring.py
  state.py
  tiles.py
  agents/
  logging/
  render/
tests/
init_maque.bat
start_maque.bat
```

## 10. 说明

这是实验版，不保证所有地方都与线下牌馆判例完全一致。若你要继续扩展，可优先加：
- 更完整计分参数（底分、封顶、买马规则可配置）
- 更强的 AI 策略对照（规则引擎 / LLM / 混合）
- 更详细回放（Prompt / token / action latency）

