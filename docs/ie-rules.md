# Irish rules reference (`farm_functions.ie`)

Source table for the Irish rules layer (ADR-0053). Every value the Engine uses
for Ireland must appear here with its legal basis and source. Researched
2026-10-12 (after Budget 2027, 6 Oct 2026; before Finance Bill 2026).

**Status:** `enacted` = in an Act / S.I. or Revenue manual; `announced` =
Budget 2027, not yet law (re-check against Finance Act 2026); `unverified` =
secondary source only. Abbreviations: TCA = Taxes Consolidation Act 1997,
VATCA = VAT Consolidation Act 2010, FA = Finance Act, TDM = Revenue Tax and
Duty Manual, NfG = Revenue Notes for Guidance (FA 2025 edition), YTF = young
trained farmer, RFP = registered farm partnership, SFP = succession farm
partnership. `ST` sole trader, `P` partner, `Co` company.

Main sources: Revenue TDMs Part 23 (farming) and Part 9 (capital allowances);
NfG Parts 9, 11C, 23; irishstatutebook.ie (Finance Acts); DoF *Budget 2027 Tax
Policy Changes* (assets.gov.ie/static/documents/c6792805/Budget_2027_Tax_Policy_Changes_v2.pdf);
DSP *PRSI Contribution Rates and User Guide SW14* (Jan 2026); Revenue tax
credit and USC rate pages; Teagasc NFS 2025 report and dairy factsheet.

## 1. VAT

| rule_id | value | from | to | legal ref | status | applies |
|---|---|---|---|---|---|---|
| vat_fra | 5.4% | 2015-01-01 | 2020-12-31 | s.86 VATCA (FA2014 s.67) | enacted | flat-rate farmers |
| vat_fra | 5.6% | 2021-01-01 | 2021-12-31 | FA2020 s.40 | enacted | |
| vat_fra | 5.5% | 2022-01-01 | 2022-12-31 | FA2021 s.54 | enacted | |
| vat_fra | 5.0% | 2023-01-01 | 2023-12-31 | FA2022 s.56 | enacted | |
| vat_fra | 4.8% | 2024-01-01 | 2024-12-31 | F(No.2)A2023 s.62 | enacted | |
| vat_fra | 5.1% | 2025-01-01 | 2025-12-31 | FA2024 s.83 | enacted | |
| vat_fra | 4.5% | 2026-01-01 | 2026-12-31 | FA2025 s.73 | enacted | |
| vat_fra | 4.8% | 2027-01-01 | — | Budget 2027 §4.9 | announced | |
| vat_livestock_rate | 4.8% | pre-2020 | — | s.46(1)(d) VATCA | enacted | registered sellers, marts |
| vat_threshold_services | €42,500 | 2025-01-01 | — | FA2024 s.78 | enacted | agri contracting > this must register |
| vat_threshold_goods | €85,000 | 2025-01-01 | — | FA2024 s.78 | enacted | |

- **Flat-rate addition (FRA)** = % of the price of agricultural produce/services
  sold to a VAT-registered buyer (milk to co-op, cattle to factory). Computed on
  the **gross** milk price before contra deductions (feed bill etc.), not on
  non-agricultural items (e.g. transport). Not paid between two flat-rate
  farmers. Mart sales: the mart pays the FRA to the farmer. Source: TDM
  *Special flat-rate scheme for farmers* (rev. Jul 2026).
- **Flat-rate farmer** = not registered and not obliged to; pure agricultural
  production never obliges registration. A **company can be a flat-rate
  farmer** (s.4 "a person"; Teagasc — `unverified` against Revenue).
- Registration only for intra-EU acquisitions (> €41,000) or foreign services
  is ring-fenced: flat-rate status kept.
- Input VAT for flat-rate farmers is a cost (the FRA compensates it), except
  **VAT 58 refunds** (S.I. 201/2012) on farm buildings, fencing, drainage, land
  reclamation, micro-generation — not machinery.
- Input rates (reference only): feed 0%, fertiliser ≥10 kg 0%, oral vet
  medicines 0%, non-oral vet medicines 23% (non-oral respiratory vaccines → 9%
  in 2027, `announced`), machinery/building materials 23%, most agricultural
  contracting 13.5%.

## 2. Income tax, USC, PRSI (individuals)

| rule_id | 2024 | 2025 | 2026 | 2027 | ref | status |
|---|---|---|---|---|---|---|
| it_rate_standard / higher | 20% / 40% | same | same | same | TCA s.15 | enacted |
| it_band_single | 42,000 | 44,000 | 44,000 | 46,500 | s.15 | 2027 announced |
| it_band_one_parent | 46,000 | 48,000 | 48,000 | 50,500 | s.15 | 2027 announced |
| it_band_married_one_income | 51,000 | 53,000 | 53,000 | 55,500 | s.15 | 2027 announced |
| it_band_married_second_income_max | 33,000 | 35,000 | 35,000 | 37,500 | s.15 | 2027 announced |
| it_credit_personal_single | 1,875 | 2,000 | 2,000 | 2,125 | s.461 | 2027 announced |
| it_credit_personal_married | 3,750 | 4,000 | 4,000 | 4,250 | s.461 | 2027 announced |
| it_credit_earned_income | 1,875 | 2,000 | 2,000 | 2,125 | s.472AB | 2027 announced |
| it_credit_employee (PAYE) | 1,875 | 2,000 | 2,000 | 2,125 | s.472 | 2027 announced |

- Second-income band increase = min(max above, lower earner's income).
- Earned income credit (self-employed, farmers) + employee credit together are
  capped at the employee-credit amount.
- Other credits (single person child carer, home carer, rent) exist but are
  not modelled initially.

**USC** (TCA Part 18D, s.531AN)

| band | 2024 | 2025 | 2026 | 2027 (announced) |
|---|---|---|---|---|
| 0.5% | 0–12,012 | 0–12,012 | 0–12,012 | 0–12,012 |
| 2% | –25,760 | –27,382 | –28,700 | –30,300 |
| 4% (2024) / 3% (2025+) | –70,044 | –70,044 | –70,044 | –70,044 |
| 8% | above | above | above | above |

- Exempt if total income ≤ €13,000 (then USC on all income above it).
- +3% surcharge on non-PAYE income above €100,000 (11% band) — scope
  "above €100k only" is `unverified` (KPMG; Revenue page silent).
- Reduced rate (age 70+ or full medical card, income ≤ €60,000): 0.5% to
  12,012, 2% on the rest. Not modelled initially.

**PRSI Class S** (self-employed, proprietary directors; SWCA s.13 as amended by
SW(MP)A 2024)

| period | rate | status |
|---|---|---|
| to 2024-09-30 | 4.0% | enacted |
| 2024-10-01 → 2025-09-30 | 4.1% | enacted |
| 2025-10-01 → 2026-09-30 | 4.2% | enacted |
| 2026-10-01 → 2027-09-30 | 4.35% | enacted |
| 2027-10-01 → 2028-09-30 | 4.5% | enacted (schedule not opened directly) |
| from 2028-10-01 | 4.7% | enacted (schedule not opened directly) |

- Self-assessed annual rate = 9 months old + 3 months new: 2024 4.025%,
  2025 4.125%, 2026 4.2375%, 2027 4.3875% (last one our arithmetic).
- Applies when reckonable income ≥ €5,000; minimum contribution €650
  (2024 blended €537.50).
- Employer Class A (farm employees): 11.40% from 2026-10-01 (9.15% reduced
  rate) above a weekly threshold of €552 (2026), €600 (2027, announced).
  Wages are already an operating cost; employer PRSI is reference only.

## 3. Companies

| rule_id | value | ref | status |
|---|---|---|---|
| ct_rate_trading | 12.5% (farming is a trade) | TCA s.21 | enacted |
| ct_rate_non_trading | 25% (rent, interest) | s.21A | enacted |
| ct_close_surcharge | 20% on undistributed investment/estate income (after 7.5% reduction for trading cos; nil if ≤ €2,000; avoided by distributing within 18 months) | s.440 | enacted |
| ct_service_co_surcharge | does **not** apply to a farming company (not a profession/service) | s.441 | enacted (our reading) |
| dwt_rate | 25% withheld on dividends | s.172B | enacted |

- Company: general stock relief (25%) only; no YTF/RFP enhanced relief, no
  income averaging, no SFP credit. Capital allowances and FRA as individuals.
- Extraction (salary → PAYE + USC + Class S for proprietary directors with
  > 15%; dividends → marginal IT + USC + PRSI, DWT credited) is a later phase;
  summary is `unverified`.
- Teagasc *Farming Through a Company* (2018) is useful for structure (lease
  land to the company, directors' loan from assets at book value, tell DAFM and
  the milk processor) but its rates are stale.

## 4. Stock relief

| rule_id | value | base / limits | applies | to | ref | status |
|---|---|---|---|---|---|---|
| stock_relief_general | 25% | × (closing − opening trading stock) | ST, P, Co | Co: periods ending ≤ 2027-12-31; individuals: tax year 2027 | s.665, s.666; TDM 23-02-02 | enacted |
| stock_relief_ytf | 100% | year first qualifying + next 3; cap **€40,000/yr and €100,000 over the 4 years** of IT + USC saved | individuals | qualifying by 2027-12-31 | s.667B; TDM 23-02-01 | enacted |
| stock_relief_rfp | 50% (YTF partner: 100% for their 4 years) | partner's share of the increase; de minimis cap **€20,000 over rolling 3 years** of all agri de minimis aid | P (individuals) | periods ending ≤ 2027-12-31 | s.667C(3A); Reg. 1408/2013 | enacted |

- In the Engine tables these rules start on 2024-01-01: the start of the
  researched window, not when each relief began.
- **Trading stock** (s.665): livestock, crops, produce, direct inputs (feed,
  fertiliser, seed) — not machinery, diesel, tools. Values as in the accounts.
- Relief **cannot create or increase a loss**; model as
  `min(relief, profit before relief)`. In a claim year, losses and unused
  capital allowances brought forward cannot be carried on — report it.
- Claimed in writing by the return filing date.
- YTF qualifying: from 2007, under 35 at the start of the first year, holds a
  s.654A qualification (e.g. QQI L6 Farming / Dairy Herd Management), first
  time head of holding, micro/small enterprise, Teagasc business plan.
- **Young farmer State aid lifetime cap €100,000** (from 2024; was €70,000)
  across YTF stock relief, SFP credit and YTF stamp duty relief, measured as tax
  saved (Reg. (EU) 2022/2472 Art. 18(7); s.667B(7), s.667D(8)). The aid already
  used is history the Platform holds.

## 5. Capital allowances

| rule_id | value | base | applies | from / to | ref | status |
|---|---|---|---|---|---|---|
| ca_plant_wear_tear | 12.5%/yr × 8 yrs, straight line | cost − grants (s.317) − recoverable VAT; owned and in use at period end | all | post 2002 | s.284(2)(ad) | enacted |
| ca_farm_buildings | 15%/yr yrs 1–6, 10% yr 7 | net of grants (s.658(13)); buildings (not dwellings), yards, roads, fences, drains, reclamation, water, electrics | all | — | s.658; TDM 23-01-07 | enacted |
| ca_slurry_storage | 50%/yr × 2 yrs | buildings via s.658, Sch. 35A equipment via s.284; net of grants; cap €500k tax benefit; SME only | all | spend 2023-01-01 → 2029-12-31 | s.658A; TDM 23-01-37 | enacted |
| ca_farm_safety | 50%/yr × 2 yrs | DAFM-certified Sch. 35 items at DAFM reasonable cost, net of TAMS | all | spend 2021-01-01 → 2026-12-31 (law); → 2029-12-31 + 12 items | s.285D; TDM 09-02-07; Budget 2027 §4.10 | enacted / extension announced |
| ca_car_limit | €24,000 (A–B ≤140 g/km); C 141–155 min(€12k, 50%); D–F nil — from 2027: A ≤120 €24k, B 121–140 min(€12k, 50%), C–F nil | over 8 yrs; tractors/vans exempt | all | 2027 change enacted | s.380K–M | enacted |
| ca_balancing | allowance / charge = written-down value vs proceeds on sale or cessation; charge ≤ allowances given | | all | — | s.288 | enacted |

- **Capital grants (TAMS 3) are not income**: they reduce the qualifying cost.
  TAMS 3: 40% standard, 60% YTF; ceiling €90,000 per holding, €160,000 for an
  RFP with 2+ eligible partners (`unverified`, from T&C quotes).
- s.659 (pollution control) expired 2010 — use s.658A for slurry storage.

## 6. Income averaging (s.657; TDM 23-01-34)

- Assessable profit = **1/5 × (this year + previous 4 years)** of farming
  profit/loss **before** capital allowances and balancing charges; those are
  then applied on the current-year basis. Net 5-year loss → nil assessable,
  1/5 of the loss available for loss relief. USC and PRSI follow the averaged
  figure.
- Eligible: individuals (incl. partners) charged on farming for each of the
  previous 4 years. Off-farm trade / > 25% directorship no longer bars entry
  (since 2019). Not companies.
- Minimum 5 years in. Exit: the previous 4 years are topped up to the final
  averaged figure. Step-out: one year on actual profit once every 5 years;
  deferred tax paid in 4 equal instalments (all due on permanent exit).
  Re-entry after 4 years on the normal basis.
- A sole trade moving into an RFP continues for averaging (s.657(10A)).

## 7. Partnerships

- Transparent: profit computed as a sole trader (no deduction for partner
  salaries or interest), split by the **profit-sharing ratio** (not changeable
  retrospectively); each partner taxed on their share. Capital allowances and
  balancing charges shared. RFP: 2–10 members, DAFM register, written
  agreement ≥ 5 years. Young farmer partner ≥ 20% profit share.
- **SFP credit** (s.667D; TDM 23-02-11): per partner min(credit × profit
  share, partner's assessable profit after capital allowances), year of
  registration + 4 years; none in a year the successor is 40+ on 1 Jan.
  **€5,000/yr; €10,000/yr for SFPs registered from 2027-01-01** (`announced`),
  and the 3-year transfer wait is removed for applications from 2027.
  Counts towards the €100k young farmer cap.

## 8. Other farm items

- **Scheme payments** (BISS, CRISS, CISYF, eco-scheme, ACRES) are Case I
  trading income — earnings basis or receipts basis, used consistently (BPS
  TDM 23-01-35; ACRES by PQ; BISS by analogy, `unverified`). Dairy Beef
  Welfare by analogy, `unverified`.
- **Compulsory disposal of livestock** (s.668/669; TDM 23-02-07): profit
  spread over 4 periods; deemed 100% stock relief if replacements bought within
  4 years. Not modelled initially.
- **Carbon tax on farm diesel** (s.664A): extra deduction = (carbon rate −
  €41.30) per 1,000 L; €172.14 from 2025-05-01 → €130.84 extra per 1,000 L,
  next increase deferred to 2027-05-01. Not modelled initially.
- Out of scope: CGT (31% from 2026-10-07, announced), CAT, stamp duty,
  retirement relief, land-leasing exemption (landowner side).

## 9. Teagasc NFS definitions (NFS 2025 report, Appendix 4)

| term | definition |
|---|---|
| Gross output | Sales − livestock purchases + house use + hire/service receipts + net inventory change; **includes non-capital grants in the year paid** and land let income |
| Direct costs | Concentrates, bulky feed, fertiliser, crop protection, seed, contractors, transport, AI/vet, **casual labour**, levies, detergents, bulk tank rental, mart commission |
| Overhead costs | Conacre rent, car/electricity/phone, **regular hired labour**, **interest**, machinery and building depreciation and running costs, land improvement, insurance, accountancy, advisory |
| Family farm income (FFI) | Gross output − direct − overhead costs; no charge for own labour, owned land, own capital |
| Depreciation | Replacement cost, declining balance: machinery 10%, buildings 5% |
| Dairy total costs (c/L) | Direct + fixed costs, excluding family labour and decoupled payments; net margin = gross output/L − total costs/L |

Benchmarks (dairy enterprise, c/L): 2025 milk price 53.80, gross output 58.16,
direct 20.08, fixed 14.95, total 35.03, net margin 23.13 (282 farms). 2024:
total 35.65, net margin 17.60, milk price 51.57. Dairy FFI 2025 €154,988.
Imputed own labour 2025: 13c/L at €15/h … 26c/L at €30/h.

The Profit Monitor's own definitions are behind a login and not public.

## 10. Open items

1. Re-check every `announced` row against **Finance Act 2026** (Bill due
   15 Oct 2026).
2. Confirm the SW(MP)A 2024 PRSI schedule (4.5% / 4.7%) on irishstatutebook.
3. Current TDM 23-02-09 (RFP) is offline; the archived Oct 2023 copy is
   superseded by NfG FA2025 (end 2027, €20k cap, €100k lifetime).
4. ABER (Reg. 2022/2472) end date; corporate partner in an RFP and the 50% rate.
5. USC surcharge scope; BISS tax TDM; TAMS 3 T&Cs.
6. DoF Budget 2027 PDF says "4.8% (4.5% in 2025)" — typo; 4.5% is 2026 (FA2025).
