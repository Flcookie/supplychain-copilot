# Data Dictionary｜Ratti Supplier Lifecycle Copilot

## category_rules

| Field | Type | Meaning | Source/Logic | Simulated? | Example |
|---|---|---|---|---|---|
| category_level_1 | TEXT | First-tier category | Ratti project | No |  |
| category_level_2 | TEXT | Second-tier category | Ratti project | No |  |
| kraljic_quadrant | TEXT | Category segmentation | Ratti project Kraljic logic | No |  |
| monitoring_frequency | TEXT | Recommended review frequency | Ratti project | No |  |
| required_documents | TEXT | Documents required by category | Derived from project logic | Partly |  |
| default_weight_operational | INTEGER | Vendor rating operational weight | Project proposal / category logic | Partly |  |
| default_weight_risk | INTEGER | Vendor rating risk weight | Project proposal / category logic | Partly |  |
| default_weight_esg | INTEGER | Vendor rating ESG weight | Project proposal / category logic | Partly |  |

## delivery_events

| Field | Type | Meaning | Source/Logic | Simulated? | Example |
|---|---|---|---|---|---|
| delivery_id | TEXT PK | Delivery record ID | Synthetic demo table; derived where applicable | Yes |  |
| po_id | TEXT FK | Linked purchase order | Synthetic demo table; derived where applicable | Yes |  |
| supplier_id | TEXT FK | Linked supplier | Synthetic demo table; derived where applicable | Yes |  |
| delivery_delay_days | INTEGER | Actual delivery delay | Synthetic demo table; derived where applicable | Yes |  |
| on_time_flag | INTEGER | Whether delivery is on time | Synthetic demo table; derived where applicable | Yes |  |

## documents

| Field | Type | Meaning | Source/Logic | Simulated? | Example |
|---|---|---|---|---|---|
| document_id | TEXT PK | Document metadata ID | Synthetic demo table; derived where applicable | Yes |  |
| supplier_id | TEXT FK | Linked supplier | Synthetic demo table; derived where applicable | Yes |  |
| document_type | TEXT | Type of supplier document | Synthetic demo table; derived where applicable | Yes |  |
| expiry_date | DATE | Document expiry date | Synthetic demo table; derived where applicable | Yes |  |
| document_status | TEXT | Document validity status | Synthetic demo table; derived where applicable | Yes |  |
| ai_extraction_confidence | REAL | Confidence from document parser | Synthetic demo table; derived where applicable | Yes |  |
| manual_validation_required | TEXT | Whether buyer must validate | Synthetic demo table; derived where applicable | Yes |  |

## esg_assessments

| Field | Type | Meaning | Source/Logic | Simulated? | Example |
|---|---|---|---|---|---|
| supplier_id | TEXT FK | Supplier | Synthetic demo table; derived where applicable | Yes |  |
| environmental_score_0_100 | REAL | Environmental compliance score | Synthetic demo table; derived where applicable | Yes |  |
| social_score_0_100 | REAL | Social compliance score | Synthetic demo table; derived where applicable | Yes |  |
| governance_score_0_100 | REAL | Governance compliance score | Synthetic demo table; derived where applicable | Yes |  |
| final_esg_score | REAL | E*0.4 + S*0.3 + G*0.3 | Synthetic demo table; derived where applicable | Yes |  |

## purchase_orders

| Field | Type | Meaning | Source/Logic | Simulated? | Example |
|---|---|---|---|---|---|
| po_id | TEXT PK | Purchase order ID | Synthetic demo table; derived where applicable | Yes |  |
| supplier_id | TEXT FK | Supplier linked to PO | Synthetic demo table; derived where applicable | Yes |  |
| order_date | DATE | PO creation date | Synthetic demo table; derived where applicable | Yes |  |
| expected_delivery_date | DATE | Expected delivery date | Synthetic demo table; derived where applicable | Yes |  |
| actual_delivery_date | DATE | Actual delivery date | Synthetic demo table; derived where applicable | Yes |  |
| order_amount_eur | REAL | PO amount in EUR | Synthetic demo table; derived where applicable | Yes |  |

## quality_events

| Field | Type | Meaning | Source/Logic | Simulated? | Example |
|---|---|---|---|---|---|
| quality_event_id | TEXT PK | Quality issue ID | Synthetic demo table; derived where applicable | Yes |  |
| po_id | TEXT FK | Linked PO | Synthetic demo table; derived where applicable | Yes |  |
| supplier_id | TEXT FK | Linked supplier | Synthetic demo table; derived where applicable | Yes |  |
| non_conformity_type | TEXT | Quality issue category | Synthetic demo table; derived where applicable | Yes |  |
| severity | TEXT | Quality severity | Synthetic demo table; derived where applicable | Yes |  |
| defect_rate | REAL | Defects / inspection quantity | Synthetic demo table; derived where applicable | Yes |  |

## risk_events

| Field | Type | Meaning | Source/Logic | Simulated? | Example |
|---|---|---|---|---|---|
| risk_event_id | TEXT PK | Risk event ID | Synthetic demo table; derived where applicable | Yes |  |
| supplier_id | TEXT FK | Linked supplier | Synthetic demo table; derived where applicable | Yes |  |
| risk_type | TEXT | Risk category | Synthetic demo table; derived where applicable | Yes |  |
| likelihood_1_5 | INTEGER | Risk likelihood | Synthetic demo table; derived where applicable | Yes |  |
| impact_1_5 | INTEGER | Risk impact | Synthetic demo table; derived where applicable | Yes |  |
| recommended_action | TEXT | Suggested mitigation | Synthetic demo table; derived where applicable | Yes |  |

## suppliers

| Field | Type | Meaning | Source/Logic | Simulated? | Example |
|---|---|---|---|---|---|
| supplier_id | TEXT PK | Anonymized unique supplier identifier | Generated for demo | Yes | SUP001 |
| supplier_name_anonymized | TEXT | Masked supplier name for demo | Synthetic anonymization | Yes | Supplier_Yarns_IT_001 |
| sap_supplier_code | TEXT | SAP supplier code placeholder | Simulated based on Ratti SAP-code concept | Yes | RATTI-10001 |
| country | TEXT | Supplier commercial location | Synthetic distribution, Italy-heavy to reflect Ratti context | Yes | Italy, China, Germany |
| category_level_1 | TEXT | First-tier procurement macro-category | Ratti project category structure | No | Goods, Services, Transportation, Fixed Assets, Manufacturing |
| category_level_2 | TEXT | Second-tier category | Ratti project category tree/Kraljic logic | No | Yarns, Fabrics |
| kraljic_quadrant | TEXT | Category segmentation | Derived from project Kraljic table | No | Strategic/Bottleneck/Leverage/Non-Critical |
| monitoring_frequency | TEXT | Review frequency | Derived from category rules | No | Quarterly/Semi-annual/Annual |
| qualification_status | TEXT | Supplier lifecycle status | Synthetic but aligned with target statuses | Partly | Qualified, Qualified with Reserve, Risky, Not Qualified, Blacklisted |
| annual_spend_eur | INTEGER | Estimated annual supplier spend | Synthetic | Yes |  |
| supply_risk_score | REAL | Composite risk score, higher is worse | Synthetic weighted risk | Yes | 0-100 |
| next_review_date | DATE | Next scheduled review date | Derived from last review + frequency | Yes | YYYY-MM-DD |

## vendor_rating

| Field | Type | Meaning | Source/Logic | Simulated? | Example |
|---|---|---|---|---|---|
| supplier_id | TEXT FK | Supplier | Synthetic demo table; derived where applicable | Yes |  |
| on_time_delivery_rate_pct | REAL | OTD rate | Synthetic demo table; derived where applicable | Yes |  |
| quality_defect_rate_pct | REAL | Quality defect rate | Synthetic demo table; derived where applicable | Yes |  |
| operational_score | REAL | Operational performance score | Synthetic demo table; derived where applicable | Yes |  |
| risk_inverse_score | REAL | 100 - supply_risk_score | Synthetic demo table; derived where applicable | Yes |  |
| final_vendor_rating_score | REAL | Weighted score | Synthetic demo table; derived where applicable | Yes |  |
| rating_class | TEXT | A/B/C/D rating | Synthetic demo table; derived where applicable | Yes |  |

