# Data Provenance and Limitations

## Five-Node System

- Type: synthetic validation case.
- Data source in repository: built-in case definition in `src/dnr/cases.py` and `configs/cases.yml`.
- Purpose: algorithmic/control validation.
- Voltage-feasibility note: the controlled optimum has `Vmin < 0.90 p.u.`, so it is not voltage-feasible under the manuscript voltage criterion.

## IEEE 33-Node System

- Type: public benchmark distribution system.
- Released input: `data/ieee33/case33.m`.
- OpenDSS model generation: handled by the code in `src/dnr/dss_writer.py` during evaluation.
- Reliability inputs: released benchmark configuration uses the documented default reliability parameters in `configs/cases.yml`.
- Full public rerun: supported when OpenDSSDirect.py and a compatible OpenDSS backend are available.

## Anonymized Real Distribution System

- Type: operator-derived real distribution system, anonymized for publication.
- Public structural data:
  - `docs/real_system/real_system_annex_C_data.xlsx`;
  - `docs/real_system/anonymized_real_system_topology.pdf`;
  - `docs/real_system/anonymized_real_system_topology.svg`;
  - `docs/real_system/anonymized_real_system_topology_600dpi.png`.
- Public results:
  - `results/real_system_anonymized/representative_solutions.csv`;
  - `results/real_system_anonymized/pareto_feasible.csv`;
  - `results/real_system_anonymized/pareto_operationally_feasible.csv`;
  - `results/real_system_anonymized/summarized_results.csv`.

The real-system public data package documents:

- 131 line sections;
- 109 feeder sections;
- 22 reconfigurable interconnections;
- 109 load nodes;
- load nodes 2 to 110;
- total active demand of 20,849.76 kW;
- total reactive demand of 10,098.05 kVAr;
- reported apparent demand of 23,166.42 kVA;
- power factor of 0.9;
- total customers of 43,068 in Annex C.

The sum of individually rounded apparent-power values in Annex C gives 23,166.40 kVA, whereas the source table reports 23,166.42 kVA. The repository preserves the source total and documents the difference as rounding.

## Reliability Provenance

- Demand data: operator-derived and anonymized in Annex C.
- Customer data: operator-derived and anonymized in Annex C.
- Failure rates: restricted/private source for the real-system optimization; not fully published in the anonymized package.
- Mean repair time: the code parameter `repair_time_hours = 0.3659` is used as a mean repair time. It should not be described as restoration time unless supported by additional source evidence.

## Operational Limitations

The public repository does not provide traceable branch-level thermal ratings or ampacities for the real system. Therefore:

- no thermal feasibility claim is made;
- no branch loading constraint is asserted;
- line ratings are not inferred;
- protection coordination is not modeled;
- switching sequences are not validated;
- source-capacity checks beyond the OpenDSS power-flow model are not claimed;
- full field-operability beyond modeled topology and voltage constraints is not claimed.

The historical result field `operationally_feasible` and files named `pareto_operationally_feasible.csv` are retained for compatibility with the analysis pipeline. For the released real-system data, they should be interpreted as voltage-feasible under the modeled constraints, with no failed topology/load-supply checks and no available thermal-rating violation. They should not be interpreted as proof of complete operational readiness.

## Reproducibility Boundary

The five-node and IEEE 33-node cases are public rerun cases. The real-system case is a public verification and traceability package, not a full public rerun package, because original operator files and restricted reliability inputs are excluded.
