# Native Core

ValidKit は通常の Python 実装だけで動きます。追加で `validkit-py-core` を入れると、対応している `compile(...).validate(...)` の成功パスと一部の `collect_errors=True` が Rust/PyO3 のネイティブコアを使います。

```bash
pip install validkit-py validkit-py-core
```

```python
from validkit import compile, v

schema = compile({
    "user": {
        "id": v.int(),
        "profile": {
            "name": v.str().min(3),
            "tags": v.list(v.str().min(2)),
        },
    },
    "metrics": v.dict(str, v.list(v.int().range(0, 1000))),
})

data = {
    "user": {"id": 1, "profile": {"name": "Alice", "tags": ["py", "vk"]}},
    "metrics": {"daily": [1, 2, 3]},
}

validated = schema.validate(data)
```

## 使われる条件

ネイティブコアは起動時に一度だけ検出されます。見つからない場合は自動でPython実装に戻ります。

対応している主な形:

- `dict` スキーマ
- `v.str()`, `v.int()`, `v.float()`, `v.bool()`
- `v.list(...)`
- `v.dict(str, ...)`
- `min` / `max` / `range` の非排他的な数値境界
- 文字列長の `min` / `max`

Pythonへ戻る主な形:

- `partial`, `base`, `migrate`
- `.optional()`, `.default()`, `.coerce()`, `.custom()`, `.when()`, `.env()`, `.regex()`
- 排他的な数値境界
- リスト長制約
- tuple入力をlistへ変換する必要がある場合
- unknown keyを落として出力形状を変える必要がある場合

## 性能方針

ネイティブコアはオプションなので、入っている場合は性能を優先します。出力形状を変える必要がない成功ケースでは、検証済みの入力オブジェクトをそのまま返して余計なコピーを避けます。

```python
schema = compile({"tags": v.list(v.str())})
data = {"tags": ["fast", "path"]}

assert schema.validate(data) is data  # native core 使用時
```

Python経路のコピー互換が必要な検証では、強制的にPython経路を使えます。

```python
schema.validate(data, _force_python=True)
```

## 無効化

トラブルシュートやベンチ比較では環境変数で無効化できます。

```bash
VALIDKIT_DISABLE_NATIVE=1 python app.py
```

## ベンチマーク

```bash
python benchmarks/benchmark_validation.py --native-mode both
```

`both` はネイティブ自動選択とPython強制経路を両方測ります。
