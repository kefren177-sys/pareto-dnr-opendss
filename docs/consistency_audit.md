# Consistency Audit

No differences exceeded the defined manuscript rounding tolerances.

| case | metric | manuscript_value | repository_value | absolute_difference | tolerance | status |
|---|---:|---:|---:|---:|---:|---|
| five_node | base P_loss_kW | 418.91 | 418.911044 | 0.001044 | 0.01 | OK |
| five_node | base SAIDI_h_user_year | 14.616 | 14.616456 | 0.000456 | 0.001 | OK |
| five_node | base Vmin_pu | 0.835 | 0.834747 | 0.000253 | 0.001 | OK |
| five_node | optimum P_loss_kW | 309.77 | 309.765368 | 0.004632 | 0.01 | OK |
| five_node | optimum SAIDI_h_user_year | 8.981 | 8.981013 | 0.000013 | 0.001 | OK |
| five_node | optimum Vmin_pu | 0.886 | 0.885523 | 0.000477 | 0.001 | OK |
| ieee33 | base P_loss_kW | 185.68 | 185.680636 | 0.000636 | 0.01 | OK |
| ieee33 | base SAIDI_h_user_year | 3.846 | 3.846095 | 0.000095 | 0.001 | OK |
| ieee33 | min_loss P_loss_kW | 137.34 | 137.340382 | 0.000382 | 0.01 | OK |
| ieee33 | min_loss SAIDI_h_user_year | 3.355 | 3.355444 | 0.000444 | 0.001 | OK |
| ieee33 | min_loss Vmin_pu | 0.937 | 0.937046 | 0.000046 | 0.001 | OK |
| ieee33 | min_SAIDI P_loss_kW | 142.10 | 142.095806 | 0.004194 | 0.01 | OK |
| ieee33 | min_SAIDI SAIDI_h_user_year | 2.999 | 2.999030 | 0.000030 | 0.001 | OK |
| ieee33 | min_SAIDI Vmin_pu | 0.927 | 0.927233 | 0.000233 | 0.001 | OK |
| ieee33 | compromise P_loss_kW | 137.63 | 137.634008 | 0.004008 | 0.01 | OK |
| ieee33 | compromise SAIDI_h_user_year | 3.019 | 3.018552 | 0.000448 | 0.001 | OK |
| ieee33 | compromise Vmin_pu | 0.932 | 0.932267 | 0.000267 | 0.001 | OK |
| real_system_anonymized | n_nodes | 110 | 110 | 0 | 0 | OK |
| real_system_anonymized | n_lines | 131 | 131 | 0 | 0 | OK |
| real_system_anonymized | n_open_required | 22 | 22 | 0 | 0 | OK |
| real_system_anonymized | users_used_for_reliability | 43069 | 43069 | 0 | 0 | OK |
| real_system_anonymized | base P_loss_kW | 1397.03 | 1397.026080 | 0.003920 | 0.01 | OK |
| real_system_anonymized | base SAIDI_h_user_year | 5.765 | 5.765255 | 0.000255 | 0.001 | OK |
| real_system_anonymized | base SAIFI_int_user_year | 15.756 | 15.756368 | 0.000368 | 0.001 | OK |
| real_system_anonymized | base ENS_MWh_year | 118.507 | 118.507202 | 0.000202 | 0.001 | OK |
| real_system_anonymized | base Vmin_pu | 0.826 | 0.825557 | 0.000443 | 0.001 | OK |
| real_system_anonymized | min_loss P_loss_kW | 841.42 | 841.417905 | 0.002095 | 0.01 | OK |
| real_system_anonymized | min_loss SAIDI_h_user_year | 4.807 | 4.806723 | 0.000277 | 0.001 | OK |
| real_system_anonymized | min_loss Vmin_pu | 0.918 | 0.917877 | 0.000123 | 0.001 | OK |
| real_system_anonymized | min_SAIDI P_loss_kW | 927.74 | 927.735447 | 0.004553 | 0.01 | OK |
| real_system_anonymized | min_SAIDI SAIDI_h_user_year | 4.339 | 4.339299 | 0.000299 | 0.001 | OK |
| real_system_anonymized | min_SAIDI Vmin_pu | 0.898 | 0.898405 | 0.000405 | 0.001 | OK |
| real_system_anonymized | compromise P_loss_kW | 856.42 | 856.421978 | 0.001978 | 0.01 | OK |
| real_system_anonymized | compromise SAIDI_h_user_year | 4.413 | 4.412753 | 0.000247 | 0.001 | OK |
| real_system_anonymized | compromise SAIFI_int_user_year | 12.060 | 12.059997 | 0.000003 | 0.001 | OK |
| real_system_anonymized | compromise ENS_MWh_year | 95.775 | 95.775287 | 0.000287 | 0.001 | OK |
| real_system_anonymized | compromise Vmin_pu | 0.914 | 0.913607 | 0.000393 | 0.001 | OK |

## Notes

- The anonymized real system reports 43069 users because this is the denominator used by the current reliability calculation.
- The original working article table previously included slack/source placeholder users; the clean repository reports users considered in reliability calculations.
- IEEE33 `min_SAIDI` uses the corrected tie-break rule: among solutions within `1e-9 h/customer-year` of the minimum SAIDI, the representative solution is the one with lower active power losses. This selects `7,10,14,27,36` rather than the earlier `6,10,13,27,36`.
- The complete evaluated-solution cloud for the anonymized real system is not included in the clean repository. Public traceability is provided through representative solutions, summarized results, and Pareto fronts.
- OpenDSS is used as an electrical evaluator, not as an optimizer.
- Thermal limits are not asserted because traceable ratings are unavailable.
