# Anonymized Real Distribution-System Documentation

This directory contains the public documentation package for the anonymized real distribution system.

## Files

- `anonymized_real_system_topology.pdf`: topology exported from AutoCAD. This is the graphical reference.
- `anonymized_real_system_topology.svg`: vector export of the same anonymized topology.
- `anonymized_real_system_topology_600dpi.png`: high-resolution raster export of the same topology.
- `real_system_annex_C_data.xlsx`: structured Annex C data package prepared for repository publication.

## Topological Convention

The topology uses anonymized identifiers only:

- substations: `S/E 10`, `S/E 20`, `S/E 30`;
- feeders/circuits: `11`, `12`, `13`, `21`, `22`, `31`, `32`, `33`, `34`;
- line sections: `S-1` to `S-131`;
- feeder sections: `S-1` to `S-109`;
- reconfigurable interconnections: `S-110` to `S-131`.

In the graphical topology, red dashed lines identify the 22 reconfigurable links.

## Public Structural Counts

From `real_system_annex_C_data.xlsx`:

- line sections: 131;
- feeder sections: 109;
- reconfigurable interconnections: 22;
- load nodes: 109;
- load-node range: 2 to 110;
- total active demand: 20,849.76 kW;
- total reactive demand: 10,098.05 kVAr;
- reported apparent demand: 23,166.42 kVA;
- total customers: 43,068;
- power factor: 0.9.

The sum of rounded individual apparent-power values is 23,166.40 kVA. The source total of 23,166.42 kVA is preserved.

## Confidentiality Boundary

The files do not contain real geographic names, commercial identifiers, operator names, original internal feeder names, coordinates, or original operator documents. They are intended for manuscript traceability and public verification of aggregated/representative results.
