from root.impacts.emissions import GHGCalculator
import pytest

class TestGHGCalculator:
    
    @pytest.fixture
    def calc(self):
        return GHGCalculator(region="US", currency="usd")
    
    @pytest.mark.parametrize(
        "id, value, unit, unit_type",
        [
            ("textiles-type_textiles", 10, None, "money"),
            # ("energy-source") TODO: add a test for each unit_type
        ]
    )
    def test__call__(self, id, value, unit, unit_type, calc):
        res = calc(activity_id=id, value=value, unit=unit, unit_type=unit_type)
        assert res.keys() & {"co2e", "co2", "n2o", "ch4"}
    