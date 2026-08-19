import pytest
from pydantic import ValidationError

from local_mlx.schemas import CameraScene, TemporalAnalysis


def test_camera_confidence_is_bounded() -> None:
    with pytest.raises(ValidationError):
        CameraScene(scene_summary="x", person_present=False, person_count=0,
                    package_present=False, vehicle_present=False, animal_present=False,
                    door_open=False, lighting="day", weather_visible="clear",
                    notable_objects=[], confidence=1.2, uncertain=[])


def test_temporal_schema() -> None:
    value = TemporalAnalysis.model_validate({"changes": [{"type": "object_appeared",
        "object": "package", "first_seen": "08:15"}], "summary": "Package appeared.",
        "confidence": 0.9})
    assert value.changes[0].first_seen == "08:15"
