# Lemmatization & Contraction Expansion Design

**Date:** 2026-05-31  
**Status:** Approved  
**Goal:** 使系统能识别单词的变形形式（复数、-ing、过去式等）和缩写词（we're, don't），避免将已认识词族的其他形式误判为生词。

## Background

当前系统问题：
1. **无词形还原**：`run`、`runs`、`running`、`ran` 是4条独立词汇记录。用户将 `run` 标记为已知后，`running` 仍显示为生词。
2. **无缩写处理**：`we're`、`don't`、`can't` 等缩写被整体识别为单个生词。即使 `we` 和 `are` 都已知，`we're` 仍是生词。
3. **`lemma` 列闲置**：数据库 Word 表有 `lemma` 列但从未被代码写入。

## Design Decisions

| 决策 | 选择 |
|------|------|
| Lemmatization 范围 | 完整词形还原（规则+不规则），NLTK WordNetLemmatizer |
| Contraction 处理 | 分词前展开：we're → we are |
| Word 存储模型 | 词族共享同一条 Word 记录（word_lower = lemma） |
| NLP 依赖 | NLTK + wordnet 数据 |

## Architecture

### Pipeline 改动

```
原文 ─→ [缩写展开] ─→ [分词] ─→ [词形还原] ─→ [词汇查找] ─→ [ArticleWord入库]
```

### 新增模块

#### 1. `backend/app/services/contractions.py` — 缩写展开

- 维护 ~100 条英语缩写映射表（标准否定、人称+be/have/will、特殊形式）
- `expand(text: str) -> str`：对输入文本做正则替换
- 大小写感知：`We're` → `We are`，`DON'T` → `DO NOT`

#### 2. `backend/app/services/lemmatizer.py` — 词形还原

- 包装 NLTK WordNetLemmatizer
- `lemmatize(word: str) -> str`：启发式 POS 判断（动词→名词→形容词）
- 首次调用自动 `nltk.download('wordnet')`，带超时和重试
- 未知词返回原词（NLTK 默认行为）

### 修改模块

#### 3. `backend/app/services/tokenizer.py`

- `tokenize(text)` 内部先调用 `expand_contractions(text)` 再分词

#### 4. `backend/app/services/vocabulary.py`

- `get_or_create_word(db, word_text)` 改为：
  1. `lemma = lemmatize(word_text.lower())`
  2. 按 `word_lower == lemma` 查找/创建 Word 记录
  3. Word 表存储 lemma 形式（如 `word_lower="run"`）
  4. ArticleWord 仍存储原始表面形式（如 `word_text="running"`）

#### 5. `backend/app/services/article.py`

- 适配新的 `get_or_create_word` 语义，确保 ArticleWord.word_text 存原文

#### 6. `backend/app/importers/epub_importer.py`

- `_html_to_clean_html()` 对文本节点做缩写展开
- `inject_word_spans()` 无需改动（span_tokens 已是展开后分词结果）

#### 7. `backend/app/analysis/unknown_word.py`

- `UnknownWordAnalyzer` 改用 lemma 判断：
  1. 加载已知词集合时，对已知词做 lemmatize
  2. 判断 ArticleWord 是否生词时，对比 word_lower 的 lemma 而非 word_lower 本身

### 数据库迁移

- **新增迁移**：清理现有 Word 表冗余记录
  1. 扫描所有 Word，计算每个 `word` 的 lemma
  2. 同一 lemma 的多条记录合并为一条（保留 encounter_count 之和，保留最常用表面形式）
  3. ArticleWord 的 `word_id` 更新为合并后的记录 ID
  4. 删除冗余 Word 记录
  5. 可选：为 `word_lower` 列添加索引（已有 UNIQUE 约束）

## Data Flow Example

```
输入: "We're running quickly to the stores."

[缩写展开]
  "We're" → "We are"
  输出: "We are running quickly to the stores."

[分词]
  Token("We",1), Token("are",2), Token("running",3), Token("quickly",4),
  Token("to",5), Token("the",6), Token("stores",7), Token(".",8)

[词形还原 + 词汇查找]
  "we"      → lemma="we"      → Word("we")      ✓ known
  "are"     → lemma="be"      → Word("be")      ✓ known
  "running" → lemma="run"     → Word("run")     ✓ known
  "quickly" → lemma="quickly" → Word("quickly")  ✗ unknown
  "to"      → lemma="to"      → Word("to")      ✓ known
  "the"     → lemma="the"     → Word("the")     ✓ known
  "stores"  → lemma="store"   → Word("store")   ✓ known

[结果] 7个词中1个生词 (quickly)
```

## Lemmatization Algorithm

```python
def lemmatize(word: str) -> str:
    wl = word.lower().strip()
    # 1. 先尝试动词（覆盖 -ing, -ed, 不规则过去式）
    verb_lemma = lemmatizer.lemmatize(wl, pos="v")
    if verb_lemma != wl:
        return verb_lemma  # running→run, went→go, ran→run
    # 2. 再尝试名词（覆盖复数、不规则复数）
    noun_lemma = lemmatizer.lemmatize(wl, pos="n")
    if noun_lemma != wl:
        return noun_lemma  # stores→store, feet→foot
    # 3. 尝试形容词/副词（覆盖比较级）
    adj_lemma = lemmatizer.lemmatize(wl, pos="a")
    return adj_lemma  # better→good, quicker→quick
```

## Contraction Mapping (excerpt)

```python
CONTRACTIONS = {
    "don't": "do not",    "doesn't": "does not",   "can't": "cannot",
    "won't": "will not",  "isn't": "is not",       "aren't": "are not",
    "wasn't": "was not",  "weren't": "were not",   "haven't": "have not",
    "I'm": "I am",        "we're": "we are",       "you're": "you are",
    "they're": "they are","he's": "he is",         "she's": "she is",
    "it's": "it is",      "I've": "I have",        "I'll": "I will",
    "let's": "let us",    "ain't": "is not",
}
```

## Error Handling

- **NLTK 未安装**：启动时 import 检测，给出 `pip install nltk` 提示
- **wordnet 未下载**：首次调用 lemmatize() 自动下载，10s 超时，失败则降级返回原词
- **未知词**：lemmatizer 返回原词，不影响系统运行
- **数据迁移**：分步执行，先 dry-run 统计影响行数，确认后再执行

## Affected Files

| 文件 | 改动类型 | 说明 |
|------|----------|------|
| `backend/app/services/contractions.py` | **新增** | 缩写展开模块 |
| `backend/app/services/lemmatizer.py` | **新增** | 词形还原模块 |
| `backend/app/services/tokenizer.py` | 修改 | tokenize() 前调用缩写展开 |
| `backend/app/services/vocabulary.py` | 修改 | get_or_create_word() 先做词形还原 |
| `backend/app/services/article.py` | 修改 | 适配新语义 |
| `backend/app/importers/epub_importer.py` | 修改 | clean HTML 文本节点缩写展开 |
| `backend/app/analysis/unknown_word.py` | 修改 | 用 lemma 判断生词 |
| `backend/migrations/versions/009_merge_lemma_words.py` | **新增** | 数据清理迁移 |
| `backend/requirements.txt` | 修改 | 添加 nltk 依赖 |
| `frontend/` | 无需改动 | 前端通过 word_id 查状态，不受影响 |

## Out of Scope

- 同形异义词消歧（如 "saw" 名词/动词）— NLTK 默认用最高频义项
- 短语动词识别（如 "give up"）— 仍按单词独立处理
- 上下文感知的缩写展开（如 "it's" 可能是 "it is" 或 "it has"）— 统一展开为最常见形式

## Risks

1. **缩写展开改变原文**：读者看到 "we are" 而非 "we're"。学习场景下展开形式更清晰，且不影响原始 EPUB 文件（仅影响导入后的副本）。
2. **词形还原准确率**：NLTK 对常见英语词准确率 >95%，但同形异义词有歧义。对学习场景影响可控。
3. **数据迁移复杂度**：合并 Word 记录时需处理 encounter_count、notes 等字段。迁移脚本需充分测试。
4. **向后兼容**：现有 ArticleWord 记录不变，仅新导入的文章受新逻辑影响。旧文章需重新分析以更新 `is_unknown_at_import`。
