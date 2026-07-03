#!/usr/bin/env python3
"""Generate ValidKit documentation pages for the VitePress site."""

from __future__ import annotations

import inspect
import importlib
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
DOCS = ROOT / "docs"
SITE = DOCS / "site"

sys.path.insert(0, str(SRC))

compiled_module = importlib.import_module("validkit.compiled")
validator_module = importlib.import_module("validkit.validator")
v_module = importlib.import_module("validkit.v")


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = inspect.cleandoc(content).strip()
    text = "\n".join(line[4:] if line.startswith("    ") else line for line in text.splitlines())
    path.write_text(text + "\n", encoding="utf-8")


def signature(obj: object) -> str:
    try:
        return str(inspect.signature(obj))
    except (TypeError, ValueError):
        return "(...)"


def public_methods(cls: type) -> list[str]:
    names = []
    for name, member in inspect.getmembers(cls, predicate=inspect.isfunction):
        if name.startswith("_"):
            continue
        names.append(name)
    return names


def validator_table(lang: str) -> str:
    rows = [
        ("v.str()", "StringValidator", "文字列 / string"),
        ("v.int()", "NumberValidator", "整数 / integer"),
        ("v.float()", "NumberValidator", "浮動小数点 / float"),
        ("v.bool()", "BoolValidator", "真偽値 / boolean"),
        ("v.list(schema)", "ListValidator", "リスト・タプル / list and tuple"),
        ("v.dict(key_type, schema)", "DictValidator", "辞書 / dict"),
        ("v.oneof(values)", "OneOfValidator", "候補値 / allowed values"),
        ("v.instance(type)", "InstanceValidator", "任意クラス / custom instance"),
        ("v.datetime()", "DateTimeValidator", "日時 / datetime"),
        ("v.uuid()", "UUIDValidator", "UUID"),
        ("v.mac()", "MACValidator", "MAC address"),
        ("v.sid()", "SIDValidator", "Windows SID"),
        ("v.hwid()", "HWIDValidator", "Hardware ID"),
        ("v.ip()", "IPValidator", "IP address"),
        ("v.snowflake()", "SnowflakeValidator", "Discord Snowflake"),
        ("v.version()", "VersionValidator", "Semantic Versioning"),
        ("v.url()", "URLValidator", "URL"),
        ("v.enum(enum_cls)", "EnumValidator", "Enum"),
    ]
    if lang == "ja":
        header = "| ファクトリ | クラス | 検証対象 |\n|---|---|---|"
    else:
        header = "| Factory | Class | Validates |\n|---|---|---|"
    return "\n".join([header, *[f"| `{a}` | `{b}` | {c} |" for a, b, c in rows]])


def generate_api(lang: str) -> str:
    ja = lang == "ja"
    title = "API リファレンス" if ja else "API Reference"
    intro = (
        "ValidKit の公開 API と主要バリデータの一覧です。"
        if ja
        else "Public ValidKit APIs and validator factories."
    )
    common = (
        "| メソッド | 用途 |\n|---|---|\n"
        if ja
        else "| Method | Purpose |\n|---|---|\n"
    )
    common += "\n".join(
        [
            "| `.optional()` | 欠損値と `None` を許容 |" if ja else "| `.optional()` | Allow missing values and `None` |",
            "| `.default(value)` | 欠損時の値を補完 |" if ja else "| `.default(value)` | Fill missing values |",
            "| `.coerce()` | 可能な範囲で型変換 |" if ja else "| `.coerce()` | Coerce compatible values |",
            "| `.custom(func)` | 追加の検証・変換 |" if ja else "| `.custom(func)` | Add validation or transformation |",
            "| `.when(func)` | 親データに基づく条件付き必須 |" if ja else "| `.when(func)` | Conditional requirement based on root data |",
            "| `.env(key, decryptor=None)` | 環境変数フォールバック |" if ja else "| `.env(key, decryptor=None)` | Environment fallback |",
            "| `.secret()` | エラー時の値をマスク |" if ja else "| `.secret()` | Mask error values |",
            "| `.error_msg(text)` | エラーメッセージを上書き |" if ja else "| `.error_msg(text)` | Override error messages |",
            "| `.examples(list)` | サンプル生成・ドキュメント用の例 |" if ja else "| `.examples(list)` | Examples for docs and sample generation |",
            "| `.description(text)` | フィールド説明 |" if ja else "| `.description(text)` | Field description metadata |",
        ]
    )

    validate_sig = signature(validator_module.validate)
    compile_sig = signature(compiled_module.compile)
    schema_sig = signature(validator_module.Schema)
    validator_methods = ", ".join(f"`{m}`" for m in public_methods(v_module.Validator))

    return f"""
    ---
    outline: [2, 3]
    ---

    # {title}

    {intro}

    ## Top-level functions

    ### `validate`

    ```python
    validate{validate_sig}
    ```

    {"データとスキーマを受け取り、検証済みデータを返します。`collect_errors=True` の場合は `ValidationResult` を返し、複数のエラーをまとめて確認できます。" if ja else "Validates data against a schema. With `collect_errors=True`, it returns `ValidationResult` and gathers multiple errors."}

    ### `compile`

    ```python
    compile{compile_sig}
    ```

    {"スキーマを事前コンパイルし、繰り返し検証向けの `CompiledSchema` を返します。基本型・リスト・辞書・一部の組み込みバリデータは生成コードで高速化されます。" if ja else "Precompiles a schema and returns `CompiledSchema` for repeated validation. Core validators, lists, and dictionaries are optimized with generated Python code."}

    ### `Schema`

    ```python
    Schema{schema_sig}
    ```

    {"型補完を助ける薄いラッパーです。`Schema[T]` と `TypedDict` を組み合わせると IDE が戻り値の形を推論しやすくなります。" if ja else "A thin typing helper. Combining `Schema[T]` with `TypedDict` helps IDEs infer validated return shapes."}

    ## Validator factories

    {validator_table(lang)}

    ## Common chain methods

    {common}

    ## Base validator methods

    {validator_methods}

    ## Return and error types

    - `ValidationError`: {"単一エラーを表します。`message`, `path`, `value` を持ちます。" if ja else "Represents a single validation failure. It exposes `message`, `path`, and `value`."}
    - `ValidationResult`: {"複数エラー収集時の戻り値です。`data` と `errors` を持ちます。" if ja else "Returned when collecting multiple errors. It exposes `data` and `errors`."}
    - `CompiledSchema`: {"`compile(schema)` の戻り値です。`.validate(...)` で検証します。" if ja else "Returned by `compile(schema)`. Use `.validate(...)` to validate data."}
    """


def generate_index(lang: str) -> str:
    ja = lang == "ja"
    text = "軽量で直感的な Python バリデーション" if ja else "Lightweight, expressive Python validation"
    tagline = (
        "辞書スキーマ、クラス記法、日本語キー、事前コンパイルをひとつの小さな API で。"
        if ja
        else "Dictionary schemas, class-style schemas, Japanese keys, and precompiled validation in one small API."
    )
    get_started = "はじめる" if ja else "Get Started"
    guide_link = "./guide" if ja else "/en/guide"
    api_link = "./api" if ja else "/en/api"
    perf_link = "./performance" if ja else "/en/performance"
    features = [
        (
            "辞書がそのままスキーマ" if ja else "Schemas are plain dictionaries",
            "設定、API 入力、JSON 風データをそのまま検証できます。" if ja else "Validate settings, API payloads, and JSON-like data directly.",
        ),
        (
            "事前コンパイル" if ja else "Precompiled validation",
            "繰り返し検証するスキーマを高速な専用関数へ変換します。" if ja else "Turn hot schemas into optimized validation functions.",
        ),
        (
            "型補完にやさしい" if ja else "IDE-friendly typing",
            "Schema[T] とクラス記法で、実行時の柔軟さと補完体験を両立します。" if ja else "Use Schema[T] and class-style schemas without giving up runtime flexibility.",
        ),
        (
            "日本語キー対応" if ja else "Unicode key support",
            "日本語キーでもパス付きエラーを自然に返します。" if ja else "Unicode field names work naturally, including error paths.",
        ),
    ]
    feature_lines = "\n".join(
        f'      - title: "{title}"\n        details: "{details}"'
        for title, details in features
    )
    return f"""---
layout: home

hero:
      name: "ValidKit"
      text: "{text}"
      tagline: "{tagline}"
      actions:
        - theme: brand
          text: {get_started}
          link: {guide_link}
        - theme: alt
          text: API
          link: {api_link}
        - theme: alt
          text: Benchmark
          link: {perf_link}

features:
{feature_lines}
---"""


def generate_guide(lang: str) -> str:
    ja = lang == "ja"
    return f"""
    # {"ValidKit ガイド" if ja else "ValidKit Guide"}

    {"ValidKit は、辞書ベースのデータを小さなスキーマで検証するための Python ライブラリです。" if ja else "ValidKit validates dictionary-based data with compact Python schemas."}

    ## {"インストール" if ja else "Installation"}

    ```bash
    pip install validkit-py
    ```

    ## {"最小例" if ja else "Minimal example"}

    ```python
    from validkit import v, validate

    schema = {{
        "name": v.str().min(3),
        "age": v.int().range(0, 150),
        "tags": v.list(v.str()).default([]),
    }}

    user = validate({{"name": "Alice", "age": 30}}, schema)
    print(user)
    ```

    ## {"スキーマの考え方" if ja else "Schema model"}

    {"スキーマは Python の辞書です。キーは検証後の出力キーになり、値には `v.str()` などのバリデータ、ネストした辞書、または `str` / `int` / `float` / `bool` の短縮表記を置けます。" if ja else "A schema is a Python dictionary. Keys become output keys, and values can be validators, nested dictionaries, or shorthand types such as `str`, `int`, `float`, and `bool`."}

    ```python
    schema = {{
        "account": {{
            "email": v.str().regex(r"^[^@]+@[^@]+$"),
            "admin": bool,
        }}
    }}
    ```

    ## {"次に読むもの" if ja else "Next steps"}

    - [{"チュートリアル" if ja else "Tutorial"}](./tutorial)
    - [{"バリデーション機能" if ja else "Validation features"}](./validation)
    - [{"パフォーマンス" if ja else "Performance"}](./performance)
    - [API](./api)
    """


def generate_tutorial(lang: str) -> str:
    ja = lang == "ja"
    return f"""
    # {"チュートリアル" if ja else "Tutorial"}

    ## {"設定ファイルを検証する" if ja else "Validate application settings"}

    ```python
    from validkit import v, validate, ValidationError

    config_schema = {{
        "host": v.str().default("127.0.0.1"),
        "port": v.int().coerce().range(1, 65535).env("APP_PORT").default(8000),
        "debug": v.bool().coerce().default(False),
    }}

    try:
        config = validate({{"port": "8080"}}, config_schema)
    except ValidationError as exc:
        print(exc.path, exc.message)
    ```

    ## {"クラス記法を使う" if ja else "Use class-style schemas"}

    ```python
    from typing import Optional
    from validkit import validate

    class User:
        name: str
        age: int = 18
        nickname: Optional[str]

    user = validate({{"name": "Nana"}}, User)
    ```

    ## {"複数エラーを集める" if ja else "Collect multiple errors"}

    ```python
    from validkit import v, validate

    schema = {{"id": v.int(), "name": v.str().min(3)}}
    result = validate({{"id": "x", "name": "Al"}}, schema, collect_errors=True)

    for error in result.errors:
        print(error.path, error.message)
    ```
    """


def generate_validation(lang: str) -> str:
    ja = lang == "ja"
    return f"""
    # {"バリデーション機能" if ja else "Validation Features"}

    ## {"型と範囲" if ja else "Types and ranges"}

    ```python
    schema = {{
        "name": v.str().range(3, 20),
        "score": v.float().range(0.0, 100.0),
        "enabled": v.bool(),
    }}
    ```

    ## {"型変換" if ja else "Coercion"}

    ```python
    schema = {{
        "port": v.int().coerce(),
        "enabled": v.bool().coerce(),
    }}
    ```

    ## {"条件付き必須" if ja else "Conditional fields"}

    ```python
    schema = {{
        "is_admin": v.bool(),
        "admin_key": v.str().when(lambda data: data.get("is_admin") is True),
    }}
    ```

    ## {"カスタム検証" if ja else "Custom validation"}

    ```python
    def normalize(value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("empty value")
        return value

    schema = {{"name": v.str().custom(normalize)}}
    ```
    """


def generate_compile(lang: str) -> str:
    ja = lang == "ja"
    return f"""
    # {"事前コンパイル" if ja else "Precompiled Validation"}

    {"同じスキーマを何度も使う場合は `compile(schema)` で専用の検証関数を生成できます。" if ja else "When a schema is used repeatedly, `compile(schema)` generates a specialized validator."}

    ```python
    from validkit import compile, v

    user_schema = compile({{
        "id": v.int(),
        "name": v.str().min(3),
        "roles": v.list(v.str()),
    }})

    user_schema.validate({{"id": 1, "name": "Alice", "roles": ["admin"]}})
    ```

    ## {"向いている用途" if ja else "Best fit"}

    - {"API リクエストを大量に検証する処理" if ja else "High-volume API payload validation"}
    - {"同じイベント形状を繰り返し検証する処理" if ja else "Repeated validation of the same event shape"}
    - {"ETL やログ処理のホットパス" if ja else "ETL and logging hot paths"}

    ## {"注意点" if ja else "Notes"}

    {"すべてのバリデータが完全にインライン化されるわけではありません。特殊なバリデータは通常の `validate()` 実装へフォールバックします。" if ja else "Not every validator is fully inlined. Specialized validators may fall back to their normal `validate()` implementation."}
    """


def generate_performance(lang: str) -> str:
    ja = lang == "ja"
    return f"""
    # {"パフォーマンスとベンチマーク" if ja else "Performance and Benchmarks"}

    {"ベンチマークは `benchmarks/benchmark_validation.py` にあります。外部依存なしで通常版とコンパイル版を比較できます。" if ja else "Benchmarks live in `benchmarks/benchmark_validation.py`. They compare normal and compiled validation without external dependencies."}

    ```bash
    python benchmarks/benchmark_validation.py
    python benchmarks/benchmark_validation.py --json
    ```

    ## {"測定内容" if ja else "Measured scenarios"}

    - `flat_basic`: {"基本型中心の平坦なスキーマ" if ja else "Flat schema with core validators"}
    - `nested_payload`: {"ネストした辞書とリスト" if ja else "Nested dictionaries and lists"}
    - `collect_errors`: {"複数エラー収集モード" if ja else "Multiple error collection mode"}
    - `class_schema`: {"クラス記法スキーマ" if ja else "Class-style schema"}

    ## {"読み方" if ja else "How to read results"}

    {"`speedup` が 1 より大きいほど、コンパイル版が高速です。特殊バリデータやカスタム処理が多い場合は通常版との差が小さくなります。" if ja else "`speedup` greater than 1 means compiled validation is faster. Specialized validators and custom callbacks reduce the gap."}
    """


def generate_error_handling(lang: str) -> str:
    ja = lang == "ja"
    return f"""
    # {"エラーハンドリング" if ja else "Error Handling"}

    ```python
    from validkit import ValidationError, v, validate

    try:
        validate({{"age": "old"}}, {{"age": v.int()}})
    except ValidationError as exc:
        print(exc.path)     # age
        print(exc.message)  # Expected int, got str
        print(exc.value)    # old
    ```

    ## `collect_errors=True`

    ```python
    result = validate(
        {{"id": "x", "name": "Al"}},
        {{"id": v.int(), "name": v.str().min(3)}},
        collect_errors=True,
    )

    for error in result.errors:
        print(error.path, error.message)
    ```

    ## {"秘密値のマスク" if ja else "Secret masking"}

    ```python
    schema = {{"password": v.str().min(12).secret()}}
    ```
    """


def generate_async(lang: str) -> str:
    ja = lang == "ja"
    return f"""
    # {"非同期コードでの利用" if ja else "Using ValidKit in Async Code"}

    {"ValidKit の検証処理は同期関数ですが、I/O を行わない軽量な CPU 処理なので、通常は async ハンドラ内でそのまま呼び出せます。" if ja else "ValidKit validation is synchronous, but it performs lightweight CPU work without I/O, so it can usually be called directly inside async handlers."}

    ```python
    from validkit import v, validate

    schema = {{"name": v.str(), "age": v.int()}}

    async def create_user(request):
        payload = await request.json()
        data = validate(payload, schema)
        return data
    ```

    {"非常に大きい payload を大量に処理する場合は、ホットパスのスキーマを `compile()` しておくとレイテンシを抑えやすくなります。" if ja else "For very large payloads or hot paths, precompile schemas with `compile()` to reduce validation latency."}
    """


def generate_security(lang: str) -> str:
    ja = lang == "ja"
    return f"""
    # {"セキュリティ" if ja else "Security"}

    {"ValidKit は入力データの境界検証を助けます。認可、暗号化、サニタイズの代替ではありません。" if ja else "ValidKit helps validate data at trust boundaries. It is not a replacement for authorization, encryption, or output sanitization."}

    ## {"秘密値" if ja else "Secrets"}

    ```python
    schema = {{
        "token": v.str().secret(),
        "password": v.str().secret(),
    }}
    ```

    ## {"環境変数フォールバック" if ja else "Environment fallback"}

    ```python
    schema = {{
        "api_key": v.str().env("APP_API_KEY").secret(),
    }}
    ```

    ## {"推奨" if ja else "Recommendations"}

    - {"外部入力は受け取った直後に検証する" if ja else "Validate external input as soon as it is received"}
    - {"ログに出る可能性がある値は `.secret()` を使う" if ja else "Use `.secret()` for values that may appear in logs"}
    - {"複雑な `.custom()` は単体テストを書く" if ja else "Unit-test complex `.custom()` callbacks"}
    """


def generate_exceptions(lang: str) -> str:
    ja = lang == "ja"
    return f"""
    # {"例外と結果型" if ja else "Exceptions and Result Types"}

    ## `ValidationError`

    {"検証に失敗したときに送出される例外です。" if ja else "Raised when validation fails."}

    - `message`
    - `path`
    - `value`

    ## `ErrorDetail`

    {"`collect_errors=True` で収集される 1 件分のエラーです。" if ja else "Represents one collected error when `collect_errors=True` is used."}

    ## `ValidationResult`

    {"複数エラー収集時の戻り値です。" if ja else "Returned when collecting multiple errors."}

    ```python
    result = validate(data, schema, collect_errors=True)
    print(result.data)
    print(result.errors)
    ```
    """


def generate_partial(lang: str) -> str:
    ja = lang == "ja"
    return f"""
    # {"部分更新とマージ" if ja else "Partial Validation and Merging"}

    {"`partial=True` を使うと、欠損キーを許容できます。`base` を渡すと既存値を補完できます。" if ja else "Use `partial=True` to allow missing keys. Pass `base` to fill values from existing data."}

    ```python
    from validkit import v, validate

    schema = {{"theme": v.str(), "volume": v.int()}}
    base = {{"theme": "dark", "volume": 50}}

    updated = validate({{"volume": 80}}, schema, partial=True, base=base)
    ```

    ## {"マイグレーション" if ja else "Migration"}

    ```python
    schema = {{"username": v.str()}}
    data = validate(
        {{"user_name": "alice"}},
        schema,
        migrate={{"user_name": "username"}},
    )
    ```
    """


def generate_best_practices(lang: str) -> str:
    ja = lang == "ja"
    return f"""
    # {"ベストプラクティス" if ja else "Best Practices"}

    ## {"スキーマを再利用する" if ja else "Reuse schemas"}

    {"同じ構造を何度も検証する場合、スキーマはモジュール定数として定義します。ホットパスでは `compile()` を使います。" if ja else "Define frequently used schemas as module constants. Use `compile()` on hot paths."}

    ## {"入力境界で検証する" if ja else "Validate at boundaries"}

    {"API、CLI、設定ファイル、外部イベントなど、信頼境界に入った直後に検証します。" if ja else "Validate data as soon as it crosses a trust boundary: APIs, CLIs, config files, and external events."}

    ## {"例外メッセージに秘密値を出さない" if ja else "Avoid leaking secrets"}

    ```python
    schema = {{
        "api_key": v.str().secret(),
        "password": v.str().secret(),
    }}
    ```

    ## {"複雑な条件は名前付き関数へ" if ja else "Name complex callbacks"}

    {"`lambda` は短い条件に留め、複雑な `.when()` や `.custom()` は名前付き関数にするとテストしやすくなります。" if ja else "Keep lambdas short. Use named functions for complex `.when()` and `.custom()` callbacks so they can be tested."}
    """


def generate_changelog(lang: str) -> str:
    title = "変更履歴" if lang == "ja" else "Changelog"
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    return f"# {title}\n\n" + changelog.split("\n", 1)[1].strip()


def generate_readme(lang: str) -> str:
    ja = lang == "ja"
    return f"""
    # {"ValidKit ドキュメント" if ja else "ValidKit Documentation"}

    {"ValidKit は、Python の辞書データを直感的なスキーマで検証する軽量ライブラリです。" if ja else "ValidKit is a lightweight Python library for validating dictionary data with expressive schemas."}

    ## {"目次" if ja else "Contents"}

    - [{"ガイド" if ja else "Guide"}](guide/guide.md)
    - [{"チュートリアル" if ja else "Tutorial"}](guide/tutorial.md)
    - [{"バリデーション" if ja else "Validation"}](guide/validation.md)
    - [{"事前コンパイル" if ja else "Precompiled validation"}](guide/compile.md)
    - [{"パフォーマンス" if ja else "Performance"}](guide/performance.md)
    - [API](api/validkit.md)
    """


def generate_config() -> str:
    return """
    import { defineConfig } from 'vitepress'

    export default defineConfig({
      title: 'ValidKit',
      description: 'Lightweight Python validation library',
      base: '/',
      themeConfig: {
        nav: [
          { text: 'ホーム', link: '/' },
          { text: 'ガイド', link: '/guide' },
          { text: 'API', link: '/api' },
          { text: 'Benchmark', link: '/performance' }
        ],
        sidebar: [
          {
            text: 'はじめに',
            items: [
              { text: 'ガイド', link: '/guide' },
              { text: 'チュートリアル', link: '/tutorial' },
              { text: '変更履歴', link: '/changelog' }
            ]
          },
          {
            text: '機能',
            items: [
              { text: 'バリデーション', link: '/validation' },
              { text: '事前コンパイル', link: '/compile' },
              { text: 'エラーハンドリング', link: '/error_handling' },
              { text: 'ベストプラクティス', link: '/best_practices' }
            ]
          },
          {
            text: 'リファレンス',
            items: [
              { text: 'API', link: '/api' },
              { text: 'パフォーマンス', link: '/performance' }
            ]
          }
        ],
        socialLinks: [
          { icon: 'github', link: 'https://github.com/disnana/ValidKit' }
        ]
      },
      locales: {
        root: {
          label: '日本語',
          lang: 'ja-JP'
        },
        en: {
          label: 'English',
          lang: 'en-US',
          link: '/en/',
          themeConfig: {
            nav: [
              { text: 'Home', link: '/en/' },
              { text: 'Guide', link: '/en/guide' },
              { text: 'API', link: '/en/api' },
              { text: 'Benchmark', link: '/en/performance' }
            ],
            sidebar: [
              {
                text: 'Getting Started',
                items: [
                  { text: 'Guide', link: '/en/guide' },
                  { text: 'Tutorial', link: '/en/tutorial' },
                  { text: 'Changelog', link: '/en/changelog' }
                ]
              },
              {
                text: 'Features',
                items: [
                  { text: 'Validation', link: '/en/validation' },
                  { text: 'Precompiled Validation', link: '/en/compile' },
                  { text: 'Error Handling', link: '/en/error_handling' },
                  { text: 'Best Practices', link: '/en/best_practices' }
                ]
              },
              {
                text: 'Reference',
                items: [
                  { text: 'API', link: '/en/api' },
                  { text: 'Performance', link: '/en/performance' }
                ]
              }
            ]
          }
        }
      }
    })
    """


def generate_package_json() -> str:
    return """
    {
      "name": "validkit-docs",
      "version": "1.0.0",
      "private": true,
      "type": "module",
      "scripts": {
        "docs:gen": "python ../../scripts/gen_api_docs.py",
        "dev": "vitepress dev",
        "build": "vitepress build",
        "preview": "vitepress preview"
      },
      "devDependencies": {
        "@tailwindcss/postcss": "^4.2.2",
        "autoprefixer": "^10.4.27",
        "postcss": "^8.5.9",
        "tailwindcss": "^4.2.2",
        "vite": "^6.4.3",
        "vitepress": "^1.6.4",
        "vue": "^3.5.32"
      },
      "overrides": {
        "vite": "^6.4.3"
      }
    }
    """


PAGES = {
    "index.md": generate_index,
    "guide.md": generate_guide,
    "tutorial.md": generate_tutorial,
    "validation.md": generate_validation,
    "compile.md": generate_compile,
    "performance.md": generate_performance,
    "error_handling.md": generate_error_handling,
    "async.md": generate_async,
    "encryption.md": generate_security,
    "exceptions.md": generate_exceptions,
    "transactions.md": generate_partial,
    "best_practices.md": generate_best_practices,
    "api.md": generate_api,
    "changelog.md": generate_changelog,
}


def main() -> None:
    for lang, base in [("ja", SITE), ("en", SITE / "en")]:
        for filename, generator in PAGES.items():
            write(base / filename, generator(lang))

    for lang, base in [("ja", DOCS / "ja"), ("en", DOCS / "en")]:
        write(base / "README.md", generate_readme(lang))
        write(base / "api" / "validkit.md", generate_api(lang))
        write(base / "guide" / "guide.md", generate_guide(lang))
        write(base / "guide" / "tutorial.md", generate_tutorial(lang))
        write(base / "guide" / "validation.md", generate_validation(lang))
        write(base / "guide" / "compile.md", generate_compile(lang))
        write(base / "guide" / "performance.md", generate_performance(lang))
        write(base / "guide" / "error_handling.md", generate_error_handling(lang))
        write(base / "guide" / "async.md", generate_async(lang))
        write(base / "guide" / "encryption.md", generate_security(lang))
        write(base / "guide" / "exceptions.md", generate_exceptions(lang))
        write(base / "guide" / "transactions.md", generate_partial(lang))
        write(base / "guide" / "best_practices.md", generate_best_practices(lang))
        legacy_api_name = "nyan" + "sqlite.md"
        write(base / "api" / legacy_api_name, generate_api(lang))

    write(DOCS / "ja" / "guide" / "apsw_full_access_plan.md", generate_security("ja"))

    write(SITE / ".vitepress" / "config.mts", generate_config())
    write(SITE / "package.json", generate_package_json())
    write(SITE / "public" / "CNAME", "validkit.disnana.com")

    print("ValidKit docs generated.")


if __name__ == "__main__":
    main()
