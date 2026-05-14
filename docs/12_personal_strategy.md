---
revision: 2026-05-14
owner: test
benchmark: ^N225
review_frequency: weekly_friday

target_buckets:
  group_a: { label_ja: "A群（コア・逆相関）", weight_pct: 45.00 }
  group_b: { label_ja: "B群（日本株テーマ）", weight_pct: 45.00 }
  cash:    { label_ja: "現金",              weight_pct: 10.00 }

target_holdings:
  - { code: "2559", name: "オルカン",       bucket: "group_a", weight_pct: 15.00 }
  - { code: "1540", name: "純金",           bucket: "group_a", weight_pct: 15.00 }
  - { code: "200A", name: "半導体",         bucket: "group_a", weight_pct: 15.00 }
  - { code: "1306", name: "TOPIX",          bucket: "group_b", weight_pct:  9.00 }
  - { code: "1629", name: "商社",           bucket: "group_b", weight_pct:  9.00 }
  - { code: "1615", name: "銀行",           bucket: "group_b", weight_pct:  9.00 }
  - { code: "2646", name: "メタル",         bucket: "group_b", weight_pct:  9.00 }
  - { code: "1618", name: "エネルギー資源", bucket: "group_b", weight_pct:  9.00 }

mechanical_rules:
  min_holding_months: 6
  loss_cut_pct: -20.0
  take_profit_pct: [50.0, 100.0]
  n225_drawdown_trigger_pct: -5.0
  n225_drawdown_basis: previous_close
  n225_dca_lookback_days: 10
  alpha_deviation_threshold_pp: 10.0
  drift_ok_pp: 3.0
  drift_warn_pp: 5.0
  rebalance_check_basis: close

revision_history:
  - { date: "2026-05-14", note: "A群/B群モデル統一、core/theme廃止、sell_schedule/buy_dca_schedule撤去、rebalance通知をmorningに統合" }
  - { date: "2026-04-29", note: "初版・案1B戦略確定" }
---

# testユーザー個人投資戦略

## 1. 戦略の背景

過去1年間（2025年4月〜2026年4月）の運用で、ベンチマーク（^N225）に対して **α-46.9pp** 劣後する結果となった。原因は以下:

- 単一業種への集中ベット（電力ガス、商社、エネルギー、防衛テック）
- 株価下落時の「動かなかった1ヶ月」で約22万円の機会損失
- 戦略ドキュメント不在による行動原則のブレ
- 損益通算と感情判断の混在

この反省を踏まえ、**機械的なルール**と**日々のリマインド**で行動を縛り直すための戦略書を策定する。

## 2. 全体方針（A群/B群モデル採用）

| 区分 | 配分 | 役割 |
|------|------|------|
| A群（コア・逆相関） | 45% | オルカン(15%) + 純金(15%) + 半導体(15%)。互いに相関の低い3資産で大局を構成 |
| B群（日本株テーマ） | 45% | TOPIX / 商社 / 銀行 / メタル / エネルギー資源 各9%。日本株5テーマに均等配分 |
| 現金 | 10% | 急落時の機動枠 |

ベンチマークは **^N225（日経平均）** を継続。^N225 比較で α が ±10pp を超えて逸脱したら警告。

採用銘柄および目標配分は frontmatter `target_buckets` / `target_holdings` を参照。

## 3. 現状からのリバランス

採用外で保有している銘柄は **次回四半期末（3/6/9/12月末営業日）に全量売却** を推奨する。
採用8銘柄については、各銘柄の目標配分と現状配分の乖離 (`drift_pp`) に応じて、四半期末リバランスで売買数量を **自動算出** する。

日付固定の売却スケジュール（旧 `sell_schedule`）は廃止した。日々の `morning` 通知に当日の推奨アクション（採用外売却＋採用銘柄の不足/超過調整）が組み込まれる。

## 4. 買付方針

月次DCA（旧 `buy_dca_schedule`）は廃止。四半期末リバランスでのみ目標配分に追従する。

理由:

- A群/B群モデルでは目標配分そのものが分散効果を担うため、追加買付タイミングを月次に細分化する優位性が小さい
- 緊急時の機動枠（現金10%）は維持し、N225 急落（-5%）時のみ前倒し買付を検討する

## 5. 機械ルール

戦略を感情に左右されず守るため、以下のルールを **mechanical_rule_watcher** が日中監視し、発動時にメール通知 + DBへevent記録を行う。

### 5.1 個別銘柄ルール

| ルール | 閾値 | 説明 |
|--------|------|------|
| 損切り | -20.0% | 取得単価比 -20% で売却検討（最低保有期間6ヶ月経過後のみ発火） |
| 利確第1段 | +50.0% | 半数売却で利益確定 |
| 利確第2段 | +100.0% | さらに半数売却 |
| 最低保有期間 | 6ヶ月 | 損切りを抑制（短期ノイズへの過剰反応を防ぐ） |

### 5.2 マクロルール

| ルール | 閾値 | 説明 |
|--------|------|------|
| N225 急落（watcher） | -5.0%（前日終値比） | アラートメール送信、買付前倒し検討 |
| N225 直近10営業日DD | -5.0% | 買付前倒しトリガー |
| 配分逸脱 OK | `drift_ok_pp` (3.0pp) | A群/B群/現金の目標配分から終値ベースで 3pp 未満なら問題なし |
| 配分逸脱 WARN | `drift_warn_pp` (5.0pp) | 3pp 以上 5pp 未満で warn、5pp 以上で critical |
| α逸脱 | `alpha_deviation_threshold_pp` (10pp) | ベンチマーク比 ±10pp を超えた銘柄を週次レビューで強調 |

### 5.3 fingerprint による重複通知抑止

`mechanical_rule_events` テーブルに `fingerprint = sha256(date + code + rule_kind)` を保存し、同日同銘柄同ルールの再発動はメール通知しない（DBには記録）。日跨ぎでルール継続中は毎日通知（行動を促す意図）。

## 6. レビュー頻度

- **毎日朝7時（morning）**: 当日の推奨売買・配分状況・前日比をメール（rebalance kind は morning に統合済み）
- **平日17:30（evening）**: 当日終値ベースの保有状況・配分・α 概況
- **金曜18時（weekly）**: 過去5営業日の振り返り（α、配分逸脱、機械ルール発動履歴）
- **平日 9:00-15:00 5分間隔（watcher）**: N225・個別銘柄の機械ルール監視（イベント発生時のみメール）

## 7. 改訂ルール

- 戦略変更は frontmatter の `revision` 日付を更新し、`revision_history` に追記
- 機械ルール閾値の変更は **月次以上の頻度では行わない**（短期相場で揺れる）
- 採用銘柄の入替（`target_holdings`）は四半期末以降の reflection を待って判断

---

参照: `backend/src/services/strategy_loader.py`、`backend/src/services/daily_advisor_service.py`
