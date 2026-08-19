from local_mlx.benchmark import apply_context, load_cases, score_legacy
from local_mlx.schemas import SecurityReview


def test_all_required_categories_have_cases() -> None:
    cases = load_cases()
    categories = {case["benchmark"] for case in cases}
    assert categories == {
        "coding",
        "cybersecurity",
        "instruction_following",
        "rag",
        "reasoning",
        "structured_output",
    }
    assert len(cases) >= 21


def test_rag_cases_use_fixed_document() -> None:
    cases = load_cases(["rag"])
    assert all("[P4]" in case["prompt"] for case in cases)


def test_rag_context_materially_scales_prompt() -> None:
    case = load_cases(["rag"])[0]
    sizes = [len(apply_context(case, context)["prompt"]) for context in (2048, 8192, 16384)]
    assert sizes[0] < sizes[1] < sizes[2]
    assert sizes[2] > 40_000


def test_rag_quality_checks_grounding() -> None:
    case = load_cases(["rag"])[0]
    assert score_legacy(case, "Tuesday at 15:00 UTC [P1]", None) == 1
    assert score_legacy(case, "I do not know", None) == 0


def test_security_schema() -> None:
    value = SecurityReview.model_validate(
        {
            "summary": "Risk exists.",
            "remediations": [
                {"severity": "high", "finding": "No MFA", "recommendation": "Require MFA"}
            ],
        }
    )
    assert value.remediations[0].severity == "high"
