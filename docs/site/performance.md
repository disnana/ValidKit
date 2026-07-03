# パフォーマンスとベンチマーク

ベンチマークは `benchmarks/benchmark_validation.py` にあります。外部依存なしで通常版とコンパイル版を比較できます。

```bash
python benchmarks/benchmark_validation.py
python benchmarks/benchmark_validation.py --json
```

## 測定内容

- `flat_basic`: 基本型中心の平坦なスキーマ
- `nested_payload`: ネストした辞書とリスト
- `collect_errors`: 複数エラー収集モード
- `class_schema`: クラス記法スキーマ

## 読み方

`speedup` が 1 より大きいほど、コンパイル版が高速です。特殊バリデータやカスタム処理が多い場合は通常版との差が小さくなります。
