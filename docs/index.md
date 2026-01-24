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

## バリデータビルダー `v`

`v` は流れるようなインターフェース（Fluent Interface）を提供し、バリデータを直感的に構築できます。

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
- `.custom(func)`: 独自の検証・変換関数を適用します。関数は値を返し、エラー時は例外（`ValueError`, `TypeError`）を投げる必要があります。
- `.when(condition_func)`: 他のフィールドの状態に応じて、このバリデーションを適用するか決定します。`condition_func` はデータ全体を受け取ります。

型固有のメソッド：
- `.regex(pattern)`: (str限定) 正規表現にマッチするか検証。
- `.range(min, max)`: (int/float限定) 値が範囲内にあるか検証。
- `.min(val)` / `.max(val)`: (int/float限定) 最小値または最大値を検証。

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
