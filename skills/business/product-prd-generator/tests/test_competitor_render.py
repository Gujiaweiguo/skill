from product_prd_generator.competitor_render import Capability, render_competitor_feature_list


def test_render_competitor_feature_list_excludes_capabilities_without_competitor_evidence():
    capabilities: list[Capability] = [
        {
            "name": "lease contract management",
            "reconciled_status": "existing",
            "confidence": "high",
            "evidence": [
                {"kind": "spec", "ref": "openspec/specs/lease-contract-management/spec.md"},
                {"kind": "doc", "ref": "02-competitors/海鼎/合同管理.md"},
                {"kind": "image", "ref": "02-competitors/海鼎/合同管理_media/image1.png"},
            ],
        },
        {
            "name": "customer-only capability",
            "reconciled_status": "missing",
            "confidence": "low",
            "evidence": [
                {"kind": "doc", "ref": "01-customer-requirements/客户A/需求.md"},
            ],
        },
    ]

    rendered = render_competitor_feature_list(capabilities)

    assert "lease contract management" in rendered
    assert "customer-only capability" not in rendered
    assert "共 1 项归一化能力" in rendered
    assert "02-competitors/海鼎/合同管理.md" in rendered
