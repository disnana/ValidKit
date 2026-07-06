# 実用パターン

## クラス記法

辞書ではなくクラスでスキーマを表現できます。型注釈から基本バリデータが作られ、クラス属性に明示的なバリデータを書くと制約を足せます。

```python
from dataclasses import dataclass
from validkit import compile, v

@dataclass
class User:
    name: str
    age: int = v.int().range(0, 150)
    active: bool = True

schema = compile(User)
user = schema.validate({"name": "Alice", "age": 30})

assert isinstance(user, User)
```

`partial=True` の場合は、コンストラクタに必要な値が揃わない可能性があるため辞書を返します。

## Pydanticとの併用

ValidKitは入力境界の軽い検証や設定ファイル、プラグイン設定の検証に向いています。Pydanticモデルをすでに使っているアプリでは、外側の高速な形チェックとしてValidKitを置き、ドメインモデル化はPydanticに任せる構成もできます。

```python
from pydantic import BaseModel
from validkit import compile, v

class UserModel(BaseModel):
    name: str
    age: int

incoming = compile({
    "name": v.str().min(3),
    "age": v.int().range(0, 150),
})

data = incoming.validate(payload)
user = UserModel(**data)
```

逆に、Pydanticモデルの出力を外部API向けに軽く再検証する使い方もできます。

## カスタム型

任意のPython型をそのまま受けたい場合は `v.instance(...)` を使います。

```python
from pathlib import Path
from validkit import validate, v

schema = {"output": v.instance(Path)}

result = validate({"output": Path("dist")}, schema)
```

値を変換したい場合は `.custom(...)` を使います。

```python
from uuid import UUID
from validkit import validate, v

schema = {
    "id": v.str().custom(UUID),
}

result = validate({"id": "6f9619ff-8b86-d011-b42d-00cf4fc964ff"}, schema)
assert isinstance(result["id"], UUID)
```

`.custom(...)` や `v.instance(...)` はPythonオブジェクトや任意関数を扱うため、ネイティブコアではなくPython経路で検証されます。
