from root.mock import TempModelTools
from numbers import Number
import numpy as np
import pytest

parametrize = pytest.mark.parametrize

@pytest.mark.omit
class TestModelTools:
    
    @pytest.fixture(scope="class")
    def tools(self, database):
        savior_id = "__TESTUSER__"
        model_tools = TempModelTools(
            savior_id=savior_id,
            embeddings_generator=lambda text: np.random.randn(1536)
        )
        helpers = {
            "savior_id": savior_id,
            "activity_unit": "usd",
            "emission_logs_fields": database.logs.find_one().keys(),
            "pledge_fields": database.pledges.find_one().keys(),
        }
        return model_tools, helpers, database
    
    @staticmethod 
    def assert_reponse_made(result):
        assert result[0].isdigit()
        assert result.endswith("Kilograms CO2e")    
    
    # #TODO: we can end up doing really extensive testing by comparing activity query to activity id once we have emission factors
    @parametrize(
        "update_user_emissions",
        ((False), (True))
    )
    def test_calculate_emissions(self, update_user_emissions, tools):
        model_tools, helpers, db = tools
        result = model_tools.calculate_emissions(
            activity= "__UNITTESTING__",
            activity_value=1,
            activity_unit="money",
            update_user_emissions=update_user_emissions,
        )
        if update_user_emissions:
            post_update, pre_update = tuple(
            db.logs.find(
                {"savior_id": helpers["savior_id"]},
                sort=[("date", -1)], limit=2
            ))
            assert np.greater(
                post_update["current_emissions"], pre_update["current_emissions"]
            )
        else:
            self.assert_reponse_made(result=result)
        
    @parametrize(
        "period, time_delta, from_tool_call",
        (
            ("current", None, False), 
            ("historical", None, True),
            (None, {"weeks": 2, "days": 1}, True)
        )
    )
    def test_get_user_emissions(self, period, time_delta, from_tool_call, tools):
        model_tools, _, _ = tools
        result = model_tools.get_user_emissions(
            period=period, time_delta=time_delta, from_tool_call=from_tool_call
        )
        if from_tool_call:
            self.assert_reponse_made(result)
        else: 
            assert isinstance(result, Number)
            
    def test_make_pledge(
        self,
        activity,
        activity_unit, 
        pledge_frequency,
        pledge_name
    ) -> None:
        model_tools, helpers, db = model_tools
        pledges = db.pledges
        count = lambda:  pledges.count_documents({"savior_id": helpers["savior_id"]})
        before_count = count()
        res = model_tools.make_pledge(
            activity=activity, 
            activity_unit=activity_unit, 
            pledge_name=pledge_name,
            pledge_frequency=pledge_frequency
        )
        after_count = count()
        assert after_count > before_count
        assert isinstance(res, str) 
        assert all(map(lambda x: x in res, ["Success", "Pledge name", "Impact"]))
        
        
    
    @parametrize(
        "pledge_names",
        ((["__TESTPLEDGENAME__"]), ([]))
    )
    def test_get_pledge_impacts(self, pledge_names, tools, cleanup_files):
        model_tools, _, _ = tools
        print(pledge_names)
        impacts = model_tools.get_pledge_impacts(pledge_names=pledge_names)
        if impacts:
            impacts = impacts[0]
            assert impacts.keys() == {"pledge_name", "impact"}
            cleanup_files(["testing.mp3"])
        
        
        
        
        
        
            
        
        
    
        
        
    