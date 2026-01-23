# ValidKit 詳細ドキュメント

## API リファレンス

### `validate(data, schema, **options)`
メインの検証関数です。

- **引数**:
  - `data` (Any): 検証対象のデータ
  - `schema` (Any): スキーマ定義（辞書、バリデータ、または型）
  - `partial` (bool): `True` の場合、スキーマにあるキーが入力データになくてもエラーにしません
  - `base` (dict): 不足しているキーのデフォルト値を埋めるためのベース辞書
  - `migrate` (dict): キーの改名（文字列）や値の変換（関数）を定義
  - `collect_errors` (bool): `True` の場合、最初のエラーで止まらずにすべてのエラーを収集して `ValidationResult` を返します

### バリデータビルダー `v`

#### 型バリデータ
- `v.str()`: 文字列
- `v.int()`: 整数
- `v.float()`: 浮動小数点数
- `v.bool()`: 真偽値

#### チェーンメソッド
- `.optional()`: フィールドを任意にします
- `.regex(pattern)`: (str限定) 正規表現チェック
- `.range(min, max)`: (int/float限定) 範囲チェック
- `.min(val)` / `.max(val)`: 最小値/最大値チェック
- `.custom(func)`: 独自の検証・変換関数を適用
- `.when(condition_func)`: データの全体状態に基づいて検証の要否を決定

#### コンテナ型バリデータ
- `v.list(item_schema)`: 各要素が `item_schema` に適合するリスト
- `v.dict(key_type, value_schema)`: 指定した型をキーとし、値が `value_schema` に適合する辞書
- `v.oneof(choices)`: 許可される値のリストのいずれかであること

## 高度なパターン

### 条件付きバリデーション (`when`)
他のフィールドの値に応じて、特定のフィールドを必須にする例：

```python
SCHEMA = {
    "通知": v.bool(),
    "通知先": v.str().when(lambda d: d.get("通知") == True)
}
```

### カスタムバリデータでの変換
データを検証するだけでなく、正規化（大文字化など）も行えます：

```python
def normalize_name(s):
    return s.strip().capitalize()

SCHEMA = {"name": v.str().custom(normalize_name)}
```

## エラーハンドリング

通常は `ValidationError` が発生しますが、`collect_errors=True` を使うと詳細なリストを取得できます。

```python
result = validate(data, SCHEMA, collect_errors=True)
for err in result.errors:
    print(f"Path: {err.path}")
    print(f"Msg: {err.message}")
    print(f"Value: {err.value}")
```
