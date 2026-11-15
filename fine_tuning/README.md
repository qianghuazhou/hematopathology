# Hematopathology AI fine-tuning — dataset preparation v1.0

Status: **Dataset preparation only. No model training or clinical validation has been performed.**

## Source audit (2026-11-15)

The following source files were fetched and inspected from the repository. Sizes are approximate character counts of HTML source, **not counts of usable independent examples**.

| File | Approx. characters | Role |
| --- | ---: | --- |
| bone_marrow_reporting_template_v18.html | 167,841 | BM report generator |
| bone_marrow_synoptic_who5_with_dx_v14.html | 69,172 | WHO5 BM synoptic |
| bm_report_tool_uhn_style_v2.html | 28,076 | Alternative BM style |
| cbc_smear_comment_generator_v91.html | 51,764 | CBC/smear reporting (page title says v92) |
| flow_cytometry_reporting_tool.html | 142,261 | Flow reporting |
| lymph_node_morphology_generator.html | 46,194 | Morphology phrases |
| lymph_node_reporting_workspace_v1.html | 45,926 | Lymph node workspace |
| dr_delabie_style_lymphoma_generator_v16.html | 56,567 | Lymphoma prose |
| lymphoma_synoptic_generator_who5_v34.html | 103,386 | Lymphoma synoptic |
| hodgkin_synoptic_generator_v16.html | 51,226 | Hodgkin synoptic |
| heme_bodyfluid_comment_generator.html | 20,514 | Body fluid comments |
| integrated_hematopathology_cytology.html | 35,473 | Cytology |
| Comments.txt | 6,822 | General comments |
| diagnosis_templates_v3.html | 8,854 | Template index |

Workspace pages are wrappers: bone_marrow_workspace.html points to three actual tools; lymphoma_reporting_workspace.html points to four. Do not mistake wrappers for training material.

## Audit conclusion

The repository has substantial structured and prose material, but source-file sizes and selectable choices do not establish the number of medically distinct, complete input-to-output examples. No claim is made that 200 usable pairs already exist.

## Workflow

1. Clone the repository locally. Run `python fine_tuning/extract_candidates.py --repo . --out private_candidates.jsonl`.
2. Review extracted **candidates**. They are not labeled training pairs. Do not train directly on them.
3. For each approved example, write a JSONL object containing `id`, `category`, `source_file`, `review_status`, `source_findings`, `expected_checks`, and `messages` (system, user, assistant).
4. Keep one clinical case/family in only one of train, validation or test to avoid leakage. Remove duplicates and near-duplicates.
5. Run `python fine_tuning/validate_reports.py --data curated.jsonl` to check schema, basic leakage, expected exact strings and expected negative/positive markers.
6. Have a pathologist verify each source-to-target mapping. A passing automated check does **not** establish diagnostic correctness.
7. Establish baseline performance on an unseen test set before LoRA training.

## Suggested pilot

Start with 20 reviewed **synthetic** examples covering DLBCL, follicular lymphoma, reactive lymphoid hyperplasia, marrow myeloid disorders, plasma cell neoplasms, peripheral blood and flow. Expand to ~100–200 reviewed pairs if pilot performance and diversity warrant it. These are planning targets, not current dataset counts.

## Security

The repository is public. **Do not commit patient-derived reports, PHI, confidential clinical material, or patient-derived adapters/checkpoints.** Keep any real-data extraction and training in an approved institutional environment. Add local dataset outputs to .gitignore or keep them outside the repo. Human sign-out and deterministic source-to-output checks remain mandatory.
