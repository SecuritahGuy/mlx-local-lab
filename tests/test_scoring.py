from local_mlx.schemas import CameraScene
from local_mlx.scoring import (
    abstained,
    camera_score,
    category_scores,
    hallucination_score,
    recommendations,
)


def test_abstention_and_unsupported_claim_scoring() -> None:
    assert abstained("INSUFFICIENT_EVIDENCE: firmware_version is missing.")
    assert abstained("The provided data does not contain enough information.")
    assert abstained("No firmware version is specified in the provided JSON.")
    assert abstained("It is not possible to determine that from this image.")
    assert abstained("It is **not possible** to determine that from this image.")
    assert abstained("The image lacks enough evidence to answer that.")
    assert hallucination_score("Cannot determine from the image.", True)["score"] == 1
    assert hallucination_score("The shirt is red.", True)["unsupported_claim_rate"] == 1


def test_camera_scoring_does_not_score_summary_wording() -> None:
    scene = CameraScene(scene_summary="Any wording", person_present=True, person_count=1,
                        package_present=True, vehicle_present=False, animal_present=False,
                        door_open=False, lighting="day", weather_visible="clear",
                        notable_objects=["box"], confidence=0.9, uncertain=[])
    truth = {"person_present": True, "person_count": 1, "package_present": True,
             "vehicle_present": False, "animal_present": False, "door_open": False,
             "lighting": "day", "weather_visible": "clear"}
    metrics = camera_score(scene, truth)
    assert metrics["object_presence_accuracy"] == 1
    assert metrics["object_count_accuracy"] == 1


def test_normalized_scores_and_recommendations() -> None:
    scores = category_scores([{"benchmark": "camera", "quality_score": 0.8},
                              {"benchmark": "camera", "quality_score": 0.6}])
    assert scores == {"camera": 7.0}
    assert not recommendations(scores)
