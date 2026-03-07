# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Changed

- `NumberValidator.range()` は `min > max` の不正な境界を定義時に `ValueError` で拒否するようになりました。あわせて `.min()` / `.max()` のチェーンでも矛盾する境界設定を防ぎます。
- `Schema.generate_sample()` は生成した候補値を各バリデータで再検証するようになりました。`regex()` や `custom()` を満たせない場合は、不正なサンプルを返さず `ValueError` を送出します。

### Added

#### `v.auto_infer(data, type_map=None, schema_overrides=None)` — スキーマ逆生成

渡されたデータから ValidKit スキーマを自動生成する静的メソッドを追加しました。
既存のデータ構造をそのままスキーマに変換してバリデーションのブートストラップに使えます。

**`schema_overrides` パラメータ** (新規)

特定のフィールドのバリデータを手動で上書きできます。値は `Validator` インスタンスのみ受け付けるため、出力スキーマは常に検証・保管に使える形になります。**トップレベルの dict のキーにのみ適用され、ネストした dict やリスト内の要素には適用されません。**

```python
schema = v.auto_infer(
    {"name": "Alice", "score": 9.5, "bio": "dev"},
    schema_overrides={
        "score": v.float().range(0.0, 10.0),  # 推論をスキップして指定バリデータを使用
        "bio": v.str().optional(),             # optional 指定も可能
    },
)
```

**`type_map` の callable 自動変換** (機能強化)

`type_map` の値として callable を渡したとき、その戻り値が `Validator` インスタンスであればそのまま使用し、プリミティブ値 (`str`, `int`, `float`, `bool`, `list`, `dict`, `None`) であれば変換後の値で `auto_infer` を再帰呼び出しします（オプション自動変換）。

```python
import datetime

# callable が str を返す → auto_infer("2024-01-01") → StringValidator
schema = v.auto_infer(
    {"ts": datetime.date(2024, 1, 1)},
    type_map={datetime.date: lambda val: val.isoformat()},
)

# type_map と schema_overrides の併用
schema = v.auto_infer(
    {"name": "Alice", "score": 9.5, "created_at": datetime.date(2024, 1, 1)},
    type_map={datetime.date: v.str()},
    schema_overrides={"score": v.float().range(0.0, 10.0)},
)
```

**型推論のルール:**

| 型 | 返すバリデータ |
|---|---|
| `None` | `Validator().optional()` (型不明のため optional 扱い) |
| `bool` | `BoolValidator` (int より先に評価) |
| `int` | `NumberValidator(int)` |
| `float` | `NumberValidator(float)` |
| `str` | `StringValidator` |
| `list` | `ListValidator` (最初の要素から推論; 空は `StringValidator`) |
| `dict` | ネストした dict スキーマ (再帰) |
| その他 | `type_map` で処理; なければ `TypeError` |

---

## [1.2.0] — 2024-XX-XX

### Added

- `v.str()`, `v.int()`, `v.float()`, `v.bool()` に `.default(value)` メソッドを追加。フィールドが欠損した際に自動補完します。`.default()` を設定したフィールドは自動的に optional になります。
- すべてのバリデータに `.examples(list)` メソッドを追加。サンプルデータ生成・ドキュメント生成の補助情報として使用します。
- すべてのバリデータに `.description(text)` メソッドを追加。フィールドの説明文を保持します。
- `Schema.generate_sample()` メソッドを追加。スキーマ定義からサンプルデータを生成します（優先順位: `.default()` > `.examples()[0]` > 型ダミー値）。
- `v.auto_infer(data, type_map=None)` 静的メソッドを追加。渡されたデータから ValidKit スキーマを逆生成します。`None` は optional 扱い、カスタム型は `type_map` で対応できます。

[Unreleased]: https://github.com/disnana/ValidKit/compare/v1.2.0...HEAD
[1.2.0]: https://github.com/disnana/ValidKit/releases/tag/v1.2.0
