# ValidKit Performance Roadmap

作成日: 2026-07-05

この計画書は、ValidKit が Pydantic と比較されるホットパスで十分に速くなるための実装方針をまとめるものです。短期的には Python 実装の無駄を削り、中期的には optional Rust accelerator を検討します。API の軽さ、依存なしで使える現在の強み、既存の `validate()` / `compile()` の使い心地は維持します。

## 目標

- `compile(schema).validate(data)` を性能面の主戦場にする。
- 平坦な成功パスでは Pydantic を安定して上回る。
- 入れ子 payload と list/dict validator でも Pydantic に近づき、可能なら上回る。
- 通常の `validate(data, schema)` は柔軟性とデバッグ性を保ちつつ、明らかな再計算をなくす。
- Rust 化する場合も Python API は壊さず、純 Python fallback を維持する。

## 現状認識

現在の比較では、compiled path は `flat_basic` や一部の class schema で Pydantic を上回れる。一方で `nested_payload` と `collect_errors` はまだ負けている。

主な理由は次の通り。

- 通常版 `validate()` は実行ごとにスキーマ解釈を行うため、事前コンパイル済みの Pydantic model と比較すると不利。
- compiled path でも、入れ子の dict/list 検証で結果用の dict/list を再構築している。
- `collect_errors=True` はエラー収集のためのオブジェクト作成と分岐が多く、成功パスより最適化しづらい。
- Python/Rust 境界をまたぐ場合、データ変換やコピーが増えると Rust 化の利点を失う。

## 方針

### Phase 1: Python compiled path のコピー削減

最初に行うべき作業は、Rust 化ではなく Python 側の compiled path を詰めること。

対象:

- `src/validkit/compiled.py`
- `tests/test_compile.py`
- `benchmarks/benchmark_validation.py`

内容:

- dict schema の成功パスで、入力 dict を再構築せず返せる条件を明確化する。
- `ListValidator` / `DictValidator` の成功パスで、要素の変換が発生しない場合は入力 list/dict をそのまま返す。
- `.coerce()`, `.default()`, `.custom()`, `.env()`, `.when()`, `.optional()`, `partial`, `base`, `collect_errors` がある場合は preserve 最適化を無効にする。
- extra key が存在する場合は従来どおり schema に定義されたキーだけを返す。
- 失敗時の error path は従来と同じ文字列を維持する。

期待効果:

- `nested_payload` の compiled path を大きく改善する。
- Rust 化前に「Python 側で残っている無駄」を減らし、ネイティブ化すべき範囲を見極めやすくする。

### Phase 2: schema IR の分離

Rust accelerator を見据え、Python の Validator オブジェクトから実行用 IR を分離する。

内容:

- compile 時に、Validator ツリーを小さな immutable IR に変換する。
- IR には型チェック、min/max、length、regex、key schema、value schema など実行に必要な情報だけを持たせる。
- Python callable を含む `.custom()` / `.when()` / decryptor は Rust fast path 対象外にするか、Python callback として明示的に扱う。
- IR を Python コード生成と Rust 実行エンジンの両方で共有できる形にする。

期待効果:

- 現在の文字列コード生成を整理できる。
- Rust 化する場合の境界が明確になる。
- テストしやすい内部表現を作れる。

### Phase 3: optional Rust accelerator

Rust 化は全体ではなく、compiled schema の実行エンジンから始める。

内容:

- `validkit-rs` または package 内 native module として optional extension を用意する。
- Python API は `compile(schema)` のまま維持する。
- Rust extension が利用可能な場合のみ、対象 IR を Rust executor に渡す。
- 対応できない schema は Python compiled path に fallback する。
- Python dict/list を直接巡回し、不要な変換やシリアライズは行わない。

避けること:

- 既存 `validate()` API の全面置き換え。
- Python dict を msgspec などで毎回 encode/decode してから検証する設計。
- Rust 側で結果 dict/list を常に再構築する設計。

期待効果:

- 成功パスの型チェック、range check、list/dict traversal を Rust 側に逃がせる。
- Python callback が不要な pure schema で大きな速度改善が狙える。

### Phase 4: bytes/JSON 入力の高速入口

msgspec のような高速 decoder が活きるのは、入力が最初から JSON bytes の場合。

内容:

- `validate_json(data: bytes, schema)` または `compiled.validate_json(data)` を検討する。
- JSON decode と validation を二重に行わない構造にする。
- msgspec 採用は optional dependency とし、標準 API には必須化しない。

期待効果:

- Web API の request body など、bytes 起点のユースケースで高速化できる。
- 既に Python dict になっているデータでは無理に msgspec を挟まない判断ができる。

## Rust 化の判断基準

Rust 化に進む条件:

- Phase 1 後も `nested_payload` が Pydantic に大きく負ける。
- cProfile で Python ループ、`isinstance`, dict/list traversal が支配的である。
- pure schema の割合が高く、Python callback を避けられるユースケースが十分ある。
- wheel 配布、CI、Windows/macOS/Linux 対応のメンテナンスコストを受け入れられる。

Rust 化を保留する条件:

- Python compiled path だけで主要ベンチが十分改善する。
- 境界コストや fallback 分岐により、実測で差が出ない。
- API の単純さや pure Python 配布の価値を損なう。

## ベンチマーク方針

- 比較対象は Pydantic v2 の `BaseModel.model_validate(...)`。
- ValidKit は通常 `validate(...)` と `compile(...).validate(...)` を分けて測る。
- 最低限、次のケースを継続測定する。
  - flat object
  - nested object
  - list/dict heavy payload
  - collect errors
  - class schema
  - defaults/coerce/custom を含む fallback schema
- median だけでなく、複数回実行して揺れを確認する。

## 第一弾の完了条件

- `nested_payload` の compiled path が現状より明確に改善している。
- `flat_basic` と `class_schema` の Pydantic 優位を維持している。
- `collect_errors=True`, `partial=True`, `base`, default, optional, env, when, custom の既存テストが壊れていない。
- preserve 最適化の条件がテストで明示されている。
