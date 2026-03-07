# ValidKit 詳細ドキュメント

ValidKit の API リファレンスおよび高度な使用方法について詳しく説明します。

---

## メイン API

### `validate(data, schema, **options)`

入力データを指定されたスキーマで検証し、必要に応じて変換を行います。

**引数:**
- `data` (Any): 検証対象のデータ（通常は `dict`）。
- `schema` (Any): スキーマ定義。`dict`、`Validator` オブジェクト、または `int`, `str` などの組み込み型が使用可能です。
- `partial` (bool): `True` の場合、スキーマで定義されているキーが入力データになくてもエラーにしません。部分更新に便利です。
- `base` (dict): デフォルト値として機能する辞書。`data` に不足しているキーがある場合、この `base` から値が補完されます。
- `migrate` (dict): データの構造変換を定義します。
  - キーの改名: `{"旧キー": "新キー"}`
  - 値の変換: `{"キー": lambda v: v.lower()}`
- `collect_errors` (bool): `True` の場合、最初のエラーで停止せず、すべてのエラーを収集します。

**戻り値:**
- 検証・変換済みのデータ。
- `collect_errors=True` の場合は `ValidationResult` オブジェクト。

---

`v` は流れるようなインターフェース（Fluent Interface）を提供し、バリデータを直感的に構築できます。

### `Schema[T]` クラス

型情報を持つスキーマのラッパーです。

#### `.generate_sample()`
スキーマ定義からサンプルデータの辞書を生成します。生成後の値は各バリデータで再検証されるため、制約を満たさないサンプルは返されません。

```python
sample = SCHEMA.generate_sample()
```

優先順位: `.default()` > `.examples()[0]` > 各型のデフォルト値。

`regex()` や `custom()` などでこれらの候補が制約を満たせない場合は、`ValueError` を送出します。その場合は `.default(...)` または `.examples([...])` で妥当なサンプル候補を与えてください。

### スキーマ自動生成

#### `v.auto_infer(data, type_map=None, schema_overrides=None)`

渡されたデータから ValidKit スキーマを **逆生成** します。既存のデータ構造からスキーマをブートストラップするのに便利です。

**引数:**
- `data` (Any): スキーマを推論する元データ。
- `type_map` (dict, 省略可能): カスタム型 → バリデータのマッピング。
  - 値に `Validator` インスタンスを渡すとそのまま使用します。
  - 値に callable (値 → `Validator`) を渡すと、呼び出し結果を使用します。
  - 値に callable (値 → プリミティブ) を渡すと、変換後の値で `auto_infer` を再帰呼び出しします（**オプション自動変換**）。
- `schema_overrides` (dict, 省略可能): フィールド名 → バリデータの補完マッピング。`data` が `dict` の場合のみ有効。指定されたフィールドは型推論をスキップします。`.optional()` もチェーン可能です。**トップレベルの dict のキーにのみ適用され、ネストした dict やリスト内の要素には適用されません。**

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

**使用例:**

```python
# 基本的な使い方
data = {"name": "Alice", "age": 30, "active": True, "tags": ["admin"]}
schema = v.auto_infer(data)
result = validate(data, schema)  # 元データでそのまま検証できる

# None フィールドは自動で optional になる
data = {"name": "Alice", "nickname": None}
schema = v.auto_infer(data)
# -> {"name": StringValidator, "nickname": Validator().optional()}

# type_map でカスタム型を処理 (バリデータインスタンス)
import datetime
schema = v.auto_infer(
    {"created_at": datetime.date(2024, 1, 1)},
    type_map={datetime.date: v.str()},
)

# type_map の callable がプリミティブを返す場合 → 変換後の値で再推論 (オプション自動変換)
schema = v.auto_infer(
    {"ts": datetime.datetime(2024, 6, 15, 12, 0)},
    type_map={datetime.datetime: lambda val: val.isoformat()},  # str に変換 → StringValidator
)

# schema_overrides でフィールドを手動補完・optional 指定
schema = v.auto_infer(
    {"name": "Alice", "score": 9.5, "bio": "dev"},
    schema_overrides={
        "score": v.float().range(0.0, 10.0),
        "bio": v.str().optional(),
    },
)

# type_map と schema_overrides の併用
schema = v.auto_infer(
    {"name": "Alice", "score": 9.5, "created_at": datetime.date(2024, 1, 1)},
    type_map={datetime.date: v.str()},
    schema_overrides={"score": v.float().range(0.0, 10.0)},
)
```

---

### 型バリデータ
- `v.str()`: 文字列であることを検証。
- `v.int()`: 整数であることを検証。
- `v.float()`: 浮動小数点数であることを検証。
- `v.bool()`: 真偽値であることを検証。

### コンテナ型バリデータ
- `v.list(item_schema)`: 各要素が `item_schema` に適合するリストであることを検証。
- `v.dict(key_type, value_schema)`: キーが `key_type` であり、値が `value_schema` に適合する辞書であることを検証。
- `v.oneof(choices)`: 値が `choices` リストのいずれかであることを検証。

### 修飾メソッド（チェーンメソッド）
すべてのバリデータで使用可能なメソッド：
- `.optional()`: フィールドを任意（省略可能）にします。
- `.default(value)`: フィールドが欠損している場合のデフォルト値を設定します。設定すると自動的に `.optional()` となります。
- `.examples(list)`: 具体的な値の例をリストで保持します（サンプル生成等に使用）。
- `.description(text)`: フィールドの説明文を保持します。
- `.custom(func)`: 独自の検証・変換関数を適用します。関数は値を返し、エラー時は例外（`ValueError`, `TypeError`）を投げる必要があります。
- `.when(condition_func)`: 他のフィールドの状態に応じて、このバリデーションを適用するか決定します。`condition_func` はデータ全体を受け取ります。

型固有のメソッド：
- `.regex(pattern)`: (str限定) 正規表現にマッチするか検証。
- `.range(min, max)`: (int/float限定) 値が範囲内にあるか検証。`min <= max` が必須で、不正な境界は定義時に `ValueError` になります。
- `.min(val)` / `.max(val)`: (int/float限定) 最小値または最大値を検証。既存の反対側境界と矛盾する値は設定できません。

---

## エラーハンドリング

### `ValidationError`
検証に失敗した際に発生します。
- `path`: エラーが発生した場所（例: `"ユーザー.設定[0].名前"`）。
- `message`: 人間が読みやすいエラーメッセージ。
- `value`: エラーの原因となった値。

### エラーの全件取得
`collect_errors=True` を指定すると、複数のエラーを一度に取得できます。

```python
result = validate(data, SCHEMA, collect_errors=True)
if result.errors:
    for err in result.errors:
        print(f"場所: {err.path}, 内容: {err.message}")
```

---

## 高度なパターン

### 条件付きバリデーション (`when`)
「AがTrueの場合のみ、Bを必須にする」といった定義が可能です。

```python
SCHEMA = {
    "通知": v.bool(),
    "メールアドレス": v.str().when(lambda d: d.get("通知") == True)
}
```

### 動的な変換
`custom` メソッドを使って、検証と同時にデータの正規化を行えます。

```python
def normalize_and_validate(v):
    v = v.strip()
    if len(v) < 3:
        raise ValueError("短すぎます")
    return v.upper()

SCHEMA = {"code": v.str().custom(normalize_and_validate)}
```
