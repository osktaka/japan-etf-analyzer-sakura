---
revision: 2026-04-29
owner: test
benchmark: ^N225
review_frequency: weekly_friday

target_allocation:
  core: 0.65
  theme: 0.25
  cash: 0.10

target_holdings:
  core:
    - { code: "2559", name: "MAXIS全世界株", weight: 0.35 }
    - { code: "1655", name: "iShares S&P500", weight: 0.20 }
    - { code: "1306", name: "NF TOPIX", weight: 0.10 }
  theme:
    - { code: "200A", name: "NF日経半導体", weight: 0.10 }
    - { code: "1545", name: "NF NASDAQ100", weight: 0.08 }
    - { code: "2638", name: "GXロボティクス&AI日本", weight: 0.07 }

sell_schedule:
  - { date: "2026-05-07", code: "1540", name: "純金", quantity: 10, action: "all", reason: "金過剰、含み損損益通算枠" }
  - { date: "2026-05-11", code: "2646", name: "メタル", quantity: 50, action: "all", reason: "テーマ枠を半導体/AIへ振替" }
  - { date: "2026-05-13", code: "1627", name: "電力ガス", quantity: 15, action: "all", reason: "α-11.2pp、単一業種ベット撤収" }
  - { date: "2026-05-14", code: "1629", name: "商社", quantity: 700, action: "all", reason: "α-12.2pp" }
  - { date: "2026-05-19", code: "1618", name: "エネルギー", quantity: 4, action: "all", reason: "α-22.0pp" }
  - { date: "2026-05-22", code: "466A", name: "防衛テック", quantity: 65, action: "all", reason: "α-23.6pp" }

buy_dca_schedule:
  - { date: "2026-05-20", code: "2559", quantity: 3 }
  - { date: "2026-05-20", code: "1306", quantity: 8 }
  - { date: "2026-05-20", code: "1655", quantity: 105 }
  - { date: "2026-05-20", code: "200A", quantity: 4 }
  - { date: "2026-05-20", code: "1545", quantity: 1 }
  - { date: "2026-05-20", code: "2638", quantity: 11 }
  - { date: "2026-06-24", code: "2559", quantity: 3 }
  - { date: "2026-06-24", code: "1306", quantity: 8 }
  - { date: "2026-06-24", code: "1655", quantity: 105 }
  - { date: "2026-06-24", code: "200A", quantity: 4 }
  - { date: "2026-06-24", code: "2638", quantity: 12 }
  - { date: "2026-07-22", code: "2559", quantity: 3 }
  - { date: "2026-07-22", code: "1306", quantity: 8 }
  - { date: "2026-07-22", code: "1655", quantity: 105 }
  - { date: "2026-07-22", code: "200A", quantity: 4 }
  - { date: "2026-07-22", code: "1545", quantity: 1 }
  - { date: "2026-07-22", code: "2638", quantity: 12 }
  - { date: "2026-08-19", code: "2559", quantity: 3 }
  - { date: "2026-08-19", code: "1306", quantity: 8 }
  - { date: "2026-08-19", code: "1655", quantity: 105 }
  - { date: "2026-08-19", code: "200A", quantity: 3 }
  - { date: "2026-08-19", code: "1545", quantity: 1 }
  - { date: "2026-08-19", code: "2638", quantity: 11 }

mechanical_rules:
  min_holding_months: 6
  loss_cut_pct: -20.0
  take_profit_pct: [50.0, 100.0]
  n225_drawdown_trigger_pct: -5.0
  n225_drawdown_basis: "previous_close"
  n225_dca_lookback_days: 10
  alpha_deviation_threshold_pp: 10.0
  rebalance_threshold_pct: 5.0
  rebalance_check_basis: "close"

revision_history:
  - { date: "2026-04-29", note: "初版・案1B戦略確定（コア65%/テーマ25%/現金10%）" }
---

# testユーザー個人投資戦略

## 1. 戦略の背景

過去1年間（2025年4月〜2026年4月）の運用で、ベンチマーク（^N225）に対して **α-46.9pp** 劣後する結果となった。原因は以下:

- 単一業種への集中ベット（電力ガス、商社、エネルギー、防衛テック）
- 株価下落時の「動かなかった1ヶ月」で約22万円の機会損失
- 戦略ドキュメント不在による行動原則のブレ
- 損益通算と感情判断の混在

この反省を踏まえ、**機械的なルール**と**日々のリマインド**で行動を縛り直すための戦略書を策定する。

## 2. 全体方針（案1B採用）

| 区分 | 配分 | 役割 |
|------|------|------|
| コア | 65% | 全世界・S&P500・TOPIXの広域インデックス |
| テーマ | 25% | 半導体・NASDAQ100・ロボティクスAI（4ヶ月DCAで段階構築） |
| 現金 | 10% | 急落時の機動枠 |

ベンチマークは **^N225（日経平均）** を継続。^N225 比較で α が ±10pp を超えて逸脱したら警告。

## 3. 売却スケジュール

α劣後・テーマ重複・損益通算を加味した順序で 2026-05-07 〜 2026-05-22 に段階売却する。詳細は frontmatter `sell_schedule` を参照。

主な根拠:

- **1540 純金**: コモディティ枠が過剰（金 + メタル ≈ 18%）。含み損で損益通算枠として活用
- **2646 メタル**: テーマ枠を半導体/AI/全世界株に振替（戦略整合性）
- **1627 電力ガス / 1629 商社 / 1618 エネルギー / 466A 防衛テック**: α逸脱が10pp超の単一業種集中銘柄、撤収して6銘柄ポートフォリオに集約

## 4. 買付（DCA）スケジュール

売却完了後の現金を **4ヶ月 DCA**（毎月第3水曜前後、計4回）で6銘柄に投入。各回約25万円、6銘柄に等分の数量で購入。詳細は frontmatter `buy_dca_schedule` を参照。

DCA を使う理由:

- 一括投入で底値判断ミスのリスクを排除
- 行動の習慣化（毎月のリマインド受信→約定→記帳）
- 急落時は前倒しで投入（後述の「N225 -5%下落」ルール）

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
| N225 急落（watcher） | -5.0%（前日終値比） | アラートメール送信、DCA前倒し検討 |
| N225 直近10営業日DD | -5.0% | DCA前倒しトリガー |
| 配分逸脱 | 5pp | コア/テーマ/現金の目標配分から終値ベースで5pp逸脱で warn |
| α逸脱 | 10pp | ベンチマーク比 ±10pp を超えた銘柄を週次レビューで強調 |

### 5.3 fingerprint による重複通知抑止

`mechanical_rule_events` テーブルに `fingerprint = sha256(date + code + rule_kind)` を保存し、同日同銘柄同ルールの再発動はメール通知しない（DBには記録）。日跨ぎでルール継続中は毎日通知（行動を促す意図）。

## 6. レビュー頻度

- **毎日朝7時**: 当日の売買予定・前日比をメール
- **平日17:30**: 当日終値ベースの保有状況・配分・α 概況
- **金曜18時**: 過去5営業日の振り返り（α、配分逸脱、機械ルール発動履歴）
- **平日 9:00-15:00 5分間隔**: N225・個別銘柄の機械ルール監視（イベント発生時のみメール）

## 7. 改訂ルール

- 戦略変更は frontmatter の `revision` 日付を更新し、`revision_history` に追記
- 機械ルール閾値の変更は **月次以上の頻度では行わない**（短期相場で揺れる）
- 売買スケジュール完了後、実績と乖離があれば次月の改訂で反映

---

参照: `backend/src/services/strategy_loader.py`、`backend/src/services/daily_advisor_service.py`
